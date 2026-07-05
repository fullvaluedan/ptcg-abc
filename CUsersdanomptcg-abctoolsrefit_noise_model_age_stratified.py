"""Age-stratified refit of the U22 noise model.

Fresh reads (< 48h old) may be inflated by recent luck. Aged reads (> 72h old)
better represent true strength after convergence. This tool extracts timestamped
reads from state/current.md's ledger section, stratifies by age, and compares
the family means to see if fresh reads are systematically higher.

P4 directive: re-derive the true king estimate from AGED reads only.
"""
from __future__ import annotations

import argparse
import datetime
import math
import re
import statistics as st
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.loop_state import read_current, write_current  # noqa: E402

MIN_FAMILY_N = 3
SIGMA_MULTIPLE = 2


def extract_timestamped_reads(current_md_path: str, now: datetime.datetime) -> list:
    """Extract board-check reads with timestamps from the ledger section.
    
    Parses lines like:
      "Board check 2026-07-04: 602.4 (drifted from 584.7)."
    Returns list of dicts: {"build": name, "ladder": score, "timestamp": datetime, "age_hours": N}
    """
    reads = []
    
    with open(current_md_path, "r") as f:
        content = f.read()
    
    # Extract the "Per-build ledger" section (between ## header and ## next section)
    ledger_start = content.find("## Per-build ledger")
    if ledger_start == -1:
        return []
    
    ledger_end = content.find("\n## ", ledger_start + 1)
    if ledger_end == -1:
        ledger_end = content.find("\n```json", ledger_start + 1)
    
    ledger_text = content[ledger_start:ledger_end]
    
    # Pattern: "| build | ... |" then "| heuristic+trolley (floor restoration) | ... | Board check 2026-07-04: 602.4 ..."
    # Find all lines with "Board check YYYY-MM-DD: NNN.N"
    board_check_pattern = r"Board check (\d{4}-\d{2}-\d{2}): ([\d.]+)"
    
    # For each line in the ledger text, extract build name and checks
    lines = ledger_text.split("\n")
    current_build = None
    
    for line in lines:
        # Lines with build names start with "| " (table rows)
        if line.startswith("| ") and " | " in line:
            parts = line.split(" | ")
            if len(parts) >= 2:
                potential_build = parts[1].strip()
                # It's a build name if it's not "build" (header) and contains typical names
                if potential_build != "build" and potential_build and not potential_build.startswith("---"):
                    current_build = potential_build
        
        # Extract board checks from the line
        for match in re.finditer(board_check_pattern, line):
            date_str, score_str = match.groups()
            try:
                date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                score = float(score_str)
                age = now - date
                age_hours = age.total_seconds() / 3600
                
                reads.append({
                    "build": current_build or "unknown",
                    "ladder": score,
                    "timestamp": date,
                    "age_hours": age_hours,
                })
            except (ValueError, TypeError):
                pass
    
    return reads


def family_key(build: str) -> str:
    """Extract family name (part before first parenthetical)."""
    return build.split(" (")[0].strip()


def stratify_by_age(reads: list) -> dict:
    """Stratify reads by age: <48h (fresh), 48-72h (middle), >72h (aged)."""
    fresh = []  # < 48h
    middle = []  # 48-72h
    aged = []  # > 72h
    
    for read in reads:
        age_h = read["age_hours"]
        if age_h < 48:
            fresh.append(read)
        elif age_h < 72:
            middle.append(read)
        else:
            aged.append(read)
    
    return {"fresh": fresh, "middle": middle, "aged": aged}


def compute_family_stats(reads: list) -> dict:
    """Compute per-family stats (same as refit_noise_model.py)."""
    families = {}
    for read in reads:
        family = family_key(read["build"])
        families.setdefault(family, []).append(read["ladder"])
    
    per_family = {}
    for name, values in sorted(families.items()):
        entry = {
            "n": len(values),
            "mean": st.mean(values),
            "stdev": st.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
        }
        per_family[name] = entry
    
    return per_family


def refit_age_stratified(reads: list) -> dict:
    """Compute per-family stats for all reads, then for aged reads only."""
    all_families = compute_family_stats(reads)
    
    # Separate aged reads
    stratified = stratify_by_age(reads)
    aged_families = compute_family_stats(stratified["aged"])
    fresh_families = compute_family_stats(stratified["fresh"])
    
    # Compute pooled residuals (aged reads only)
    residuals_aged = []
    for name, values in stratified["aged"]:
        family = family_key(name["build"])
        if family in aged_families and aged_families[family]["n"] >= MIN_FAMILY_N:
            mean = aged_families[family]["mean"]
            residuals_aged.extend(v - mean for v in values)
    
    # Fix the logic above: iterate over aged reads, not families
    residuals_aged = []
    aged_values_by_family = {}
    for read in stratified["aged"]:
        family = family_key(read["build"])
        aged_values_by_family.setdefault(family, []).append(read["ladder"])
    
    for family, values in aged_values_by_family.items():
        if len(values) >= MIN_FAMILY_N:
            mean = st.mean(values)
            residuals_aged.extend(v - mean for v in values)
    
    if len(residuals_aged) >= 2:
        pooled_stdev_aged = st.stdev(residuals_aged)
        max_abs_residual_aged = max(abs(r) for r in residuals_aged)
        sigma_bound_aged = SIGMA_MULTIPLE * pooled_stdev_aged
        recommended_M_aged = int(math.ceil(max(sigma_bound_aged, max_abs_residual_aged) / 10.0) * 10)
    else:
        pooled_stdev_aged = None
        max_abs_residual_aged = None
        recommended_M_aged = None
    
    return {
        "all_reads": {
            "per_family": all_families,
            "count": len(reads),
        },
        "fresh_reads": {
            "per_family": fresh_families,
            "count": len(stratified["fresh"]),
            "note": "< 48h old",
        },
        "aged_reads": {
            "per_family": aged_families,
            "count": len(stratified["aged"]),
            "note": "> 72h old",
            "pooled_n": len(residuals_aged),
            "pooled_stdev": pooled_stdev_aged,
            "max_abs_residual": max_abs_residual_aged,
            "recommended_M": recommended_M_aged,
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--now", default=None,
                         help="reference time (YYYY-MM-DD HH:MM) for age calculation; default=now")
    args = parser.parse_args(argv)
    
    if args.now:
        now = datetime.datetime.strptime(args.now, "%Y-%m-%d %H:%M")
    else:
        now = datetime.datetime.utcnow()
    
    md_path = _ROOT / "state" / "current.md"
    reads = extract_timestamped_reads(str(md_path), now)
    
    if not reads:
        print("No timestamped board-check reads found in state/current.md")
        return 1
    
    print(f"Extracted {len(reads)} timestamped reads from state/current.md (reference time: {now} UTC)")
    print()
    
    report = refit_age_stratified(reads)
    
    print("=== Age-Stratified Noise Model Refit ===\n")
    print(f"All reads (n={report['all_reads']['count']}):")
    for name, entry in report["all_reads"]["per_family"].items():
        print(
            f"  {name}: n={entry['
