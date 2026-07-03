"""Tests for analysis/gameplan_mine.py, the game-plan miner (plan U36, piece 2).

The miner distills a target family's real expert episodes into six stat blocks,
each contrasting the family's WINNING appearances with its LOSING ones, so the
seeds emitter (piece 3) can read the winning-play signal. These tests pin the
mining primitives over synthetic replays so no cg engine or competition data is
touched:

  1. the categorical/timing block extractors read the resolved decision stream
     the way piece 3 expects (opening category, attach/play/evolve targets,
     first-attack / first-evolve ordinals),
  2. categorical_stats / timing_stats report resolution_rate, mode/mode_share
     (share) and mode_ordinal/consistency (timing) correctly, including the
     empty and all-unresolved edges,
  3. mine splits win vs loss and bars a block whose winning split resolves under
     BAR_RESOLUTION,
  4. episode_family_streams yields (won, decisions) only for the target family's
     seats, includes losing appearances, and drops draws / unreadable openers.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis import expert_cohort as ec  # noqa: E402
from analysis import gameplan_mine as gm  # noqa: E402
from analysis.replay_trace import AREA_ACTIVE, AREA_HAND, SEL_MAIN  # noqa: E402

# OptionType values the spine maps to categories (analysis/replay_trace.OPT_CATEGORY).
PLAY, ATTACH, EVOLVE, ATTACK, END = 7, 8, 9, 13, 14


# --- fixtures --------------------------------------------------------------

def _decision(category_type, *, card_id=None, attack_id=None):
    """One resolved-decision record as iter_resolved_decisions yields it.

    Only the `played` option matters to the block extractors, so the option list
    is a single-element list; card_id None models an option that did not resolve.
    """
    from analysis.replay_trace import OPT_CATEGORY

    played = {
        "type": category_type,
        "category": OPT_CATEGORY.get(category_type, "OTHER"),
        "card_id": card_id,
        "attack_id": attack_id,
    }
    return {"obs": {}, "played_index": 0, "played": played, "options": [played]}


# --- block extractors ------------------------------------------------------

def test_opening_category_is_first_decision_category():
    decisions = [_decision(PLAY), _decision(ATTACK)]
    assert gm._opening_category(decisions) == ["PLAY"]
    assert gm._opening_category([]) == []


def test_opening_category_other_is_unresolved():
    # An unknown option type resolves to OTHER, which the block treats as None.
    assert gm._opening_category([_decision(999)]) == [None]


def test_target_extractors_read_played_card_by_category():
    decisions = [
        _decision(ATTACH, card_id="basic-water"),
        _decision(PLAY, card_id="ball"),
        _decision(EVOLVE, card_id="stage2"),
        _decision(ATTACH, card_id=None),  # unresolved attach
        _decision(ATTACK, attack_id=77),  # not any target category
    ]
    assert gm._attach_targets(decisions) == ["basic-water", None]
    assert gm._play_targets(decisions) == ["ball"]
    assert gm._evolve_targets(decisions) == ["stage2"]


def test_first_ordinals_are_one_based_and_none_when_absent():
    decisions = [_decision(PLAY), _decision(EVOLVE), _decision(ATTACK)]
    assert gm._first_evolve_ordinal(decisions) == 2
    assert gm._first_attack_ordinal(decisions) == 3
    assert gm._first_attack_ordinal([_decision(PLAY)]) is None


# --- turn-scoped blocks (U91 comprehension track) ---------------------------

def test_turns_splits_on_end_and_keeps_trailing_partial_turn():
    decisions = [_decision(PLAY), _decision(END), _decision(ATTACH), _decision(ATTACK)]
    turns = gm._turns(decisions)
    assert len(turns) == 2
    assert [d["played"]["category"] for d in turns[0]] == ["PLAY", "END"]
    assert [d["played"]["category"] for d in turns[1]] == ["ATTACH", "ATTACK"]
    assert gm._turns([]) == []


def test_attach_before_attack_only_counts_turns_with_both():
    # Turn 1: attach then attack (True). Turn 2: attack then attach (False).
    # Turn 3: attach only (no attack) -> not counted.
    decisions = [
        _decision(ATTACH), _decision(ATTACK), _decision(END),
        _decision(ATTACK), _decision(ATTACH), _decision(END),
        _decision(ATTACH), _decision(END),
    ]
    assert gm._attach_before_attack(decisions) == [True, False]
    assert gm._attach_before_attack([_decision(PLAY), _decision(END)]) == []


def test_energy_banking_true_when_no_attack_that_turn():
    decisions = [
        _decision(ATTACH), _decision(ATTACK), _decision(END),  # spent, not banked
        _decision(ATTACH), _decision(END),  # banked
        _decision(PLAY), _decision(END),  # no attach -> not counted
    ]
    assert gm._energy_banking(decisions) == [False, True]


def test_game_length_turns_counts_turns_and_none_when_empty():
    decisions = [_decision(PLAY), _decision(END), _decision(ATTACK), _decision(END)]
    assert gm._game_length_turns(decisions) == 2
    assert gm._game_length_turns([]) is None


# --- stat folds ------------------------------------------------------------

def test_categorical_stats_resolution_and_mode_share():
    stats = gm.categorical_stats(["a", "a", "b", None])
    assert stats["total"] == 4 and stats["resolved"] == 3
    assert stats["resolution_rate"] == 0.75
    assert stats["mode"] == "a"
    assert stats["mode_share"] == 2 / 3  # share OF resolved, not of total


def test_categorical_stats_empty_and_all_unresolved():
    empty = gm.categorical_stats([])
    assert empty["resolution_rate"] == 0.0 and empty["mode"] is None
    none_only = gm.categorical_stats([None, None])
    assert none_only["resolution_rate"] == 0.0 and none_only["mode_share"] == 0.0


def test_timing_stats_consistency_and_absence():
    stats = gm.timing_stats([2, 2, 3, None])
    assert stats["episodes"] == 4 and stats["present"] == 3
    assert stats["resolution_rate"] == 0.75
    assert stats["mode_ordinal"] == 2
    assert stats["consistency"] == 2 / 3
    assert stats["distribution"] == {"2": 2, "3": 1}


# --- mine (win/loss split + bar) -------------------------------------------

def _stream_win(decisions):
    return (True, decisions)


def _stream_loss(decisions):
    return (False, decisions)


def test_mine_splits_win_and_loss():
    streams = [
        _stream_win([_decision(ATTACH, card_id="w"), _decision(ATTACK)]),
        _stream_loss([_decision(ATTACH, card_id="l"), _decision(PLAY, card_id="p")]),
    ]
    result = gm.mine(streams)
    assert result["episodes_win"] == 1 and result["episodes_loss"] == 1
    attach = result["blocks"]["attach_target"]
    assert attach["win"]["mode"] == "w"
    assert attach["loss"]["mode"] == "l"
    # First-attack ordinal present in the win, absent in the loss.
    fa = result["blocks"]["first_attack_ordinal"]
    assert fa["win"]["mode_ordinal"] == 2
    assert fa["loss"]["present"] == 0


def test_mine_bars_block_below_resolution_on_winning_split():
    # Winning attaches: one resolved, four unresolved -> res 0.2 < 0.90 -> barred.
    win = [_decision(ATTACH, card_id="w")] + [_decision(ATTACH, card_id=None)] * 4
    result = gm.mine([_stream_win(win)])
    assert result["blocks"]["attach_target"]["barred"] is True
    # A fully resolved block is not barred.
    ok = [_decision(ATTACH, card_id="w")] * 5
    result2 = gm.mine([_stream_win(ok)])
    assert result2["blocks"]["attach_target"]["barred"] is False


def test_all_nine_blocks_present():
    result = gm.mine([_stream_win([_decision(PLAY, card_id="p")])])
    assert set(result["blocks"]) == {
        "opening_category",
        "attach_target",
        "play_target",
        "evolve_target",
        "attach_before_attack",
        "energy_banking",
        "first_attack_ordinal",
        "first_evolve_ordinal",
        "game_length_turns",
    }


def test_mine_keep_raw_stashes_prefold_values():
    streams = [
        _stream_win([_decision(ATTACH, card_id="w"), _decision(ATTACK), _decision(END)]),
        _stream_loss([_decision(ATTACH, card_id="l")]),
    ]
    without_raw = gm.mine(streams)
    assert "raw" not in without_raw["blocks"]["attach_target"]
    with_raw = gm.mine(streams, keep_raw=True)
    assert with_raw["blocks"]["attach_target"]["raw"] == {"win": ["w"], "loss": ["l"]}
    assert with_raw["blocks"]["attach_before_attack"]["raw"] == {"win": [True], "loss": []}


# --- live wrapper (family filter, win flag, drop rules) --------------------

SIG_ALPHA = frozenset({10, 11, 12, 13})
SIG_BETA = frozenset({20, 21, 22, 23})
SIGNATURES = {"alpha": SIG_ALPHA, "beta": SIG_BETA}


def _deck(distinct_ids, filler=8):
    deck = list(distinct_ids)
    return tuple(deck + [filler] * (ec.DECK_SIZE - len(deck)))


def _main_entry(seat, action, options, players=None):
    sel = {"type": SEL_MAIN, "minCount": 1, "maxCount": 1, "option": options}
    current = {"yourIndex": seat}
    if players is not None:
        current["players"] = players
    return {
        "action": action,
        "status": "ACTIVE",
        "observation": {"select": sel, "current": current},
    }


def _inactive():
    return {"action": [], "status": "INACTIVE",
            "observation": {"select": None, "current": None}}


def _replay(rewards, deck0, deck1, extra_steps=()):
    """A decided replay: openers in step 0, then any extra ACTIVE MAIN steps."""
    step0 = [
        {"status": "ACTIVE", "visualize": [{"action": [list(deck0), list(deck1)]}]},
        _inactive(),
    ]
    return {
        "rewards": list(rewards),
        "info": {"TeamNames": ["A", "B"]},
        "steps": [step0, *extra_steps],
    }


def test_episode_family_streams_filters_target_and_marks_winner():
    # Seat 0 = alpha (winner), seat 1 = beta (loser). Mine target "alpha".
    rep = _replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_BETA))
    got = list(gm.episode_family_streams(rep, SIGNATURES, "alpha"))
    assert len(got) == 1
    won, decisions = got[0]
    assert won is True and decisions == []
    # Mining "beta" yields the losing seat.
    got_beta = list(gm.episode_family_streams(rep, SIGNATURES, "beta"))
    assert len(got_beta) == 1 and got_beta[0][0] is False


def test_episode_family_streams_reads_target_seat_decisions():
    # Seat 0 (alpha) makes one scorable ATTACH among two options, powering its
    # active (attach_target reads the RECEIVING Pokemon, not the energy spent).
    players = [{"active": [{"id": "basic-water"}], "bench": [], "hand": [{"id": "energy"}]}]
    attach_opt = {"type": ATTACH, "area": AREA_HAND, "index": 0, "inPlayArea": AREA_ACTIVE}
    end_opt = {"type": END}
    step1 = [
        _main_entry(0, action=[0], options=[attach_opt, end_opt], players=players),
        _inactive(),
    ]
    rep = _replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_BETA), extra_steps=[step1])
    got = list(gm.episode_family_streams(rep, SIGNATURES, "alpha"))
    won, decisions = got[0]
    assert won is True
    assert [d["played"]["category"] for d in decisions] == ["ATTACH"]
    assert decisions[0]["played"]["card_id"] == "basic-water"


def test_episode_family_streams_drops_draw_and_unreadable_opener():
    d = _deck(SIG_ALPHA)
    assert list(gm.episode_family_streams(_replay([0, 0], d, d), SIGNATURES, "alpha")) == []
    # Neither seat is the target family -> no streams.
    rep = _replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_BETA))
    assert list(gm.episode_family_streams(rep, SIGNATURES, "gamma")) == []


def test_run_mine_over_a_directory(tmp_path):
    import json

    players = [{"active": [{"id": "basic-water"}], "bench": [], "hand": [{"id": "energy"}]}]
    attach_opt = {"type": ATTACH, "area": AREA_HAND, "index": 0, "inPlayArea": AREA_ACTIVE}
    end_opt = {"type": END}
    step1 = [
        _main_entry(0, action=[0], options=[attach_opt, end_opt], players=players),
        _inactive(),
    ]
    rep = _replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_BETA), extra_steps=[step1])
    (tmp_path / "1.json").write_text(json.dumps(rep), encoding="utf-8")

    result = gm.run_mine(str(tmp_path), SIGNATURES, "alpha")
    assert result["episodes_win"] == 1
    assert result["blocks"]["attach_target"]["win"]["mode"] == "basic-water"
