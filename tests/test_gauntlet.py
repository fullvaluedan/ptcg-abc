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
