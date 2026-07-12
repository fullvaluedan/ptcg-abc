"""Tests for the pure-Python outcome-labeled option scorer
(search/learned_ranker.py), mirroring tests/test_learned_eval.py's posture for
the sibling state-level module: loads the committed search/ranker_model.json,
stays bounded, and returns None (never raises, never fabricates a neutral
score) on a malformed feature vector or a missing/stale/corrupt model file.
"""
import json

from agents.imitation_features import N_FEATURES, feature_version
from search import learned_ranker


def _reset_cache():
    learned_ranker._model = None
    learned_ranker._load_attempted = False


def setup_function(_fn):
    _reset_cache()


def teardown_function(_fn):
    _reset_cache()


def test_score_option_loads_committed_model_and_is_bounded():
    p = learned_ranker.score_option([0.0] * N_FEATURES)
    assert p is not None
    assert 0.0 <= p <= 1.0


def test_score_option_wrong_length_returns_none():
    assert learned_ranker.score_option([0.0] * (N_FEATURES - 1)) is None
    assert learned_ranker.score_option([]) is None


def test_score_option_missing_model_file_returns_none(monkeypatch):
    monkeypatch.setattr(learned_ranker, "_model_path", lambda: "/no/such/file.json")
    _reset_cache()
    assert learned_ranker.score_option([0.0] * N_FEATURES) is None


def test_score_option_stale_feature_version_returns_none(tmp_path, monkeypatch):
    stale_model = tmp_path / "ranker_model.json"
    stale_model.write_text(json.dumps({
        "model_type": "logreg",
        "feature_names": [f"f{i}" for i in range(N_FEATURES)],
        "feature_version": ["0", "0"],
        "mean": [0.0] * N_FEATURES,
        "std": [1.0] * N_FEATURES,
        "coef": [1.0] * N_FEATURES,
        "intercept": 0.0,
    }))
    monkeypatch.setattr(learned_ranker, "_model_path", lambda: stale_model)
    _reset_cache()
    assert learned_ranker.score_option([0.0] * N_FEATURES) is None


def test_score_option_missing_feature_version_key_returns_none(tmp_path, monkeypatch):
    legacy_model = tmp_path / "ranker_model.json"
    legacy_model.write_text(json.dumps({
        "model_type": "logreg",
        "feature_names": [f"f{i}" for i in range(N_FEATURES)],
        "mean": [0.0] * N_FEATURES,
        "std": [1.0] * N_FEATURES,
        "coef": [1.0] * N_FEATURES,
        "intercept": 0.0,
    }))
    monkeypatch.setattr(learned_ranker, "_model_path", lambda: legacy_model)
    _reset_cache()
    assert learned_ranker.score_option([0.0] * N_FEATURES) is None


def test_score_option_unknown_model_type_returns_none(tmp_path, monkeypatch):
    bad_model = tmp_path / "ranker_model.json"
    bad_model.write_text(json.dumps({
        "model_type": "not_a_real_type",
        "feature_names": [f"f{i}" for i in range(N_FEATURES)],
        "feature_version": list(feature_version()),
        "mean": [0.0] * N_FEATURES,
        "std": [1.0] * N_FEATURES,
    }))
    monkeypatch.setattr(learned_ranker, "_model_path", lambda: bad_model)
    _reset_cache()
    assert learned_ranker.score_option([0.0] * N_FEATURES) is None


def test_score_option_logreg_roundtrip(tmp_path, monkeypatch):
    model = tmp_path / "ranker_model.json"
    model.write_text(json.dumps({
        "model_type": "logreg",
        "feature_names": ["a", "b", "c"],
        "feature_version": ["v", "t"],
        "mean": [0.0, 0.0, 0.0],
        "std": [1.0, 1.0, 1.0],
        "coef": [1.0, 0.0, 0.0],
        "intercept": 0.0,
    }))
    monkeypatch.setattr(learned_ranker, "_model_path", lambda: model)
    monkeypatch.setattr(learned_ranker, "_imitation_feature_version", lambda: ("v", "t"))
    _reset_cache()
    # coef=[1,0,0], intercept=0 -> sigmoid(x0); a large positive x0 pushes p -> 1.
    p_high = learned_ranker.score_option([10.0, 0.0, 0.0])
    p_low = learned_ranker.score_option([-10.0, 0.0, 0.0])
    assert p_high > 0.9
    assert p_low < 0.1


def test_score_option_mlp_roundtrip(tmp_path, monkeypatch):
    # One hidden unit, identity-like wiring: hidden = relu(x0), output = hidden.
    # A positive x0 should score high, a negative x0 (relu clamps to 0) neutral-ish.
    model = tmp_path / "ranker_model.json"
    model.write_text(json.dumps({
        "model_type": "mlp",
        "feature_names": ["a"],
        "feature_version": ["v", "t"],
        "mean": [0.0],
        "std": [1.0],
        "w0": [[1.0]],
        "b0": [0.0],
        "w1": [10.0],
        "b1": -5.0,
    }))
    monkeypatch.setattr(learned_ranker, "_model_path", lambda: model)
    monkeypatch.setattr(learned_ranker, "_imitation_feature_version", lambda: ("v", "t"))
    _reset_cache()
    p_pos = learned_ranker.score_option([5.0])   # hidden=5, z=10*5-5=45 -> ~1
    p_neg = learned_ranker.score_option([-5.0])  # hidden=0 (relu), z=-5 -> low
    assert p_pos > 0.99
    assert p_neg < 0.5
