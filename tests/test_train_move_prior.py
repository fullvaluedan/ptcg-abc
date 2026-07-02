"""Tests for the move-ordering training/export script (plan U8b, tools/train_move_prior.py).

Covers the pieces the plan gates on: group_keys keep each decision's option
rows together across a train/test split, top1_accuracy/random_baseline score
only well-formed decision groups (exactly one is_chosen row), and
export_model writes a JSON search/move_prior.py (U8c) can load.
"""
import csv
import json

import numpy as np

from agents.imitation_features import FEATURE_NAMES, feature_version
from tools.train_move_prior import (
    export_model,
    load_pooled,
    load_rows,
    random_baseline,
    top1_accuracy,
)
from tools.train_eval import fit_standardized, game_split


def _feature_row(**overrides):
    values = [0.0] * len(FEATURE_NAMES)
    for name, value in overrides.items():
        values[FEATURE_NAMES.index(name)] = value
    return values


def _write_csv(path, rows, source=None):
    header = ["game_id", "seat", "decision_id", "n_options", "option_index", "is_chosen", *FEATURE_NAMES]
    if source is not None:
        header.append("source")
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for row in rows:
            writer.writerow([*row, source] if source is not None else row)
    return path


def _decision_rows(game_id, decision_id, n_options, chosen_idx, signal="is_play", seat=0):
    rows = []
    for i in range(n_options):
        feat = _feature_row(**{signal: 1.0 if i == chosen_idx else 0.0})
        rows.append([game_id, seat, decision_id, n_options, i, 1 if i == chosen_idx else 0, *feat])
    return rows


def _perfectly_separable_dataset(n_games, decisions_per_game, seed=0):
    """Games whose decisions all have a `is_play` feature that lights up on the
    chosen option and no other, so a fitted model should score it near-perfectly.
    """
    rng = np.random.RandomState(seed)
    rows = []
    for g in range(n_games):
        for d in range(decisions_per_game):
            n_options = int(rng.randint(2, 5))
            chosen = int(rng.randint(0, n_options))
            rows.extend(_decision_rows(f"g{g}", d, n_options, chosen))
    return rows


def test_load_rows_reads_features_group_keys_and_labels(tmp_path):
    path = _write_csv(tmp_path / "moves.csv", _decision_rows("g0", 0, 3, chosen_idx=1))

    game_ids, group_keys, X, y = load_rows(path)

    assert game_ids.tolist() == ["g0", "g0", "g0"]
    assert group_keys.tolist() == ["g0:0", "g0:0", "g0:0"]
    assert X.shape == (3, len(FEATURE_NAMES))
    assert y.tolist() == [0, 1, 0]
    play_idx = FEATURE_NAMES.index("is_play")
    assert X[1, play_idx] == 1.0


def test_load_rows_tags_game_ids_and_group_keys_with_prefix(tmp_path):
    path = _write_csv(tmp_path / "moves.csv", _decision_rows("g0", 0, 2, chosen_idx=0))

    game_ids, group_keys, _, _ = load_rows(path, tag_prefix="ladder")

    assert game_ids.tolist() == ["ladder:g0", "ladder:g0"]
    assert group_keys.tolist() == ["ladder:g0:0", "ladder:g0:0"]


def test_load_pooled_tags_each_file_with_its_own_stem_to_avoid_collisions(tmp_path):
    # Two different files both using game_id "g0": without a per-file prefix,
    # pooling would silently merge two unrelated games onto the same id.
    path_a = _write_csv(tmp_path / "batch_a.csv", _decision_rows("g0", 0, 2, chosen_idx=0))
    path_b = _write_csv(tmp_path / "batch_b.csv", _decision_rows("g0", 0, 2, chosen_idx=1))

    game_ids, group_keys, X, y = load_pooled([str(path_a), str(path_b)])

    assert len(set(game_ids.tolist())) == 2
    assert len(set(group_keys.tolist())) == 2
    assert X.shape == (4, len(FEATURE_NAMES))
    assert y.tolist() == [1, 0, 0, 1]


def test_top1_accuracy_counts_correct_argmax_per_decision():
    # Two decisions: scores correctly rank the chosen option in one, not the other.
    scores = np.array([0.1, 0.9, 0.7, 0.2])
    y = np.array([0, 1, 1, 0])
    group_keys = np.array(["d0", "d0", "d1", "d1"])

    accuracy, n_scored = top1_accuracy(scores, y, group_keys)

    assert n_scored == 2
    assert accuracy == 1.0  # d0's argmax (idx 1) is chosen; d1's argmax (idx 2) is chosen


def test_top1_accuracy_skips_groups_without_exactly_one_chosen():
    scores = np.array([0.1, 0.9, 0.5, 0.5, 0.3])
    y = np.array([0, 0, 1, 1, 0])  # d0: no chosen row; d1: two chosen rows
    group_keys = np.array(["d0", "d0", "d1", "d1", "d1"])

    accuracy, n_scored = top1_accuracy(scores, y, group_keys)

    assert n_scored == 0
    assert accuracy == 0.0


def test_random_baseline_is_mean_inverse_group_size_over_scored_groups():
    y = np.array([0, 1, 1, 0, 0])  # d0: 2 options, one chosen; d1: 3 options, one chosen
    group_keys = np.array(["d0", "d0", "d1", "d1", "d1"])

    baseline = random_baseline(group_keys, y)

    assert baseline == (0.5 + 1 / 3) / 2


def test_random_baseline_excludes_unresolved_groups():
    y = np.array([0, 0, 1, 0, 0])  # d0: no chosen row (excluded); d1: 3 options, one chosen
    group_keys = np.array(["d0", "d0", "d1", "d1", "d1"])

    baseline = random_baseline(group_keys, y)

    assert baseline == 1 / 3


def test_fitted_model_beats_baseline_on_perfectly_separable_data(tmp_path):
    rows = _perfectly_separable_dataset(n_games=40, decisions_per_game=5, seed=0)
    path = _write_csv(tmp_path / "moves.csv", rows)

    game_ids, group_keys, X, y = load_rows(path)
    train_mask, test_mask = game_split(game_ids, test_frac=0.2, seed=0)
    model, mean, std = fit_standardized(X[train_mask], y[train_mask])
    scores = model.predict_proba((X[test_mask] - mean) / std)[:, 1]

    accuracy, n_scored = top1_accuracy(scores, y[test_mask], group_keys[test_mask])
    baseline = random_baseline(group_keys[test_mask], y[test_mask])

    assert n_scored > 0
    assert accuracy > baseline + 0.3  # the signal is perfectly separable; a wide margin


def test_export_model_writes_expected_payload(tmp_path):
    rows = _perfectly_separable_dataset(n_games=20, decisions_per_game=5, seed=1)
    path = _write_csv(tmp_path / "moves.csv", rows)
    game_ids, _, X, y = load_rows(path)
    model, mean, std = fit_standardized(X, y)

    model_path = tmp_path / "move_prior.json"
    export_model(model, mean, std, model_path)
    payload = json.loads(model_path.read_text())

    assert payload["feature_names"] == list(FEATURE_NAMES)
    assert payload["feature_version"] == list(feature_version())
    assert len(payload["mean"]) == len(FEATURE_NAMES)
    assert len(payload["std"]) == len(FEATURE_NAMES)
    assert len(payload["coef"]) == len(FEATURE_NAMES)
    assert isinstance(payload["intercept"], float)
