# Convergence Residual Sigma (U7 / U115)

Generated 2026-07-10. Extends tools/refit_noise_model_age_stratified.py over the full 77-read ledger in state/current.md (not just the 3-snapshot drift log).

## Covariate

**Fallback in effect.** The plan's preferred covariate is each read's episode count, reconstructed by listing the ref's episodes and counting those created before the read's date. That reconstruction was unavailable in this environment: kaggle CLI unavailable (C:\Users\danom\AppData\Local\Programs\Python\Python311\python.exe: No module named kaggle). This document therefore uses age-hours (time between the read's noted date and the reference date above) as the covariate instead. This is stated explicitly here and in the tool's console output, not silently substituted.

## Fresh-read-depression correction

Per analysis/age_stratified_refit_findings.md and findings.md, reads taken within 48h of the reference date read low relative to aged reads of the same family (fresh is depressed, not inflated). This tool excludes them from the terminal sigma estimate below; they remain visible in the curve. On this run: 0 of 61 dated reads were excluded as fresh. The correction has zero reads to exclude whenever the reference date is run well after the ledger's most recent note date (as it is here, on 2026-07-10 against notes that top out around 2026-07-04) -- every dated read has already crossed 48h. The earlier 2026-07-06 snapshot in analysis/age_stratified_refit_findings.md did have a live contrast (heuristic+trolley: 422.2 fresh, n=1, vs 600.0 aged, n=1, a -177.8pp gap), which is the evidence the correction is based on; this run's zero-exclusion result confirms the ledger has fully aged into the converged regime, not that the correction stopped applying.

## Per-family stats (aged reads only)

| Family | n | mean | stdev |
| --- | --- | --- | --- |
| heuristic+trolley | 30 | 442.7 | 31.2 |
| heuristic+trolley-ability | 30 | 570.7 | 42.5 |
| heuristic+trolley_thick | 1 | 446.2 | 0.0 |

## Sigma-vs-covariate curve

| hours bucket | n | sigma |
| --- | --- | --- |
| [0, 24) | 0 | n/a |
| [24, 48) | 0 | n/a |
| [48, 72) | 0 | n/a |
| [72, 96) | 0 | n/a |
| [96, 120) | 0 | n/a |
| [120, 144) | 2 | 9.6 |
| [144, 168) | 57 | 31.4 |
| [168, 192) | 0 | n/a |
| [192, inf) | 1 | n/a |

Note fields carry a date, not a timestamp, so age-hours resolves only to whole days. That bunches most reads into one or two buckets rather than spreading them across the full curve; the buckets are still real, just coarse.

## Result

**End-of-window residual sigma: 37.0, 90% CI [26.0, 46.9], n=60** (proxy for the 200-350 game convergence window; real episode counts were not reconstructable in this environment, see Covariate above).

This number is what U10's E[max] arithmetic uses to decide whether a runner-up's ring CI overlap is real signal or residual read noise.
