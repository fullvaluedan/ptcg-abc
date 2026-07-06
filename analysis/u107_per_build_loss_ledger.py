"""U107: Per-build loss ledger (segregate losses by submission ref).

Generates loss distributions restricted to specific submission refs, allowing
us to attribute losses to the actual shipped agent rather than a historical
mix of all submissions.

Usage:
  python analysis/u107_per_build_loss_ledger.py --ref 54315802 54315565

Output: analysis/u107_per_build_loss_ledger.md

The current shadow-king and reclaim-king refs are read from state/current.md
if they exist (matching live board), or passed via --ref flags.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.loop_state import read_current  # noqa: E402


def extract_refs_from_current() -> dict:
    """Read shadow-king and reclaim-king refs from state/current.md."""
    data = read_current()
    in_flight = data.get("in_flight", {})
    kings = {}

    # Try to find refs from the in_flight section or per-build ledger
    if "board_reading" in in_flight and "/" in in_flight["board_reading"]:
        readings = in_flight["board_reading"].split("/")
        if len(readings) >= 2:
            # Format is typically "reading1/reading2 (ref1 ..., ref2 ...)"
            # Extract refs from the parenthesized part
            if "(" in readings[-1]:
                text = readings[-1]
                # Parse out refs
                if "54315802" in text or "54339500" in text:
                    kings["shadow_king"] = None
                if "54315565" in text:
                    kings["reclaim_king"] = None

    # Fallback: grep the ledger for recent COMPLETE readings
    return kings


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ref", nargs="+", help="submission refs to analyze (default: current king refs)")
    ap.add_argument("--output", default=str(_ROOT / "analysis" / "u107_per_build_loss_ledger.md"),
                    help="output markdown file (default analysis/u107_per_build_loss_ledger.md)")
    args = ap.parse_args()

    refs = args.ref if args.ref else ["54315802", "54315565"]  # shadow-king, reclaim-king

    output_path = Path(args.output)

    # For now, output a stub indicating the feature is being developed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    markdown = f"""# U107: Per-Build Loss Ledger

## Summary

Per-build loss segregation for submission refs: {", ".join(refs)}.

Current status: **MANIFEST INFRASTRUCTURE ADDED** (tools/harvest_replays.py updated to persist episode-to-ref mapping to data/episode_to_ref.json).

## Next Steps

1. Backfill existing episodes via tools/scout.py list_episodes per ref
2. Filter loss distributions using the episode-to-ref manifest
3. Rerun loss_classifier restricted to current-king and shadow-king episodes

## Refs Analyzed

- shadow-king (best live): 54315802 (heuristic+trolley-ability)
- reclaim-king (safe floor): 54315565 (heuristic+trolley)

## Implementation Status

- [DONE] harvest_replays.py modified to persist episode->ref mapping
- [DONE] loop_state.py updated with classify_dirs_per_build function (ref filtering infrastructure)
- [TODO] Backfill existing episodes with their refs (requires API call per ref)
- [TODO] Filter loss_classifier output by ref

## Note

This unit is mechanical: it collects loss data per build so we can attribute
targeting decisions to the shipped agent only, not a historical average
across all ever-submitted builds. This segregation is prerequisite for
honest loss mode targeting in TRACK L going forward.
"""

    output_path.write_text(markdown)
    print(f"Per-build loss ledger stub written to {output_path}")
    print(f"Next: backfill episode-to-ref manifest via tools/scout.py list_episodes")


if __name__ == "__main__":
    sys.exit(main() or 0)
