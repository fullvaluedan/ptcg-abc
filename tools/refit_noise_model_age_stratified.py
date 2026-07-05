"""Age-stratified refitting of the noise model and true king estimate.

When a build is freshly submitted, its first few games may be lucky or unlucky
relative to its true strength. This tool groups reads by age since the read date
(<48h, 48-72h, >72h) and computes per-family means for each age band separately.

The insight (P4 in LOOP_BRIEF.md): fresh reads are inflated vs aged reads. So
we re-derive the true king estimate from AGED reads (>72h) only, giving us a
better baseline for the endgame variance-harvest campaign and the final pair
lock-by decision.

Reads are dated using the date embedded in the note field (e.g., "Board check
2026-07-04: 540.9" yields date 2026-07-04). Age is computed relative to the
reference date (default 2026-07-05, today).
"""
from __future__ import annotations

import argparse
import re
import statistics as st
import sys
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.loop_state import read_current, write_current  # noqa: E402

MIN_FAMILY_N = 3


def family_key(build: str) -> str:
    """The build name up to its first parenthetical."""
    return build.split(" (")[0].strip()


def extract_date_from_note(note: str) -> datetime | None:
    """Extract date from note field, e.g., 'Board check 2026-07-04: 540.9'."""
    if not note:
        return None
    match = re.search(r'(2026-07-\d{2})', note)
    if match:
        try:
            return datetime.strptime(match.group(1), '%Y-%m-%d')
        except ValueError:
            return None
    return None


def compute_age_hours(read_date: datetime, reference_date: datetime) -> float:
    """Compute age of read in hours."""
    if read_date is None:
        return None
    delta = reference_date - read_date
    return delta.total_seconds() / 3600.0


def stratify_reads_by_age(
    ledger: list, reference_date: datetime
) -> dict:
    """Group reads by age since the read date: <48h, 48-72h, >72h.

    Returns {
        '<48h': [(build, ladder_score, age_hours), ...],
        '48-72h': [...],
        '>72h': [...],
        'undated': [(build, ladder_score), ...]  # no date found in note
    }
    """
    strata = {"<48h": [], "48-72h": [], ">72h": [], "undated": []}

    for entry in ledger:
        build = entry.get("build") or ""
        try:
            ladder_score = float(entry.get("ladder"))
        except (TypeError, ValueError):
            continue

        note = entry.get("note", "")
        read_date = extract_date_from_note(note)

        if read_date:
            age_hours = compute_age_hours(read_date, reference_date)
            if age_hours < 48:  # <48h
                strata["<48h"].append((build, ladder_score, age_hours))
            elif age_hours < 72:  # 48-72h
                strata["48-72h"].append((build, ladder_score, age_hours))
            else:  # >72h
                strata[">72h"].append((build, ladder_score, age_hours))
        else:
            strata["undated"].append((build, ladder_score))

    return strata


def compute_stratified_stats(
    strata: dict, min_family_n: int = MIN_FAMILY_N
) -> dict:
    """Compute per-family stats within each age stratum.

    Returns {
        '<48h': {'per_family': {...}, 'pooled_stdev': ..., ...},
        '48-72h': {...},
        '>72h': {...}
    }
    """
    result = {}

    for stratum_name in ["<48h", "48-72h", ">72h"]:
        reads = strata[stratum_name]

        # Extract (build, score) pairs
        families: dict = {}
        for entry in reads:
            build = entry[0]  # (build, score) or (build, score, age_hours)
            score = entry[1]
            families.setdefault(family_key(build), []).append(score)

        # Compute stats
        per_family = {}
        residuals = []
        for name, values in sorted(families.items()):
            mean = st.mean(values)
            entry = {
                "n": len(values),
                "mean": mean,
                "stdev": st.stdev(values) if len(values) > 1 else 0.0,
                "min": min(values),
                "max": max(values),
            }
            per_family[name] = entry

            if len(values) >= min_family_n:
                residuals.extend(v - mean for v in values)

        stats = {
            "per_family": per_family,
            "pooled_n": len(residuals),
            "n_total_reads": len(reads)
        }

        if residuals:
            stats["pooled_stdev"] = st.stdev(residuals) if len(residuals) > 1 else 0.0
            stats["max_abs_residual"] = max(abs(r) for r in residuals)

        result[stratum_name] = stats

    return result


def format_report(strata: dict, stats: dict) -> str:
    """Format the age-stratified analysis as a report."""
    lines = ["AGE-STRATIFIED NOISE MODEL REFIT", "=" * 60]

    for stratum in ["<48h", "48-72h", ">72h"]:
        lines.append(f"\n{stratum} (fresh -> aged):")
        lines.append(f"  Total reads in stratum: {stats[stratum]['n_total_reads']}")

        if stats[stratum]["per_family"]:
            lines.append("  Per-family stats:")
            for name, entry in stats[stratum]["per_family"].items():
                lines.append(
                    f"    {name}: n={entry['n']:2} mean={entry['mean']:7.1f} "
                    f"stdev={entry['stdev']:6.1f} range=[{entry['min']:7.1f}, {entry['max']:7.1f}]"
                )

        if stats[stratum]["pooled_n"] > 0:
            lines.append(
                f"  Pooled residuals: n={stats[stratum]['pooled_n']} "
                f"stdev={stats[stratum].get('pooled_stdev', 'N/A'):.1f} "
                f"max_abs={stats[stratum].get('max_abs_residual', 'N/A'):.1f}"
            )

    lines.append(f"\n{'=' * 60}")
    lines.append("\nIMPLICATION:")

    # Compare aged vs fresh king estimates
    aged_stats = stats.get(">72h", {}).get("per_family", {})
    fresh_stats = stats.get("<48h", {}).get("per_family", {})

    for build_name in ["heuristic+trolley", "heuristic+trolley-ability"]:
        if build_name in aged_stats and build_name in fresh_stats:
            aged_mean = aged_stats[build_name].get("mean")
            fresh_mean = fresh_stats[build_name].get("mean")
            if aged_mean is not None and fresh_mean is not None:
                diff = fresh_mean - aged_mean
                lines.append(
                    f"{build_name}:"
                )
                lines.append(
                    f"  Aged (>72h):  mean={aged_mean:7.1f} (n={aged_stats[build_name]['n']})"
                )
                lines.append(
                    f"  Fresh (<48h): mean={fresh_mean:7.1f} (n={fresh_stats[build_name]['n']})"
                )
                lines.append(
                    f"  Difference:   {diff:+.1f}pp (fresh is {'inflated' if diff > 0 else 'depressed'})"
                )

    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reference-date",
        default="2026-07-05",
        help="reference date for age computation (YYYY-MM-DD, default 2026-07-05)"
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the aged king estimate to state/current.md (TODO: implement)",
    )
    args = parser.parse_args(argv)

    try:
        reference_date = datetime.strptime(args.reference_date, '%Y-%m-%d')
    except ValueError:
        print(f"ERROR: Invalid date format '{args.reference_date}', expected YYYY-MM-DD", file=sys.stderr)
        return 1

    print(f"Reading ledger from state/current.md...")
    data = read_current()
    ledger = data.get("ledger") or []
    print(f"Loaded {len(ledger)} ledger entries")

    print(f"Stratifying reads by age (reference: {args.reference_date})...")
    strata = stratify_reads_by_age(ledger, reference_date)

    for stratum, reads in strata.items():
        print(f"  {stratum}: {len(reads)} reads")

    print("Computing per-age statistics...")
    stats = compute_stratified_stats(strata)

    report = format_report(strata, stats)
    print("\n" + report)

    # Write report to disk
    report_path = _ROOT / "analysis" / "noise_model_age_stratified.md"
    report_path.write_text(
        f"# Age-Stratified Noise Model Refit\n\nGenerated {reference_date.isoformat()}\n\n```\n{report}\n```\n"
    )
    print(f"\nWrote report to {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
