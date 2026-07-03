"""Tests for the per-family clone-policy trainer (plan U71, tools/train_clone.py).

Covers the pieces the plan gates on: rows_for_family flattens groups into
(X, y, group_id) filtered by family/split, top1_accuracy and
first_legal_baseline score only well-formed decisions, a fitted model
recovers a planted preference and clearly beats the first-legal baseline,
and the exported payload round-trips the same shape
tools/train_move_prior.py already proved search/move_prior.py can load.
"""
import json

import numpy as np
import pytest

from agents.imitation_features import FEATURE_NAMES, feature_version
from tools import train_clone as TC


def _feature_row(**overrides):
    values = [0.0] * len(FEATURE_NAMES)
    for name, value in overrides.items():
        values[FEATURE_NAMES.index(name)] = value
    return values


def _group(family, played, n_options, episode, split, signal="is_play", won=True):
    features = [_feature_row(**{signal: 1.0 if i == played else 0.0}) for i in range(n_options)]
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


def test_feature_mask_marks_only_excluded_columns_false():
    mask = TC.feature_mask(("opt_index_norm", "opt_is_first"))

    assert mask.dtype == bool
    assert mask.sum() == len(FEATURE_NAMES) - 2
    assert mask[FEATURE_NAMES.index("opt_index_norm")] == False  # noqa: E712
    assert mask[FEATURE_NAMES.index("opt_is_first")] == False  # noqa: E712
    assert mask[FEATURE_NAMES.index("opt_local_rank_norm")] == True  # noqa: E712


def test_feature_mask_raises_on_unknown_feature_name():
    with pytest.raises(ValueError):
        TC.feature_mask(("not_a_real_feature",))


def test_rows_for_family_filters_by_family_and_split():
    groups = [
        _group("alpha", played=1, n_options=2, episode="e0", split="train"),
        _group("alpha", played=0, n_options=2, episode="e1", split="test"),
        _group("beta", played=0, n_options=3, episode="e2", split="train"),
    ]

    X, y, group_id = TC.rows_for_family(groups, "alpha", split="train")

    assert X.shape == (2, len(FEATURE_NAMES))
    assert y.tolist() == [0, 1]
    assert group_id.tolist() == [0, 0]


def test_rows_for_family_all_splits_when_split_is_none():
    groups = [
        _group("alpha", played=1, n_options=2, episode="e0", split="train"),
        _group("alpha", played=0, n_options=2, episode="e1", split="test"),
    ]

    X, y, group_id = TC.rows_for_family(groups, "alpha", split=None)

    assert X.shape == (4, len(FEATURE_NAMES))
    assert set(group_id.tolist()) == {0, 1}


def test_rows_for_family_excludes_named_columns():
    groups = [_group("alpha", played=1, n_options=2, episode="e0", split="train")]

    X, y, group_id = TC.rows_for_family(groups, "alpha", split="train", exclude=("opt_index_norm", "opt_is_first"))

    assert X.shape == (2, len(FEATURE_NAMES) - 2)


def test_top1_accuracy_counts_correct_argmax_per_decision():
    scores = np.array([0.1, 0.9, 0.7, 0.2])
    y = np.array([0, 1, 1, 0])
    group_id = np.array([0, 0, 1, 1])

    accuracy, n_scored = TC.top1_accuracy(scores, y, group_id)

    assert n_scored == 2
    assert accuracy == 1.0  # group 0's argmax (idx 1) is played; group 1's argmax (idx 2) is played


def test_top1_accuracy_skips_groups_without_exactly_one_played():
    scores = np.array([0.1, 0.9, 0.5, 0.5, 0.3])
    y = np.array([0, 0, 1, 1, 0])  # group 0: no played row; group 1: two played rows
    group_id = np.array([0, 0, 1, 1, 1])

    accuracy, n_scored = TC.top1_accuracy(scores, y, group_id)

    assert n_scored == 0
    assert accuracy == 0.0


def test_first_legal_baseline_is_fraction_where_played_is_zero():
    # group 0: played is index 0 (first-legal correct); group 1: played is index 2 (incorrect)
    y = np.array([1, 0, 0, 0, 1])
    group_id = np.array([0, 0, 1, 1, 1])

    baseline = TC.first_legal_baseline(y, group_id)

    assert baseline == 0.5


def test_first_legal_baseline_excludes_unresolved_groups():
    y = np.array([0, 0, 0, 0, 1])  # group 0: no played row (excluded); group 1: played is the LAST row
    group_id = np.array([0, 0, 1, 1, 1])

    baseline = TC.first_legal_baseline(y, group_id)

    assert baseline == 0.0


def test_train_family_recovers_planted_preference_and_beats_first_legal_baseline():
    train_groups = _planted_groups("meta_alpha", n_groups=200, split="train", seed=0)
    test_groups = _planted_groups("meta_alpha", n_groups=60, split="test", seed=1)

    result = TC.train_family(train_groups + test_groups, "meta_alpha")

    assert result is not None
    assert result["n_scored"] > 0
    assert (result["accuracy"] - result["baseline"]) > 0.3  # the signal is perfectly separable


def test_train_family_best_exclude_removes_the_only_signal_column():
    # Signal lives ONLY in opt_is_first: every other feature is zero regardless
    # of which option was played (see _feature_row/_group). Without exclude,
    # the model finds it and separates perfectly; excluding it removes the
    # only column that ever varies with the target, so every row in a group
    # is identical (all zeros) and the fit can do no better than always
    # picking the first row -- exactly the first-legal baseline, margin ~0.
    train_groups = _planted_groups("meta_alpha", n_groups=200, split="train", seed=0, signal="opt_is_first")
    test_groups = _planted_groups("meta_alpha", n_groups=60, split="test", seed=1, signal="opt_is_first")
    groups = train_groups + test_groups

    with_signal = TC.train_family_best(groups, "meta_alpha")
    without_signal = TC.train_family_best(groups, "meta_alpha", exclude=("opt_is_first",))

    assert (with_signal["accuracy"] - with_signal["baseline"]) > 0.3
    assert abs(without_signal["accuracy"] - without_signal["baseline"]) < 1e-9


def test_train_family_returns_none_without_train_rows():
    groups = _planted_groups("meta_alpha", n_groups=10, split="test", seed=0)

    assert TC.train_family(groups, "meta_alpha") is None


def test_train_family_returns_none_without_test_rows():
    groups = _planted_groups("meta_alpha", n_groups=10, split="train", seed=0)

    assert TC.train_family(groups, "meta_alpha") is None


def test_qualifies_requires_both_margin_and_min_test_groups():
    strong = {"accuracy": 0.9, "baseline": 0.5, "n_scored": 50}
    thin_signal = {"accuracy": 0.55, "baseline": 0.5, "n_scored": 50}
    too_few = {"accuracy": 0.9, "baseline": 0.5, "n_scored": 5}

    assert TC.qualifies(strong, margin=0.15, min_test_groups=20) is True
    assert TC.qualifies(thin_signal, margin=0.15, min_test_groups=20) is False
    assert TC.qualifies(too_few, margin=0.15, min_test_groups=20) is False
    assert TC.qualifies(None, margin=0.15, min_test_groups=20) is False


def test_export_round_trip_writes_loadable_payload(tmp_path):
    train_groups = _planted_groups("meta_alpha", n_groups=200, split="train", seed=2)
    test_groups = _planted_groups("meta_alpha", n_groups=60, split="test", seed=3)
    result = TC.train_family(train_groups + test_groups, "meta_alpha")

    model_path = tmp_path / "meta_alpha.json"
    from tools.train_move_prior import export_model
    export_model(result["model"], result["mean"], result["std"], model_path)
    payload = json.loads(model_path.read_text())

    assert payload["feature_names"] == list(FEATURE_NAMES)
    assert payload["feature_version"] == list(feature_version())
    assert len(payload["mean"]) == len(FEATURE_NAMES)
    assert len(payload["std"]) == len(FEATURE_NAMES)
    assert len(payload["coef"]) == len(FEATURE_NAMES)
    assert isinstance(payload["intercept"], float)


def test_train_family_tree_recovers_planted_preference_and_beats_first_legal_baseline():
    train_groups = _planted_groups("meta_alpha", n_groups=200, split="train", seed=0)
    test_groups = _planted_groups("meta_alpha", n_groups=60, split="test", seed=1)

    result = TC.train_family_tree(train_groups + test_groups, "meta_alpha")

    assert result is not None
    assert result["model_kind"] == "tree"
    assert result["n_scored"] > 0
    assert (result["accuracy"] - result["baseline"]) > 0.3  # the signal is perfectly separable


def test_train_family_tree_returns_none_without_train_or_test_rows():
    train_only = _planted_groups("meta_alpha", n_groups=10, split="train", seed=0)
    test_only = _planted_groups("meta_alpha", n_groups=10, split="test", seed=0)

    assert TC.train_family_tree(test_only, "meta_alpha") is None
    assert TC.train_family_tree(train_only, "meta_alpha") is None


def test_train_family_best_returns_none_when_neither_kind_trains():
    groups = _planted_groups("meta_alpha", n_groups=10, split="test", seed=0)

    assert TC.train_family_best(groups, "meta_alpha") is None


def test_train_family_best_picks_the_larger_margin_and_keeps_the_loser_as_other(monkeypatch):
    linear_result = {"model_kind": "linear", "accuracy": 0.5, "baseline": 0.5, "n_scored": 50,
                      "n_train": 100, "n_test": 50}
    tree_result = {"model_kind": "tree", "accuracy": 0.9, "baseline": 0.5, "n_scored": 50,
                   "n_train": 100, "n_test": 50}
    monkeypatch.setattr(TC, "train_family", lambda groups, family, exclude=None: dict(linear_result))
    monkeypatch.setattr(TC, "train_family_tree", lambda groups, family, exclude=None: dict(tree_result))

    best = TC.train_family_best([], "meta_alpha")

    assert best["model_kind"] == "tree"
    assert best["other"]["model_kind"] == "linear"


def test_train_family_best_keeps_linear_on_a_tied_margin(monkeypatch):
    linear_result = {"model_kind": "linear", "accuracy": 0.7, "baseline": 0.5, "n_scored": 50,
                      "n_train": 100, "n_test": 50}
    tree_result = {"model_kind": "tree", "accuracy": 0.7, "baseline": 0.5, "n_scored": 50,
                   "n_train": 100, "n_test": 50}
    monkeypatch.setattr(TC, "train_family", lambda groups, family, exclude=None: dict(linear_result))
    monkeypatch.setattr(TC, "train_family_tree", lambda groups, family, exclude=None: dict(tree_result))

    best = TC.train_family_best([], "meta_alpha")

    assert best["model_kind"] == "linear"
    assert best["other"]["model_kind"] == "tree"


def test_train_family_best_falls_back_to_whichever_kind_trained(monkeypatch):
    tree_result = {"model_kind": "tree", "accuracy": 0.9, "baseline": 0.5, "n_scored": 50,
                   "n_train": 100, "n_test": 50}
    monkeypatch.setattr(TC, "train_family", lambda groups, family, exclude=None: None)
    monkeypatch.setattr(TC, "train_family_tree", lambda groups, family, exclude=None: dict(tree_result))

    best = TC.train_family_best([], "meta_alpha")

    assert best["model_kind"] == "tree"
    assert best["other"] is None


def test_export_tree_model_round_trip_matches_sklearn_decision_function(tmp_path):
    train_groups = _planted_groups("meta_alpha", n_groups=200, split="train", seed=7)
    test_groups = _planted_groups("meta_alpha", n_groups=40, split="test", seed=8)
    result = TC.train_family_tree(train_groups + test_groups, "meta_alpha")
    X_test, y_test, gid_test = TC.rows_for_family(test_groups, "meta_alpha", split="test")

    model_path = tmp_path / "meta_alpha.json"
    TC.export_tree_model(result["model"], FEATURE_NAMES, model_path)
    payload = json.loads(model_path.read_text())

    assert payload["model_type"] == "gbdt"
    assert payload["feature_names"] == list(FEATURE_NAMES)
    assert payload["feature_version"] == list(feature_version())
    assert len(payload["trees"]) == result["model"].n_estimators_

    from agents import clone_policy
    clone_policy._models.clear()
    weights_dir = tmp_path
    import shutil
    (weights_dir / "clone_weights").mkdir()
    shutil.copy(model_path, weights_dir / "clone_weights" / "meta_alpha.json")
    import agents.clone_policy as cp
    orig = cp._weights_dir
    cp._weights_dir = lambda: weights_dir / "clone_weights"
    try:
        expected = result["model"].decision_function(X_test)
        scored = cp.score_options(X_test.tolist(), "meta_alpha")
        assert scored is not None
        for got, want in zip(scored, expected):
            assert got == pytest.approx(want, abs=1e-9)
    finally:
        cp._weights_dir = orig
        cp._models.clear()


def test_main_exports_only_qualifying_families(tmp_path):
    strong_train = _planted_groups("meta_strong", n_groups=200, split="train", seed=4)
    strong_test = _planted_groups("meta_strong", n_groups=60, split="test", seed=5)
    # A "family" with no signal at all (every option's features are identical
    # zeros regardless of which one was played): the fitted model can only
    # score every option in a group equally, which degrades to "always pick
    # the first option" -- exactly the first-legal baseline, margin 0.0.
    rng = np.random.RandomState(6)
    weak_groups = []
    for i, split in enumerate((["train"] * 120) + (["test"] * 40)):
        n_options = int(rng.randint(2, 5))
        played = int(rng.randint(0, n_options))
        weak_groups.append({
            "features": [[0.0] * len(FEATURE_NAMES) for _ in range(n_options)],
            "played": played, "team": "topteam", "family": "meta_weak", "won": True,
            "episode": f"w{i}", "split": split,
        })

    npz_path = tmp_path / "clone_groups.npz"
    from tools.clone_dataset import write_npz
    write_npz(strong_train + strong_test + weak_groups, npz_path)

    out_dir = tmp_path / "weights"
    report_path = tmp_path / "clone_quality.md"
    rc = TC.main([str(npz_path), "--out-dir", str(out_dir), "--report", str(report_path),
                  "--min-test-groups", "20"])

    assert rc == 0
    assert (out_dir / "meta_strong.json").exists()
    assert not (out_dir / "meta_weak.json").exists()
    report = report_path.read_text()
    assert "meta_strong" in report and "meta_weak" in report
    assert "Qualified families (1): meta_strong" in report


def test_main_ablation_mode_skips_export_and_notes_report(tmp_path):
    train_groups = _planted_groups("meta_alpha", n_groups=200, split="train", seed=0, signal="opt_is_first")
    test_groups = _planted_groups("meta_alpha", n_groups=60, split="test", seed=1, signal="opt_is_first")

    npz_path = tmp_path / "clone_groups.npz"
    from tools.clone_dataset import write_npz
    write_npz(train_groups + test_groups, npz_path)

    out_dir = tmp_path / "weights"
    report_path = tmp_path / "clone_quality.md"
    rc = TC.main([str(npz_path), "--out-dir", str(out_dir), "--report", str(report_path),
                  "--min-test-groups", "20", "--exclude-features", "opt_is_first"])

    assert rc == 0
    assert not out_dir.exists() or not any(out_dir.iterdir())
    report = report_path.read_text()
    assert "Ablation mode" in report
    assert "opt_is_first" in report
    assert "no weights were exported" in report


def test_main_rejects_unknown_exclude_feature(tmp_path):
    groups = _planted_groups("meta_alpha", n_groups=10, split="train", seed=0)
    npz_path = tmp_path / "clone_groups.npz"
    from tools.clone_dataset import write_npz
    write_npz(groups, npz_path)

    with pytest.raises(ValueError):
        TC.main([str(npz_path), "--exclude-features", "not_a_real_feature"])
