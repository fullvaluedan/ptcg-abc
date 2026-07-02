import csv

from ptcg_agent.features import FEATURE_NAMES, N_FEATURES
from tools import parallel_gauntlet as pg
from tools.train_eval import load_rows


def test_chunk_matches_sums_to_total_and_all_positive():
    sizes = pg._chunk_matches(17, 5)
    assert sum(sizes) == 17
    assert all(s > 0 for s in sizes)
    assert len(sizes) == 5


def test_chunk_matches_caps_jobs_at_match_count():
    sizes = pg._chunk_matches(3, 10)
    assert sum(sizes) == 3
    assert len(sizes) == 3  # never more shards than matches


def test_chunk_matches_zero_matches():
    assert pg._chunk_matches(0, 5) == []


def test_default_jobs_leaves_headroom(monkeypatch):
    monkeypatch.setattr(pg.os, "cpu_count", lambda: 20)
    assert pg.default_jobs() == 16  # min(20-2, 16)
    monkeypatch.setattr(pg.os, "cpu_count", lambda: 4)
    assert pg.default_jobs() == 2  # min(4-2, 16)
    monkeypatch.setattr(pg.os, "cpu_count", lambda: 1)
    assert pg.default_jobs() == 1  # floored at 1


def _write_shard_csv(path, game_ids, seats=(0, 1)):
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["game_id", "seat", "turn", *FEATURE_NAMES, "label"])
        for gid in game_ids:
            for seat in seats:
                writer.writerow([gid, seat, 1, *([0.0] * N_FEATURES), 1])


def test_merge_logs_namespaces_game_ids_and_sums_rows(tmp_path):
    shard0 = tmp_path / "shard0.csv"
    shard1 = tmp_path / "shard1.csv"
    _write_shard_csv(shard0, [0, 1])
    _write_shard_csv(shard1, [0, 1])  # same nominal ids as shard 0

    shard_results = [
        (0, {"log_path": str(shard0)}),
        (1, {"log_path": str(shard1)}),
    ]
    out_path, row_count = pg._merge_logs(shard_results, tmp_path / "merged.csv")

    with open(out_path, newline="") as fh:
        rows = list(csv.reader(fh))
    header, data_rows = rows[0], rows[1:]
    assert header == ["game_id", "seat", "turn", *FEATURE_NAMES, "label"]
    game_ids = {row[0] for row in data_rows}
    assert game_ids == {"shard0:0", "shard0:1", "shard1:0", "shard1:1"}  # no collision
    assert row_count == len(data_rows) == 8  # 2 games x 2 seats x 2 shards
    assert sum(1 for _ in game_ids) == 4


def test_merge_logs_dedupes_repeated_game_id(tmp_path):
    shard0 = tmp_path / "shard0.csv"
    _write_shard_csv(shard0, [0])
    # a shard result list containing the same shard twice (defensive dedupe check)
    shard_results = [(0, {"log_path": str(shard0)}), (0, {"log_path": str(shard0)})]
    out_path, row_count = pg._merge_logs(shard_results, tmp_path / "merged.csv")
    with open(out_path, newline="") as fh:
        rows = list(csv.reader(fh))
    assert row_count == len(rows) - 1 == 2  # 1 game x 2 seats, not duplicated


def test_aggregate_stats_sums_shard_counters():
    shard_results = [
        (0, {"matches": 5, "wins": 3, "draws": 1, "losses": 1, "decisions": 50,
             "invalid_moves": 0, "avg_decision_ms": 2.0, "max_decision_ms": 5.0}),
        (1, {"matches": 5, "wins": 2, "draws": 0, "losses": 3, "decisions": 40,
             "invalid_moves": 1, "avg_decision_ms": 3.0, "max_decision_ms": 9.0}),
    ]
    result = pg._aggregate_stats("baseline", ["random"], 10, shard_results, [], 2)
    assert result["matches"] == 10
    assert result["shortfall"] == 0
    assert result["wins"] == 5
    assert result["draws"] == 1
    assert result["losses"] == 4
    assert result["decisions"] == 90
    assert result["invalid_moves"] == 1
    assert result["max_decision_ms"] == 9.0
    assert 0.0 <= result["win_rate"] <= 1.0


def test_aggregate_stats_reports_shortfall_from_errors():
    shard_results = [
        (0, {"matches": 5, "wins": 5, "draws": 0, "losses": 0, "decisions": 20,
             "invalid_moves": 0, "avg_decision_ms": 1.0, "max_decision_ms": 2.0}),
    ]
    result = pg._aggregate_stats("baseline", ["random"], 10, shard_results, ["shard 1: boom"], 2)
    assert result["matches"] == 5
    assert result["shortfall"] == 5
    assert result["shard_errors"] == ["shard 1: boom"]


def test_run_parallel_gauntlet_skips_failed_shard_and_reports_shortfall(monkeypatch):
    def fake_run_shard(shard_idx, agent, opponents, n, seed, log_path, python_exe):
        if shard_idx == 1:
            return None, f"shard {shard_idx}: boom"
        stats = {
            "matches": n, "wins": n, "draws": 0, "losses": 0, "decisions": n * 2,
            "invalid_moves": 0, "avg_decision_ms": 1.0, "max_decision_ms": 2.0,
        }
        return stats, None

    monkeypatch.setattr(pg, "_run_shard", fake_run_shard)
    result = pg.run_parallel_gauntlet("baseline", ["random"], 10, jobs=2, seed=0)
    assert result["shard_errors"] == ["shard 1: boom"]
    assert result["matches"] < result["requested_matches"]
    assert result["shortfall"] == result["requested_matches"] - result["matches"]


def test_run_parallel_gauntlet_jobs_1_matches_requested_count():
    stats = pg.run_parallel_gauntlet("baseline", ["random"], 4, jobs=1)
    assert stats["jobs"] == 1
    assert stats["matches"] == 4
    assert stats["shortfall"] == 0
    assert stats["shard_errors"] == []


def test_run_parallel_gauntlet_real_run_merges_state_log(tmp_path):
    out = tmp_path / "merged_states.csv"
    stats = pg.run_parallel_gauntlet(
        "baseline", ["random"], 6, jobs=2, log_states=True, log_path=out, seed=1,
    )
    assert stats["matches"] == 6
    assert stats["shard_errors"] == []
    assert stats["log_path"] == str(out)
    assert out.exists()

    game_ids, X, y = load_rows(out)
    assert X.shape[1] == N_FEATURES
    assert len(game_ids) == stats["log_rows"]
    # every id is shard-namespaced, and both shards contributed
    prefixes = {gid.split(":")[0] for gid in game_ids}
    assert prefixes == {"shard0", "shard1"}
    assert len(set(game_ids.tolist())) == stats["matches"]  # one unique id per game
