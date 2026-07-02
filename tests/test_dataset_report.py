import csv

from agents.imitation_features import FEATURE_NAMES as MOVE_FEATURE_NAMES
from analysis.early_archetype_features import FEATURE_NAMES as ARCHETYPE_FEATURE_NAMES
from ptcg_agent.features import FEATURE_NAMES
from tools.dataset_report import (
    BALANCE_HI,
    BALANCE_LO,
    OTHER_MIN_ROWS,
    archetype_report,
    move_report,
    report,
)


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


def test_report_balanced_clean_dataset(tmp_path):
    path = tmp_path / "states.csv"
    rows = []
    for i in range(10):
        label = 1 if i < 4 else 0  # 40% wins, inside 35-65
        rows.append(["g0", 0, i, *_feature_row(turn_number=float(i)), label])
    _write_csv(path, rows)

    result = report(path)
    assert result["n_rows"] == 10
    assert result["n_games"] == 1
    assert BALANCE_LO <= result["class_balance"] <= BALANCE_HI
    assert result["balance_ok"] is True
    assert result["n_nan"] == 0
    assert result["nan_ok"] is True
    assert result["feature_stats"]["turn_number"] == (0.0, 9.0)


def test_report_flags_bad_balance(tmp_path):
    path = tmp_path / "states.csv"
    rows = [["g0", 0, i, *_feature_row(), 1] for i in range(9)]
    rows.append(["g0", 0, 9, *_feature_row(), 0])  # 90% wins, outside 35-65
    _write_csv(path, rows)

    result = report(path)
    assert result["balance_ok"] is False


def test_report_flags_nan_values(tmp_path):
    path = tmp_path / "states.csv"
    rows = [
        ["g0", 0, 0, *_feature_row(prize_diff=0.5), 1],
        ["g0", 0, 1, *_feature_row(prize_diff=float("nan")), 0],
    ]
    _write_csv(path, rows)

    result = report(path)
    assert result["n_nan"] == 1
    assert result["nan_ok"] is False


def _write_move_csv(path, rows):
    header = (["game_id", "seat", "decision_id", "n_options", "option_index", "is_chosen"]
              + list(MOVE_FEATURE_NAMES) + ["source"])
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def _move_group(game_id, decision_id, n_options, chosen_index):
    feats = [0.0] * len(MOVE_FEATURE_NAMES)
    return [
        [game_id, 0, decision_id, n_options, i, 1 if i == chosen_index else 0, *feats, "gauntlet"]
        for i in range(n_options)
    ]


def test_move_report_clean_dataset(tmp_path):
    path = tmp_path / "move_rows.csv"
    rows = _move_group("g0", 0, 2, 0) + _move_group("g0", 1, 3, 2) + _move_group("g1", 0, 2, 1)
    _write_move_csv(path, rows)

    result = move_report(path)
    assert result["n_rows"] == 7
    assert result["n_games"] == 2
    assert result["n_decisions"] == 3
    assert result["group_size_ok"] is True
    assert result["multi_chosen_ok"] is True
    assert result["ok"] is True
    assert result["class_balance"] == round(3 / 7, 4)  # one chosen row per decision
    assert result["expected_balance"] == round(3 / 7, 4)  # n_decisions / n_rows


def test_move_report_flags_bad_group_size(tmp_path):
    path = tmp_path / "move_rows.csv"
    rows = _move_group("g0", 0, 3, 0)[:-1]  # drop one row: group claims 3 options, has 2
    _write_move_csv(path, rows)

    result = move_report(path)
    assert result["group_size_ok"] is False
    assert result["bad_group_size"] == 1
    assert result["ok"] is False


def test_move_report_flags_multiple_chosen_in_one_decision(tmp_path):
    path = tmp_path / "move_rows.csv"
    rows = _move_group("g0", 0, 2, 0)
    rows[1][5] = 1  # both options marked chosen: a logging bug
    _write_move_csv(path, rows)

    result = move_report(path)
    assert result["multi_chosen_ok"] is False
    assert result["multi_chosen_groups"] == 1
    assert result["ok"] is False


def _write_archetype_csv(path, rows):
    header = ["game_id", "label", *ARCHETYPE_FEATURE_NAMES, "source"]
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def _archetype_row(game_id, label):
    return [game_id, label, *[0.0] * len(ARCHETYPE_FEATURE_NAMES), "ladder"]


def test_archetype_report_counts_per_label(tmp_path):
    path = tmp_path / "archetype_rows.csv"
    rows = (
        [_archetype_row(f"g{i}", "Mega Starmie ex") for i in range(3)]
        + [_archetype_row(f"g{i}", "Dragapult ex") for i in range(3, 5)]
    )
    _write_archetype_csv(path, rows)

    result = archetype_report(path)
    assert result["n_rows"] == 5
    assert result["n_games"] == 5
    assert result["n_labels"] == 2
    assert result["label_counts"] == {"Mega Starmie ex": 3, "Dragapult ex": 2}
    assert result["other_count"] == 0
    assert result["other_ok"] is True


def test_archetype_report_flags_thin_other_bucket(tmp_path):
    path = tmp_path / "archetype_rows.csv"
    rows = (
        [_archetype_row(f"g{i}", "Mega Starmie ex") for i in range(10)]
        + [_archetype_row(f"o{i}", "other") for i in range(OTHER_MIN_ROWS - 1)]
    )
    _write_archetype_csv(path, rows)

    result = archetype_report(path)
    assert result["other_count"] == OTHER_MIN_ROWS - 1
    assert result["other_ok"] is False


def test_archetype_report_ok_when_other_bucket_clears_threshold(tmp_path):
    path = tmp_path / "archetype_rows.csv"
    rows = [_archetype_row(f"o{i}", "other") for i in range(OTHER_MIN_ROWS)]
    _write_archetype_csv(path, rows)

    result = archetype_report(path)
    assert result["other_count"] == OTHER_MIN_ROWS
    assert result["other_ok"] is True
