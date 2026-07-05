"""Gate board checks on the newest episode ID advancing (LOOP_BRIEF P5, queue item 7).

When the loop considers a board check, this tool queries the newest episode ID for the
tracked submission refs and compares it to the last recorded check. Only returns True
if the newest ID has advanced (i.e., new episodes have been played), preventing repeated
logging of frozen boards per ANTI-CHURN protocol.

Usage:
  python tools/gate_board_check.py --refs <ref1> <ref2> ... [--last-check-episode <id>]
  Returns 0 (gate open, proceed with board check) if newest episode has advanced.
  Returns 1 (gate closed, skip board check) if newest episode is unchanged.
  Writes the new newest_episode_id to stdout on successful gate-open.
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

from tools.scout import kaggle_base, run_kaggle  # noqa: E402

SIMULATION_SLUG = "pokemon-tcg-ai-battle"


def newest_episode_for_ref(ref: str) -> int | None:
    """Query the Kaggle API for the newest (highest) episode ID for a submission ref.

    Returns the newest episode ID as an int, or None on error.
    The Kaggle CLI outputs episode IDs in ascending order; we take the last one.
    """
    cmd = kaggle_base() + ["competitions", "episodes", str(ref), "-c", SIMULATION_SLUG]
    res = run_kaggle(cmd, timeout=30)
    if not res["ok"]:
        return None

    lines = res["output"].strip().split("\n")
    if len(lines) < 2:
        return None

    try:
        last_line = lines[-1].split()
        episode_id = int(last_line[0])
        return episode_id
    except (IndexError, ValueError):
        return None


def max_newest_episode(refs: list[str]) -> int | None:
    """Return the maximum newest episode ID across all refs."""
    ids = [newest_episode_for_ref(ref) for ref in refs]
    ids = [id for id in ids if id is not None]
    return max(ids) if ids else None


def should_gate_open(refs: list[str], last_check_episode: int | None) -> bool:
    """Return True if newest episode has advanced, False if frozen or error."""
    current_newest = max_newest_episode(refs)

    if current_newest is None:
        return False

    if last_check_episode is None:
        return True

    return current_newest > last_check_episode


def main():
    parser = argparse.ArgumentParser(
        description="Gate board checks on newest episode ID advancing"
    )
    parser.add_argument(
        "--refs",
        nargs="+",
        required=True,
        help="Submission refs to check (e.g., 54339500 54315802)",
    )
    parser.add_argument(
        "--last-check-episode",
        type=int,
        default=None,
        help="The newest episode ID from the last board check (optional)",
    )

    args = parser.parse_args()

    if should_gate_open(args.refs, args.last_check_episode):
        current_newest = max_newest_episode(args.refs)
        if current_newest is not None:
            print(current_newest)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
