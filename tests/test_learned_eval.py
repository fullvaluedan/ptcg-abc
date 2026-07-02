"""Tests for the learned win-probability predictor (plan U4, search/learned_eval.py).

Checks the predictor loads the committed search/eval_model.json, returns a
win probability in [0, 1] and a value in [-1, 1] for a normal state, and falls
back to a neutral estimate (never raises) on a malformed state or a missing
model file.
"""
import json

from search import learned_eval


def _pokemon(hp, max_hp, energy_count=0):
    return {"hp": hp, "maxHp": max_hp, "energyCards": [{"id": 1}] * energy_count}


def _player(prizes=6, deck_count=50, hand_count=5, active=None, bench=None):
    return {
        "prize": [None] * prizes,
        "deckCount": deck_count,
        "handCount": hand_count,
        "active": [active] if active else [],
        "bench": bench or [],
    }


def _state(players, turn=3, first_player=0):
    return {
        "turn": turn,
        "firstPlayer": first_player,
        "supporterPlayed": False,
        "energyAttached": False,
        "players": players,
    }


def _reset_cache():
    learned_eval._model = None
    learned_eval._load_attempted = False


def setup_function(_fn):
    _reset_cache()


def teardown_function(_fn):
    _reset_cache()


def test_predict_win_probability_loads_committed_model_and_is_bounded():
    me = _player(prizes=2, active=_pokemon(100, 120, energy_count=2),
                 bench=[_pokemon(90, 90)])
    opp = _player(prizes=5, active=_pokemon(20, 100, energy_count=1))
    state = _state([me, opp])

    p = learned_eval.predict_win_probability(state, 0)

    assert 0.0 <= p <= 1.0


def test_predict_value_is_bounded_and_maps_probability():
    me = _player(prizes=2, active=_pokemon(100, 120), bench=[_pokemon(90, 90)])
    opp = _player(prizes=5, active=_pokemon(20, 100))
    state = _state([me, opp])

    p = learned_eval.predict_win_probability(state, 0)
    v = learned_eval.predict_value(state, 0)

    assert -1.0 <= v <= 1.0
    assert v == 2.0 * p - 1.0


def test_leading_state_scores_above_trailing_state():
    # We are two prizes ahead with a healthier board; the model should say we
    # are more likely to win than a mirrored state where the opponent leads.
    strong = _player(prizes=1, active=_pokemon(120, 120, energy_count=2),
                      bench=[_pokemon(100, 100), _pokemon(100, 100)])
    weak = _player(prizes=5, active=_pokemon(20, 120))
    leading = _state([strong, weak])
    trailing = _state([weak, strong])

    assert (learned_eval.predict_win_probability(leading, 0)
            > learned_eval.predict_win_probability(trailing, 0))


def test_malformed_state_stays_bounded_not_exception():
    # ptcg_agent.features never raises on a malformed state (it falls back to a
    # zero vector), so these score as a degenerate but legitimate state rather
    # than hitting learned_eval's own neutral fallback; the contract under test
    # here is "never raises, stays in range", not a specific neutral value.
    for state, idx in ((None, 0), ({"players": "not-a-list"}, 0), ({}, 5)):
        v = learned_eval.predict_value(state, idx)
        p = learned_eval.predict_win_probability(state, idx)
        assert -1.0 <= v <= 1.0
        assert 0.0 <= p <= 1.0


def test_feature_extraction_failure_falls_back_to_neutral(monkeypatch):
    def _boom(_state, _idx):
        raise RuntimeError("simulated extractor failure")

    monkeypatch.setattr(learned_eval, "extract_features", _boom)

    assert learned_eval.predict_win_probability({}, 0) == 0.5
    assert learned_eval.predict_value({}, 0) == 0.0


def test_missing_model_file_falls_back_to_neutral(monkeypatch):
    monkeypatch.setattr(learned_eval, "_model_path", lambda: "/no/such/file.json")
    _reset_cache()

    me = _player(prizes=1, active=_pokemon(120, 120))
    opp = _player(prizes=5, active=_pokemon(20, 120))
    state = _state([me, opp])

    assert learned_eval.predict_win_probability(state, 0) == 0.5
    assert learned_eval.predict_value(state, 0) == 0.0


def test_stale_feature_version_model_falls_back_to_neutral(tmp_path, monkeypatch):
    # Plan U64: a model exported before the feature-layout change (or one
    # otherwise trained against a different feature set) must be rejected
    # outright rather than scored with a mismatched mean/std/coef array, even
    # if it happens to carry the same feature COUNT.
    from ptcg_agent.features import N_FEATURES

    stale_model = tmp_path / "eval_model.json"
    stale_model.write_text(json.dumps({
        "feature_names": [f"f{i}" for i in range(N_FEATURES)],
        "feature_version": "0",
        "mean": [0.0] * N_FEATURES,
        "std": [1.0] * N_FEATURES,
        "coef": [1.0] * N_FEATURES,
        "intercept": 0.0,
    }))
    monkeypatch.setattr(learned_eval, "_model_path", lambda: stale_model)
    _reset_cache()

    me = _player(prizes=1, active=_pokemon(120, 120))
    opp = _player(prizes=5, active=_pokemon(20, 120))
    state = _state([me, opp])

    assert learned_eval.predict_win_probability(state, 0) == 0.5
    assert learned_eval.predict_value(state, 0) == 0.0


def test_missing_feature_version_key_falls_back_to_neutral(tmp_path, monkeypatch):
    # A model exported by the pre-U64 tools/train_eval.py never wrote a
    # feature_version key at all; payload.get(...) reads that as None, which
    # never equals the current FEATURE_VERSION string, so this also rejects.
    from ptcg_agent.features import N_FEATURES

    legacy_model = tmp_path / "eval_model.json"
    legacy_model.write_text(json.dumps({
        "feature_names": [f"f{i}" for i in range(N_FEATURES)],
        "mean": [0.0] * N_FEATURES,
        "std": [1.0] * N_FEATURES,
        "coef": [1.0] * N_FEATURES,
        "intercept": 0.0,
    }))
    monkeypatch.setattr(learned_eval, "_model_path", lambda: legacy_model)
    _reset_cache()

    me = _player(prizes=1, active=_pokemon(120, 120))
    opp = _player(prizes=5, active=_pokemon(20, 120))
    state = _state([me, opp])

    assert learned_eval.predict_win_probability(state, 0) == 0.5
