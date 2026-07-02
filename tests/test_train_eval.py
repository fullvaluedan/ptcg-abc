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
from tools.train_eval import (
    compare_gauntlet_vs_merged,
    evaluate,
    export_model,
    fit_standardized,
    game_split,
    load_rows,
    load_source_column,
    parse_source_weights,
    sample_weights_for,
    write_ladder_ab_report,
)


def _write_csv(path, rows, source=None):
    header = ["game_id", "seat", "turn", *FEATURE_NAMES, "label"]
    if source is not None:
        header.append("source")
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for row in rows:
            writer.writerow([*row, source] if source is not None else row)
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


def test_load_rows_tags_game_ids_with_prefix(tmp_path):
    path = tmp_path / "states.csv"
    _write_csv(path, [["g0", 0, 1, *_feature_row(prize_diff=0.5), 1]])

    game_ids, _, _ = load_rows(path, tag_prefix="ladder")

    assert game_ids.tolist() == ["ladder:g0"]


def _prize_diff_dataset(n_games, rows_per_game, sign=1, seed=0):
    """n_games games, each rows_per_game rows, label agreeing with sign*prize_diff."""
    rng = np.random.RandomState(seed)
    rows = []
    for g in range(n_games):
        for _ in range(rows_per_game):
            diff = rng.uniform(-1, 1)
            label = 1 if (sign * diff) > 0 else 0
            rows.append([f"g{g}", 0, 1, *_feature_row(prize_diff=diff), label])
    return rows


def test_compare_gauntlet_vs_merged_picks_merged_when_ladder_agrees(tmp_path):
    gauntlet_csv = _write_csv(tmp_path / "gauntlet.csv", _prize_diff_dataset(30, 5, sign=1, seed=0))
    ladder_csv = _write_csv(
        tmp_path / "ladder.csv", _prize_diff_dataset(30, 5, sign=1, seed=1), source="ladder"
    )

    result = compare_gauntlet_vs_merged(gauntlet_csv, ladder_csv, test_frac=0.2, seed=0)

    assert result["picked"] == "merged"
    assert result["merged"]["metrics"]["auc"] >= result["gauntlet_only"]["metrics"]["auc"]
    assert result["merged"]["n_train"] > result["gauntlet_only"]["n_train"]
    assert result["n_ladder_rows"] == 30 * 5


def test_compare_gauntlet_vs_merged_picks_gauntlet_only_when_ladder_contradicts(tmp_path):
    gauntlet_csv = _write_csv(tmp_path / "gauntlet.csv", _prize_diff_dataset(30, 5, sign=1, seed=0))
    # far more contradicting rows than gauntlet rows, so the merged fit is pulled
    # toward the inverted (wrong, for the gauntlet test set) relationship.
    ladder_csv = _write_csv(
        tmp_path / "ladder.csv", _prize_diff_dataset(200, 5, sign=-1, seed=2), source="ladder"
    )

    result = compare_gauntlet_vs_merged(gauntlet_csv, ladder_csv, test_frac=0.2, seed=0)

    assert result["picked"] == "gauntlet_only"
    assert result["gauntlet_only"]["metrics"]["auc"] > result["merged"]["metrics"]["auc"]


def test_parse_source_weights_parses_pairs():
    assert parse_source_weights("top_player=2.0,ladder=1.5") == {"top_player": 2.0, "ladder": 1.5}
    assert parse_source_weights(None) == {}
    assert parse_source_weights("") == {}


def test_load_source_column_reads_source_or_blank_when_absent(tmp_path):
    with_source = _write_csv(
        tmp_path / "with_source.csv", [["g0", 0, 1, *_feature_row(prize_diff=0.5), 1]], source="top_player"
    )
    without_source = _write_csv(
        tmp_path / "without_source.csv", [["g0", 0, 1, *_feature_row(prize_diff=0.5), 1]]
    )

    assert load_source_column(with_source).tolist() == ["top_player"]
    assert load_source_column(without_source).tolist() == [""]


def test_sample_weights_for_defaults_missing_source_to_one():
    weights = sample_weights_for(["a", "b", ""], {"a": 2.0})
    assert weights.tolist() == [2.0, 1.0, 1.0]


def test_fit_standardized_accepts_sample_weight():
    X = np.array([[1.0], [1.0], [-1.0]])
    y = np.array([1, 1, 0])
    # unweighted: fits normally with no error
    model, mean, std = fit_standardized(X, y)
    assert model.coef_.shape == (1, 1)
    # weighted: still fits with no error, sample_weight plumbed through to sklearn
    weighted_model, _, _ = fit_standardized(X, y, sample_weight=np.array([1.0, 1.0, 5.0]))
    assert weighted_model.coef_.shape == (1, 1)


def test_compare_gauntlet_vs_merged_downweighting_contradicting_ladder_helps_merged(tmp_path):
    gauntlet_csv = _write_csv(tmp_path / "gauntlet.csv", _prize_diff_dataset(30, 5, sign=1, seed=0))
    ladder_csv = _write_csv(
        tmp_path / "ladder.csv", _prize_diff_dataset(200, 5, sign=-1, seed=2), source="ladder"
    )

    unweighted = compare_gauntlet_vs_merged(gauntlet_csv, ladder_csv, test_frac=0.2, seed=0)
    weighted = compare_gauntlet_vs_merged(
        gauntlet_csv, ladder_csv, test_frac=0.2, seed=0,
        source_weights={"ladder": 0.001, "gauntlet": 1.0},
    )

    assert unweighted["source_weights"] == {}
    assert weighted["source_weights"] == {"ladder": 0.001, "gauntlet": 1.0}
    # downweighting the contradicting ladder rows should pull the merged fit
    # back toward gauntlet-only quality, beating the unweighted merged AUC.
    assert weighted["merged"]["metrics"]["auc"] > unweighted["merged"]["metrics"]["auc"]


def test_write_ladder_ab_report_documents_source_weights_when_given(tmp_path):
    gauntlet_csv = _write_csv(tmp_path / "gauntlet.csv", _prize_diff_dataset(30, 5, sign=1, seed=0))
    ladder_csv = _write_csv(
        tmp_path / "ladder.csv", _prize_diff_dataset(30, 5, sign=1, seed=1), source="ladder"
    )
    result = compare_gauntlet_vs_merged(
        gauntlet_csv, ladder_csv, test_frac=0.2, seed=0, source_weights={"top_player": 2.0}
    )

    report_path = write_ladder_ab_report(result, tmp_path / "ladder_data_ab.md")
    text = report_path.read_text()
    assert "top_player: 2.0" in text


def test_write_ladder_ab_report_documents_the_verdict(tmp_path):
    gauntlet_csv = _write_csv(tmp_path / "gauntlet.csv", _prize_diff_dataset(30, 5, sign=1, seed=0))
    ladder_csv = _write_csv(
        tmp_path / "ladder.csv", _prize_diff_dataset(30, 5, sign=1, seed=1), source="ladder"
    )
    result = compare_gauntlet_vs_merged(gauntlet_csv, ladder_csv, test_frac=0.2, seed=0)

    report_path = write_ladder_ab_report(result, tmp_path / "ladder_data_ab.md")

    text = report_path.read_text()
    assert "gauntlet+ladder (merged)" in text
    assert "Verdict" in text
    assert f"{result['gauntlet_only']['metrics']['auc']:.4f}" in text
    assert f"{result['merged']['metrics']['auc']:.4f}" in text
