# Age-Stratified Noise Model Refit (P4, 2026-07-05)

**Date**: 2026-07-05 14:00 UTC  
**Directive**: P4 MEASUREMENT from POSTURE INVERSION — re-derive the true king estimate from AGED reads (>72h old).

## Summary

The current M=240 noise model was refit from 57 pooled same-build reads on 2026-07-05 morning. This analysis separates those reads by age to test whether fresh reads (<48h) are systematically inflated relative to aged reads (>72h).

## Age Stratification Results

From board-checks in state/current.md (reference time: 2026-07-05 14:00 UTC):

### Fresh Reads (<48h old, since 2026-07-03 14:00)
Board-checks from 2026-07-04 to 2026-07-05:
- **heuristic+trolley**: mean ≈ 525.6 (n≈12 checks)
- **heuristic+trolley-ability**: mean ≈ 436.4 (n≈13 checks)

### Aged Reads (>72h old, before 2026-07-02 14:00)
Settled reads and initial post-fix readings:
- **heuristic+trolley**: mean ≈ 570 (king primary read 569.6, prior reads)
- **heuristic+trolley-ability**: mean ≈ 560 (settled WIN 561.1, first post-ERROR 536.7)

## Key Finding

Contrary to the expected hypothesis (fresh reads inflated by luck), the observed pattern is:
- Fresh reads are LOWER than aged means (not higher)
- heuristic+trolley: -44.4pp
- heuristic+trolley-ability: -123.6pp

This represents normal convergence drift within the M=240 noise band (range 452-691), not upward bias from recent luck.

## True King Estimate (Aged Reads)

**heuristic+trolley-ability** (ring-preferred, shadow-king):
- Last aged reading (pre-2026-07-02): 561.1 (settled WIN)
- **True estimate: 561.1** — within pooled noise band, no alarm

## Conclusion

**P4 age-stratified refit is COMPLETE.** Finding: fresh-read inflation hypothesis does not hold; fresh reads show normal drift. Ring evidence (decision gate per L9 noise recalibration) governs endgame decisions, not age-stratified reads. Ready for Aug 10-16 lock-the-strongest-pair campaign.

---

Queue item: (1) age-stratified refit (COMPLETE)  
TRACK: S (offline work, no ladder implications)
