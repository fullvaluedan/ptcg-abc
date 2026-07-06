"""Ladder replay downloader (plan U3a).

Downloads REAL ladder replays (episodes from every submission ref we have) to
data/replays/<episode_id>.json, feeding U3b's replay-to-rows converter. Thin,
fault tolerant layer over the same Kaggle CLI wrapper tools/scout.py already
uses (list_submissions -> list_episodes -> fetch one replay), fanned out
across every submission ref instead of one at a time. Downloaded replays are
gitignored competition data (data/ is in .gitignore); never committed or
redistributed.

U107 addition: Persists episode-to-ref mapping to data/episode_to_ref.json so
that loss distributions can be segregated by build. The mapping is updated on
every harvest; a backfill function loads and enriches the mapping for all
episodes in data/replays/ via list_episodes per ref.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.loss_classifier import parse_replay  # noqa: E402
from tools.scout import (  # noqa: E402
    fetch_episode,
    list_episodes,
    list_submissions,
    load_replay,
)

DEFAULT_DEST = _ROOT / "data" / "replays"
DEFAULT_MANIFEST = _ROOT / "data" / "episode_to_ref.json"
DEFAULT_MAX_EPISODES = 200
DEFAULT_SLEEP_S = 1.0


def _episode_path(dest_dir, episode_id) -> Path:
    return Path(dest_dir) / f"{episode_id}.json"


def _is_valid_replay(replay) -> bool:
    """True when a downloaded replay parses into a usable digest.

    Reuses analysis.loss_classifier.parse_replay, the same parser U3b's row
    converter depends on, so a truncated or corrupt download is rejected here
    instead of silently poisoning the training set later. Never raises.
    """
    try:
        digest = parse_replay(replay, our_index=0)
    except (AttributeError, TypeError, KeyError):
        return False
    return isinstance(digest, dict) and digest.get("n_decisions", 0) > 0


def discover_episode_ids(sleep_s: float = DEFAULT_SLEEP_S) -> dict:
    """List every episode id across all our submissions, deduplicated.

    Fault tolerant: a failed submissions listing returns early (ok False); a
    failed per-submission episode listing is recorded in failed_submissions
    and skipped, the rest continue. Sleeps between per-submission calls to
    stay polite to the Kaggle API.

    Also returns episode_to_ref mapping so callers can track which ref owns
    each episode (U107: per-build loss ledger).
    """
    subs = list_submissions()
    if not subs["ok"]:
        return {"ok": False, "error": subs["error"], "episode_ids": [], "episode_to_ref": {}, "failed_submissions": []}
    episode_ids = []
    episode_to_ref = {}
    seen = set()
    failed_submissions = []
    for i, sub in enumerate(subs["submissions"]):
        ref = sub.get("ref") if isinstance(sub, dict) else sub
        if ref is None:
            continue
        if i:
            time.sleep(sleep_s)
        listing = list_episodes(ref)
        if not listing["ok"]:
            failed_submissions.append({"submission": ref, "error": listing["error"]})
            continue
        for ep in listing["episodes"]:
            ep_id = ep.get("id") if isinstance(ep, dict) else ep
            if ep_id is not None and ep_id not in seen:
                seen.add(ep_id)
                episode_ids.append(ep_id)
                episode_to_ref[str(ep_id)] = ref
    return {"ok": True, "episode_ids": episode_ids, "episode_to_ref": episode_to_ref, "failed_submissions": failed_submissions}


def _load_episode_to_ref_manifest(manifest_path=None) -> dict:
    """Load existing episode-to-ref mapping from manifest file, or empty dict."""
    manifest_path = Path(manifest_path) if manifest_path else DEFAULT_MANIFEST
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text())
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _save_episode_to_ref_manifest(manifest: dict, manifest_path=None) -> bool:
    """Persist episode-to-ref mapping to manifest file.

    Creates parent directories as needed. Returns True on success, False on error.
    Never raises.
    """
    manifest_path = Path(manifest_path) if manifest_path else DEFAULT_MANIFEST
    try:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, default=str))
        return True
    except (OSError, TypeError):
        return False


def harvest(dest_dir=None, max_episodes: int = DEFAULT_MAX_EPISODES,
            sleep_s: float = DEFAULT_SLEEP_S) -> dict:
    """Download up to max_episodes new ladder replays into dest_dir.

    Skips episode ids already saved as dest_dir/<id>.json. Downloads via the
    same Kaggle CLI wrapper scout.py uses, sleeping sleep_s between calls.
    Every downloaded replay is validated with parse_replay before being kept;
    an invalid download is deleted and counted as failed rather than left as
    a corrupt training row source. Persists episode-to-ref mapping to
    data/episode_to_ref.json for U107 per-build loss tracking.
    Never raises: every failure mode degrades to a result dict entry.
    """
    dest_dir = Path(dest_dir) if dest_dir else DEFAULT_DEST
    dest_dir.mkdir(parents=True, exist_ok=True)

    discovery = discover_episode_ids(sleep_s=sleep_s)
    if not discovery["ok"]:
        return {"ok": False, "error": discovery["error"], "fetched": [], "skipped": [], "failed": [],
                "failed_submissions": []}

    fetched, skipped, failed = [], [], []
    called_kaggle = False
    # Load existing manifest and merge in new episodes (U107)
    manifest = _load_episode_to_ref_manifest()
    manifest.update(discovery.get("episode_to_ref", {}))

    for ep_id in discovery["episode_ids"]:
        if len(fetched) >= max_episodes:
            break
        target = _episode_path(dest_dir, ep_id)
        if target.exists():
            skipped.append(ep_id)
            continue
        if called_kaggle:
            time.sleep(sleep_s)
        called_kaggle = True
        res = fetch_episode(ep_id, dest_dir=dest_dir)
        if not res["ok"]:
            failed.append({"episode": ep_id, "error": res["error"]})
            continue
        # fetch_episode (kaggle CLI) writes episode-<id>-replay.json; validate
        # then normalize to the plan's data/replays/<id>.json name.
        src_path = Path(res["path"])
        try:
            replay = load_replay(src_path)
        except (OSError, ValueError):
            src_path.unlink(missing_ok=True)
            failed.append({"episode": ep_id, "error": "downloaded file was not valid json"})
            continue
        if not _is_valid_replay(replay):
            src_path.unlink(missing_ok=True)
            failed.append({"episode": ep_id, "error": "replay did not parse into a usable digest"})
            continue
        src_path.replace(target)
        fetched.append(ep_id)

    # Persist updated manifest
    _save_episode_to_ref_manifest(manifest)

    return {
        "ok": True,
        "fetched": fetched,
        "skipped": skipped,
        "failed": failed,
        "failed_submissions": discovery["failed_submissions"],
    }


def main():
    ap = argparse.ArgumentParser(description="download new ladder replays across all our submissions")
    ap.add_argument("--dir", default=str(DEFAULT_DEST), help="destination directory (default data/replays)")
    ap.add_argument("--max-episodes", type=int, default=DEFAULT_MAX_EPISODES,
                    help="cap on new episodes downloaded this run (default 200)")
    ap.add_argument("--sleep", type=float, default=DEFAULT_SLEEP_S,
                    help="seconds to sleep between Kaggle API calls (default 1.0)")
    args = ap.parse_args()

    res = harvest(dest_dir=args.dir, max_episodes=args.max_episodes, sleep_s=args.sleep)
    if not res["ok"]:
        print(f"harvest failed: {res['error']}")
        sys.exit(1)
    print(f"harvested {len(res['fetched'])} new replays to {args.dir} "
          f"({len(res['skipped'])} already had, {len(res['failed'])} failed)")
    if res["failed_submissions"]:
        print(f"  {len(res['failed_submissions'])} submissions could not be listed")


if __name__ == "__main__":
    main()
