"""Tests for the per-family clone-policy scorer (plan U71, agents/clone_policy.py).

Mirrors tests/test_move_prior.py's coverage of the sibling move-ordering
scorer: loading a committed weight file, scoring a row per option in input
order, and falling back safely (score_options -> None, choose_index -> 0,
the first legal option) on a missing family, a stale feature_version, or a
malformed row. Never touches the committed agents/clone_weights/ directory;
every test points the module at a tmp_path weights dir via monkeypatch.
"""
import json

import pytest

from agents import clone_policy


def _reset_cache():
    clone_policy._models.clear()


def setup_function(_fn):
    _reset_cache()


def teardown_function(_fn):
    _reset_cache()


def _write_model(path, n_features, feature_version, coef=None, intercept=0.0):
    payload = {
        "feature_names": [f"f{i}" for i in range(n_features)],
        "feature_version": list(feature_version),
        "mean": [0.0] * n_features,
        "std": [1.0] * n_features,
        "coef": coef if coef is not None else [1.0] * n_features,
        "intercept": intercept,
    }
    path.write_text(json.dumps(payload))
    return path


def test_score_options_loads_committed_family_and_returns_one_score_per_row(tmp_path, monkeypatch):
    from agents.imitation_features import N_FEATURES, feature_version
    weights_dir = tmp_path / "clone_weights"
    weights_dir.mkdir()
    _write_model(weights_dir / "meta_alpha.json", N_FEATURES, feature_version())
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: weights_dir)

    rows = [[0.0] * N_FEATURES, [1.0] * N_FEATURES, [0.5] * N_FEATURES]
    scores = clone_policy.score_options(rows, "meta_alpha")

    assert scores is not None
    assert len(scores) == len(rows)
    assert all(isinstance(s, float) for s in scores)


def test_score_options_is_deterministic(tmp_path, monkeypatch):
    from agents.imitation_features import N_FEATURES, feature_version
    weights_dir = tmp_path / "clone_weights"
    weights_dir.mkdir()
    _write_model(weights_dir / "meta_alpha.json", N_FEATURES, feature_version())
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: weights_dir)

    rows = [[0.0] * N_FEATURES, [1.0] * N_FEATURES]
    assert clone_policy.score_options(rows, "meta_alpha") == clone_policy.score_options(rows, "meta_alpha")


def test_score_options_none_for_empty_rows(tmp_path, monkeypatch):
    from agents.imitation_features import N_FEATURES, feature_version
    weights_dir = tmp_path / "clone_weights"
    weights_dir.mkdir()
    _write_model(weights_dir / "meta_alpha.json", N_FEATURES, feature_version())
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: weights_dir)

    assert clone_policy.score_options([], "meta_alpha") == []


def test_score_options_none_for_unknown_family(tmp_path, monkeypatch):
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: tmp_path / "clone_weights")

    assert clone_policy.score_options([[0.0]], "no_such_family") is None


def test_score_options_none_on_row_length_mismatch(tmp_path, monkeypatch):
    from agents.imitation_features import N_FEATURES, feature_version
    weights_dir = tmp_path / "clone_weights"
    weights_dir.mkdir()
    _write_model(weights_dir / "meta_alpha.json", N_FEATURES, feature_version())
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: weights_dir)

    assert clone_policy.score_options([[0.0] * (N_FEATURES - 1)], "meta_alpha") is None
    assert clone_policy.score_options([[0.0] * (N_FEATURES + 1)], "meta_alpha") is None


def test_stale_feature_version_model_falls_back_to_none(tmp_path, monkeypatch):
    from agents.imitation_features import N_FEATURES
    weights_dir = tmp_path / "clone_weights"
    weights_dir.mkdir()
    _write_model(weights_dir / "meta_alpha.json", N_FEATURES, ("0", "0"))
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: weights_dir)

    assert clone_policy.score_options([[0.0] * N_FEATURES], "meta_alpha") is None


def test_malformed_row_falls_back_to_none(tmp_path, monkeypatch):
    from agents.imitation_features import N_FEATURES, feature_version
    weights_dir = tmp_path / "clone_weights"
    weights_dir.mkdir()
    _write_model(weights_dir / "meta_alpha.json", N_FEATURES, feature_version())
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: weights_dir)

    good_row = [0.0] * N_FEATURES
    bad_row = ["not-a-number"] * N_FEATURES
    assert clone_policy.score_options([good_row, bad_row], "meta_alpha") is None


def test_available_families_lists_weight_files_present_on_disk(tmp_path, monkeypatch):
    weights_dir = tmp_path / "clone_weights"
    weights_dir.mkdir()
    (weights_dir / "meta_alpha.json").write_text("{}")
    (weights_dir / "meta_beta.json").write_text("{}")
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: weights_dir)

    assert clone_policy.available_families() == ["meta_alpha", "meta_beta"]


def test_available_families_empty_when_dir_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: tmp_path / "no_such_dir")

    assert clone_policy.available_families() == []


def test_choose_index_never_raises_and_falls_back_to_zero_for_unknown_family(tmp_path, monkeypatch):
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: tmp_path / "clone_weights")

    assert clone_policy.choose_index([[0.0], [1.0], [2.0]], "no_such_family") == 0


def test_choose_index_falls_back_to_zero_on_malformed_rows(tmp_path, monkeypatch):
    from agents.imitation_features import N_FEATURES, feature_version
    weights_dir = tmp_path / "clone_weights"
    weights_dir.mkdir()
    _write_model(weights_dir / "meta_alpha.json", N_FEATURES, feature_version())
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: weights_dir)

    bad_row = ["not-a-number"] * N_FEATURES
    assert clone_policy.choose_index([bad_row], "meta_alpha") == 0


def test_choose_index_returns_zero_for_empty_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: tmp_path / "clone_weights")

    assert clone_policy.choose_index([], "meta_alpha") == 0


def _write_gbdt_model(path, n_features, feature_version, trees, learning_rate=1.0, init_score=0.0):
    payload = {
        "model_type": "gbdt",
        "feature_names": [f"f{i}" for i in range(n_features)],
        "feature_version": list(feature_version),
        "learning_rate": learning_rate,
        "init_score": init_score,
        "trees": trees,
    }
    path.write_text(json.dumps(payload))
    return path


def _single_split_tree(feature_idx, threshold, left_value, right_value):
    """A depth-1 tree: node 0 splits on feature_idx <= threshold, else right leaf."""
    return {
        "feature": [feature_idx, -2, -2],
        "threshold": [threshold, -2.0, -2.0],
        "left": [1, -1, -1],
        "right": [2, -1, -1],
        "value": [0.0, left_value, right_value],
    }


def test_score_options_scores_gbdt_model_by_walking_the_tree(tmp_path, monkeypatch):
    from agents.imitation_features import feature_version
    weights_dir = tmp_path / "clone_weights"
    weights_dir.mkdir()
    tree = _single_split_tree(feature_idx=0, threshold=0.5, left_value=-1.0, right_value=2.0)
    _write_gbdt_model(weights_dir / "meta_alpha.json", 2, feature_version(), trees=[tree],
                       learning_rate=1.0, init_score=0.0)
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: weights_dir)

    below = [0.0, 0.0]   # feature 0 <= 0.5 -> left leaf, -1.0
    above = [1.0, 0.0]   # feature 0 > 0.5 -> right leaf, 2.0
    scores = clone_policy.score_options([below, above], "meta_alpha")

    assert scores == [-1.0, 2.0]


def test_score_options_gbdt_applies_learning_rate_and_init_score(tmp_path, monkeypatch):
    from agents.imitation_features import feature_version
    weights_dir = tmp_path / "clone_weights"
    weights_dir.mkdir()
    tree = _single_split_tree(feature_idx=0, threshold=0.5, left_value=-1.0, right_value=2.0)
    _write_gbdt_model(weights_dir / "meta_alpha.json", 2, feature_version(), trees=[tree, tree],
                       learning_rate=0.5, init_score=1.0)
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: weights_dir)

    scores = clone_policy.score_options([[1.0, 0.0]], "meta_alpha")

    # init_score 1.0 + 0.5 * (2.0 + 2.0) == 3.0
    assert scores == pytest.approx([3.0])


def test_score_options_gbdt_none_on_malformed_tree_arrays(tmp_path, monkeypatch):
    from agents.imitation_features import feature_version
    weights_dir = tmp_path / "clone_weights"
    weights_dir.mkdir()
    bad_tree = {"feature": [0, -2, -2], "threshold": [0.5, -2.0], "left": [1, -1, -1],
                "right": [2, -1, -1], "value": [0.0, -1.0, 2.0]}  # threshold too short
    _write_gbdt_model(weights_dir / "meta_alpha.json", 2, feature_version(), trees=[bad_tree])
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: weights_dir)

    assert clone_policy.score_options([[0.0, 0.0]], "meta_alpha") is None


def test_choose_index_picks_the_highest_scoring_gbdt_option(tmp_path, monkeypatch):
    from agents.imitation_features import feature_version
    weights_dir = tmp_path / "clone_weights"
    weights_dir.mkdir()
    tree = _single_split_tree(feature_idx=0, threshold=0.5, left_value=-1.0, right_value=2.0)
    _write_gbdt_model(weights_dir / "meta_alpha.json", 2, feature_version(), trees=[tree])
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: weights_dir)

    rows = [[0.0, 0.0], [1.0, 0.0], [0.0, 0.0]]
    assert clone_policy.choose_index(rows, "meta_alpha") == 1


def test_choose_index_picks_the_highest_scoring_option(tmp_path, monkeypatch):
    from agents.imitation_features import N_FEATURES, feature_version
    weights_dir = tmp_path / "clone_weights"
    weights_dir.mkdir()
    # coef all positive: an all-ones row scores higher than an all-zeros row.
    _write_model(weights_dir / "meta_alpha.json", N_FEATURES, feature_version(), coef=[1.0] * N_FEATURES)
    monkeypatch.setattr(clone_policy, "_weights_dir", lambda: weights_dir)

    rows = [[0.0] * N_FEATURES, [1.0] * N_FEATURES, [0.0] * N_FEATURES]
    assert clone_policy.choose_index(rows, "meta_alpha") == 1
