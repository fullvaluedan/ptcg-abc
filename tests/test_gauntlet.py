import csv

from ptcg_agent.features import FEATURE_NAMES, N_FEATURES
from tools.gauntlet import run_gauntlet, _is_legal, _wilson


def test_wilson_bounds():
    lo, hi = _wilson(5, 10)
    assert 0.0 <= lo <= 0.5 <= hi <= 1.0
    assert _wilson(0, 0) == (0.0, 0.0)


def test_is_legal_rules():
    obs = {"select": {"option": [0, 1, 2], "minCount": 1, "maxCount": 2}}
    assert _is_legal([0, 1], obs)
    assert not _is_legal([0, 0], obs)              # duplicate
    assert not _is_legal([3], obs)                 # out of range
    assert not _is_legal([], obs)                  # below minCount
    assert not _is_legal([0, 1, 2], obs)           # above maxCount
    assert _is_legal(list(range(60)), {"select": None})
    assert not _is_legal([1, 2], {"select": None})  # deck must be 60


def test_gauntlet_stats_shape():
    stats = run_gauntlet("baseline", ["random"], 6)
    assert stats["matches"] == 6
    assert stats["wins"] + stats["draws"] + stats["losses"] == 6
    assert 0.0 <= stats["win_rate"] <= 1.0
    assert stats["decisions"] > 0
    assert stats["invalid_moves"] == 0  # baseline never returns an illegal move
    assert len(stats["win_rate_ci95"]) == 2


def test_state_logging_writes_labelled_rows_for_both_seats(tmp_path):
    log_path = tmp_path / "states.csv"
    stats = run_gauntlet("baseline", ["random"], 2, log_states=True, log_path=log_path)
    assert stats["log_path"] == str(log_path)
    assert log_path.exists()

    with open(log_path, newline="") as fh:
        rows = list(csv.reader(fh))
    header, data_rows = rows[0], rows[1:]

    assert header == ["game_id", "seat", "turn"] + list(FEATURE_NAMES) + ["label"]
    assert len(header) == 3 + N_FEATURES + 1
    assert len(data_rows) > 20
    assert {row[1] for row in data_rows} == {"0", "1"}  # both seats logged
    labels = {row[-1] for row in data_rows}
    assert labels <= {"0", "1"}
    assert labels == {"0", "1"}  # both win and loss labels present
