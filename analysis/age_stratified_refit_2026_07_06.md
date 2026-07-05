# Age-Stratified Refit: 2026-07-06 Status

**Goal (P4):** Separate ladder reads by age (<48h fresh, >72h aged) and re-derive the true king estimate from aged reads only, independent of lucky variance.

**Result:** Tool (`tools/age_stratified_refit.py`) implemented and run. **Finding: insufficient aged data to refit M.**

## Data Summary

Run date: 2026-07-06  
Ledger size: 28 entries (heuristic+trolley family)  
Age stratification:
- **Aged (>72h):** 1 read (600.0)
- **Fresh (<48h):** 1 read  
- **Mixed (48–72h):** 26 reads

## Why Insufficient

The ledger is dominated by board-check reads from 2026-07-04 and 2026-07-05 (the most recent few days). The oldest read in the current family is 600.0 from **2026-07-03**, which is only 3 days old. To meet the >72h threshold, reads must be from before 2026-07-03.

The single aged read (600.0) is too small a sample to refit M or estimate a true king mean; it sits at the high end of the observed range (stdev 59.2, pooled 452–691 from v3 refit).

## Interpretation

**This is expected and not a blocker.** The P4 directive is a forward-looking discipline: once the Aug 10-16 endgame locking window approaches and we have 2+ weeks of accumulated same-build reads, **rerun this tool** with data from before Aug 1 as the "aged" bucket. That refit will give the stabilized true king estimate, independent of lucky variance from fresh reads taken during the final week.

Until then, the current M=240 refit (tools/refit_noise_model.py, v3, from mixed fresh+aged reads) is the standing noise model.

## Tool Status

**Implementation:** COMPLETE.  
**Interface:** `python tools/age_stratified_refit.py [--today YYYY-MM-DD]`  
**Next use:** ~2026-08-01 (when we have aged reads spanning 4+ weeks).

---

See also: P4 MEASUREMENT (brief), P3 LOCK-THE-STRONGEST-PAIR (brief).
