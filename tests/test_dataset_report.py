import csv

from ptcg_agent.features import FEATURE_NAMES
from tools.dataset_report import BALANCE_HI, BALANCE_LO, report


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
