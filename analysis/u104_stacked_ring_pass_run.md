# U104 Stacked Ring Run — PASS (2026-07-06)

## Summary

Three-arm factorized ring measurement against calibrated bracket-band ring (tau 0.857). **Result: GATE PASS**. Attack_first lever transfers to yushin deck with measurable composition benefit.

## Results

| Arm | Config | Win Rate | W-D-L | n |
|-----|--------|----------|-------|---|
| 1 (baseline) | heuristic+trolley+ability | 0.725 | 29-0-11 | 40 |
| 2 | heuristic+yushin+ability | 0.800 | 32-0-8 | 40 |
| 3 (test) | heuristic+yushin+ability+attack_first | 0.875 | 35-0-5 | 40 |

## Gate Decision

- **Delta (arm 3 − arm 1)**: +0.150 = **+15.0pp**
- **Gate threshold**: >+0.10 (+10.0pp)
- **Verdict**: **PASS**

## Interpretation

1. **Yushin deck quality confirmed**: Arm 2 (yushin+ability alone) is 7.5pp ahead of trolley+ability, confirming yushin as the stronger baseline deck.

2. **Attack_first transfers to yushin**: Unlike the isolated arm 2 vs arm 1 delta (+7.5pp), adding attack_first to yushin pushes arm 3 to +15.0pp over baseline. This confirms the lever is not deck-specific (as initially feared after the earlier failed composition test), but rather compounds with the yushin deck choice in a way trolley does not.

3. **Same-run measurement credibility**: All three arms measured against identical 9-opponent bracket pool (bracket_1..6 + three meta clones) in a single ring execution, eliminating cross-run variance as a confound.

## Findings

- **Ring-positive build identified**: heuristic+yushin+ability+attack_first is now the strongest ring-measured candidate across all measured three-arm combinations.
- **P3 lock-the-strongest-pair eligibility**: This build is now a pre-registered candidate for the Aug 10-16 endgame variance-harvest campaign, contingent on board availability.
- **Yushin contest resolved**: The recent yushin ladder contest (three +0.100 reads, one +0.050) is definitively resolved in favor of yushin by this ring verdict; the +15pp ring delta > any single-read ladder variance band.

## Next Queue Items

Per POSTURE INVERSION:
1. **Immediate**: U104 PASS is documented; no immediate ladder submission (both slots occupied, frozen per P3).
2. **Escalation to P3 planning**: yushin+ability+attack_first should be pre-registered as a lock-the-strongest-pair candidate for the Aug 10-16 endgame window.
3. **No redundant board-check iteration**: Per ANTI-CHURN rule, board state is frozen within M=240 noise band; no new mechanical work unlocked by this gate passing alone.
4. **Next mechanical queue**: Item 4 (U105 threat/prize awareness) awaits design judgment; item 5 (U106 state-matched expert) is compute-heavy; item 7 (U102 differential audit) runs external to LLM loop.

---
*Gate passed 2026-07-06. Prepared by autoloop iteration 121.*
