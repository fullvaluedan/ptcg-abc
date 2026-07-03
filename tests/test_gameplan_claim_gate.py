"""Tests for analysis/gameplan_claim_gate.py, the U91 claim/prediction gates.

The two gates decide whether a mined win-vs-loss pattern is trustworthy enough
to call a finding: claim_gate needs both splits big enough AND a bootstrap CI on
the win-vs-loss gap that excludes zero; prediction_gate needs the SAME pattern,
mined on the KD4 train split only, to also describe the held-out test split.
These tests pin the bootstrap primitives on hand-built data (where the right
answer is knowable) and the live train/test wiring over a tiny synthetic replay
directory, so no cg engine or competition data is touched.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis import expert_cohort as ec  # noqa: E402
from analysis import gameplan_claim_gate as gcg  # noqa: E402
from analysis.replay_trace import AREA_ACTIVE, AREA_HAND, SEL_MAIN  # noqa: E402

PLAY, ATTACH, EVOLVE, ATTACK, END = 7, 8, 9, 13, 14


# --- bootstrap primitives ----------------------------------------------------

def test_bootstrap_mean_ci_brackets_the_true_mean_of_constant_data():
    # Every value equal -> every bootstrap mean equals it -> CI collapses to it.
    lo, hi = gcg.bootstrap_mean_ci([3.0] * 50, n_resamples=200)
    assert lo == 3.0 and hi == 3.0


def test_bootstrap_mean_ci_empty_is_none():
    assert gcg.bootstrap_mean_ci([]) == (None, None)


def test_bootstrap_mean_ci_is_reproducible_given_a_seed():
    values = [0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 0.0]
    a = gcg.bootstrap_mean_ci(values, n_resamples=500, seed=7)
    b = gcg.bootstrap_mean_ci(values, n_resamples=500, seed=7)
    assert a == b


def test_bootstrap_diff_ci_excludes_zero_for_a_clear_separation():
    win = [1.0] * 40
    loss = [0.0] * 40
    lo, hi = gcg.bootstrap_diff_ci(win, loss, n_resamples=500)
    assert lo > 0

    lo2, hi2 = gcg.bootstrap_diff_ci([1.0, 0.0] * 20, [1.0, 0.0] * 20, n_resamples=500)
    assert lo2 <= 0 <= hi2


def test_bootstrap_diff_ci_empty_side_is_none():
    assert gcg.bootstrap_diff_ci([], [1.0]) == (None, None)
    assert gcg.bootstrap_diff_ci([1.0], []) == (None, None)


# --- claim_gate ---------------------------------------------------------------

def _categorical_block(win_raw, loss_raw):
    return {"kind": "categorical", "raw": {"win": win_raw, "loss": loss_raw}}


def _timing_block(win_raw, loss_raw):
    return {"kind": "timing", "raw": {"win": win_raw, "loss": loss_raw}}


def test_claim_gate_fails_below_min_n_even_with_a_clean_separation():
    block = _categorical_block([True] * 10, [False] * 10)
    result = gcg.claim_gate(block, min_n=200, n_resamples=200)
    assert result["n_win"] == 10 and result["n_loss"] == 10
    assert result["passes"] is False


def test_claim_gate_passes_with_enough_n_and_a_real_gap():
    block = _categorical_block([True] * 250, [False] * 250)
    result = gcg.claim_gate(block, min_n=200, n_resamples=300)
    assert result["win_mean"] == 1.0 and result["loss_mean"] == 0.0
    assert result["ci_lo"] > 0
    assert result["passes"] is True


def test_claim_gate_fails_when_ci_straddles_zero_despite_enough_n():
    # Win and loss have the SAME distribution -> no real gap.
    values = ([True] * 100 + [False] * 100)
    block = _categorical_block(values, values)
    result = gcg.claim_gate(block, min_n=200, n_resamples=300)
    assert result["ci_lo"] <= 0 <= result["ci_hi"]
    assert result["passes"] is False


def test_claim_gate_works_on_timing_blocks_too():
    block = _timing_block([10.0] * 250, [20.0] * 250)
    result = gcg.claim_gate(block, min_n=200, n_resamples=300)
    assert result["win_mean"] == 10.0 and result["loss_mean"] == 20.0
    assert result["ci_hi"] < 0  # win - loss is consistently negative
    assert result["passes"] is True


# --- prediction_gate ------------------------------------------------------

def test_prediction_gate_passes_when_test_mean_matches_train_pattern():
    train = _categorical_block([True] * 200 + [False] * 20, [])
    test = _categorical_block([True] * 33 + [False] * 3, [])
    result = gcg.prediction_gate(train, test, n_resamples=300)
    assert result["passes"] is True


def test_prediction_gate_fails_when_test_contradicts_train():
    train = _categorical_block([True] * 200, [])
    test = _categorical_block([False] * 30, [])
    result = gcg.prediction_gate(train, test, n_resamples=300)
    assert result["passes"] is False


def test_prediction_gate_empty_side_fails_closed():
    block = _categorical_block([], [])
    result = gcg.prediction_gate(block, block)
    assert result["passes"] is False


# --- live wiring: run_split_mine / run_gates over a synthetic directory -----

SIG_ALPHA = frozenset({10, 11, 12, 13})
SIGNATURES = {"alpha": SIG_ALPHA}


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
    step0 = [
        {"status": "ACTIVE", "visualize": [{"action": [list(deck0), list(deck1)]}]},
        _inactive(),
    ]
    return {
        "rewards": list(rewards),
        "info": {"TeamNames": ["A", "B"]},
        "steps": [step0, *extra_steps],
    }


def _attach_step(seat):
    players = [{"active": [{"id": "mon"}], "bench": [], "hand": [{"id": "energy"}]}]
    attach_opt = {"type": ATTACH, "area": AREA_HAND, "index": 0, "inPlayArea": AREA_ACTIVE}
    end_opt = {"type": END}
    return [_main_entry(seat, action=[0], options=[attach_opt, end_opt], players=players), _inactive()]


def test_run_split_mine_partitions_by_kd4_episode_id(tmp_path):
    import json

    # "0" hashes to bucket 50 (train), "1" hashes to bucket 11 (test) -- pinned
    # against analysis.replay_trace.episode_bucket, the canonical KD4 split.
    train_rep = _replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_ALPHA), extra_steps=[_attach_step(0)])
    test_rep = _replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_ALPHA), extra_steps=[_attach_step(0)])
    (tmp_path / "0.json").write_text(json.dumps(train_rep), encoding="utf-8")
    (tmp_path / "1.json").write_text(json.dumps(test_rep), encoding="utf-8")

    mined = gcg.run_split_mine(str(tmp_path), SIGNATURES, "alpha")
    assert mined["train"]["episodes_win"] == 1
    assert mined["test"]["episodes_win"] == 1
    # Both mined with keep_raw, so the raw lists are present for the gates.
    assert "raw" in mined["train"]["blocks"]["attach_target"]


def test_run_gates_reports_a_verdict_per_claim_block(tmp_path):
    import json

    rep = _replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_ALPHA), extra_steps=[_attach_step(0)])
    (tmp_path / "0.json").write_text(json.dumps(rep), encoding="utf-8")

    report = gcg.run_gates(str(tmp_path), SIGNATURES, "alpha", n_resamples=50)
    assert set(report["blocks"]) == set(gcg.CLAIM_BLOCKS)
    for row in report["blocks"].values():
        assert row["verdict"] in ("CONFIRMED", "CUT")
        # Tiny synthetic sample can never clear MIN_CLAIM_N -> always CUT here.
        assert row["verdict"] == "CUT"
