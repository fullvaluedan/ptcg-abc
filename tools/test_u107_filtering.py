#!/usr/bin/env python3
"""Minimal test for U107 per-build loss ledger filtering (backfill + classify_dirs_per_build)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools import harvest_replays as hr
from tools import loop_state as ls


def test_backfill_manifest():
    """Test backfill_manifest creates and populates the manifest."""
    manifest_path = _ROOT / "data" / "episode_to_ref.json"
    print(f"[TEST] backfill_manifest: creating manifest at {manifest_path}")
    res = hr.backfill_manifest()
    assert res.get("ok"), f"backfill failed: {res.get('error')}"
    assert res.get("total_discovered", 0) > 0, f"no episodes discovered: {res}"
    assert manifest_path.exists(), f"manifest file not created at {manifest_path}"
    manifest = hr._load_episode_to_ref_manifest()
    assert isinstance(manifest, dict) and len(manifest) > 0, f"manifest is empty: {manifest}"
    print(f"  PASS: backfilled {res['total_discovered']} episode->ref mappings")
    return manifest


def test_classify_dirs_per_build(manifest: dict):
    """Test classify_dirs_per_build filters by ref."""
    replay_dir = _ROOT / "data" / "replays"
    if not replay_dir.is_dir():
        print("[SKIP] test_classify_dirs_per_build: data/replays not found")
        return

    # Collect some refs from the manifest
    refs_in_manifest = list(set(manifest.values()))[:3]  # Sample a few refs
    print(f"[TEST] classify_dirs_per_build: filtering by refs {refs_in_manifest}")

    # Test with filtering
    report = ls.classify_dirs_per_build([str(replay_dir)], ref_filter=refs_in_manifest)
    assert report.get("ok") is not False, f"classify failed: {report}"
    filtered = report.get("filtered_episodes", 0)
    total = report.get("games", 0)
    print(f"  PASS: filtered {filtered}/{total} episodes for refs {refs_in_manifest}")

    # Test without filtering
    report_no_filter = ls.classify_dirs_per_build([str(replay_dir)])
    total_no_filter = report_no_filter.get("games", 0)
    print(f"  PASS: no-filter report has {total_no_filter} episodes")
    assert total_no_filter >= filtered, f"filtered count > total: {filtered} > {total_no_filter}"


if __name__ == "__main__":
    print("=== U107 Per-Build Loss Ledger: Backfill + Filtering Tests ===\n")
    try:
        manifest = test_backfill_manifest()
        print()
        test_classify_dirs_per_build(manifest)
        print("\n=== ALL TESTS PASSED ===")
    except Exception as e:
        print(f"\n!!! TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
