"""Tests for the training/export script (plan U4, tools/train_eval.py).

Covers the two things the plan gates on: the game-level split never lets one
game straddle train and test (row-level splitting would leak near-duplicate
states across the boundary), and export_model writes a JSON that
search/learned_eval.py can load and score identically to the sklearn model it
came from.
"""
import csv
import json

import numpy as np
import pytest

from ptcg_agent.features import FEATURE_NAMES
from search import learned_eval
from tools.train_eval import evaluate, export_model, fit_standardized, game_split, load_rows


def _write_csv(path, rows):
    header = ["game_id", "seat", "turn", *FEATURE_NAMES, "label"]
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def _feature_row(**overrides):
    values = [0.0] * len(FEATURE_NAMES)
    for name, value in overrides.items():
        values[FEATURE_NAMES.index(name)] = value
    return values


def test_game_split_partitions_rows_without_splitting_a_game():
    game_ids = np.array([f"g{i}" for i in range(20) for _ in range(5)])  # 100 rows, 20 games
    train_mask, test_mask = game_split(game_ids, test_frac=0.2, seed=0)

    assert (train_mask | test_mask).all()
    assert not (train_mask & test_mask).any()
    train_games = set(game_ids[train_mask].tolist())
    test_games = set(game_ids[test_mask].tolist())
    assert train_games.isdisjoint(test_games)
    assert len(test_games) == 4  # 20% of 20 games


def test_load_rows_reads_features_and_labels(tmp_path):
    path = tmp_path / "states.csv"
    rows = [
        ["g0", 0, 1, *_feature_row(prize_diff=0.5, turn_number=1.0), 1],
        ["g0", 1, 1, *_feature_row(prize_diff=-0.5, turn_number=1.0), 0],
        ["g1", 0, 2, *_feature_row(prize_diff=0.2, turn_number=2.0), 0],
    ]
    _write_csv(path, rows)

    game_ids, X, y = load_rows(path)

    assert game_ids.tolist() == ["g0", "g0", "g1"]
    assert X.shape == (3, len(FEATURE_NAMES))
    assert y.tolist() == [1, 0, 0]
    prize_idx = FEATURE_NAMES.index("prize_diff")
    assert X[0, prize_idx] == 0.5


def test_exported_model_round_trips_through_learned_eval(tmp_path, monkeypatch):
    rng = np.random.RandomState(0)
    n = 200
    prize_idx = FEATURE_NAMES.index("prize_diff")
    X = np.zeros((n, len(FEATURE_NAMES)))
    X[:, prize_idx] = rng.uniform(-1, 1, size=n)
    y = (X[:, prize_idx] > 0).astype(int)

    model, mean, std = fit_standardized(X, y)
    metrics = evaluate(model, mean, std, X, y)
    assert metrics["auc"] > 0.9  # sanity: the synthetic signal is easy to fit

    model_path = tmp_path / "eval_model.json"
    export_model(model, mean, std, model_path)
    payload = json.loads(model_path.read_text())
    assert payload["feature_names"] == list(FEATURE_NAMES)
    assert len(payload["coef"]) == len(FEATURE_NAMES)

    monkeypatch.setattr(learned_eval, "_model_path", lambda: model_path)
    learned_eval._model = None
    learned_eval._load_attempted = False
    try:
        state = {
            "turn": 1,
            "firstPlayer": 0,
            "supporterPlayed": False,
            "energyAttached": False,
            "players": [
                {"prize": [None] * 2, "deckCount": 50, "handCount": 5,
                 "active": [{"hp": 100, "maxHp": 100, "energyCards": []}], "bench": []},
                {"prize": [None] * 5, "deckCount": 50, "handCount": 5,
                 "active": [{"hp": 100, "maxHp": 100, "energyCards": []}], "bench": []},
            ],
        }
        p_learned = learned_eval.predict_win_probability(state, 0)

        from ptcg_agent.features import extract_features
        features = extract_features(state, 0)
        p_sklearn = model.predict_proba([(np.array(features) - mean) / std])[0, 1]

        assert p_learned == pytest.approx(p_sklearn, abs=1e-9)
    finally:
        learned_eval._model = None
        learned_eval._load_attempted = False
