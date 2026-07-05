"""Refit noise model M using age-stratified analysis.

Per P4 POSTURE INVERSION: fresh reads are inflated vs aged reads. This tool
separates ladder reads by age (<48h = fresh, >72h = aged) and refits M using
AGED reads only to get the true king estimate independent of luck variance.

Usage:
  python tools/age_stratified_refit.py [--today YYYY-MM-DD] [--verbose]

Output: age-stratified report with per-family means and recommended M (aged only).
"""
from __future__ import annotations

import argparse
import math
import re
import statistics as st
import sys
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.loop_state import read_current  # noqa: E402

MIN_FAMILY_N = 3
SIGMA_MULTIPLE = 2


def extract_date_from_note(note: str) -> datetime | None:
    """Extract date from ledger note, e.g. 'Board check 2026-07-05: 563.8'.

    Returns datetime object or None if no date found.
    """
    # Match "Board check YYYY-MM-DD" or "2026-07-XX" patterns
    patterns = [
        r"Board check (\d{4}-\d{2}-\d{2})",
        r"settled (\d{4}-\d{2}-\d{2})",
        r"(\d{4}-\d{2}-\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, note)
        if match:
            try:
                return datetime.strptime(match.group(1), "%Y-%m-%d")
            except ValueError:
                pass
    return None


def parse_ledger(ledger: list, today: datetime) -> dict:
    """Parse ledger entries and stratify by age.

    Returns: {family: {fresh: [values], aged: [values], mixed: [values]}}
    """
    result = {}
    for entry in ledger:
        build = entry.get("build") or ""
        try:
            value = float(entry.get("ladder"))
        except (TypeError, ValueError):
            continue

        note = entry.get("note") or ""
        date = extract_date_from_note(note)
        if date is None:
            continue

        # Calculate age in hours
        age_hours = (today - date).total_seconds() / 3600

        # Categorize: fresh <48h, aged >72h, mixed in between
        if age_hours < 48:
            bucket = "fresh"
        elif age_hours > 72:
            bucket = "aged"
        else:
            bucket = "mixed"

        family = build.split(" (")[0].strip()
        if family not in result:
            result[family] = {"fresh": [], "aged": [], "mixed": []}
        result[family][bucket].append((value, age_hours))

    return result


def refit_aged(stratified: dict, min_family_n: int = MIN_FAMILY_N) -> dict:
    """Refit M using aged reads only (>72h).

    Returns: {family: stats, pooled: stats, recommended_M: int}
    """
    per_family = {}
    residuals = []

    for family, buckets in sorted(stratified.items()):
        aged_values = [v for v, _ in buckets["aged"]]

        if len(aged_values) == 0:
            continue

        mean = st.mean(aged_values)
        entry = {
            "n_aged": len(aged_values),
            "n_fresh": len(buckets["fresh"]),
            "n_mixed": len(buckets["mixed"]),
            "n_total": len(aged_values) + len(buckets["fresh"]) + len(buckets["mixed"]),
            "mean_aged": mean,
            "stdev_aged": st.stdev(aged_values) if len(aged_values) > 1 else 0.0,
            "min_aged": min(aged_values),
            "max_aged": max(aged_values),
        }
        per_family[family] = entry

        # Contribute to pooled residuals only if n_aged >= min_family_n
        if len(aged_values) >= min_family_n:
            residuals.extend(v - mean for v in aged_values)

    if len(residuals) >= 2:
        pooled_stdev = st.stdev(residuals)
        max_abs_residual = max(abs(r) for r in residuals)
        sigma_bound = SIGMA_MULTIPLE * pooled_stdev
        recommended_M = int(math.ceil(max(sigma_bound, max_abs_residual) / 10.0) * 10)
    else:
        pooled_stdev = None
        max_abs_residual = None
        recommended_M = None

    return {
        "per_family": per_family,
        "pooled_n": len(residuals),
        "pooled_stdev": pooled_stdev,
        "max_abs_residual": max_abs_residual,
        "sigma_multiple": SIGMA_MULTIPLE,
        "recommended_M": recommended_M,
    }


def format_report(stratified: dict, refitted: dict, today: datetime) -> str:
    """Format a readable report."""
    lines = [
        f"Age-Stratified Noise Model Refit",
        f"Today: {today.strftime('%Y-%m-%d')}",
        f"Threshold: fresh <48h, aged >72h, mixed in-between",
        "",
        "Per-family breakdown (aged reads):".upper(),
        "",
    ]

    for family in sorted(refitted["per_family"].keys()):
        entry = refitted["per_family"][family]
        lines.append(
            f"{family:30s} "
            f"aged={entry['n_aged']:2d} "
            f"mean={entry['mean_aged']:6.1f} "
            f"stdev={entry['stdev_aged']:5.1f} "
            f"[{entry['min_aged']:6.1f}, {entry['max_aged']:6.1f}] "
            f"(fresh={entry['n_fresh']:2d} mixed={entry['n_mixed']:2d})"
        )

    lines.extend(
        [
            "",
            "Pooled statistics (aged reads, families with n_aged >= 3):".upper(),
            f"  Pooled n:             {refitted['pooled_n']}",
            f"  Pooled stdev:         {refitted['pooled_stdev']:.1f}" if refitted['pooled_stdev'] else "  Pooled stdev:         N/A",
            f"  Max |residual|:       {refitted['max_abs_residual']:.1f}" if refitted['max_abs_residual'] else "  Max |residual|:       N/A",
            f"  Sigma multiple:       {refitted['sigma_multiple']}",
            f"  Recommended M (aged):  {refitted['recommended_M']}" if refitted['recommended_M'] else "  Recommended M (aged):  N/A (insufficient data)",
            "",
        ]
    )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--today",
        type=str,
        default="2026-07-06",
        help="Reference date (YYYY-MM-DD), default 2026-07-06",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-family details",
    )
    args = parser.parse_args()

    today = datetime.strptime(args.today, "%Y-%m-%d")
    state = read_current()

    if not state or "ledger" not in state:
        print("ERROR: No ledger found in state/current.md")
        sys.exit(1)

    ledger = state["ledger"]
    stratified = parse_ledger(ledger, today)
    refitted = refit_aged(stratified)

    print(format_report(stratified, refitted, today))


if __name__ == "__main__":
    main()
