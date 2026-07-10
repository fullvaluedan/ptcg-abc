"""Tests for tools/convergence_sigma.py (plan U7 / U115).

Fully offline: all fixtures are synthetic ledger entries built in-memory, never
real state/current.md data (real-data behavior is covered by running the tool
directly and inspecting analysis/convergence_sigma.md, not by this suite).

Ledger note dates must match the extract_date_from_note regex inherited from
tools/refit_noise_model_age_stratified.py, which only recognizes
"2026-07-DD" -- so every synthetic date below lives in that window.
"""
import random
import statistics as st
from datetime import datetime

from tools.convergence_sigma import (
    AGE_HOUR_BINS,
    EPISODE_BINS,
    FRESH_CUTOFF_HOURS,
    apply_fresh_read_depression_correction,
    build_reads,
    estimate_convergence_sigma,
)


def _entry(build: str, ladder: float, date: str, ref: str = "ref1") -> dict:
    return {
        "build": build,
        "ladder": ladder,
        "note": f"Board check {date}: {ladder:.1f}",
        "ref": ref,
    }


# --------------------------------------------------------------------------- #
# 1. the estimator reproduces a known sigma on synthetic reads with injected
#    noise
# --------------------------------------------------------------------------- #
def test_estimator_recovers_known_sigma_on_synthetic_reads():
    rng = random.Random(12345)
    sigma_true = 25.0
    family_mean = 500.0
    n = 150

    # All dates well before the reference date -> every read is "aged" (>=48h),
    # so nothing gets excluded and the whole sample feeds the residual sigma.
    dates = [f"2026-07-{(i % 10) + 1:02d}" for i in range(n)]
    ledger = [
        _entry("synthfam", family_mean + rng.gauss(0.0, sigma_true), d)
        for d in dates
    ]
    reference_date = datetime(2026, 7, 20)

    reads = build_reads(ledger, reference_date)
    assert len(reads) == n  # every synthetic read is dated and parses

    result = estimate_convergence_sigma(reads)

    assert result["n_fresh_excluded"] == 0
    assert result["sigma"] is not None
    # With n=150 the sample stdev should land close to the injected sigma.
    assert abs(result["sigma"] - sigma_true) < 0.25 * sigma_true
    assert result["ci"] is not None
    lo, hi = result["ci"]
    assert lo <= result["sigma"] <= hi


def test_estimator_recovers_known_sigma_across_seeds():
    # Same construction, different seed/sigma, to make sure the first test
    # isn't a lucky seed pick.
    rng = random.Random(999)
    sigma_true = 12.0
    family_mean = 300.0
    n = 120
    dates = [f"2026-07-{(i % 15) + 1:02d}" for i in range(n)]
    ledger = [_entry("synthfam2", family_mean + rng.gauss(0.0, sigma_true), d) for d in dates]
    reference_date = datetime(2026, 7, 25)

    reads = build_reads(ledger, reference_date)
    result = estimate_convergence_sigma(reads)

    assert result["sigma"] is not None
    assert abs(result["sigma"] - sigma_true) < 0.35 * sigma_true


# --------------------------------------------------------------------------- #
# 2. age-stratification excludes sub-48h reads from the terminal estimate
# --------------------------------------------------------------------------- #
def test_fresh_reads_are_split_out_by_apply_fresh_read_depression_correction():
    reference_date = datetime(2026, 7, 15)
    # Aged: 2026-07-01 is 14 days (336h) before reference -> aged.
    aged_ledger = [_entry("fam", 500.0 + i, "2026-07-01") for i in range(5)]
    # Fresh: 2026-07-15 is 0h before reference -> fresh.
    fresh_ledger = [_entry("fam", 500.0 + i, "2026-07-15") for i in range(5)]

    reads = build_reads(aged_ledger + fresh_ledger, reference_date)
    aged, fresh = apply_fresh_read_depression_correction(reads, FRESH_CUTOFF_HOURS)

    assert len(aged) == 5
    assert len(fresh) == 5
    assert all(r["age_hours"] >= FRESH_CUTOFF_HOURS for r in aged)
    assert all(r["age_hours"] < FRESH_CUTOFF_HOURS for r in fresh)


def test_fresh_reads_do_not_leak_into_terminal_sigma_estimate():
    rng = random.Random(42)
    reference_date = datetime(2026, 7, 20)
    sigma_true = 10.0
    aged_mean = 500.0
    n_aged = 60
    n_fresh = 20

    # Aged reads: tight noise around 500, dated well past 48h.
    aged_dates = [f"2026-07-{(i % 10) + 1:02d}" for i in range(n_aged)]
    aged_ledger = [
        _entry("depressfam", aged_mean + rng.gauss(0.0, sigma_true), d)
        for d in aged_dates
    ]

    # Fresh reads: dated within 48h of reference (2026-07-19/20), badly
    # depressed (offset -300) relative to the aged mean. If these leaked into
    # the terminal sigma they would blow up both the per-family mean and the
    # residual spread.
    fresh_dates = ["2026-07-19"] * (n_fresh // 2) + ["2026-07-20"] * (n_fresh - n_fresh // 2)
    fresh_ledger = [_entry("depressfam", aged_mean - 300.0, d) for d in fresh_dates]

    reads = build_reads(aged_ledger + fresh_ledger, reference_date)
    result = estimate_convergence_sigma(reads)

    assert result["n_total"] == n_aged + n_fresh
    assert result["n_fresh_excluded"] == n_fresh
    assert result["n_aged"] == n_aged

    # Family mean used for residuals must reflect only the aged reads.
    fam_stats = result["per_family"]["depressfam"]
    assert fam_stats["n"] == n_aged
    assert abs(fam_stats["mean"] - aged_mean) < 10.0  # not pulled toward the fresh -300 offset

    # Sigma should track the aged-only noise, not be inflated by the fresh gap.
    assert result["sigma"] is not None
    assert abs(result["sigma"] - sigma_true) < 0.5 * sigma_true
    assert result["sigma"] < 50.0  # sanity ceiling: a leaked fresh cohort would push this into the hundreds

    # The fresh reads still appear in the raw `reads` list (visible in the
    # curve) even though they are excluded from the residual/sigma pipeline.
    fresh_covariates = [r for r in reads if r["age_hours"] < FRESH_CUTOFF_HOURS]
    assert len(fresh_covariates) == n_fresh


def test_exactly_48h_boundary_counts_as_aged_not_fresh():
    # apply_fresh_read_depression_correction uses >= fresh_cutoff_hours for aged,
    # so a read at exactly the cutoff must land in "aged", matching the
    # tool's own boundary convention (age_hours >= fresh_cutoff_hours -> aged).
    reference_date = datetime(2026, 7, 3)
    ledger = [_entry("boundaryfam", 500.0, "2026-07-01")]  # exactly 48h before reference
    reads = build_reads(ledger, reference_date)
    assert reads[0]["age_hours"] == 48.0

    aged, fresh = apply_fresh_read_depression_correction(reads, FRESH_CUTOFF_HOURS)
    assert len(aged) == 1
    assert len(fresh) == 0


# --------------------------------------------------------------------------- #
# 3. output includes n, sigma, CI, and the episode-count curve points
# --------------------------------------------------------------------------- #
def test_result_schema_has_n_sigma_ci_and_curve():
    rng = random.Random(7)
    reference_date = datetime(2026, 7, 20)
    n = 40
    dates = [f"2026-07-{(i % 10) + 1:02d}" for i in range(n)]
    ledger = [_entry("schemafam", 500.0 + rng.gauss(0.0, 20.0), d) for d in dates]

    reads = build_reads(ledger, reference_date)
    result = estimate_convergence_sigma(reads)

    for key in (
        "covariate_kind",
        "n_total",
        "n_aged",
        "n_fresh_excluded",
        "n_residuals",
        "per_family",
        "sigma",
        "ci",
        "ci_alpha",
        "curve",
        "convergence_window_games",
        "fresh_cutoff_hours",
    ):
        assert key in result

    assert isinstance(result["n_total"], int)
    assert isinstance(result["sigma"], float)
    assert isinstance(result["ci"], tuple)
    assert len(result["ci"]) == 2
    assert result["ci"][0] <= result["ci"][1]
    assert result["convergence_window_games"] == (200, 350)

    # age-hours fallback curve: one point per AGE_HOUR_BINS bucket, each with
    # lo/hi/n/sigma.
    assert result["covariate_kind"] == "age_hours"
    assert len(result["curve"]) == len(AGE_HOUR_BINS)
    for point in result["curve"]:
        assert set(point.keys()) == {"lo", "hi", "n", "sigma"}
        assert isinstance(point["n"], int)
        assert point["sigma"] is None or isinstance(point["sigma"], float)


def test_result_schema_with_episode_covariate_uses_episode_bins():
    reference_date = datetime(2026, 7, 20)
    n = 20
    dates = [f"2026-07-{(i % 10) + 1:02d}" for i in range(n)]
    ledger = [_entry("epfam", 500.0 + i, d) for i in range(n) for d in [dates[i]]]
    # Fabricate a real-looking episode covariate: index -> episode count.
    episode_covariate = {i: 50 + i * 10 for i in range(n)}

    reads = build_reads(ledger, reference_date, episode_covariate=episode_covariate)
    assert reads  # every entry has a covariate, none dropped
    assert all(r["covariate_kind"] == "episodes" for r in reads)

    result = estimate_convergence_sigma(reads)
    assert result["covariate_kind"] == "episodes"
    assert len(result["curve"]) == len(EPISODE_BINS)
    for point in result["curve"]:
        assert set(point.keys()) == {"lo", "hi", "n", "sigma"}


def test_curve_sigma_matches_manual_bucket_computation():
    # Cross-check one bucket of the curve against a hand-rolled stdev to make
    # sure sigma_curve's bucketing/residual logic isn't silently off.
    reference_date = datetime(2026, 7, 20)
    # All seven reads land in the [144, 168) hours bucket (exactly 6 days old).
    values = [480.0, 510.0, 495.0, 505.0, 500.0, 490.0, 515.0]
    ledger = [_entry("curvefam", v, "2026-07-14") for v in values]  # 144h before reference
    reads = build_reads(ledger, reference_date)
    result = estimate_convergence_sigma(reads, min_family_n=3)

    bucket = next(p for p in result["curve"] if p["lo"] == 144.0)
    assert bucket["n"] == len(values)
    expected_mean = st.mean(values)
    expected_sigma = st.stdev([v - expected_mean for v in values])
    assert bucket["sigma"] == expected_sigma
