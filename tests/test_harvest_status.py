"""Tests for the teacher self-play harvest progress aggregator (plan U83 prep)."""
import json

from tools import harvest_status as hs


def _write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def test_scan_counts_records_and_distinct_games(tmp_path):
    _write_jsonl(tmp_path / "shard_a.jsonl", [
        {"game_id": 0, "obs": {}, "played": 0},
        {"game_id": 0, "obs": {}, "played": 1},
        {"game_id": 1, "obs": {}, "played": 0},
    ])
    stats = hs.scan(tmp_path)
    assert stats["records"] == 3
    assert stats["games"] == 2


def test_scan_disambiguates_same_game_id_across_shards(tmp_path):
    # Every shard restarts its own game_id counter at 0; without the
    # _source stamp these would collide onto one game.
    _write_jsonl(tmp_path / "shard_a.jsonl", [{"game_id": 0, "obs": {}, "played": 0}])
    _write_jsonl(tmp_path / "shard_b.jsonl", [{"game_id": 0, "obs": {}, "played": 0}])
    stats = hs.scan(tmp_path)
    assert stats["records"] == 2
    assert stats["games"] == 2


def test_scan_train_test_split_covers_every_game_exactly_once(tmp_path):
    rows = [{"game_id": i, "obs": {}, "played": 0} for i in range(50)]
    _write_jsonl(tmp_path / "shard.jsonl", rows)
    stats = hs.scan(tmp_path)
    assert stats["train_games"] + stats["test_games"] == stats["games"] == 50


def test_scan_per_source_breakdown(tmp_path):
    _write_jsonl(tmp_path / "shard_a.jsonl", [{"game_id": 0, "obs": {}, "played": 0}] * 3)
    _write_jsonl(tmp_path / "shard_b.jsonl", [{"game_id": 0, "obs": {}, "played": 0}] * 5)
    stats = hs.scan(tmp_path)
    assert stats["per_source"] == {"shard_a.jsonl": 3, "shard_b.jsonl": 5}


def test_scan_respects_limit(tmp_path):
    rows = [{"game_id": i, "obs": {}, "played": 0} for i in range(10)]
    _write_jsonl(tmp_path / "shard.jsonl", rows)
    stats = hs.scan(tmp_path, limit=4)
    assert stats["records"] == 4


def test_scan_empty_directory_returns_zeros(tmp_path):
    stats = hs.scan(tmp_path)
    assert stats == {"records": 0, "games": 0, "train_games": 0, "test_games": 0, "per_source": {}}


def test_format_report_includes_shard_breakdown(tmp_path):
    _write_jsonl(tmp_path / "shard.jsonl", [{"game_id": 0, "obs": {}, "played": 0}])
    report = hs.format_report(hs.scan(tmp_path))
    assert "records: 1" in report
    assert "shard.jsonl: 1 records" in report


def test_main_runs_against_directory(tmp_path, capsys):
    _write_jsonl(tmp_path / "shard.jsonl", [{"game_id": 0, "obs": {}, "played": 0}])
    rc = hs.main([str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "games: 1" in out
