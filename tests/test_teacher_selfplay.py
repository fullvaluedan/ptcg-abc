"""Tests for the teacher self-play label harvester (plan U83 prep step).

Uses injectable `teacher_factory`/`opponent_names` so these stay fast (baseline
vs random, small n) rather than paying the real search-stack cost; the real
`search+trolley` default is exercised only via a monkeypatch smoke test.
Integration-flavored (plays real tiny matches), matching the pattern
`tests/test_ring_calibrate.py` and `tests/test_gauntlet.py` already use.
"""
import json
from pathlib import Path

import pytest

from tools import teacher_selfplay as ts


def test_run_teacher_selfplay_logs_decisions_regardless_of_outcome(tmp_path):
    pytest.importorskip("kaggle_environments")
    from tools import opponents

    out_path = tmp_path / "labels.jsonl"
    stats = ts.run_teacher_selfplay(
        opponent_names=["random"],
        n_matches=4,
        out_path=out_path,
        teacher_factory=lambda: opponents.get("baseline"),
    )
    assert stats["matches"] == 4
    assert stats["wins"] + stats["draws"] + stats["losses"] == 4
    assert stats["log_path"] == str(out_path)
    assert out_path.exists()

    with open(out_path, encoding="utf-8") as fh:
        lines = [json.loads(line) for line in fh if line.strip()]
    assert stats["decisions_logged"] == len(lines)
    assert lines  # baseline vs random makes plenty of scorable MAIN decisions

    seats_by_game = {}
    for rec in lines:
        assert rec["seat"] in (0, 1)
        seats_by_game.setdefault(rec["game_id"], set()).add(rec["seat"])
    # exactly one seat per game belongs to the teacher (the opponent is never logged)
    for seats in seats_by_game.values():
        assert len(seats) == 1


def test_run_teacher_selfplay_raises_without_opponents():
    with pytest.raises(RuntimeError):
        ts.run_teacher_selfplay(opponent_names=[], n_matches=1)


def test_default_teacher_delegates_to_ring_calibrate_search_trolley_build(monkeypatch, tmp_path):
    pytest.importorskip("kaggle_environments")
    from tools import opponents, ring_calibrate

    monkeypatch.setattr(ring_calibrate, "_search_trolley_agent", lambda: opponents.get("baseline"))
    stats = ts.run_teacher_selfplay(
        opponent_names=["random"], n_matches=1, out_path=tmp_path / "labels.jsonl",
    )
    assert stats["matches"] == 1


def test_resolve_teacher_factory_search_trolley_is_default_teacher():
    assert ts.resolve_teacher_factory("search_trolley") is ts._default_teacher


def test_resolve_teacher_factory_other_name_delegates_to_opponents(monkeypatch):
    from tools import opponents

    sentinel = object()
    monkeypatch.setattr(opponents, "get", lambda name: sentinel if name == "baseline" else None)
    factory = ts.resolve_teacher_factory("baseline")
    assert factory() is sentinel


@pytest.mark.parametrize("n_matches,workers,expected", [
    (10, 3, [4, 3, 3]),
    (5, 5, [1, 1, 1, 1, 1]),
    (3, 5, [1, 1, 1, 0, 0]),
    (1, 1, [1]),
])
def test_split_counts(n_matches, workers, expected):
    assert ts._split_counts(n_matches, workers) == expected


def test_run_teacher_selfplay_parallel_raises_on_non_positive_matches():
    with pytest.raises(ValueError):
        ts.run_teacher_selfplay_parallel(0)


def test_run_teacher_selfplay_parallel_caps_workers_at_n_matches(tmp_path):
    pytest.importorskip("kaggle_environments")
    stats = ts.run_teacher_selfplay_parallel(
        n_matches=2, workers=10, opponent_names=["random"], teacher="baseline",
        out_dir=tmp_path, run_tag="capworkers",
    )
    assert stats["workers"] == 2
    assert stats["matches"] == 2
    assert len(stats["shard_paths"]) == 2


def test_run_teacher_selfplay_parallel_shards_are_readable_as_one_corpus(tmp_path):
    """Shards are separate files with their own game_id counters starting at 0;
    analysis.teacher_labels.load_records must still see every record exactly
    once, distinguishing games across shards via the _source stamp (same
    disambiguation the harvest-file split logic already relies on)."""
    pytest.importorskip("kaggle_environments")
    from analysis import teacher_labels

    stats = ts.run_teacher_selfplay_parallel(
        n_matches=4, workers=2, opponent_names=["random"], teacher="baseline",
        out_dir=tmp_path, run_tag="shardcorpus",
    )
    assert stats["workers"] == 2
    for shard in stats["shard_paths"]:
        assert Path(shard).exists()

    records = list(teacher_labels.load_records(tmp_path))
    assert len(records) == stats["decisions_logged"]
    assert records  # baseline vs random makes plenty of scorable MAIN decisions

    sources = {r["_source"] for r in records}
    assert sources == {Path(p).name for p in stats["shard_paths"]}

    # game_id resets per shard, but match_key (source + game_id) must still be
    # unique per real game, not collide across shards.
    keys_by_game = {}
    for r in records:
        keys_by_game.setdefault((r["_source"], r["game_id"]), set()).add(r["seat"])
    for seats in keys_by_game.values():
        assert len(seats) == 1


def test_run_teacher_selfplay_parallel_raises_on_worker_failure(tmp_path):
    with pytest.raises(RuntimeError):
        ts.run_teacher_selfplay_parallel(
            n_matches=2, workers=2, opponent_names=["not-a-real-opponent"],
            teacher="baseline", out_dir=tmp_path, run_tag="failcase",
        )
