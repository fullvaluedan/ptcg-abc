"""U80 daily dump refresh tests.

Every Kaggle call is monkeypatched (run_kaggle), same style as
tests/test_harvest_replays.py and tests/test_top_player_tracker.py, so the
suite stays fully offline. The index dataset's manifest.csv is a small
synthetic zip built in tmp_path, never real competition data.
"""
import zipfile
from pathlib import Path

from tools import daily_refresh as dr

MANIFEST_HEADER = "date,daily_dataset_slug,daily_dataset_url,episode_count,total_bytes,top_avg_score,median_avg_score"


def _index_zip_bytes(dates) -> bytes:
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        lines = [MANIFEST_HEADER]
        for d in dates:
            slug = f"pokemon-tcg-ai-battle-episodes-{d}"
            lines.append(f"{d},{slug},https://example.invalid/{slug},100,200,1.0,1.0")
        zf.writestr("manifest.csv", "\n".join(lines) + "\n")
    return buf.getvalue()


def _fake_index_download(dates):
    def _run(args, timeout=None):
        # args: ["datasets", "download", "-d", INDEX_SLUG, "-p", dest_dir, "--force"]
        dest_dir = Path(args[args.index("-p") + 1])
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "pokemon-tcg-ai-battle-episodes-index.zip").write_bytes(_index_zip_bytes(dates))
        return {"ok": True, "stdout": "", "stderr": "", "returncode": 0, "error": None}
    return _run


def test_fetch_index_manifest_parses_rows_sorted(tmp_path, monkeypatch):
    monkeypatch.setattr(dr, "run_kaggle", _fake_index_download(["2026-06-30", "2026-07-01", "2026-06-29"]))
    res = dr.fetch_index_manifest(tmp_path)
    assert res["ok"] is True
    assert [r["date"] for r in res["rows"]] == ["2026-06-29", "2026-06-30", "2026-07-01"]


def test_fetch_index_manifest_propagates_kaggle_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(dr, "run_kaggle", lambda args, timeout=None: {"ok": False, "error": "no token"})
    res = dr.fetch_index_manifest(tmp_path)
    assert res == {"ok": False, "error": "no token", "rows": []}


def test_newest_slug_returns_last_row():
    rows = [{"daily_dataset_slug": "a"}, {"daily_dataset_slug": "b"}]
    assert dr.newest_slug(rows) == "b"


def test_newest_slug_empty_is_none():
    assert dr.newest_slug([]) is None


def test_ensure_newest_dataset_skips_when_present_and_valid(tmp_path):
    slug = "pokemon-tcg-ai-battle-episodes-2026-07-02"
    target = tmp_path / f"{slug}.zip"
    with zipfile.ZipFile(target, "w") as zf:
        zf.writestr("manifest.csv", "date\n")

    def _fail_if_called(args, timeout=None):
        raise AssertionError("should not re-download an already-present valid dataset")

    manifest_rows = [{"date": "2026-07-02", "daily_dataset_slug": slug}]
    res = dr.ensure_newest_dataset(tmp_path, manifest_rows=manifest_rows)
    assert res == {"ok": True, "slug": slug, "path": target, "downloaded": False, "error": None}


def test_ensure_newest_dataset_redownloads_corrupt_leftover(tmp_path):
    slug = "pokemon-tcg-ai-battle-episodes-2026-07-02"
    target = tmp_path / f"{slug}.zip"
    target.write_text("not a zip, a truncated leftover from an interrupted download")

    calls = []

    def _run(args, timeout=None):
        calls.append(args)
        with zipfile.ZipFile(target, "w") as zf:
            zf.writestr("manifest.csv", "date\n")
        return {"ok": True, "stdout": "", "stderr": "", "returncode": 0, "error": None}

    manifest_rows = [{"date": "2026-07-02", "daily_dataset_slug": slug}]
    orig = dr.run_kaggle
    dr.run_kaggle = _run
    try:
        res = dr.ensure_newest_dataset(tmp_path, manifest_rows=manifest_rows)
    finally:
        dr.run_kaggle = orig

    assert len(calls) == 1
    assert res["ok"] is True
    assert res["downloaded"] is True
    assert zipfile.is_zipfile(target)


def test_ensure_newest_dataset_downloads_when_missing(tmp_path, monkeypatch):
    slug = "pokemon-tcg-ai-battle-episodes-2026-07-02"
    target = tmp_path / f"{slug}.zip"
    calls = []

    def _run(args, timeout=None):
        calls.append(args)
        assert args == ["datasets", "download", "-d", f"kaggle/{slug}", "-p", str(tmp_path)]
        with zipfile.ZipFile(target, "w") as zf:
            zf.writestr("manifest.csv", "date\n")
        return {"ok": True, "stdout": "", "stderr": "", "returncode": 0, "error": None}

    monkeypatch.setattr(dr, "run_kaggle", _run)
    manifest_rows = [{"date": "2026-07-02", "daily_dataset_slug": slug}]
    res = dr.ensure_newest_dataset(tmp_path, manifest_rows=manifest_rows)
    assert len(calls) == 1
    assert res == {"ok": True, "slug": slug, "path": target, "downloaded": True, "error": None}


def test_ensure_newest_dataset_propagates_download_failure(tmp_path, monkeypatch):
    slug = "pokemon-tcg-ai-battle-episodes-2026-07-02"
    monkeypatch.setattr(dr, "run_kaggle", lambda args, timeout=None: {"ok": False, "error": "429 rate limited"})
    manifest_rows = [{"date": "2026-07-02", "daily_dataset_slug": slug}]
    res = dr.ensure_newest_dataset(tmp_path, manifest_rows=manifest_rows)
    assert res["ok"] is False
    assert res["error"] == "429 rate limited"
    assert res["path"] is None


def test_ensure_newest_dataset_propagates_index_fetch_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(dr, "run_kaggle", lambda args, timeout=None: {"ok": False, "error": "no token"})
    res = dr.ensure_newest_dataset(tmp_path)
    assert res["ok"] is False
    assert res["error"] == "no token"


def test_refresh_orchestrates_all_steps_and_tolerates_partial_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(dr, "ensure_newest_dataset",
                        lambda episodes_dir=None: {"ok": True, "slug": "s", "path": tmp_path / "s.zip",
                                                    "downloaded": True, "error": None})
    monkeypatch.setattr(dr, "refresh_top_player_corpus",
                        lambda dataset_path, top_n=20, days=14: {"ok": False, "error": "leaderboard fetch failed"})
    monkeypatch.setattr(dr.harvest_replays, "harvest",
                        lambda dest_dir=None, max_episodes=200: {"ok": True, "fetched": [1], "skipped": [],
                                                                  "failed": [], "failed_submissions": []})
    monkeypatch.setattr(dr, "refresh_loss_distribution",
                        lambda ladder_dirs=None: {"top_bucket": "early_collapse", "sample_size": 5,
                                                   "wins": 2, "draws": 0, "losses": 3, "buckets": {}})

    result = dr.refresh()

    assert result["dataset"]["downloaded"] is True
    assert result["top_player"]["ok"] is False
    assert result["ladder_harvest"]["fetched"] == [1]
    assert result["loss_distribution"]["top_bucket"] == "early_collapse"


def test_refresh_falls_back_to_newest_local_dataset_when_download_fails(tmp_path, monkeypatch):
    local_zip = tmp_path / "pokemon-tcg-ai-battle-episodes-2026-06-30.zip"
    local_zip.write_bytes(b"")

    monkeypatch.setattr(dr, "ensure_newest_dataset",
                        lambda episodes_dir=None: {"ok": False, "error": "no network", "slug": None,
                                                    "path": None, "downloaded": False})
    monkeypatch.setattr(dr.tpt, "newest_dataset", lambda episodes_dir=None: local_zip)
    seen = {}

    def _fake_top_player(dataset_path, top_n=20, days=14):
        seen["dataset_path"] = dataset_path
        return {"ok": True, "new_win_rows": 0, "new_loss_rows": 0, "games_matched": 0,
                "games_considered": 0, "unmapped": []}

    monkeypatch.setattr(dr, "refresh_top_player_corpus", _fake_top_player)
    monkeypatch.setattr(dr.harvest_replays, "harvest",
                        lambda dest_dir=None, max_episodes=200: {"ok": True, "fetched": [], "skipped": [],
                                                                  "failed": [], "failed_submissions": []})
    monkeypatch.setattr(dr, "refresh_loss_distribution",
                        lambda ladder_dirs=None: {"top_bucket": None, "sample_size": 0,
                                                   "wins": 0, "draws": 0, "losses": 0, "buckets": {}})

    result = dr.refresh(episodes_dir=tmp_path)
    assert seen["dataset_path"] == local_zip
    assert result["top_player"]["ok"] is True
