"""Tests for analysis/episode_scoreboard.py (plan U23).

The scoreboard's statistics are pure over plain rows and outcome lists, so these
cover the raw win rate, the early-stop eviction gate, the shared-bracket
settlement math, and the same-build noise read with hand-built data. No native
engine, no card data, and no competition dataset are touched.

The live wrappers (outcomes_from_dir / rows_from_dir) are exercised against a
tiny directory of synthetic replay JSONs so the retrodiction path is covered
without the card database: outcomes_from_dir uses only parse_replay and the seat
helper, and the win/loss tally it produces is cross-checked against the loss
classifier's independent parse of the same files.
"""
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.episode_scoreboard import (  # noqa: E402
    bracket_records,
    early_stop,
    outcomes_from_dir,
    raw_win_rate,
    same_build_spread,
    settlement,
    shared_brackets,
    two_proportion_confidence,
    win_loss_draw,
)
from analysis.loss_classifier import parse_replay  # noqa: E402


def _row(bracket, outcome):
    return {"bracket": bracket, "outcome": outcome}


# --- raw win rate + early stop ------------------------------------------------

def test_win_loss_draw_counts():
    assert win_loss_draw(["win", "loss", "win", "draw", "unknown"]) == (2, 1, 1)


def test_raw_win_rate_over_all_games_including_draws():
    # 2 wins over 4 games (a draw counts as a non-win), not 2/3.
    assert raw_win_rate(["win", "win", "loss", "draw"]) == 0.5


def test_raw_win_rate_none_when_empty():
    assert raw_win_rate([]) is None


def test_early_stop_holds_below_min_episodes():
    # 0% win rate but only 14 games: too few to evict.
    out = early_stop(["loss"] * 14)
    assert out["evict"] is False
    assert out["n"] == 14


def test_early_stop_evicts_clear_loser_after_min_episodes():
    # 4 wins / 15 = 0.267 < 0.35 floor at exactly the minimum sample.
    out = early_stop(["win"] * 4 + ["loss"] * 11)
    assert out["n"] == 15
    assert out["evict"] is True
    assert out["win_rate"] < 0.35


def test_early_stop_keeps_build_above_floor():
    # 6 wins / 15 = 0.40 > 0.35: not evicted.
    out = early_stop(["win"] * 6 + ["loss"] * 9)
    assert out["evict"] is False


# --- bracketing ---------------------------------------------------------------

def test_bracket_records_tally():
    rows = [
        _row("Archaludon ex", "win"),
        _row("Archaludon ex", "loss"),
        _row("Dragapult ex", "win"),
        _row("Dragapult ex", "draw"),
        _row("Dragapult ex", "unknown"),  # counted into the bracket, not the tally
    ]
    recs = bracket_records(rows)
    assert recs["Archaludon ex"] == {"win": 1, "loss": 1, "draw": 0}
    assert recs["Dragapult ex"] == {"win": 1, "loss": 0, "draw": 1}


def test_shared_brackets_is_intersection():
    a = [_row("A", "win"), _row("B", "loss")]
    b = [_row("B", "win"), _row("C", "loss")]
    assert shared_brackets(a, b) == {"B"}


# --- settlement ---------------------------------------------------------------

def test_two_proportion_confidence_directions():
    # Clearly better sample -> high confidence; symmetric case -> low.
    hi = two_proportion_confidence(18, 20, 8, 20)
    lo = two_proportion_confidence(8, 20, 18, 20)
    assert hi > 0.9
    assert lo < 0.1
    # Empty sample is undefined.
    assert two_proportion_confidence(0, 0, 5, 10) is None


def test_two_proportion_confidence_tie_is_half():
    assert two_proportion_confidence(5, 10, 5, 10) == 0.5


def test_settlement_favors_candidate_on_shared_brackets():
    # Candidate wins most shared-bracket games, king loses most; only shared
    # brackets (A, B) count, the candidate-only bracket C is ignored.
    cand = (
        [_row("A", "win")] * 9 + [_row("A", "loss")] * 1
        + [_row("B", "win")] * 9 + [_row("B", "loss")] * 1
        + [_row("C", "win")] * 5
    )
    king = (
        [_row("A", "win")] * 2 + [_row("A", "loss")] * 8
        + [_row("B", "win")] * 3 + [_row("B", "loss")] * 7
    )
    res = settlement(cand, king)
    assert res["shared_brackets"] == ["A", "B"]
    assert res["cand_decisive"] == 20  # C excluded
    assert res["verdict"] == "candidate"
    assert res["favors_candidate"] is True


def test_settlement_neutral_when_close():
    cand = [_row("A", "win")] * 6 + [_row("A", "loss")] * 4
    king = [_row("A", "win")] * 5 + [_row("A", "loss")] * 5
    res = settlement(cand, king)
    assert res["verdict"] == "neutral"
    assert res["favors_candidate"] is False


def test_settlement_favors_king_when_worse():
    cand = [_row("A", "win")] * 2 + [_row("A", "loss")] * 8
    king = [_row("A", "win")] * 9 + [_row("A", "loss")] * 1
    res = settlement(cand, king)
    assert res["verdict"] == "king"


# --- same-build noise ---------------------------------------------------------

def test_same_build_spread_reports_delta():
    a = [_row("A", "win")] * 6 + [_row("A", "loss")] * 4
    b = [_row("A", "win")] * 5 + [_row("A", "loss")] * 5
    out = same_build_spread(a, b)
    assert out["rate_a"] == 0.6
    assert out["rate_b"] == 0.5
    assert abs(out["delta"] - 0.1) < 1e-9


# --- live wrapper: outcomes_from_dir over synthetic replays -------------------

def _decision_step(seat, *, my_prize, opp_prize, status="ACTIVE"):
    """One two-seat step where `seat` is ACTIVE and makes a trivial MAIN pick."""
    prizes = [None, None]
    prizes[seat] = my_prize
    prizes[1 - seat] = opp_prize
    active = {
        "action": [0],
        "status": status,
        "observation": {
            "select": {"type": 0, "minCount": 1, "maxCount": 1, "option": [0, 1]},
            "current": {
                "yourIndex": seat,
                "turn": 5,
                "players": [
                    {"prize": [None] * prizes[0], "deckCount": 20, "bench": [1]}
                    if prizes[0] is not None else {},
                    {"prize": [None] * prizes[1], "deckCount": 20, "bench": [1]}
                    if prizes[1] is not None else {},
                ],
            },
        },
    }
    inactive = {"action": [], "status": "INACTIVE",
                "observation": {"select": None, "current": None}}
    step = [None, None]
    step[seat] = active
    step[1 - seat] = inactive
    return step


def _replay(reward_us, reward_opp, opp_name="Rival Trainer"):
    """A minimal replay where seat 0 is us; rewards decide the outcome."""
    return {
        "info": {"TeamNames": ["Dan Arreola", opp_name]},
        "steps": [_decision_step(0, my_prize=3, opp_prize=4)],
        "rewards": [reward_us, reward_opp],
    }


def test_outcomes_from_dir_matches_loss_classifier(tmp_path):
    files = {
        "win.json": _replay(1, -1),
        "loss.json": _replay(-1, 1),
        "draw.json": _replay(0, 0),
    }
    for name, replay in files.items():
        (tmp_path / name).write_text(json.dumps(replay), encoding="utf-8")

    outcomes = outcomes_from_dir(tmp_path)
    assert win_loss_draw(outcomes) == (1, 1, 1)

    # Cross-check: the same files parsed independently by the loss classifier
    # give the identical per-file outcome (retrodiction of the recorded W/L).
    independent = []
    for name in sorted(files):
        replay = json.loads((tmp_path / name).read_text(encoding="utf-8"))
        independent.append(parse_replay(replay, our_index=0)["outcome"])
    assert win_loss_draw(independent) == win_loss_draw(outcomes)


def test_outcomes_from_dir_can_skip_self_play(tmp_path):
    (tmp_path / "ladder.json").write_text(
        json.dumps(_replay(1, -1, opp_name="Rival Trainer")), encoding="utf-8")
    (tmp_path / "selfplay.json").write_text(
        json.dumps(_replay(1, -1, opp_name="Dan Arreola")), encoding="utf-8")
    # Default keeps both; skip_self_play drops the mirror validation game.
    assert len(outcomes_from_dir(tmp_path)) == 2
    assert len(outcomes_from_dir(tmp_path, skip_self_play=True)) == 1
