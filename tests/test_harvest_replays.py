"""U3a ladder replay downloader tests.

Every Kaggle call is monkeypatched (list_submissions / list_episodes /
fetch_episode) so the suite stays fully offline. The one real file on disk is
the synthetic fixture replay under tests/fixtures/, shaped like a real
env.toJSON dump but containing no competition data.
"""
import json
from pathlib import Path

from tools import harvest_replays as hr

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_replay.json"


def _fixture_replay():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_is_valid_replay_accepts_fixture():
    assert hr._is_valid_replay(_fixture_replay()) is True


def test_is_valid_replay_rejects_garbage():
    assert hr._is_valid_replay({"steps": [], "rewards": [None, None]}) is False
    assert hr._is_valid_replay(None) is False
    assert hr._is_valid_replay({"unrelated": 1}) is False


def test_discover_episode_ids_dedupes_across_submissions(monkeypatch):
    monkeypatch.setattr(
        hr, "list_submissions",
        lambda: {"ok": True, "submissions": [{"ref": 1}, {"ref": 2}]},
    )

    def _episodes(ref):
        # ref 2 re-lists an episode ref 1 already surfaced (shared opponent).
        table = {1: [{"id": 100}, {"id": 101}], 2: [{"id": 101}, {"id": 102}]}
        return {"ok": True, "episodes": table[ref]}

    monkeypatch.setattr(hr, "list_episodes", _episodes)
    res = hr.discover_episode_ids(sleep_s=0)
    assert res["ok"] is True
    assert res["episode_ids"] == [100, 101, 102]
    assert res["failed_submissions"] == []


def test_discover_episode_ids_propagates_submission_listing_failure(monkeypatch):
    monkeypatch.setattr(
        hr, "list_submissions",
        lambda: {"ok": False, "error": "401 unauthorized", "submissions": []},
    )
    res = hr.discover_episode_ids(sleep_s=0)
    assert res["ok"] is False
    assert res["error"] == "401 unauthorized"
    assert res["episode_ids"] == []


def test_discover_episode_ids_skips_failed_submission_but_continues(monkeypatch):
    monkeypatch.setattr(
        hr, "list_submissions",
        lambda: {"ok": True, "submissions": [{"ref": 1}, {"ref": 2}]},
    )

    def _episodes(ref):
        if ref == 1:
            return {"ok": False, "error": "403 forbidden", "episodes": []}
        return {"ok": True, "episodes": [{"id": 200}]}

    monkeypatch.setattr(hr, "list_episodes", _episodes)
    res = hr.discover_episode_ids(sleep_s=0)
    assert res["ok"] is True
    assert res["episode_ids"] == [200]
    assert res["failed_submissions"] == [{"submission": 1, "error": "403 forbidden"}]


def test_harvest_skips_existing_files(monkeypatch, tmp_path):
    monkeypatch.setattr(hr, "discover_episode_ids",
                        lambda sleep_s: {"ok": True, "episode_ids": [1, 2],
                                        "failed_submissions": []})
    (tmp_path / "1.json").write_text("{}")
    calls = []

    def _fetch(eid, dest_dir=None):
        calls.append(eid)
        raw = Path(dest_dir) / f"episode-{eid}-replay.json"
        raw.write_text(FIXTURE.read_text(encoding="utf-8"))
        return {"ok": True, "episode": eid, "path": str(raw)}

    monkeypatch.setattr(hr, "fetch_episode", _fetch)
    res = hr.harvest(dest_dir=tmp_path, sleep_s=0)
    # episode 1 already on disk: fetch_episode must never be called for it.
    assert calls == [2]
    assert res["skipped"] == [1]


def test_harvest_respects_max_episodes(monkeypatch, tmp_path):
    monkeypatch.setattr(hr, "discover_episode_ids",
                        lambda sleep_s: {"ok": True, "episode_ids": [1, 2, 3],
                                        "failed_submissions": []})

    def _fetch(eid, dest_dir=None):
        (Path(dest_dir) / f"episode-{eid}-replay.json").write_text(json.dumps(_fixture_replay()))
        return {"ok": True, "episode": eid, "path": str(Path(dest_dir) / f"episode-{eid}-replay.json")}

    monkeypatch.setattr(hr, "fetch_episode", _fetch)
    res = hr.harvest(dest_dir=tmp_path, max_episodes=2, sleep_s=0)
    assert res["fetched"] == [1, 2]  # capped before episode 3


def test_harvest_validates_and_renames_downloaded_replay(monkeypatch, tmp_path):
    monkeypatch.setattr(hr, "discover_episode_ids",
                        lambda sleep_s: {"ok": True, "episode_ids": [55],
                                        "failed_submissions": []})

    def _fetch(eid, dest_dir=None):
        raw = Path(dest_dir) / f"episode-{eid}-replay.json"
        raw.write_text(FIXTURE.read_text(encoding="utf-8"))
        return {"ok": True, "episode": eid, "path": str(raw)}

    monkeypatch.setattr(hr, "fetch_episode", _fetch)
    res = hr.harvest(dest_dir=tmp_path, sleep_s=0)
    assert res["fetched"] == [55]
    assert (tmp_path / "55.json").exists()
    assert not (tmp_path / "episode-55-replay.json").exists()  # normalized away


def test_harvest_discards_invalid_replay(monkeypatch, tmp_path):
    monkeypatch.setattr(hr, "discover_episode_ids",
                        lambda sleep_s: {"ok": True, "episode_ids": [9],
                                        "failed_submissions": []})

    def _fetch(eid, dest_dir=None):
        raw = Path(dest_dir) / f"episode-{eid}-replay.json"
        raw.write_text(json.dumps({"steps": [], "rewards": [None, None]}))
        return {"ok": True, "episode": eid, "path": str(raw)}

    monkeypatch.setattr(hr, "fetch_episode", _fetch)
    res = hr.harvest(dest_dir=tmp_path, sleep_s=0)
    assert res["fetched"] == []
    assert res["failed"] == [{"episode": 9, "error": "replay did not parse into a usable digest"}]
    assert not (tmp_path / "episode-9-replay.json").exists()  # bad download removed
    assert not (tmp_path / "9.json").exists()


def test_harvest_discards_malformed_json(monkeypatch, tmp_path):
    monkeypatch.setattr(hr, "discover_episode_ids",
                        lambda sleep_s: {"ok": True, "episode_ids": [7],
                                        "failed_submissions": []})

    def _fetch(eid, dest_dir=None):
        raw = Path(dest_dir) / f"episode-{eid}-replay.json"
        raw.write_text("{ not json")
        return {"ok": True, "episode": eid, "path": str(raw)}

    monkeypatch.setattr(hr, "fetch_episode", _fetch)
    res = hr.harvest(dest_dir=tmp_path, sleep_s=0)
    assert res["fetched"] == []
    assert res["failed"][0]["episode"] == 7
    assert "not valid json" in res["failed"][0]["error"]


def test_harvest_records_fetch_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(hr, "discover_episode_ids",
                        lambda sleep_s: {"ok": True, "episode_ids": [3],
                                        "failed_submissions": []})
    monkeypatch.setattr(hr, "fetch_episode",
                        lambda eid, dest_dir=None: {"ok": False, "episode": eid, "error": "429 rate limited"})
    res = hr.harvest(dest_dir=tmp_path, sleep_s=0)
    assert res["fetched"] == []
    assert res["failed"] == [{"episode": 3, "error": "429 rate limited"}]


def test_harvest_propagates_discovery_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(hr, "discover_episode_ids",
                        lambda sleep_s: {"ok": False, "error": "no kaggle token",
                                        "episode_ids": [], "failed_submissions": []})
    res = hr.harvest(dest_dir=tmp_path, sleep_s=0)
    assert res["ok"] is False
    assert res["error"] == "no kaggle token"
