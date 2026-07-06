# Age-stratified Refit: Findings (2026-07-06)

## Status: INSUFFICIENT DATA FOR AGED READS

Ran tools/age_stratified_refit.py on the full ledger in state/current.md, stratifying all same-build reads by age relative to 2026-07-06:
- **fresh** (<48h old): reads submitted 2026-07-04 or later
- **mixed** (48h-72h old): reads submitted 2026-07-03
- **aged** (>72h old): reads submitted 2026-07-02 or earlier

**Results:**

| Family | n_aged | n_fresh | n_mixed | n_total | mean_aged | stdev_aged |
| --- | --- | --- | --- | --- | --- | --- |
| heuristic+trolley | 1 | 1 | 28 | 30 | 600.0 | 0.0 |
| (all others) | 0 | * | * | * | n/a | n/a |

**Pooled statistics:** 0 families with n_aged >= 3. Cannot compute pooled residual stdev or recommended M (aged).

## Interpretation

The current M=240 noise model (v3, refit 2026-07-04 via tools/refit_noise_model.py) was calibrated on 57 pooled same-build reads mixing age cohorts. Only 1 read is old enough (>72h) to be considered "stabilized" by the P4 criterion, and it carries a single family (heuristic+trolley, one read at 600.0), so no family-specific aged mean is meaningful yet.

**Key insight:** All live builds (54315802, 54315565) were submitted recently and are accumulating fresh reads. As of 2026-07-06, none have decayed into the "aged" category to enable a robust re-fit.

## Timeline to re-test

- **Aged reads begin:** 2026-07-05 23:59 UTC + 72h = 2026-07-08 23:59 UTC (3 days from today)
- **Recommended re-test window:** 2026-07-10 or later, when heuristic+trolley and heuristic+trolley-ability will each have multiple aged reads available

The re-test will compare:
1. Aged reads only (stabilized, less luck variance)
2. Fresh reads only (inflated by luck)
3. Per-family aged mean vs per-family pooled residual stdev

This refitted M will inform the P3 LOCK-THE-STRONGEST-PAIR decision (Aug 10-16 endgame).

## Methodology note

The tool correctly extracts dates from ledger "note" fields via regex patterns (Board check YYYY-MM-DD, settled YYYY-MM-DD, bare YYYY-MM-DD). The extract is deterministic and reconciled against tools/loop_state.py's list of all ledger entries to ensure no double-count or missing reads.

## Next steps

1. Continue daily board checks to accumulate aged reads.
2. Re-run tools/age_stratified_refit.py on 2026-07-08 (first day aged reads exist) and 2026-07-10 (first day with 3+ aged reads likely available per family).
3. If the aged-only M differs materially from the current M=240 (by >10pp), document the delta and rationale for any update to state/current.md noise_model block.
4. Use the aged-only estimate to inform the pre-August-13 lock decision per P3.

## Data completeness

Ledger: 77 entries
- King refs with multiple reads: 54315802 (heuristic+trolley-ability), 54315565 (heuristic+trolley)
- All entries since 2026-07-03 have dates in notes fields (100% extractable)
- Earliest aged read: 2026-07-02 (heuristic+trolley, 600.0)
