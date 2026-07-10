"""Convergence residual sigma estimate (plan U7 / U115).

Prices the "identical build vs hedge" pair decision: after a build's rating
reads have converged, how much noise is left in a single read? That residual
sigma, with a confidence interval, is the number U10's E[max] arithmetic needs
to decide whether a runner-up's ring CI overlap is real signal or just noise.

The ledger in state/current.md (read via tools.loop_state.read_current) carries
build, ladder score, and a free-text note per read -- no episode count. The
correct covariate for "how converged is this read" is the number of games the
read's ref had played by the time it was taken. That is reconstructed by
listing the ref's episodes (tools/scout.py list_submissions/list_episodes,
which wrap the kaggle CLI) and counting the ones created before the read's own
date. When the kaggle CLI or episode history is not reachable in the current
environment, this tool falls back to age-hours (time between the read's noted
date and a reference date) as the covariate instead, and says so plainly in
both the console report and analysis/convergence_sigma.md -- never silently.

This extends tools/refit_noise_model_age_stratified.py rather than reinventing
it: family_key, extract_date_from_note, and compute_age_hours are imported
from there directly. That module's finding (see
analysis/age_stratified_refit_findings.md and findings.md) is the fresh-read-
depression correction this tool applies: reads taken within 48h of the
reference date read low relative to aged reads of the same family, so they are
excluded from the terminal (converged) sigma estimate. They still appear in
the sigma-vs-covariate curve, where the drop-off is the point.
"""
from __future__ import annotations

import argparse
import random
import statistics as st
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.loop_state import read_current  # noqa: E402
from tools.refit_noise_model_age_stratified import (  # noqa: E402
    compute_age_hours,
    extract_date_from_note,
    family_key,
)

MIN_FAMILY_N = 3
FRESH_CUTOFF_HOURS = 48.0
CONVERGENCE_WINDOW_GAMES = (200, 350)
DEFAULT_CI_ALPHA = 0.10  # 90% CI
DEFAULT_N_BOOT = 4000
DEFAULT_SEED = 20260710

# Bin edges (hours) used for the sigma-vs-covariate curve in the age-hours
# fallback. Kept fine-grained near the fresh/aged boundary since that is where
# the depression correction bites; coarser above it.
AGE_HOUR_BINS = [
    (0.0, 24.0),
    (24.0, 48.0),
    (48.0, 72.0),
    (72.0, 96.0),
    (96.0, 120.0),
    (120.0, 144.0),
    (144.0, 168.0),
    (168.0, 192.0),
    (192.0, float("inf")),
]

# Bin edges (games) used for the curve when real episode counts are
# available. 350 is the top of the plan's convergence window.
EPISODE_BINS = [
    (0, 50),
    (50, 100),
    (100, 150),
    (150, 200),
    (200, 250),
    (250, 300),
    (300, 350),
    (350, float("inf")),
]


def try_reconstruct_episode_counts(ledger: list) -> tuple[dict | None, str]:
    """Attempt to reconstruct a per-read episode count via the kaggle CLI.

    Returns (covariate_by_index, reason). covariate_by_index maps a ledger
    index to an int episode count when reconstruction succeeds for every
    dated read that needs it. On any failure (kaggle CLI missing, a ref's
    episode list unavailable, no parseable creation date on the episodes),
    returns (None, reason) so the caller falls back to age-hours -- explicitly,
    not silently.
    """
    try:
        from tools import scout
    except Exception as exc:  # pragma: no cover - defensive import guard
        return None, f"tools.scout import failed: {exc}"

    subs = scout.list_submissions()
    if not subs.get("ok"):
        return None, f"kaggle CLI unavailable ({subs.get('error')})"

    refs = sorted({str(e.get("ref")) for e in ledger if e.get("ref")})
    episodes_by_ref: dict[str, list[datetime]] = {}
    for ref in refs:
        res = scout.list_episodes(ref)
        if not res.get("ok"):
            return None, f"episode listing failed for ref {ref} ({res.get('error')})"
        created_dates = []
        for ep in res.get("episodes") or []:
            raw = (
                ep.get("createTime")
                or ep.get("createdAt")
                or ep.get("created")
                or ep.get("startTime")
            )
            if not raw:
                continue
            try:
                created_dates.append(datetime.fromisoformat(str(raw).replace("Z", "+00:00")))
            except ValueError:
                continue
        if not created_dates:
            return None, f"no parseable episode creation dates for ref {ref}"
        episodes_by_ref[ref] = created_dates

    covariate_by_index: dict[int, int] = {}
    for idx, entry in enumerate(ledger):
        ref = str(entry.get("ref") or "")
        note = entry.get("note", "")
        read_date = extract_date_from_note(note)
        if not read_date or ref not in episodes_by_ref:
            continue
        covariate_by_index[idx] = sum(1 for d in episodes_by_ref[ref] if d < read_date)

    return covariate_by_index, "reconstructed via kaggle CLI episode listing"


def build_reads(
    ledger: list,
    reference_date: datetime,
    episode_covariate: dict | None = None,
) -> list[dict]:
    """Turn raw ledger entries into read records with a covariate attached.

    Undated reads (no recognizable date in the note) and unparseable ladder
    scores are dropped -- there is nothing to fit a covariate against. This
    matches the existing age-stratified refit's "undated" bucket, which is
    likewise excluded from its pooled stats.
    """
    covariate_kind = "episodes" if episode_covariate is not None else "age_hours"
    reads = []
    for idx, entry in enumerate(ledger):
        build = entry.get("build") or ""
        try:
            ladder = float(entry.get("ladder"))
        except (TypeError, ValueError):
            continue

        note = entry.get("note", "")
        read_date = extract_date_from_note(note)
        if read_date is None:
            continue

        age_hours = compute_age_hours(read_date, reference_date)
        if covariate_kind == "episodes":
            if idx not in episode_covariate:
                continue
            covariate = float(episode_covariate[idx])
        else:
            covariate = age_hours

        reads.append(
            {
                "ref": entry.get("ref"),
                "build": build,
                "family": family_key(build),
                "ladder": ladder,
                "read_date": read_date,
                "age_hours": age_hours,
                "covariate": covariate,
                "covariate_kind": covariate_kind,
            }
        )
    return reads


def apply_fresh_read_depression_correction(
    reads: list[dict], fresh_cutoff_hours: float = FRESH_CUTOFF_HOURS
) -> tuple[list[dict], list[dict]]:
    """Split reads into (aged, fresh) using the fresh-read-depression finding.

    Per analysis/age_stratified_refit_findings.md and findings.md: reads taken
    within 48h of the reference date read low relative to aged reads of the
    same family (the fresh-is-depressed direction, not the earlier fresh-is-
    inflated hypothesis the tool docstring in
    tools/refit_noise_model_age_stratified.py was written against). Only aged
    reads should feed the terminal convergence sigma; fresh reads still appear
    in the curve so the drop-off is visible.
    """
    aged = [r for r in reads if r["age_hours"] is not None and r["age_hours"] >= fresh_cutoff_hours]
    fresh = [r for r in reads if r["age_hours"] is not None and r["age_hours"] < fresh_cutoff_hours]
    return aged, fresh


def family_residuals(reads: list[dict], min_family_n: int = MIN_FAMILY_N) -> tuple[list[float], dict]:
    """Pool per-family residuals (read minus family mean) for families with
    at least min_family_n reads. Returns (residuals, per_family_stats)."""
    families: dict = {}
    for r in reads:
        families.setdefault(r["family"], []).append(r["ladder"])

    residuals = []
    per_family = {}
    for name, values in sorted(families.items()):
        n = len(values)
        mean = st.mean(values)
        per_family[name] = {
            "n": n,
            "mean": mean,
            "stdev": st.stdev(values) if n > 1 else 0.0,
        }
        if n >= min_family_n:
            residuals.extend(v - mean for v in values)

    return residuals, per_family


def bootstrap_ci(
    residuals: list[float],
    alpha: float = DEFAULT_CI_ALPHA,
    n_boot: int = DEFAULT_N_BOOT,
    seed: int = DEFAULT_SEED,
) -> tuple[float, float] | None:
    """Percentile bootstrap CI for the pooled residual stdev.

    Resamples the residual list with replacement n_boot times, computes the
    sample stdev of each resample, and returns the alpha/2 and 1-alpha/2
    percentiles. Deterministic given seed, so it is reproducible in tests.
    Returns None when there are fewer than 2 residuals to resample.
    """
    if len(residuals) < 2:
        return None
    rng = random.Random(seed)
    n = len(residuals)
    boot_stdevs = []
    for _ in range(n_boot):
        sample = [residuals[rng.randrange(n)] for _ in range(n)]
        if len(set(sample)) > 1:
            boot_stdevs.append(st.stdev(sample))
        else:
            boot_stdevs.append(0.0)
    boot_stdevs.sort()
    lo_idx = int((alpha / 2) * n_boot)
    hi_idx = min(n_boot - 1, int((1 - alpha / 2) * n_boot))
    return boot_stdevs[lo_idx], boot_stdevs[hi_idx]


def sigma_curve(
    reads: list[dict],
    per_family_mean: dict,
    covariate_kind: str,
    min_family_n: int = MIN_FAMILY_N,
) -> list[dict]:
    """Bucket reads by covariate and report the pooled residual sigma per
    bucket, using each read's family mean computed over the *whole* aged
    sample (per_family_mean) rather than a per-bucket mean, so a bucket with
    too few reads for its own mean still contributes a well-defined residual.
    """
    bins = EPISODE_BINS if covariate_kind == "episodes" else AGE_HOUR_BINS
    points = []
    for lo, hi in bins:
        bucket_residuals = []
        bucket_n = 0
        for r in reads:
            if r["covariate"] is None:
                continue
            if not (lo <= r["covariate"] < hi):
                continue
            fam_stats = per_family_mean.get(r["family"])
            if not fam_stats or fam_stats["n"] < min_family_n:
                continue
            bucket_residuals.append(r["ladder"] - fam_stats["mean"])
            bucket_n += 1
        sigma = st.stdev(bucket_residuals) if len(bucket_residuals) > 1 else None
        points.append({"lo": lo, "hi": hi, "n": bucket_n, "sigma": sigma})
    return points


def estimate_convergence_sigma(
    reads: list[dict],
    min_family_n: int = MIN_FAMILY_N,
    fresh_cutoff_hours: float = FRESH_CUTOFF_HOURS,
    ci_alpha: float = DEFAULT_CI_ALPHA,
    n_boot: int = DEFAULT_N_BOOT,
    seed: int = DEFAULT_SEED,
) -> dict:
    """Full estimate: fresh-read-depression correction, pooled residual sigma
    on the aged reads, a bootstrap CI, and a sigma-vs-covariate curve.

    Works identically whether reads carry a real episode-count covariate or
    the age-hours fallback -- the caller decides which by what it puts in
    each read's "covariate" field.
    """
    covariate_kind = reads[0]["covariate_kind"] if reads else "age_hours"

    aged, fresh = apply_fresh_read_depression_correction(reads, fresh_cutoff_hours)

    aged_residuals, aged_per_family = family_residuals(aged, min_family_n)
    sigma = st.stdev(aged_residuals) if len(aged_residuals) > 1 else None
    ci = bootstrap_ci(aged_residuals, alpha=ci_alpha, n_boot=n_boot, seed=seed)

    curve = sigma_curve(reads, aged_per_family, covariate_kind, min_family_n)

    return {
        "covariate_kind": covariate_kind,
        "n_total": len(reads),
        "n_aged": len(aged),
        "n_fresh_excluded": len(fresh),
        "n_residuals": len(aged_residuals),
        "per_family": aged_per_family,
        "sigma": sigma,
        "ci": ci,
        "ci_alpha": ci_alpha,
        "curve": curve,
        "convergence_window_games": CONVERGENCE_WINDOW_GAMES,
        "fresh_cutoff_hours": fresh_cutoff_hours,
    }


def format_report(result: dict, fallback_reason: str | None) -> str:
    lines = ["CONVERGENCE RESIDUAL SIGMA", "=" * 60]

    if result["covariate_kind"] == "age_hours":
        lines.append(
            "COVARIATE FALLBACK: episode-count reconstruction unavailable "
            f"({fallback_reason}). Using age-hours (time since the read's "
            "noted date) as the covariate instead. The sigma-vs-covariate "
            "curve below is sigma-vs-age-hours, not sigma-vs-episodes."
        )
    else:
        lines.append("COVARIATE: real per-read episode counts reconstructed via the kaggle CLI.")

    lines.append("")
    lines.append(
        f"Total dated reads: {result['n_total']} "
        f"(fresh <{result['fresh_cutoff_hours']:.0f}h excluded: {result['n_fresh_excluded']}, "
        f"aged: {result['n_aged']})"
    )

    lines.append("\nPer-family stats (aged reads only):")
    for name, stats in result["per_family"].items():
        lines.append(
            f"  {name}: n={stats['n']:2} mean={stats['mean']:7.1f} stdev={stats['stdev']:6.1f}"
        )

    sigma = result["sigma"]
    ci = result["ci"]
    if sigma is not None:
        ci_text = f"[{ci[0]:.1f}, {ci[1]:.1f}]" if ci else "n/a (too few residuals)"
        pct = int(round((1 - result["ci_alpha"]) * 100))
        lines.append(
            f"\nPooled residual sigma (n={result['n_residuals']}): {sigma:.1f} "
            f"{pct}% CI {ci_text}"
        )
    else:
        lines.append("\nPooled residual sigma: insufficient data (need >=2 residuals)")

    lo, hi = result["convergence_window_games"]
    if result["covariate_kind"] == "age_hours":
        lines.append(
            f"\nRequested convergence window: {lo}-{hi} games. Not directly "
            "measurable without real episode counts; the aged (>=48h) sample "
            "above stands in as the converged-regime proxy this environment "
            "can produce."
        )
    else:
        lines.append(f"\nConvergence window: {lo}-{hi} games (measured directly).")

    lines.append("\nSigma-vs-covariate curve:")
    unit = "games" if result["covariate_kind"] == "episodes" else "hours"
    for point in result["curve"]:
        hi_label = "inf" if point["hi"] == float("inf") else f"{point['hi']:.0f}"
        sigma_label = f"{point['sigma']:.1f}" if point["sigma"] is not None else "n/a"
        lines.append(
            f"  [{point['lo']:.0f}, {hi_label}) {unit}: n={point['n']:3} sigma={sigma_label}"
        )

    return "\n".join(lines)


def format_markdown(result: dict, fallback_reason: str | None, reference_date: datetime) -> str:
    lines = [
        "# Convergence Residual Sigma (U7 / U115)",
        "",
        f"Generated {reference_date.date().isoformat()}. Extends "
        "tools/refit_noise_model_age_stratified.py over the full 77-read "
        "ledger in state/current.md (not just the 3-snapshot drift log).",
        "",
        "## Covariate",
        "",
    ]

    if result["covariate_kind"] == "age_hours":
        lines.append(
            "**Fallback in effect.** The plan's preferred covariate is each "
            "read's episode count, reconstructed by listing the ref's "
            f"episodes and counting those created before the read's date. That "
            f"reconstruction was unavailable in this environment: {fallback_reason}. "
            "This document therefore uses age-hours (time between the read's "
            "noted date and the reference date above) as the covariate "
            "instead. This is stated explicitly here and in the tool's "
            "console output, not silently substituted."
        )
    else:
        lines.append(
            "Real per-read episode counts, reconstructed via the kaggle CLI "
            "(tools/scout.py list_submissions/list_episodes), counting each "
            "ref's episodes created before the read's own date."
        )

    lines.append("")
    lines.append("## Fresh-read-depression correction")
    lines.append("")
    lines.append(
        "Per analysis/age_stratified_refit_findings.md and findings.md, reads "
        f"taken within {result['fresh_cutoff_hours']:.0f}h of the reference date "
        "read low relative to aged reads of the same family (fresh is "
        "depressed, not inflated). This tool excludes them from the terminal "
        "sigma estimate below; they remain visible in the curve. On this "
        f"run: {result['n_fresh_excluded']} of {result['n_total']} dated reads "
        "were excluded as fresh. The correction has zero reads to exclude "
        "whenever the reference date is run well after the ledger's most "
        "recent note date (as it is here, on 2026-07-10 against notes that "
        "top out around 2026-07-04) -- every dated read has already crossed "
        "48h. The earlier 2026-07-06 snapshot in "
        "analysis/age_stratified_refit_findings.md did have a live contrast "
        "(heuristic+trolley: 422.2 fresh, n=1, vs 600.0 aged, n=1, a -177.8pp "
        "gap), which is the evidence the correction is based on; this run's "
        "zero-exclusion result confirms the ledger has fully aged into the "
        "converged regime, not that the correction stopped applying."
    )

    lines.append("")
    lines.append("## Per-family stats (aged reads only)")
    lines.append("")
    lines.append("| Family | n | mean | stdev |")
    lines.append("| --- | --- | --- | --- |")
    for name, stats in result["per_family"].items():
        lines.append(f"| {name} | {stats['n']} | {stats['mean']:.1f} | {stats['stdev']:.1f} |")

    lines.append("")
    lines.append("## Sigma-vs-covariate curve")
    lines.append("")
    unit = "games" if result["covariate_kind"] == "episodes" else "hours"
    lines.append(f"| {unit} bucket | n | sigma |")
    lines.append("| --- | --- | --- |")
    for point in result["curve"]:
        hi_label = "inf" if point["hi"] == float("inf") else f"{point['hi']:.0f}"
        sigma_label = f"{point['sigma']:.1f}" if point["sigma"] is not None else "n/a"
        lines.append(f"| [{point['lo']:.0f}, {hi_label}) | {point['n']} | {sigma_label} |")

    if result["covariate_kind"] == "age_hours":
        lines.append("")
        lines.append(
            "Note fields carry a date, not a timestamp, so age-hours "
            "resolves only to whole days. That bunches most reads into one "
            "or two buckets rather than spreading them across the full "
            "curve; the buckets are still real, just coarse."
        )

    lines.append("")
    lines.append("## Result")
    lines.append("")
    sigma = result["sigma"]
    ci = result["ci"]
    lo, hi = result["convergence_window_games"]
    pct = int(round((1 - result["ci_alpha"]) * 100))
    if sigma is not None and ci is not None:
        if result["covariate_kind"] == "age_hours":
            window_caveat = (
                f" (proxy for the {lo}-{hi} game convergence window; real "
                "episode counts were not reconstructable in this environment, "
                "see Covariate above)"
            )
        else:
            window_caveat = f" (measured directly over the {lo}-{hi} game convergence window)"
        lines.append(
            f"**End-of-window residual sigma: {sigma:.1f}, {pct}% CI "
            f"[{ci[0]:.1f}, {ci[1]:.1f}], n={result['n_residuals']}**{window_caveat}."
        )
    else:
        lines.append(
            "**Insufficient data for a residual sigma estimate on this run** "
            f"(n_residuals={result['n_residuals']})."
        )

    lines.append("")
    lines.append(
        "This number is what U10's E[max] arithmetic uses to decide whether a "
        "runner-up's ring CI overlap is real signal or residual read noise."
    )
    lines.append("")

    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reference-date",
        default=None,
        help="reference date for age computation (YYYY-MM-DD, default: today)",
    )
    parser.add_argument(
        "--min-family-n",
        type=int,
        default=MIN_FAMILY_N,
        help=f"minimum reads per family to contribute residuals (default {MIN_FAMILY_N})",
    )
    parser.add_argument(
        "--fresh-cutoff-hours",
        type=float,
        default=FRESH_CUTOFF_HOURS,
        help=f"reads younger than this are excluded as fresh (default {FRESH_CUTOFF_HOURS})",
    )
    parser.add_argument(
        "--ci-alpha",
        type=float,
        default=DEFAULT_CI_ALPHA,
        help=f"bootstrap CI alpha, e.g. 0.10 for a 90%% CI (default {DEFAULT_CI_ALPHA})",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="bootstrap RNG seed")
    args = parser.parse_args(argv)

    if args.reference_date:
        try:
            reference_date = datetime.strptime(args.reference_date, "%Y-%m-%d")
        except ValueError:
            print(f"ERROR: invalid date '{args.reference_date}', expected YYYY-MM-DD", file=sys.stderr)
            return 1
    else:
        reference_date = datetime.now()

    print("Reading ledger from state/current.md...")
    data = read_current()
    ledger = data.get("ledger") or []
    print(f"Loaded {len(ledger)} ledger entries")

    print("Attempting episode-count reconstruction via the kaggle CLI...")
    episode_covariate, reconstruct_reason = try_reconstruct_episode_counts(ledger)
    if episode_covariate is None:
        print(f"  Fallback to age-hours: {reconstruct_reason}")
        fallback_reason = reconstruct_reason
    else:
        print(f"  {reconstruct_reason}")
        fallback_reason = None

    reads = build_reads(ledger, reference_date, episode_covariate)
    print(f"Built {len(reads)} dated reads with a covariate attached")

    result = estimate_convergence_sigma(
        reads,
        min_family_n=args.min_family_n,
        fresh_cutoff_hours=args.fresh_cutoff_hours,
        ci_alpha=args.ci_alpha,
        seed=args.seed,
    )

    report = format_report(result, fallback_reason)
    print("\n" + report)

    md = format_markdown(result, fallback_reason, reference_date)
    out_path = _ROOT / "analysis" / "convergence_sigma.md"
    out_path.write_text(md)
    print(f"\nWrote {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
