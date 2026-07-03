"""Tests for the teacher self-play label harvester (plan U83 prep step).

Uses injectable `teacher_factory`/`opponent_names` so these stay fast (baseline
vs random, small n) rather than paying the real search-stack cost; the real
`search+trolley` default is exercised only via a monkeypatch smoke test.
Integration-flavored (plays real tiny matches), matching the pattern
`tests/test_ring_calibrate.py` and `tests/test_gauntlet.py` already use.
"""
import json

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
