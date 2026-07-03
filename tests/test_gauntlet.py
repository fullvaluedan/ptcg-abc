import csv

from agents.imitation_features import FEATURE_NAMES as MOVE_FEATURE_NAMES
from agents.imitation_features import N_FEATURES as MOVE_N_FEATURES
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


def test_bank_spend_absent_for_agents_without_a_timebudget():
    # Only agents.agent_search carries a search/timebudget.TimeBudget (plan U12);
    # baseline has no such state, so run_gauntlet must omit both keys entirely
    # rather than reporting a misleading zero.
    stats = run_gauntlet("baseline", ["random"], 2)
    assert "avg_bank_spend_s" not in stats
    assert "max_bank_spend_s" not in stats


def test_bank_spend_tracked_for_search_agent(monkeypatch):
    import agents.agent_search as agent_search
    from search.timebudget import TimeBudget

    # A small soft cap keeps this a fast unit test regardless of how many
    # searchable decisions the real match happens to reach.
    monkeypatch.setattr(agent_search, "_BUDGET", TimeBudget(soft_cap=0.05))
    stats = run_gauntlet("search", ["random"], 1)
    assert "avg_bank_spend_s" in stats
    assert "max_bank_spend_s" in stats
    assert stats["avg_bank_spend_s"] >= 0.0
    assert stats["max_bank_spend_s"] >= stats["avg_bank_spend_s"]


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


def test_move_logging_writes_winner_seat_only_candidate_rows(tmp_path):
    move_path = tmp_path / "move_rows.csv"
    stats = run_gauntlet("baseline", ["random"], 6, log_moves=True, move_log_path=move_path)
    assert stats["move_log_path"] == str(move_path)
    assert move_path.exists()
    assert "log_path" not in stats  # log_states was not requested

    with open(move_path, newline="") as fh:
        rows = list(csv.reader(fh))
    header, data_rows = rows[0], rows[1:]

    assert header == (
        ["game_id", "seat", "decision_id", "n_options", "option_index", "is_chosen"]
        + list(MOVE_FEATURE_NAMES) + ["source"]
    )
    assert len(header) == 6 + MOVE_N_FEATURES + 1
    assert data_rows  # baseline vs random has plenty of multi-option MAIN decisions
    assert {row[-1] for row in data_rows} == {"gauntlet"}

    groups = {}
    for row in data_rows:
        groups.setdefault((row[0], row[2]), []).append(row)
    for (_game_id, _decision_id), grp in groups.items():
        n_opt = int(grp[0][3])
        assert len(grp) == n_opt  # one row per candidate option in the decision
        chosen = [r for r in grp if r[5] == "1"]
        assert len(chosen) <= 1  # at most one chosen option per decision


def test_log_moves_independent_of_log_states(tmp_path):
    states_path = tmp_path / "states.csv"
    move_path = tmp_path / "moves.csv"
    stats = run_gauntlet("baseline", ["random"], 2, log_states=True, log_path=states_path,
                          log_moves=True, move_log_path=move_path)
    assert stats["log_path"] == str(states_path)
    assert stats["move_log_path"] == str(move_path)
    assert states_path.exists()
    assert move_path.exists()
