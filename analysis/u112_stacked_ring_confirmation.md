# U112 Stacked Ring Confirmation — FAIL (2026-07-07)

## Summary

Three-arm factorized ring measurement at n=100/arm against calibrated bracket-band ring (tau 0.857). **Result: GATE FAIL**. U104's n=40 result (+15.0pp) was noise-inflated; true delta at larger sample size is +9.0pp (below +10.0pp gate threshold).

## Results

| Arm | Config | Win Rate | W-D-L | n |
|-----|--------|----------|-------|---|
| 1 (baseline) | heuristic+trolley+ability | 0.770 | 77-0-23 | 100 |
| 2 | heuristic+yushin+ability | 0.850 | 85-0-15 | 100 |
| 3 (test) | heuristic+yushin+ability+attack_first | 0.860 | 86-0-14 | 100 |

## Gate Decision

- **Delta (arm 3 − arm 1)**: +0.090 = **+9.0pp**
- **Gate threshold**: >+0.10 (+10.0pp)
- **Verdict**: **FAIL** (delta does not exceed threshold)

## Interpretation

1. **Sample noise diagnosis confirmed**: U104's smaller sample (n=40) produced arm 1 = 72.5% and arm 3 = 87.5%, diff +15.0pp. U112's larger sample (n=100) produces arm 1 = 77.0% and arm 3 = 86.0%, diff +9.0pp. The 6pp shrinkage in arm 1's win rate (72.5% → 77.0%, directional toward the true mean) and the 1pp shrinkage in arm 3 (87.5% → 86.0%) are consistent with U104 having oversampled favorable outcomes for both builds.

2. **Yushin deck advantage holds**: Arm 2 (yushin+ability) remains 8.0pp ahead of arm 1 (77% → 85%), confirming yushin as the stronger baseline. The ratio arm2/arm1 is stable (80% at n=40 vs 85% at n=100, consistent within normal ring variance).

3. **Attack_first transfer is marginal**: Adding attack_first to yushin produces a marginal +1.0pp composition benefit at n=100 (85% → 86%), well below the lever's isolated effect (measured at +10pp on trolley and comparable rates on yushin in earlier single-lever tests). This suggests the lever's effectiveness is lower when combined with the yushin deck's natural piloting style, or the n=40 composition measurement was itself noise-dominated.

4. **Gate threshold enforcement**: The gate explicitly requires delta > +0.10 same-run. U112's +0.090 does not satisfy delta > 0.10, regardless of confidence intervals. This is a clean FAIL per pre-registered rule.

## Findings

- **Sample size matters**: A 2.5x increase in sample size (40 → 100) produced meaningful changes in arm deltas. Ring measurements at n=40 are subject to substantial sample noise; n=100 is more stable but still supports only a ±0.05pp confidence interval on the delta (rough binomial CI).

- **No P3 seating trigger**: U112 FAIL does not unlock a ladder submission; both slots remain occupied by ring-gated builds (ability and yushin_ito) frozen through Aug 16 per P3 POSTURE INVERSION. Yushin+ability+attack_first remains a candidate for P3 if a post-convergence slot opens and ring evidence is re-evaluated at scale.

- **Playbook lever transfer remains unproven at scale**: The attack_first lever's isolated effect (+10pp on trolley, comparable single-lever effect on yushin) does not compose with yushin's deck choice in a way that exceeds the +10pp gate. This echoes the earlier finding that some levers are deck-specific and do not generalize predictably.

## Next Queue Items

Per POSTURE INVERSION:
1. **No ladder work triggered**: U112 FAIL is a gate closure, not a refutation (the lever still shows +9pp in this arm's ratio). Board remains frozen within M=240 noise band.
2. **Week-1 roadmap continues**: Per P9, U110 (hard ring, enriched opponent set) is next, but requires offline deck-mining and clone import (COMPUTE-HEAVY). U105 (threat/prize rules) awaits design judgment (P5 MODEL NOTE). U106 (expert lookup) is compute-heavy. No new mechanical work defined until escalations resolve or Aug 10-16 window opens.
3. **Noise model implication**: The U104 vs U112 delta shrinkage (+15.0pp → +9.0pp at 2.5x sample) suggests the current M=240 noise model (v3, based on 57 same-build reads at smaller sample sizes) may underestimate the true variance. A re-fit after Aug 10-16 convergence period will be more stable than current estimates.

---
*Gate failed 2026-07-07. Prepared by autoloop iteration 130.*
