"""Tests for tools/top50_win_mechanisms.py (the reconstructed win-mechanism
pipeline for analysis/top50_win_mechanisms.md, plan: classifier decontamination
+ verified corrections).

Covers, over synthetic fixtures (no episode data, no cg engine required except
where explicitly guarded):
  1. player_turn's shared-turn-to-own-turn conversion for both seats,
  2. jaccard union-find clustering merges near-identical "other" decklists and
     keeps distinct ones apart, deterministically,
  3. name_cluster derives a stable name from a cluster's own Pokemon cards,
  4. trace_game extracts development events, first-attack turn, and a
     multi-prize-drop prize curve from a synthetic replay,
  5. the development timeline excludes generic staples and dedupes by game,
  6. build_rows classifies via the decontaminated signatures (a deck that only
     shares staples with a family never gets that family's label).
"""
import pytest

from tools import top50_win_mechanisms as wm

# signature_of (used by cluster_other_decks) and card_index need the vendored
# card engine, which lives off the normal import path until
# agents.heuristics._ensure_cg_on_path runs; importing "cg.api" directly (the
# way pytest.importorskip would) fails even when the engine IS available,
# because that path setup has not happened yet. Call the same accessor every
# other module in this codebase uses and skip only if THAT fails.
from agents.heuristics import card_index as _card_index_fn  # noqa: E402

try:
    _card_index_fn()
except Exception as exc:  # noqa: BLE001 - any failure means "engine unavailable here"
    pytest.skip(f"card engine unavailable: {exc}", allow_module_level=True)


# --- player_turn -------------------------------------------------------------

def test_player_turn_alternates_seats_correctly():
    # seat 0's turns are the odd shared turns, seat 1's the even.
    assert wm.player_turn(1) == 1
    assert wm.player_turn(2) == 1
    assert wm.player_turn(3) == 2
    assert wm.player_turn(4) == 2
    assert wm.player_turn(0) == 0


def test_player_turn_defaults_missing_to_zero():
    assert wm.player_turn(None) == 0


# --- jaccard clustering -------------------------------------------------------

def test_jaccard_empty_and_disjoint_and_full_overlap():
    assert wm._jaccard(frozenset(), frozenset()) == 0.0
    assert wm._jaccard(frozenset({1, 2}), frozenset()) == 0.0
    assert wm._jaccard(frozenset({1, 2}), frozenset({3, 4})) == 0.0
    assert wm._jaccard(frozenset({1, 2}), frozenset({1, 2})) == 1.0
    assert wm._jaccard(frozenset({1, 2, 3}), frozenset({2, 3, 4})) == pytest.approx(2 / 4)


def _deck_with(distinct_ids, filler=8, size=60):
    ids = list(distinct_ids)
    return ids + [filler] * (size - len(ids))


def test_cluster_other_decks_merges_near_identical_and_keeps_distinct_apart():
    # A and B share 3 of 4 signature cards (jaccard 3/5 = 0.6, merges); C is
    # unrelated (jaccard 0, stays separate).
    a = {"key": ("a",), "cards": _deck_with([100, 101, 102, 103])}
    b = {"key": ("b",), "cards": _deck_with([100, 101, 102, 200])}
    c = {"key": ("c",), "cards": _deck_with([500, 501, 502, 503])}
    clusters = wm.cluster_other_decks([a, b, c], threshold=0.5)
    assert clusters[("a",)] == clusters[("b",)]
    assert clusters[("c",)] != clusters[("a",)]


def test_cluster_other_decks_below_threshold_stays_separate():
    a = {"key": ("a",), "cards": _deck_with([100, 101, 102, 103])}
    b = {"key": ("b",), "cards": _deck_with([100, 200, 201, 202])}  # jaccard 1/7
    clusters = wm.cluster_other_decks([a, b], threshold=0.5)
    assert clusters[("a",)] != clusters[("b",)]


def test_cluster_other_decks_cluster_id_is_deterministic_min_key():
    # ids 1/2/3 collide with real basic-energy card ids in the card database
    # (signature_of would strip them to an empty signature); use ids well
    # outside that low range so the signature is the non-empty Pokemon/Trainer
    # set this test actually wants to exercise.
    a = {"key": ("z_team",), "cards": _deck_with([601, 602, 603])}
    b = {"key": ("a_team",), "cards": _deck_with([601, 602, 603])}
    clusters = wm.cluster_other_decks([a, b], threshold=0.5)
    assert clusters[("z_team",)] == ("a_team",)
    assert clusters[("a_team",)] == ("a_team",)


# --- name_cluster --------------------------------------------------------------

class _FakeCard:
    def __init__(self, name, card_type):
        self.name = name
        self.cardType = card_type


POKEMON = 0
TRAINER = 2


def test_name_cluster_picks_most_played_non_meta_pokemon():
    card_index_map = {
        1: _FakeCard("Riolu", POKEMON),
        2: _FakeCard("Riolu", POKEMON),
        3: _FakeCard("Solrock", POKEMON),
        4: _FakeCard("Ultra Ball", TRAINER),
    }
    cards = [1, 1, 1, 2, 3, 4, 4]
    name = wm.name_cluster(cards, meta_signature_ids=frozenset(), card_index_map=card_index_map)
    assert name == "riolu_solrock"


def test_name_cluster_excludes_meta_shared_pokemon_first():
    card_index_map = {
        1: _FakeCard("Archaludon ex", POKEMON),  # shared with a meta family
        2: _FakeCard("Okidogi", POKEMON),
    }
    cards = [1, 1, 1, 1, 2]
    name = wm.name_cluster(
        cards, meta_signature_ids=frozenset({1}), card_index_map=card_index_map
    )
    assert name == "okidogi"


def test_name_cluster_falls_back_when_no_pokemon_present():
    card_index_map = {1: _FakeCard("Ultra Ball", TRAINER)}
    name = wm.name_cluster([1, 1], meta_signature_ids=frozenset(), card_index_map=card_index_map)
    assert name == "other_cluster"


# --- trace_game ----------------------------------------------------------------

SEL_MAIN = 0
OPT_PLAY = 7
OPT_ATTACH = 8
OPT_EVOLVE = 9
OPT_ATTACK = 13


def _decision(seat, turn, options, action_idx, prize_by_seat=None, active_by_seat=None):
    prize_by_seat = prize_by_seat or {}
    active_by_seat = active_by_seat or {}
    players = []
    for s in (0, 1):
        players.append({
            "prize": [None] * prize_by_seat.get(s, 6),
            "active": active_by_seat.get(s, []),
        })
    return {
        "status": "ACTIVE",
        "action": [action_idx],
        "observation": {
            "select": {"type": SEL_MAIN, "minCount": 1, "maxCount": 1, "option": options},
            "current": {"turn": turn, "yourIndex": seat, "players": players},
        },
    }


def _replay(decisions):
    return {"steps": [[d] for d in decisions]}


def test_trace_game_collects_dev_events_and_first_turn_by_card():
    replay = _replay([
        # turn 1 (shared), seat 0: two options, plays card 111.
        _decision(0, 1, [{"type": OPT_PLAY, "cardId": 111}, {"type": OPT_PLAY, "cardId": 222}], 0),
        # turn 3 (shared, seat0's turn 2): evolves 111, offered alongside a second option.
        _decision(0, 3, [{"type": OPT_EVOLVE, "cardId": 111}, {"type": OPT_PLAY, "cardId": 333}], 0),
    ])
    trace = wm.trace_game(replay, seat=0)
    assert trace["first_turn_by_card"][111] == 1  # earliest turn wins, not overwritten by evolve
    # 333 was only ever OFFERED (option index 1), never the PLAYED option (index 0
    # picked EVOLVE 111), so it must never appear as a first-play.
    assert 333 not in trace["first_turn_by_card"]
    assert (1, "PLAY", 111) in trace["dev_events"]
    assert (2, "EVOLVE", 111) in trace["dev_events"]
    assert trace["max_turn"] == 2


def test_trace_game_single_option_decisions_are_never_seen_forced_attack_undercount():
    # A single-option ATTACK decision is not a "choice" and iter_resolved_decisions
    # (via _scorable_main's len(options) > 1 gate) never yields it -- this is the
    # documented reliability caveat, pinned here so a future change to that gate
    # does not silently start over- or under-counting attacks differently.
    replay = _replay([
        _decision(0, 1, [{"type": OPT_ATTACK, "attackId": 999}], 0),
    ])
    trace = wm.trace_game(replay, seat=0)
    assert trace["attack_ids"] == set()
    assert trace["first_attack_turn"] is None


def test_trace_game_records_first_attack_turn_and_attack_ids():
    replay = _replay([
        _decision(0, 1, [{"type": OPT_ATTACK, "attackId": 10}, {"type": OPT_PLAY, "cardId": 1}], 0),
        _decision(0, 5, [{"type": OPT_ATTACK, "attackId": 20}, {"type": OPT_PLAY, "cardId": 2}], 0),
    ])
    trace = wm.trace_game(replay, seat=0)
    assert trace["first_attack_turn"] == 1
    assert trace["attack_ids"] == {10, 20}


def test_trace_game_prize_drop_logs_one_event_per_prize_including_multi_kos():
    replay = _replay([
        _decision(0, 1, [{"type": OPT_PLAY, "cardId": 1}, {"type": OPT_PLAY, "cardId": 2}], 0,
                  prize_by_seat={0: 6, 1: 6}),
        # a double knockout drops our prize count from 6 to 4 at turn 3 (own turn 2).
        _decision(0, 3, [{"type": OPT_PLAY, "cardId": 1}, {"type": OPT_PLAY, "cardId": 2}], 0,
                  prize_by_seat={0: 4, 1: 6}),
        # a single knockout drops 4 to 3 at turn 5 (own turn 3).
        _decision(0, 5, [{"type": OPT_PLAY, "cardId": 1}, {"type": OPT_PLAY, "cardId": 2}], 0,
                  prize_by_seat={0: 3, 1: 6}),
    ])
    trace = wm.trace_game(replay, seat=0)
    assert trace["prize_events"] == [2, 2, 3]  # own-turn numbers, two events at turn 2, one at 3


# --- dev timeline bucketing ----------------------------------------------------

def test_dev_timeline_bucket_dedupes_per_game_and_excludes_staples():
    boss_orders_id = next(iter(wm.STAPLE_CARD_IDS))
    traced = [
        {"max_turn": 2, "dev_events": [
            (1, "PLAY", 111), (1, "PLAY", 111),  # same game, same (cat,card): counts once
            (1, "PLAY", boss_orders_id),          # a staple: excluded entirely
        ]},
        {"max_turn": 2, "dev_events": [(1, "PLAY", 111)]},  # a second game also plays 111
    ]
    result = wm._dev_timeline_bucket(traced, lambda t, mx: t in wm.SETUP_TURNS)
    counted = dict(result)
    assert counted[("PLAY", 111)] == 2
    assert ("PLAY", boss_orders_id) not in counted


# --- median / formatting --------------------------------------------------------

def test_median_ignores_none_and_rounds():
    assert wm._median([1, 2, None, 3]) == 2
    assert wm._median([]) is None
    assert wm._median([None]) is None


def test_fmt_num_strips_trailing_zero():
    assert wm._fmt_num(7.0) == "7"
    assert wm._fmt_num(9.5) == "9.5"
    assert wm._fmt_num(None) == "n/a"


# --- build_rows: decontamination applied to real classification ---------------

def test_build_rows_staple_only_deck_never_gets_the_family_label():
    from tools.top50_loss_modes import STAPLE_CARD_IDS, decontaminate_signatures

    family_sig = frozenset({1, 2, 3, 4}) | STAPLE_CARD_IDS  # 4 defining + all staples
    raw_signatures = {"alpha": family_sig}
    signatures = decontaminate_signatures(raw_signatures)

    staple_only_deck = _deck_with(list(STAPLE_CARD_IDS)[:6])  # only staples, no 1-4
    real_deck = _deck_with([1, 2, 3, 4])  # the real defining cards, no staples

    harvest = {
        "teams": [
            {
                "team": "StapleOnlyTeam",
                "decks": [{"cards": staple_only_deck, "games_in_window": 20}],
                "games": [
                    {"episode_id": f"e{i}", "result": "W" if i % 2 else "L", "deck_index": 0}
                    for i in range(20)
                ],
            },
            {
                "team": "RealAlphaTeam",
                "decks": [{"cards": real_deck, "games_in_window": 20}],
                "games": [
                    {"episode_id": f"r{i}", "result": "W" if i % 2 else "L", "deck_index": 0}
                    for i in range(20)
                ],
            },
        ],
    }
    from agents.heuristics import card_index

    rows, _cluster_meta = wm.build_rows(harvest, signatures, card_index())
    by_team = {}
    for r in rows:
        by_team.setdefault(r["team"], set()).add(r["archetype"])
    assert by_team["RealAlphaTeam"] == {"alpha"}
    assert "alpha" not in by_team["StapleOnlyTeam"]
