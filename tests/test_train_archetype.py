"""Tests for the archetype classifier training/export script (plan U9b,
tools/train_archetype.py).

Covers the pieces the plan gates on: load_rows reads game_id/label/feature
columns from an archetype_rows CSV, fit_standardized_multiclass fits a
one-vs-rest logistic regression, majority_baseline computes the gate's
comparison point, and export_model writes a JSON U9c's scorer can load.
"""
import csv
import json

import numpy as np

from analysis.early_archetype_features import FEATURE_NAMES, feature_version
from tools.train_archetype import (
    evaluate_seed,
    export_model,
    fit_standardized_multiclass,
    load_rows,
    majority_baseline,
    multi_seed_gate,
)
from tools.train_eval import game_split


def _feature_row(**overrides):
    values = [0.0] * len(FEATURE_NAMES)
    for name, value in overrides.items():
        values[FEATURE_NAMES.index(name)] = value
    return values


def _write_csv(path, rows):
    header = ["game_id", "label", *FEATURE_NAMES, "source"]
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for game_id, label, feats in rows:
            writer.writerow([game_id, label, *feats, "ladder"])
    return path


def _separable_dataset(n_per_label=20, seed=0):
    """Games whose label is perfectly predictable from opp_bench_count alone:
    label 'a' always has opp_bench_count 0, label 'b' always has 5, so a
    fitted model should score this near-perfectly.
    """
    rng = np.random.RandomState(seed)
    rows = []
    counter = 0
    for label, bench in (("a", 0.0), ("b", 5.0)):
        for _ in range(n_per_label):
            noise = float(rng.uniform(-0.01, 0.01))
            feats = _feature_row(opp_bench_count=bench + noise)
            rows.append((f"g{counter}", label, feats))
            counter += 1
    return rows


def test_load_rows_reads_features_and_string_labels(tmp_path):
    rows = [("g0", "archaludon", _feature_row(opp_bench_count=2.0))]
    path = _write_csv(tmp_path / "arch.csv", rows)

    game_ids, X, y = load_rows(path)

    assert game_ids.tolist() == ["g0"]
    assert X.shape == (1, len(FEATURE_NAMES))
    assert y.tolist() == ["archaludon"]
    assert X[0, FEATURE_NAMES.index("opp_bench_count")] == 2.0


def test_load_rows_tags_game_ids_with_prefix(tmp_path):
    rows = [("g0", "other", _feature_row())]
    path = _write_csv(tmp_path / "arch.csv", rows)

    game_ids, _, _ = load_rows(path, tag_prefix="ladder")

    assert game_ids.tolist() == ["ladder:g0"]


def test_majority_baseline_predicts_most_common_train_label():
    y_train = np.array(["a", "a", "a", "b"])
    y_test = np.array(["a", "a", "b"])

    accuracy, label = majority_baseline(y_train, y_test)

    assert label == "a"
    assert accuracy == 2 / 3


def test_majority_baseline_empty_returns_zero():
    accuracy, label = majority_baseline(np.array([]), np.array([]))
    assert accuracy == 0.0
    assert label is None


def test_evaluate_seed_returns_metrics_and_fitted_model(tmp_path):
    rows = _separable_dataset(n_per_label=20, seed=0)
    path = _write_csv(tmp_path / "arch.csv", rows)
    game_ids, X, y = load_rows(path)

    result = evaluate_seed(game_ids, X, y, test_frac=0.2, seed=0)

    assert result["seed"] == 0
    assert result["total"] > 0
    assert result["correct"] <= result["total"]
    assert result["n_train_games"] + result["n_test_games"] == len(set(game_ids.tolist()))
    assert hasattr(result["model"], "predict")


def test_multi_seed_gate_passes_on_separable_data(tmp_path):
    rows = _separable_dataset(n_per_label=20, seed=0)
    path = _write_csv(tmp_path / "arch.csv", rows)
    game_ids, X, y = load_rows(path)

    results, mean_accuracy, mean_baseline, passed = multi_seed_gate(
        game_ids, X, y, seeds=(0, 1, 2), test_frac=0.2, margin=0.05
    )

    assert len(results) == 3
    assert passed
    assert mean_accuracy - mean_baseline >= 0.05


def test_multi_seed_gate_fails_when_features_carry_no_signal(tmp_path):
    # Same feature vector for every row regardless of label: no amount of
    # fitting can beat the majority baseline, so the mean margin must be ~0.
    rows = [(f"g{i}", "a" if i % 2 == 0 else "b", _feature_row()) for i in range(60)]
    path = _write_csv(tmp_path / "arch.csv", rows)
    game_ids, X, y = load_rows(path)

    results, mean_accuracy, mean_baseline, passed = multi_seed_gate(
        game_ids, X, y, seeds=(0, 1, 2), test_frac=0.2, margin=0.05
    )

    assert not passed


def test_fitted_model_beats_baseline_on_separable_data(tmp_path):
    rows = _separable_dataset(n_per_label=20, seed=0)
    path = _write_csv(tmp_path / "arch.csv", rows)

    game_ids, X, y = load_rows(path)
    train_mask, test_mask = game_split(game_ids, test_frac=0.2, seed=0)
    model, mean, std = fit_standardized_multiclass(X[train_mask], y[train_mask])
    preds = model.predict((X[test_mask] - mean) / std)

    accuracy = float(np.mean(preds == y[test_mask]))
    baseline, _ = majority_baseline(y[train_mask], y[test_mask])

    assert accuracy > baseline + 0.3  # the signal is perfectly separable; a wide margin


def test_export_model_writes_expected_payload(tmp_path):
    rows = _separable_dataset(n_per_label=15, seed=1)
    path = _write_csv(tmp_path / "arch.csv", rows)
    _, X, y = load_rows(path)
    model, mean, std = fit_standardized_multiclass(X, y)

    model_path = tmp_path / "archetype_prior.json"
    export_model(model, mean, std, model_path)
    payload = json.loads(model_path.read_text())

    assert payload["feature_names"] == list(FEATURE_NAMES)
    assert payload["feature_version"] == feature_version()
    assert sorted(payload["labels"]) == ["a", "b"]
    assert len(payload["mean"]) == len(FEATURE_NAMES)
    assert len(payload["std"]) == len(FEATURE_NAMES)
    assert len(payload["coef"]) == len(payload["labels"])
    assert all(len(row) == len(FEATURE_NAMES) for row in payload["coef"])
    assert len(payload["intercept"]) == len(payload["labels"])


def test_export_model_coef_rows_align_with_labels_order(tmp_path):
    rows = _separable_dataset(n_per_label=15, seed=2)
    path = _write_csv(tmp_path / "arch.csv", rows)
    _, X, y = load_rows(path)
    model, mean, std = fit_standardized_multiclass(X, y)

    model_path = tmp_path / "archetype_prior.json"
    export_model(model, mean, std, model_path)
    payload = json.loads(model_path.read_text())

    assert payload["labels"] == list(model.classes_)
