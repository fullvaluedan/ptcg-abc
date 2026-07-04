"""Refit the U22 noise model (margin M) from accumulated same-build ladder reads.

state/current.md's per-build ledger has grown to dozens of board-check rows for
two byte-identical builds (the trolley king and the ability floor build), each
resubmitted only to hold a scored slot, never to test a lever. Those repeat
reads are exactly the data a same-build noise model needs, but the current
M=150 was set by eyeballing one full min/max range (~295 points on ~6 reads).
This module turns the full ledger into a statistical refit: group ladder reads
by build family (the part of the build name before its first parenthetical,
since "heuristic+trolley (king-copy revert, 2026-07-04)" and "heuristic+trolley
(reclaim)" are the same tarball resubmitted under different notes), compute
each family's own mean/stdev, and pool the residuals (reading minus that
family's mean) across families so a mean difference between two builds never
gets mistaken for noise. The recommended M is the larger of a 2-sigma bound and
the single worst observed pooled residual, rounded up to the nearest 10, so a
long tail (like a one-off 235-point deviation) cannot be statistically averaged
away by a bound that would not have covered it.
"""
from __future__ import annotations

import argparse
import math
import statistics as st
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.loop_state import read_current, write_current  # noqa: E402

MIN_FAMILY_N = 3
SIGMA_MULTIPLE = 2


def family_key(build: str) -> str:
    """The build name up to its first parenthetical, e.g. strip "(king-copy revert)"."""
    return build.split(" (")[0].strip()


def family_reads(ledger: list) -> dict:
    """Group numeric ladder reads from the ledger by family_key(build)."""
    families: dict = {}
    for entry in ledger:
        build = entry.get("build") or ""
        try:
            value = float(entry.get("ladder"))
        except (TypeError, ValueError):
            continue
        families.setdefault(family_key(build), []).append(value)
    return families


def refit(ledger: list, min_family_n: int = MIN_FAMILY_N) -> dict:
    """Compute per-family stats, pooled residual spread, and a recommended M.

    Families with fewer than min_family_n reads are reported but excluded from
    the pooled residual calculation: a single or double read cannot estimate a
    family's own mean well enough to contribute a meaningful residual.
    """
    families = family_reads(ledger)
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


def _format_report(report: dict) -> str:
    lines = ["Per-family same-build reads:"]
    for name, entry in report["per_family"].items():
        lines.append(
            f"  {name}: n={entry['n']} mean={entry['mean']:.1f} stdev={entry['stdev']:.1f} "
            f"range=[{entry['min']:.1f}, {entry['max']:.1f}]"
        )
    if report["recommended_M"] is not None:
        lines.append(
            f"Pooled residuals: n={report['pooled_n']} stdev={report['pooled_stdev']:.1f} "
            f"max_abs={report['max_abs_residual']:.1f}"
        )
        lines.append(
            f"Recommended M = {report['recommended_M']} "
            f"(max of {report['sigma_multiple']}-sigma bound and worst observed residual, "
            "rounded up to nearest 10)"
        )
    else:
        lines.append(
            f"Not enough qualifying families (need >= {MIN_FAMILY_N} reads each) to refit M."
        )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                         help="write the recommended M into state/current.md's noise_model block")
    parser.add_argument("--refit-by", default=None,
                         help="new re-fit-by date to record when --write is used")
    args = parser.parse_args(argv)

    data = read_current()
    ledger = data.get("ledger") or []
    report = refit(ledger)
    print(_format_report(report))

    if args.write and report["recommended_M"] is not None:
        noise = data.get("noise_model") or {}
        prior_version = noise.get("version", 1)
        noise["margin_M"] = report["recommended_M"]
        noise["version"] = prior_version + 1
        family_summary = ", ".join(
            f"{name} (n={entry['n']}, mean={entry['mean']:.1f}, stdev={entry['stdev']:.1f})"
            for name, entry in report["per_family"].items()
            if entry["n"] >= MIN_FAMILY_N
        )
        noise["basis"] = (
            f"tools/refit_noise_model.py statistical refit over {report['pooled_n']} pooled "
            f"same-build reads across {family_summary}: pooled residual stdev "
            f"{report['pooled_stdev']:.1f}, worst observed residual "
            f"{report['max_abs_residual']:.1f}. M set to the larger of "
            f"{report['sigma_multiple']}-sigma and the worst residual, rounded up to nearest 10."
        )
        if args.refit_by:
            noise["refit_by"] = args.refit_by
        data["noise_model"] = noise
        write_current(data)
        print(f"Wrote margin_M={report['recommended_M']} (v{noise['version']}) to state/current.md")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
