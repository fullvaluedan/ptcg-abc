"""Per-build loss ledger generation (plan U107).

Segregates the loss distribution by submission ref so that targeting can be
attributed to the actual shipped agent, not a historical mix of all builds.

Reads data/episode_to_ref.json (the manifest), data/replays/, and the current
live refs from state/current.md, then outputs a per-build loss distribution
report to analysis/u107_per_build_loss_ledger.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools import loop_state
from tools.harvest_replays import DEFAULT_MANIFEST


def get_live_refs() -> list[str]:
    """Load the current shadow-king and reclaim-king refs from state/current.md."""
    data = loop_state.read_current()
    return data.get("live_refs") or loop_state.DEFAULT_LIVE_REFS


def load_episode_to_ref() -> dict:
    """Load the episode-to-ref manifest, or return empty dict if it doesn't exist."""
    manifest_path = Path(DEFAULT_MANIFEST)
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def generate_per_build_report(replay_dir="data/replays") -> dict:
    """Generate the per-build loss distribution for current live refs.

    Returns a dict with per_build_reports (keyed by ref) and live_refs.
    """
    live_refs = get_live_refs()
    per_build_reports = {}

    for ref in live_refs:
        dist = loop_state.loss_distribution_from_dirs([replay_dir], ref_filter=[ref])
        per_build_reports[str(ref)] = dist

    return {
        "live_refs": live_refs,
        "per_build_reports": per_build_reports,
        "replay_dir": replay_dir,
    }


def render_markdown(report: dict) -> str:
    """Render the per-build report as markdown."""
    lines = [
        "# Per-Build Loss Ledger (U107)",
        "",
        "Loss distribution segregated by submission ref so targeting is attributed",
        "to the actual shipped agent, not a historical mix of all builds.",
        "",
        "## Summary",
        "",
    ]

    live_refs = report.get("live_refs", [])
    per_build = report.get("per_build_reports", {})

    if not per_build:
        lines.append("_No per-build reports generated._")
        return "\n".join(lines)

    for ref in live_refs:
        dist = per_build.get(str(ref), {})
        games = dist.get("sample_size", 0)
        wins = dist.get("wins", 0)
        draws = dist.get("draws", 0)
        losses = dist.get("losses", 0)
        top_bucket = dist.get("top_bucket", "unknown")

        lines.append(f"### Ref {ref}")
        lines.append(f"- Sample: {games} games (W/D/L {wins}/{draws}/{losses})")
        lines.append(f"- Top bucket: **{top_bucket}**")
        lines.append("")

    lines.append("## Per-Bucket Breakdown")
    lines.append("")

    # Show bucket-by-bucket for each ref
    for ref in live_refs:
        dist = per_build.get(str(ref), {})
        games = dist.get("sample_size", 0)
        if games == 0:
            lines.append(f"### Ref {ref}: No games")
            lines.append("")
            continue

        buckets = dist.get("buckets", {})
        lines.append(f"### Ref {ref} (n={games})")
        lines.append("")
        lines.append("| Bucket | Count | % |")
        lines.append("| --- | --- | --- |")

        for bucket in sorted(buckets.keys()):
            count = buckets[bucket]
            pct = 100.0 * count / games if games > 0 else 0.0
            lines.append(f"| {bucket} | {count} | {pct:.1f}% |")

        lines.append("")

    lines.append("## Targeting Priority")
    lines.append("")
    lines.append("Each build targets its own top loss bucket for the next unit.")
    lines.append("")

    return "\n".join(lines)


def main():
    report = generate_per_build_report()
    markdown = render_markdown(report)

    output_path = _ROOT / "analysis" / "u107_per_build_loss_ledger.md"
    output_path.write_text(markdown)

    print(f"Per-build loss ledger written to {output_path}")
    live_refs = report.get("live_refs", [])
    per_build = report.get("per_build_reports", {})
    for ref in live_refs:
        dist = per_build.get(str(ref), {})
        games = dist.get("sample_size", 0)
        top = dist.get("top_bucket", "unknown")
        print(f"  Ref {ref}: {games} games, top bucket = {top}")


if __name__ == "__main__":
    main()
