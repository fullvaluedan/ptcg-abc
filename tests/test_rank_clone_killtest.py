"""Tests for the U92 step-0 pairwise-RankNet kill test (tools/rank_clone_killtest.py).

Covers the pieces the kill test's verdict rests on: family_groups filters by
family/split into PairwiseLinearRanker's own (X, played_idx) shape,
first_legal_accuracy/rank_accuracy score only well-formed decisions, a planted
preference is recovered and clearly beats first-legal (proving the harness
itself works before trusting it on real data), and main()'s end-to-end report
path over a real clone_dataset-shaped npz file.
"""
import numpy as np

from agents.imitation_features import FEATURE_NAMES
from tools import clone_dataset as CD
from tools import rank_clone_killtest as K


def _feature_row(**overrides):
    values = [0.0] * len(FEATURE_NAMES)
    for name, value in overrides.items():
        values[FEATURE_NAMES.index(name)] = value
    return values


def _group(family, played, n_options, episode, split, signal="is_play", won=True):
    features = np.asarray(
        [_feature_row(**{signal: 1.0 if i == played else 0.0}) for i in range(n_options)],
        dtype=float,
    )
    return {
        "features": features, "played": played, "team": "topteam", "family": family,
        "won": won, "episode": episode, "split": split,
    }


def _planted_groups(family, n_groups, split, seed=0, signal="is_play"):
    rng = np.random.RandomState(seed)
    groups = []
    for i in range(n_groups):
        n_options = int(rng.randint(2, 5))
        played = int(rng.randint(0, n_options))
        groups.append(_group(family, played, n_options, episode=f"{split}-{family}-{i}", split=split, signal=signal))
    return groups


def test_family_groups_filters_by_family_and_split():
    groups = [
        _group("alpha", played=1, n_options=2, episode="e0", split="train"),
        _group("alpha", played=0, n_options=2, episode="e1", split="test"),
        _group("beta", played=0, n_options=3, episode="e2", split="train"),
    ]

    result = K.family_groups(groups, "alpha", "train")

    assert len(result) == 1
    assert result[0][1] == 1


def test_first_legal_accuracy_is_fraction_where_played_is_zero():
    groups = [
        (np.zeros((2, 3)), 0),  # first-legal correct
        (np.zeros((2, 3)), 1),  # first-legal wrong
    ]

    assert K.first_legal_accuracy(groups) == 0.5


def test_first_legal_accuracy_excludes_out_of_range_played():
    groups = [(np.zeros((2, 3)), 5)]

    assert K.first_legal_accuracy(groups) == 0.0


def test_first_legal_accuracy_empty_is_zero():
    assert K.first_legal_accuracy([]) == 0.0


def test_run_family_recovers_planted_preference_and_beats_first_legal_baseline():
    train_groups = _planted_groups("meta_alpha", n_groups=200, split="train", seed=0)
    test_groups = _planted_groups("meta_alpha", n_groups=60, split="test", seed=1)

    result = K.run_family(train_groups + test_groups, "meta_alpha")

    assert result is not None
    assert result["n_scored"] > 0
    assert result["margin"] > 0.3  # the signal is perfectly separable


def test_run_family_returns_none_without_train_rows():
    groups = _planted_groups("meta_alpha", n_groups=10, split="test", seed=0)

    assert K.run_family(groups, "meta_alpha") is None


def test_run_family_returns_none_without_test_rows():
    groups = _planted_groups("meta_alpha", n_groups=10, split="train", seed=0)

    assert K.run_family(groups, "meta_alpha") is None


def test_passes_requires_both_margin_and_min_test_groups():
    strong = {"margin": 0.2, "n_scored": 50}
    thin_signal = {"margin": 0.01, "n_scored": 50}
    too_few = {"margin": 0.2, "n_scored": 5}

    assert K.passes(strong, margin=0.03, min_test_groups=20) is True
    assert K.passes(thin_signal, margin=0.03, min_test_groups=20) is False
    assert K.passes(too_few, margin=0.03, min_test_groups=20) is False
    assert K.passes(None, margin=0.03, min_test_groups=20) is False


def test_main_writes_report_and_returns_verdict(tmp_path, capsys):
    groups = (
        _planted_groups("meta_alpha", n_groups=200, split="train", seed=0)
        + _planted_groups("meta_alpha", n_groups=60, split="test", seed=1)
    )
    npz_path = tmp_path / "clone_groups_test.npz"
    CD.write_npz(groups, npz_path)
    report_path = tmp_path / "killtest.md"

    rc = K.main([str(npz_path), "--report", str(report_path)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "VERDICT: PASS" in out
    text = report_path.read_text()
    assert "meta_alpha" in text
    assert "PASS" in text


def test_main_reports_fail_when_no_family_clears_margin(tmp_path, capsys):
    # No signal column varies with the target: every option row is identical,
    # so the ranker can do no better than the first-legal baseline (margin ~0).
    groups = (
        _planted_groups("meta_alpha", n_groups=200, split="train", seed=0, signal="opt_is_first")
        + _planted_groups("meta_alpha", n_groups=60, split="test", seed=1, signal="opt_is_first")
    )
    # Zero out the only-varying column so no feature carries the planted signal.
    for g in groups:
        g["features"] = np.zeros_like(g["features"])
    npz_path = tmp_path / "clone_groups_test.npz"
    CD.write_npz(groups, npz_path)
    report_path = tmp_path / "killtest.md"

    rc = K.main([str(npz_path), "--report", str(report_path)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "VERDICT: FAIL" in out
    assert "FAIL" in report_path.read_text()
