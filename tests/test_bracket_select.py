"""U81 bracket-band opponent selection tests.

All Kaggle CLI calls are monkeypatched (run_kaggle), same style as
tests/test_daily_refresh.py and tests/test_top_player_tracker.py, so the
suite stays fully offline. Replays are small synthetic JSON files, never
real competition data.
"""
import io
import json
import zipfile
from pathlib import Path

from tools import bracket_select as bs

LEADERBOARD_HEADER = "Rank,TeamId,TeamName,LastSubmissionDate,Score,SubmissionCount,TeamMemberUserNames"


def _leaderboard_zip_bytes(rows):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        lines = [LEADERBOARD_HEADER]
        for rank, name, score in rows:
            lines.append(f"{rank},1234{rank},{name},2026-07-03 00:00:00,{score},2,someone")
        zf.writestr("pokemon-tcg-ai-battle-publicleaderboard-2026-07-03T00:00:00.csv", "\n".join(lines) + "\n")
    return buf.getvalue()


def _fake_leaderboard_download(rows):
    def _run(args, timeout=None):
        dest_dir = Path(args[args.index("-p") + 1])
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / f"{bs.SIMULATION_SLUG}.zip").write_bytes(_leaderboard_zip_bytes(rows))
        return {"ok": True, "stdout": "", "stderr": "", "returncode": 0, "error": None}
    return _run


def _write_replay(path, team_names, our_team="Dan Arreola"):
    path.write_text(json.dumps({"info": {"TeamNames": list(team_names)}}), encoding="utf-8")


def test_fetch_full_leaderboard_parses_rows(tmp_path, monkeypatch):
    rows = [(1, "tonakaiiii", "1200.6"), (2906, "Dan Arreola", "548.3"), (3400, "TAKUMI7775", "450.5")]
    monkeypatch.setattr(bs, "run_kaggle", _fake_leaderboard_download(rows))
    res = bs.fetch_full_leaderboard(tmp_path)
    assert res["ok"] is True
    assert len(res["rows"]) == 3
    by_name = {r["name"]: r for r in res["rows"]}
    assert by_name["Dan Arreola"]["rating"] == 548.3
    assert by_name["Dan Arreola"]["rank"] == 2906


def test_fetch_full_leaderboard_propagates_kaggle_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "run_kaggle", lambda args, timeout=None: {"ok": False, "error": "no token"})
    res = bs.fetch_full_leaderboard(tmp_path)
    assert res == {"ok": False, "error": "no token", "rows": []}


def test_fetch_full_leaderboard_missing_zip_reports_error(tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "run_kaggle", lambda args, timeout=None: {"ok": True, "stdout": "", "stderr": "",
                                                                        "returncode": 0, "error": None})
    res = bs.fetch_full_leaderboard(tmp_path)
    assert res["ok"] is False
    assert "expected" in res["error"]


def test_band_teams_filters_by_rating_inclusive():
    rows = [
        {"name": "high", "rating": 900.0},
        {"name": "low_edge", "rating": 450.0},
        {"name": "high_edge", "rating": 750.0},
        {"name": "mid", "rating": 600.0},
        {"name": "below", "rating": 100.0},
        {"name": "no_rating", "rating": None},
    ]
    band = bs.band_teams(rows, low=450.0, high=750.0)
    assert band == {"low_edge": 450.0, "high_edge": 750.0, "mid": 600.0}


def test_opponents_from_replays_skips_self_play_and_unmatched(tmp_path):
    _write_replay(tmp_path / "a.json", ("Dan Arreola", "opponent_one"))
    _write_replay(tmp_path / "b.json", ("opponent_two", "Dan Arreola"))
    _write_replay(tmp_path / "self.json", ("Dan Arreola", "Dan Arreola"))
    _write_replay(tmp_path / "no_match.json", ("someone_else", "another_team"))

    opponents = bs.opponents_from_replays(tmp_path)
    assert opponents == {"opponent_one", "opponent_two"}


def test_opponents_from_replays_missing_dir_returns_empty(tmp_path):
    assert bs.opponents_from_replays(tmp_path / "does_not_exist") == set()


def test_opponents_from_replays_skips_corrupt_file(tmp_path):
    _write_replay(tmp_path / "a.json", ("Dan Arreola", "opponent_one"))
    (tmp_path / "corrupt.json").write_text("not json", encoding="utf-8")
    assert bs.opponents_from_replays(tmp_path) == {"opponent_one"}


def test_select_bracket_unions_band_and_replay_opponents(tmp_path):
    _write_replay(tmp_path / "a.json", ("Dan Arreola", "replay_only_team"))
    rows = [
        {"name": "band_team", "rating": 600.0},
        {"name": "too_high", "rating": 1000.0},
    ]
    selection = bs.select_bracket(rows, tmp_path)
    assert selection["teams"] == ["band_team", "replay_only_team"]
    assert selection["ratings"]["band_team"] == 600.0
    assert selection["ratings"]["replay_only_team"] is None
    assert selection["band_count"] == 1
    assert selection["replay_opponent_count"] == 1
    assert selection["union_count"] == 2


def test_select_bracket_prefers_leaderboard_rating_for_overlap(tmp_path):
    _write_replay(tmp_path / "a.json", ("Dan Arreola", "shared_team"))
    rows = [{"name": "shared_team", "rating": 500.0}]
    selection = bs.select_bracket(rows, tmp_path)
    assert selection["teams"] == ["shared_team"]
    assert selection["ratings"]["shared_team"] == 500.0
    assert selection["band_count"] == 1
    assert selection["replay_opponent_count"] == 1
    assert selection["union_count"] == 1


def test_select_bracket_replay_opponent_outside_band_keeps_out_of_band_rating(tmp_path):
    _write_replay(tmp_path / "a.json", ("Dan Arreola", "far_team"))
    rows = [{"name": "far_team", "rating": 950.0}]
    selection = bs.select_bracket(rows, tmp_path, low=450.0, high=750.0)
    assert selection["band_count"] == 0
    assert selection["teams"] == ["far_team"]
    assert selection["ratings"]["far_team"] == 950.0


def test_main_writes_output_json(tmp_path, monkeypatch):
    rows = [(1, "band_team", "600.0")]
    monkeypatch.setattr(bs, "run_kaggle", _fake_leaderboard_download(rows))
    replays_dir = tmp_path / "replays"
    replays_dir.mkdir()
    _write_replay(replays_dir / "a.json", ("Dan Arreola", "replay_team"))

    out_path = tmp_path / "out.json"
    rc = bs.main([
        "--leaderboard-dir", str(tmp_path / "leaderboard_cache"),
        "--replays-dir", str(replays_dir),
        "--out", str(out_path),
    ])
    assert rc == 0
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert sorted(data["teams"]) == ["band_team", "replay_team"]


def test_main_returns_nonzero_on_leaderboard_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "run_kaggle", lambda args, timeout=None: {"ok": False, "error": "429 rate limited"})
    rc = bs.main(["--leaderboard-dir", str(tmp_path)])
    assert rc == 1


def test_default_leaderboard_dir_is_not_episodes_dir():
    """The download dir must never collide with the episode-dump directory
    that tools.top_player_tracker.newest_dataset scans (lexicographic *.zip
    sort would let the leaderboard zip shadow real dated dumps forever)."""
    assert bs.DEFAULT_LEADERBOARD_DIR != bs.DEFAULT_LEADERBOARD_DIR.parent / "episodes"
    assert bs.DEFAULT_LEADERBOARD_DIR.name != "episodes"
