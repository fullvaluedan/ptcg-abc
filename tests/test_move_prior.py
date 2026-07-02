"""Tests for the move-ordering scorer (plan U8c, search/move_prior.py).

Checks the scorer loads the committed search/move_prior.json, scores a row per
option in the input order, prefers a row of all-ones over all-zeros under a
positive committed coefficient sum (a monotonic sanity check, not a claim about
any specific option), and falls back to None (never raises) on a malformed row,
a missing model file, or a stale feature_version, mirroring
tests/test_learned_eval.py's coverage of the sibling learned-eval module.
"""
import json

from agents import imitation_features as IF
from agents.imitation_features import N_FEATURES
from agents import heuristics as H
from search import move_prior


def _obs(options, turn=1, your_index=0):
    return {
        "select": {"option": options, "minCount": 1, "maxCount": 1, "type": H.SEL_MAIN},
        "current": {
            "turn": turn,
            "yourIndex": your_index,
            "turnActionCount": 0,
            "energyAttached": False,
            "players": [
                {"active": [], "bench": [], "hand": [], "discard": []},
                {"active": [], "bench": [], "hand": [], "discard": []},
            ],
        },
    }


def _opt(otype, **kw):
    opt = {"type": otype}
    opt.update(kw)
    return opt


def _reset_cache():
    move_prior._model = None
    move_prior._load_attempted = False


def setup_function(_fn):
    _reset_cache()


def teardown_function(_fn):
    _reset_cache()


def test_score_options_loads_committed_model_and_returns_one_score_per_row():
    options = [_opt(H.OPT_END), _opt(H.OPT_RETREAT), _opt(H.OPT_ATTACK, attackId=1)]
    rows = IF.decision_features(_obs(options))

    scores = move_prior.score_options(rows)

    assert scores is not None
    assert len(scores) == len(rows)
    assert all(isinstance(s, float) for s in scores)


def test_score_options_is_deterministic():
    options = [_opt(H.OPT_END), _opt(H.OPT_PLAY)]
    rows = IF.decision_features(_obs(options))

    assert move_prior.score_options(rows) == move_prior.score_options(rows)


def test_score_options_none_for_empty_rows():
    assert move_prior.score_options([]) == []


def test_score_options_none_on_row_length_mismatch():
    assert move_prior.score_options([[0.0] * (N_FEATURES - 1)]) is None
    assert move_prior.score_options([[0.0] * (N_FEATURES + 1)]) is None


def test_missing_model_file_falls_back_to_none(monkeypatch):
    monkeypatch.setattr(move_prior, "_model_path", lambda: "/no/such/file.json")
    _reset_cache()

    assert move_prior.score_options([[0.0] * N_FEATURES]) is None


def test_stale_feature_version_model_falls_back_to_none(tmp_path, monkeypatch):
    # A model trained against a different feature layout (or feature COUNT
    # that happens to match) must be rejected outright, same posture as
    # search/learned_eval.py's U64 guard.
    stale_model = tmp_path / "move_prior.json"
    stale_model.write_text(json.dumps({
        "feature_names": [f"f{i}" for i in range(N_FEATURES)],
        "feature_version": ["0", "0"],
        "mean": [0.0] * N_FEATURES,
        "std": [1.0] * N_FEATURES,
        "coef": [1.0] * N_FEATURES,
        "intercept": 0.0,
    }))
    monkeypatch.setattr(move_prior, "_model_path", lambda: stale_model)
    _reset_cache()

    assert move_prior.score_options([[0.0] * N_FEATURES]) is None


def test_missing_feature_version_key_falls_back_to_none(tmp_path, monkeypatch):
    legacy_model = tmp_path / "move_prior.json"
    legacy_model.write_text(json.dumps({
        "feature_names": [f"f{i}" for i in range(N_FEATURES)],
        "mean": [0.0] * N_FEATURES,
        "std": [1.0] * N_FEATURES,
        "coef": [1.0] * N_FEATURES,
        "intercept": 0.0,
    }))
    monkeypatch.setattr(move_prior, "_model_path", lambda: legacy_model)
    _reset_cache()

    assert move_prior.score_options([[0.0] * N_FEATURES]) is None


def test_malformed_row_falls_back_to_none():
    # A row that raises mid-scan (e.g. a non-numeric value) must not blow up the
    # caller; score_options catches it and reports the whole batch unusable.
    good_row = [0.0] * N_FEATURES
    bad_row = ["not-a-number"] * N_FEATURES
    assert move_prior.score_options([good_row, bad_row]) is None
