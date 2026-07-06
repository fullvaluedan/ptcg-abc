"""Unit tests for the U101 invariant fuzzer checkers (tools/fuzz_invariants.py).

Handcrafted synthetic state dicts only: no native engine, no competition data.
Each invariant gets a clean case and a violating case, and malformed states
are skipped, never raised.
"""
import json

from tools import fuzz_invariants as fz


# ---------------------------------------------------------------------------
# Synthetic state builders.
# ---------------------------------------------------------------------------

_SERIAL = [0]


def _next_serial():
    _SERIAL[0] += 1
    return _SERIAL[0]


def card(serial=None, cid=100, player=0):
    return {"id": cid, "serial": _next_serial() if serial is None else serial,
            "playerIndex": player}


def pokemon(serial=None, cid=200, hp=100, max_hp=100, energy=0, tools=0, pre=0):
    return {
        "id": cid,
        "serial": _next_serial() if serial is None else serial,
        "hp": hp,
        "maxHp": max_hp,
        "energyCards": [card() for _ in range(energy)],
        "tools": [card() for _ in range(tools)],
        "preEvolution": [card() for _ in range(pre)],
    }


def player_state(deck=41, hand_n=5, discard_n=2, prize_n=6, active=None,
                 bench=None, bench_max=5):
    return {
        "deckCount": deck,
        "hand": [card() for _ in range(hand_n)],
        "handCount": hand_n,
        "discard": [card() for _ in range(discard_n)],
        "prize": [None] * prize_n,  # facedown prizes are None slots
        "active": [pokemon(energy=2) if active is None else active],
        "bench": [pokemon(tools=1, pre=1)] if bench is None else bench,
        "benchMax": bench_max,
    }


def make_state(seat=0, turn=3, result=-1, me=None, opp=None, **extra):
    # Default own side sums to exactly 60:
    # 41 deck + 5 hand + 2 discard + 6 prize slots
    # + active (1 + 2 energy) + bench (1 + 1 tool + 1 preEvolution) = 60
    players = [None, None]
    players[seat] = player_state() if me is None else me
    players[1 - seat] = player_state() if opp is None else opp
    state = {
        "turn": turn,
        "yourIndex": seat,
        "result": result,
        "players": players,
        "stadium": [],
        "looking": None,
    }
    state.update(extra)
    return state


# ---------------------------------------------------------------------------
# I1: own-side card conservation.
# ---------------------------------------------------------------------------


def test_own_total_counts_attachments_and_facedown_prizes():
    state = make_state()
    total, comp = fz.compute_own_total(state, 0)
    assert total == 60
    assert comp == {"deckCount": 41, "hand": 5, "discard": 2, "prizeSlots": 6,
                    "inPlay": 6, "stadium": 0}


def test_own_total_counts_own_stadium_and_facedown_active():
    me = player_state(active=None, bench=[])
    me["active"] = [None]  # facedown active still occupies one card
    state = make_state(me=me, stadium=[card(player=0), card(player=1)])
    total, _ = fz.compute_own_total(state, 0)
    # 41 + 5 + 2 + 6 + 1 facedown active + 1 own stadium (opp stadium excluded)
    assert total == 56


def test_own_total_skips_non_empty_looking_zone():
    state = make_state(looking=[card()])
    total, reason = fz.compute_own_total(state, 0)
    assert total is None
    assert reason == "looking_active"


def test_own_total_malformed_is_skipped_not_raised():
    assert fz.compute_own_total({}, 0)[0] is None
    assert fz.compute_own_total({"players": "nope"}, 0)[0] is None
    assert fz.compute_own_total(make_state(), 7)[0] is None
    bad = make_state()
    bad["players"][0]["deckCount"] = "forty"
    assert fz.compute_own_total(bad, 0) == (None, "malformed_deckCount")


def test_i1_enforcement_flags_deviation_from_calibrated_total():
    calib = fz.Calibration()
    calib.observe(make_state(), 0)
    calib.finalize()
    assert calib.i1_enabled and calib.allowed_totals[(0, "plain")] == {60}

    checker = fz.FuzzChecker(calibration=calib)
    checker.enforce()
    tracker = fz.GameTracker("t:0", 0, "test")
    missing = make_state(me=player_state(deck=40))  # one card vanished
    checker.observe({"current": missing}, tracker)
    i1 = [v for v in checker.violations if v["invariant"] == "I1"]
    assert len(i1) == 1
    assert i1[0]["detail"]["total"] == 59
    assert i1[0]["detail"]["expected"] == [60]

    clean_tracker = fz.GameTracker("t:1", 0, "test")
    clean_checker = fz.FuzzChecker(calibration=calib)
    clean_checker.enforce()
    clean_checker.observe({"current": make_state()}, clean_tracker)
    assert clean_checker.violations == []


def test_i1_calibration_is_context_keyed():
    # Plain states calibrate to 60; effect-resolution states legally dip to 59
    # (the resolving card sits in no zone). The same 59 that is clean during
    # effect resolution is a violation in a plain state.
    calib = fz.Calibration()
    calib.observe(make_state(), 0)  # plain, total 60
    calib.observe(make_state(me=player_state(deck=40)), 0, context="effect")  # 59
    calib.finalize()
    assert calib.allowed_totals[(0, "plain")] == {60}
    assert calib.allowed_totals[(0, "effect")] == {59}

    checker = fz.FuzzChecker(calibration=calib)
    checker.enforce()
    effect_obs = {
        "current": make_state(me=player_state(deck=40)),
        "select": {"effect": {"id": 5, "serial": 9999, "playerIndex": 0}},
    }
    checker.observe(effect_obs, fz.GameTracker())
    assert [v for v in checker.violations if v["invariant"] == "I1"] == []

    checker.observe({"current": make_state(me=player_state(deck=40))}, fz.GameTracker())
    i1 = [v for v in checker.violations if v["invariant"] == "I1"]
    assert len(i1) == 1
    assert i1[0]["detail"]["context"] == "plain"


def test_i1_uncalibrated_effect_context_enforces_structural_bimodal():
    # Effect contexts are verified structurally bimodal on the real engine
    # (own-side total 59 while the context card is held out of zone, else 60),
    # so even with NO effect calibration the checker enforces {59, 60} instead
    # of skipping: a real effect state totaling far outside that band is
    # exactly the anomaly the fuzzer exists to catch. This supersedes the old
    # skip-when-uncalibrated contract for the effect context specifically
    # (run-1's 850 false positives came from undersampled effect calibration).
    calib = fz.Calibration()
    calib.observe(make_state(), 0)  # plain only
    calib.finalize()
    assert calib.allowed_for(0, "effect") == {59, 60}
    checker = fz.FuzzChecker(calibration=calib)
    checker.enforce()
    # deck=40 totals 59: LEGAL in effect context under the structural band, no
    # violation. deck=30 totals 49: outside {59, 60}, must flag.
    legal_obs = {
        "current": make_state(me=player_state(deck=40)),
        "select": {"contextCard": {"id": 5, "serial": 9999, "playerIndex": 0}},
    }
    checker.observe(legal_obs, fz.GameTracker())
    assert [v for v in checker.violations if v["invariant"] == "I1"] == []
    bad_obs = {
        "current": make_state(me=player_state(deck=30)),
        "select": {"contextCard": {"id": 5, "serial": 9999, "playerIndex": 0}},
    }
    checker.observe(bad_obs, fz.GameTracker())
    i1 = [v for v in checker.violations if v["invariant"] == "I1"]
    assert len(i1) == 1
    assert sorted(i1[0]["detail"]["expected"]) == [59, 60]


def test_select_context_detection():
    assert fz.select_context({"select": None}) == "plain"
    assert fz.select_context({"select": {"type": 0}}) == "plain"
    assert fz.select_context({"select": {"effect": {"id": 1}}}) == "effect"
    assert fz.select_context({"select": {"contextCard": {"id": 1}}}) == "effect"
    assert fz.select_context("garbage") == "plain"


# ---------------------------------------------------------------------------
# I2: HP bounds.
# ---------------------------------------------------------------------------


def test_hp_bounds_clean_at_edges():
    me = player_state(active=pokemon(hp=0, max_hp=100),
                      bench=[pokemon(hp=100, max_hp=100)])
    assert fz.check_hp_bounds(make_state(me=me)) == []


def test_hp_bounds_violations():
    me = player_state(active=pokemon(hp=120, max_hp=100),
                      bench=[pokemon(hp=-10, max_hp=100)])
    violations = fz.check_hp_bounds(make_state(me=me))
    assert {(v["zone"], v["hp"]) for v in violations} == {("active[0]", 120), ("bench[0]", -10)}


def test_hp_bounds_malformed_slot_skipped():
    me = player_state(active=pokemon(), bench=[{"id": 1}, None, "garbage"])
    assert fz.check_hp_bounds(make_state(me=me)) == []


# ---------------------------------------------------------------------------
# I3: prizes never increase mid-game.
# ---------------------------------------------------------------------------


def test_prizes_monotone_clean_and_violation():
    tracker = fz.GameTracker()
    assert fz.check_prizes_monotone(make_state(me=player_state(prize_n=6)), tracker) == []
    assert fz.check_prizes_monotone(make_state(me=player_state(prize_n=5)), tracker) == []
    violations = fz.check_prizes_monotone(make_state(me=player_state(prize_n=6)), tracker)
    assert violations == [{"seat": 0, "prev": 5, "now": 6}]


def test_prizes_monotone_ignores_setup_turn_zero():
    tracker = fz.GameTracker()
    assert fz.check_prizes_monotone(make_state(turn=0, me=player_state(prize_n=0)), tracker) == []
    # First tracked state is turn >= 1; the setup deal never reads as an increase.
    assert fz.check_prizes_monotone(make_state(turn=1, me=player_state(prize_n=6)), tracker) == []


def test_prizes_monotone_malformed_skipped():
    tracker = fz.GameTracker()
    bad = make_state()
    bad["players"][0]["prize"] = None
    assert fz.check_prizes_monotone(bad, tracker) == []


# ---------------------------------------------------------------------------
# I4: bench size <= benchMax.
# ---------------------------------------------------------------------------


def test_bench_size_clean_at_max():
    me = player_state(bench=[pokemon() for _ in range(5)], bench_max=5)
    assert fz.check_bench_size(make_state(me=me)) == []


def test_bench_size_violation():
    me = player_state(bench=[pokemon() for _ in range(6)], bench_max=5)
    violations = fz.check_bench_size(make_state(me=me))
    assert violations == [{"seat": 0, "bench": 6, "benchMax": 5}]


def test_bench_size_malformed_skipped():
    me = player_state()
    me["benchMax"] = None
    assert fz.check_bench_size(make_state(me=me)) == []


# ---------------------------------------------------------------------------
# I5: deckCount never negative.
# ---------------------------------------------------------------------------


def test_deck_count_zero_is_clean():
    assert fz.check_deck_counts(make_state(me=player_state(deck=0))) == []


def test_deck_count_negative_is_violation():
    violations = fz.check_deck_counts(make_state(me=player_state(deck=-1)))
    assert violations == [{"seat": 0, "deckCount": -1}]


def test_deck_count_malformed_skipped():
    bad = make_state()
    bad["players"][1]["deckCount"] = "lots"
    assert fz.check_deck_counts(bad) == []


# ---------------------------------------------------------------------------
# I6: turn non-decreasing, result terminal-stable.
# ---------------------------------------------------------------------------


def test_turn_result_clean_sequence():
    tracker = fz.GameTracker()
    for turn, result in ((1, -1), (2, -1), (2, -1), (3, 0), (3, 0)):
        assert fz.check_turn_result(make_state(turn=turn, result=result), tracker) == []


def test_turn_decrease_is_violation():
    tracker = fz.GameTracker()
    assert fz.check_turn_result(make_state(turn=5), tracker) == []
    violations = fz.check_turn_result(make_state(turn=4), tracker)
    assert violations[0]["kind"] == "turn_decreased"


def test_result_revert_and_flip_are_violations():
    tracker = fz.GameTracker()
    assert fz.check_turn_result(make_state(result=-1), tracker) == []
    assert fz.check_turn_result(make_state(result=1), tracker) == []
    revert = fz.check_turn_result(make_state(result=-1), tracker)
    assert revert[0]["kind"] == "result_changed"
    flip = fz.check_turn_result(make_state(result=0), tracker)
    assert flip[0]["kind"] == "result_changed"


def test_turn_result_malformed_skipped():
    tracker = fz.GameTracker()
    assert fz.check_turn_result({"turn": "three", "result": None}, tracker) == []
    assert fz.check_turn_result("not a state", tracker) == []


# ---------------------------------------------------------------------------
# I7: duplicate serials across own visible zones.
# ---------------------------------------------------------------------------


def test_duplicate_serials_clean_when_unique():
    assert fz.duplicate_serials(make_state(), 0) == []


def test_duplicate_serial_across_zones_is_violation():
    me = player_state()
    me["hand"][0]["serial"] = 777
    me["discard"][0]["serial"] = 777
    violations = fz.duplicate_serials(make_state(me=me), 0)
    assert len(violations) == 1
    assert violations[0]["serial"] == 777
    assert violations[0]["zones"] == ["hand[0]", "discard[0]"]


def test_duplicate_serials_benign_set_suppresses():
    me = player_state()
    me["hand"][0]["serial"] = 0
    me["discard"][0]["serial"] = 0
    assert fz.duplicate_serials(make_state(me=me), 0, benign=frozenset({0})) == []


def test_duplicate_serials_non_int_serial_skipped():
    me = player_state()
    me["hand"][0]["serial"] = None
    me["discard"][0]["serial"] = None
    me["hand"][1]["serial"] = "x"
    me["discard"][1]["serial"] = "x"
    assert fz.duplicate_serials(make_state(me=me), 0) == []


def test_calibration_learns_benign_serials():
    me = player_state()
    me["hand"][0]["serial"] = 0
    me["discard"][0]["serial"] = 0
    state = make_state(me=me)
    calib = fz.Calibration()
    calib.observe(state, 0)
    calib.finalize()
    assert 0 in calib.benign_serials

    checker = fz.FuzzChecker(calibration=calib)
    checker.enforce()
    checker.observe({"current": state}, fz.GameTracker())
    assert [v for v in checker.violations if v["invariant"] == "I7"] == []


# ---------------------------------------------------------------------------
# Checker robustness and violation logging.
# ---------------------------------------------------------------------------


def test_checker_never_raises_on_garbage_observations():
    checker = fz.FuzzChecker()
    tracker = fz.GameTracker()
    for obs in (None, {}, {"current": None}, {"current": "junk"},
                {"current": {"players": None}},
                {"current": {"players": [None, None], "yourIndex": 0, "turn": "x"}},
                {"current": {"players": [{"active": "bad"}, {}], "yourIndex": 2}},
                ["not", "a", "dict"]):
        checker.observe(obs, tracker)
    assert checker.violations == []


def test_checker_counts_states_and_skips_deck_selection():
    checker = fz.FuzzChecker()
    tracker = fz.GameTracker()
    checker.observe({"select": None, "current": None}, tracker)  # deck selection
    checker.observe({"current": make_state()}, tracker)
    assert checker.states_scanned == 1
    assert tracker.step == 1


def test_violations_written_as_json_lines(tmp_path):
    jsonl = tmp_path / "quirks.jsonl"
    checker = fz.FuzzChecker(jsonl_path=jsonl)
    tracker = fz.GameTracker("3:12", 42, "seat0=random,seat1=random")
    checker.observe({"current": make_state(me=player_state(deck=-2))}, tracker)
    checker.close()
    lines = jsonl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["invariant"] == "I5"
    assert record["game"] == "3:12"
    assert record["seed"] == 42
    assert record["seat"] == 0
    assert record["step"] == 1
    assert record["detail"]["deckCount"] == -2


def test_md_summary_created_with_header_and_appended(tmp_path):
    md = tmp_path / "engine_quirks.md"
    summary = {
        "ts": "2026-07-05T00:00:00+00:00", "shard": 0,
        "command": "--games 2 --agents random --seed 0 --shard 0 --calibrate 1",
        "games_requested": 2, "games_completed": 2, "calibration_games": 1,
        "enforced_games": 1, "game_errors": 0, "game_error_samples": [],
        "states_scanned": 100, "internal_errors": 0, "violations": 0,
        "by_invariant": {}, "i1_calibration_counts": {0: {60: 50}},
        "i1_calibration_skips": {}, "benign_serials": [],
        "jsonl": "analysis/engine_quirks_fuzz.jsonl", "duration_s": 1.0,
    }
    fz.append_md_summary(md, summary)
    text = md.read_text(encoding="utf-8")
    assert text.startswith("# Engine Quirks")
    assert "CLEAN, 0 violations" in text
    fz.append_md_summary(md, summary)
    assert md.read_text(encoding="utf-8").count("## Run") == 2


# ---------------------------------------------------------------------------
# Regression tests: U111 adjudication bugs (invariant_fuzzer.py defects).
# ---------------------------------------------------------------------------


def test_regression_board_slots_iterates_all_active_slots():
    """Bug in invariant_fuzzer.py line 136: only iterated player.active[0].

    That checker counted only the first active Pokemon's tools/energy, missing
    violations in multi-slot active zones. fuzz_invariants.py's _board_slots()
    correctly iterates ALL active and bench slots.
    """
    me = player_state(deck=40, bench=[])
    me["active"] = [pokemon(energy=3), pokemon(energy=2)]
    state = make_state(me=me)
    total, comp = fz.compute_own_total(state, 0)
    assert total == 60
    assert comp["inPlay"] == 2 + 3 + 2
    assert comp == {
        "deckCount": 40,
        "hand": 5,
        "discard": 2,
        "prizeSlots": 6,
        "inPlay": 2 + 5,
        "stadium": 0,
    }


def test_regression_board_slots_does_not_double_count_energy():
    """Bug in invariant_fuzzer.py line 139: counted energyCards separately.

    That checker added len(energyCards) to totals as if they were extra cards
    beyond the Pokemon itself. But energyCards are attachments to the Pokemon,
    already counted as part of the Pokemon's in-play footprint. Correct
    accounting treats them as part of that Pokemon's card count.
    """
    me = player_state(active=pokemon(energy=5), bench=[])
    state = make_state(me=me)
    total, comp = fz.compute_own_total(state, 0)
    assert total == 60
    assert comp["inPlay"] == 1 + 5
    assert comp == {
        "deckCount": 41,
        "hand": 5,
        "discard": 2,
        "prizeSlots": 6,
        "inPlay": 1 + 5,
        "stadium": 0,
    }


def test_regression_multi_active_and_benign_energy_together():
    """Both bugs combined: multiple active slots each with heavy energy."""
    me = player_state(deck=31, bench=[pokemon(energy=2), pokemon(tools=2, pre=1)])
    me["active"] = [pokemon(energy=4), pokemon(energy=3)]
    state = make_state(me=me)
    total, comp = fz.compute_own_total(state, 0)
    assert total == 60
    in_play_correct = 2 + 4 + 3 + 2 + 2 + 2 + 1
    assert comp["inPlay"] == in_play_correct
    assert comp == {
        "deckCount": 31,
        "hand": 5,
        "discard": 2,
        "prizeSlots": 6,
        "inPlay": in_play_correct,
        "stadium": 0,
    }
