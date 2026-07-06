#!/usr/bin/env python3
"""Per-build loss ledger (U107): segregate losses by submission ref.

Generates loss distributions for each build (submission ref) separately,
so that targeting is attributed to the actual shipped agent, not a
historical mix of all builds ever submitted.

Input: data/episode_to_ref.json (populated by harvest_replays.py)
Output: analysis/per_build_loss_ledger.md + per-build stats printed to stdout
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.loop_state import loss_distribution_from_dirs, read_current


def main() -> None:
    # Load the episode-to-ref manifest to find all refs
    manifest_path = _ROOT / "data" / "episode_to_ref.json"
    if not manifest_path.exists():
        print(f"Error: {manifest_path} does not exist. Run harvest_replays.py first.")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    if not manifest:
        print("No episodes found in manifest.")
        sys.exit(1)

    # Find unique refs
    refs = set(manifest.values())
    print(f"Found {len(refs)} unique refs in manifest: {sorted(refs)}")

    # Load current state to find the active builds
    current_data = read_current()
    shadow_king = current_data.get("shadow_king", {}).get("ref")
    reclaim_king = current_data.get("reclaim_king", {}).get("ref")

    print(f"\nActive builds:")
    print(f"  shadow-king: {shadow_king}")
    print(f"  reclaim-king: {reclaim_king}")

    # Generate per-build loss distributions for the active builds
    active_refs = []
    if shadow_king:
        active_refs.append(str(shadow_king))
    if reclaim_king:
        active_refs.append(str(reclaim_king))

    per_build_stats = {}
    print(f"\nPer-build loss distribution:")
    print("-" * 80)

    for ref in active_refs:
        dist = loss_distribution_from_dirs(["data/replays"], ref_filter=[ref])
        per_build_stats[ref] = dist
        print(f"Ref {ref}:")
        print(f"  Games: {dist['games']}")
        print(f"  Wins: {dist['wins']}, Draws: {dist['draws']}, Losses: {dist['losses']}")
        print(f"  Win rate: {dist['wins'] / dist['games'] * 100:.1f}%" if dist['games'] > 0 else "  No games")
        print(f"  Top bucket: {dist['top_bucket']}")
        print(f"  Bucket breakdown:")
        for bucket, count in sorted(dist['buckets'].items(), key=lambda x: -x[1]):
            if count > 0:
                pct = count / dist['losses'] * 100 if dist['losses'] > 0 else 0
                print(f"    {bucket}: {count} ({pct:.1f}% of losses)")
        print()

    # Write markdown report
    report_path = _ROOT / "analysis" / "per_build_loss_ledger.md"
    with open(report_path, "w") as f:
        f.write("# Per-build Loss Ledger (U107)\n\n")
        f.write("Segregates loss distributions by submission ref, so targeting is attributed\n")
        f.write("to the actual shipped agent, not a historical mix of all builds.\n\n")
        f.write(f"**Generated**: using episode-to-ref manifest from {manifest_path}\n\n")

        for ref in active_refs:
            dist = per_build_stats.get(ref, {})
            f.write(f"## Ref {ref}\n\n")
            f.write(f"- Games: {dist['games']}\n")
            f.write(f"- Wins: {dist['wins']} ({dist['wins']/dist['games']*100:.1f}%)\n" if dist['games'] > 0 else "- Games: 0\n")
            f.write(f"- Draws: {dist['draws']}\n")
            f.write(f"- Losses: {dist['losses']}\n")
            f.write(f"- Top bucket: {dist['top_bucket']}\n\n")

            f.write("### Loss distribution\n\n")
            f.write("| bucket | count | % of losses |\n")
            f.write("|--------|-------|-------------|\n")
            for bucket, count in sorted(dist['buckets'].items(), key=lambda x: -x[1]):
                pct = count / dist['losses'] * 100 if dist['losses'] > 0 else 0
                f.write(f"| {bucket} | {count} | {pct:.1f}% |\n")
            f.write("\n")

    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
