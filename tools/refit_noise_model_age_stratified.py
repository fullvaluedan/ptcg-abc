"""Age-stratified refitting of the noise model and true king estimate.

When a build is freshly submitted, its first few games may be lucky or unlucky
relative to its true strength. This tool groups reads by age since submission
(<48h, 48-72h, >72h) and computes per-family means for each age band separately.

The insight (P4 in LOOP_BRIEF.md): fresh reads are inflated vs aged reads. So
we re-derive the true king estimate from AGED reads (>72h) only, giving us a
better baseline for the endgame variance-harvest campaign and the final pair
lock-by decision.

Requires: the Kaggle CLI, with submission dates from 'kaggle competitions submissions'.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.loop_state import read_current, write_current  # noqa: E402
COMPETITION = "pokemon-tcg-ai-battle"
MIN_FAMILY_N = 3


def family_key(build: str) -> str:
    """The build name up to its first parenthetical."""
    return build.split(" (")[0].strip()


def fetch_submissions_with_dates() -> dict:
    """Fetch submission list from Kaggle API and parse dates.

    Returns {ref: {'date': datetime, 'score': float, 'description': str}, ...}
    """
    # Find kaggle CLI
    kaggle_exe = _ROOT / ".venv" / "Scripts" / "kaggle.exe"
    if not kaggle_exe.exists():
        print(f"Kaggle CLI not found at {kaggle_exe}", file=sys.stderr)
        return {}

    try:
        result = subprocess.run(
            [str(kaggle_exe), "competitions", "submissions", "-c", COMPETITION],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(_ROOT)
        )
    except subprocess.TimeoutExpired:
        print("Kaggle API timeout", file=sys.stderr)
        return {}
    except FileNotFoundError:
        print("Kaggle CLI not found", file=sys.stderr)
        return {}

    if result.returncode != 0:
        print(f"Kaggle API error (code {result.returncode}): {result.stderr}", file=sys.stderr)
        return {}

    submissions = {}
    lines = result.stdout.strip().split("\n")

    for i, line in enumerate(lines):
        # Skip headers and blank lines
        if not line.strip() or ("ref" in line and "date" in line) or all(c == '-' for c in line.strip()):
            continue

        # Parse the fixed-width table format
        # Pattern: <ref>  <fileName>  <date>  <time>  <description> ...
        # Extract ref from the beginning (right-aligned in a column)
        import re
        match = re.match(r'\s*(\d+)\s+(\S+)\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}\.\d+)', line)
        if not match:
            continue

        try:
            ref, filename, date_str, time_str = match.groups()
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S.%f")

            submissions[str(ref)] = {
                "ref": str(ref),
                "date": dt,
                "line": line
            }
        except (ValueError, IndexError):
            continue

    return submissions


def build_ref_to_submission_date(ledger: list, submissions: dict) -> dict:
    """Map each ledger entry's ref to its submission date.

    Extracts ref from the ledger entry's 'note' field if available.
    Returns {ref: datetime, ...}
    """
    ref_to_date = {}

    for entry in ledger:
        note = entry.get("note", "")

        # Try to extract submission ref from the note
        # Common patterns: "ref 54315802", "(ref 54315802,", etc.
        import re
        refs_in_note = re.findall(r"ref\s+(\d+)", note)

        for ref_str in refs_in_note:
            if ref_str in submissions:
                ref_to_date[ref_str] = submissions[ref_str]["date"]

    return ref_to_date


def age_days_from_now(submission_date: datetime, now: datetime) -> float:
    """Compute age in days from submission_date to now."""
    if submission_date is None:
        return None
    return (now - submission_date).total_seconds() / (24 * 3600)


def stratify_reads_by_age(
    ledger: list, ref_to_date: dict, now: datetime = None
) -> dict:
    """Group reads by submission age: <48h, 48-72h, >72h.

    Returns {
        '<48h': [(ref, build, ladder_score), ...],
        '48-72h': [...],
        '>72h': [...],
        'undated': [(build, ladder_score), ...]  # no ref found
    }
    """
    if now is None:
        now = datetime.utcnow()

    strata = {"<48h": [], "48-72h": [], ">72h": [], "undated": []}

    for entry in ledger:
        build = entry.get("build") or ""
        try:
            ladder_score = float(entry.get("ladder"))
        except (TypeError, ValueError):
            continue

        note = entry.get("note", "")

        # Try to extract the main submission ref from the note
        import re
        ref_match = re.search(r"ref\s+(\d+)", note)
        ref = ref_match.group(1) if ref_match else None

        if ref and ref in ref_to_date:
            date = ref_to_date[ref]
            age = age_days_from_now(date, now)

            if age < 2:  # <48h
                strata["<48h"].append((ref, build, ladder_score, age))
            elif age < 3:  # 48-72h
                strata["48-72h"].append((ref, build, ladder_score, age))
            else:  # >72h
                strata[">72h"].append((ref, build, ladder_score, age))
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
            build = entry[1]  # (ref, build, score, age)
            score = entry[2]
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
        "--write",
        action="store_true",
        help="write the aged king estimate to state/current.md (TODO: implement)",
    )
    args = parser.parse_args(argv)

    print("Fetching submission dates from Kaggle API...")
    sys.stdout.flush()
    submissions = fetch_submissions_with_dates()
    if not submissions:
        print("ERROR: Could not fetch submissions from Kaggle API", file=sys.stderr)
        sys.stderr.flush()
        return 1

    print(f"Loaded {len(submissions)} submissions")

    print("Reading ledger from state/current.md...")
    data = read_current()
    ledger = data.get("ledger") or []

    print("Mapping ledger entries to submission dates...")
    ref_to_date = build_ref_to_submission_date(ledger, submissions)
    print(f"Dated {len(ref_to_date)} ledger entries")

    print("Stratifying reads by age...")
    now = datetime.utcnow()
    strata = stratify_reads_by_age(ledger, ref_to_date, now)

    for stratum, reads in strata.items():
        print(f"  {stratum}: {len(reads)} reads")

    print("Computing per-age statistics...")
    stats = compute_stratified_stats(strata)

    report = format_report(strata, stats)
    print("\n" + report)

    # Write report to disk
    report_path = _ROOT / "analysis" / "noise_model_age_stratified.md"
    report_path.write_text(f"# Age-Stratified Noise Model Refit\n\nGenerated {now.isoformat()} UTC\n\n```\n{report}\n```\n")
    print(f"\nWrote report to {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
