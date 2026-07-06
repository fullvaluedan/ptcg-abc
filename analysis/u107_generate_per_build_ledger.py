#!/usr/bin/env python3
"""Generate per-build loss ledger for shadow-king and reclaim-king (U107 analysis phase)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools import loop_state as ls

# Per state/current.md
SHADOW_KING_REF = "54315802"  # heuristic+trolley-ability
RECLAIM_KING_REF = "54315565"  # heuristic+trolley


def generate_per_build_ledger(replay_dirs: list[str] = None):
    """Generate per-build loss ledger for the two current kings."""
    if replay_dirs is None:
        replay_dirs = [str(_ROOT / "data" / "replays")]

    print("=== U107 Per-Build Loss Ledger ===\n")
    print(f"Replay directories: {replay_dirs}\n")

    # Analyze shadow-king
    print(f"[1/2] Analyzing shadow-king (ref {SHADOW_KING_REF})...")
    shadow_report = ls.classify_dirs_per_build(replay_dirs, ref_filter=[SHADOW_KING_REF])
    print(f"  Games: {shadow_report.get('games', 0)}")
    print(f"  Filtered episodes: {shadow_report.get('filtered_episodes', 0)}")
    if shadow_report.get("games", 0) > 0:
        print(f"  Top buckets:")
        for i, (bucket, count) in enumerate(shadow_report.get("buckets", {}).items(), 1):
            pct = 100 * count / shadow_report.get("games", 1)
            print(f"    {i}. {bucket}: {count} ({pct:.1f}%)")

    # Analyze reclaim-king
    print(f"\n[2/2] Analyzing reclaim-king (ref {RECLAIM_KING_REF})...")
    reclaim_report = ls.classify_dirs_per_build(replay_dirs, ref_filter=[RECLAIM_KING_REF])
    print(f"  Games: {reclaim_report.get('games', 0)}")
    print(f"  Filtered episodes: {reclaim_report.get('filtered_episodes', 0)}")
    if reclaim_report.get("games", 0) > 0:
        print(f"  Top buckets:")
        for i, (bucket, count) in enumerate(reclaim_report.get("buckets", {}).items(), 1):
            pct = 100 * count / reclaim_report.get("games", 1)
            print(f"    {i}. {bucket}: {count} ({pct:.1f}%)")

    # Build ledger dict
    ledger = {
        "shadow_king": {
            "ref": SHADOW_KING_REF,
            "build": "heuristic+trolley-ability",
            **{k: v for k, v in shadow_report.items() if k in ["games", "wins", "buckets", "filtered_episodes"]},
        },
        "reclaim_king": {
            "ref": RECLAIM_KING_REF,
            "build": "heuristic+trolley",
            **{k: v for k, v in reclaim_report.items() if k in ["games", "wins", "buckets", "filtered_episodes"]},
        },
    }

    # Save to analysis/u107_per_build_loss_ledger.json
    output_path = _ROOT / "analysis" / "u107_per_build_loss_ledger.json"
    output_path.write_text(json.dumps(ledger, indent=2))
    print(f"\n=== SAVED TO {output_path} ===")
    return ledger


if __name__ == "__main__":
    try:
        generate_per_build_ledger()
        print("\nPer-build loss ledger generated successfully")
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
