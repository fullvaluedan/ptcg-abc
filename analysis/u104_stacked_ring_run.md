# U104 Stacked Ring Run Results

**Run date:** 2026-07-06, 23:55 UTC  
**Status:** FAIL (gate threshold not met)

## Results

Three-arm factorized ring run against calibrated bracket ring (tau 0.857), n=40 per arm:

| Arm | Build | Win Rate | Wins | Matches |
| --- | --- | --- | --- | --- |
| 1 (baseline) | heuristic+trolley+ability | 77.5% | 31 | 40 |
| 2 | heuristic+yushin+ability | 92.5% | 37 | 40 |
| 3 | heuristic+yushin+ability+attack_first | 80.0% | 32 | 40 |

## Gate Verdict

- diff_pp (arm 3 minus arm 1): +2.5pp
- gate threshold: >+10.0pp
- **Result: FAIL**

## Interpretation

Arm 3 (yushin+ability+attack_first) does not clear the +10pp margin required for promotion to P3 lock-the-strongest-pair selection. The +2.5pp delta is within the same-run noise band. Yushin+ability shows +2.5pp over trolley+ability (comparable to arm 3), consistent with the contested +0.050 to +0.100 ladder reads noted in 2026-07-05 briefing. The attack_first flag adds no measurable delta on the yushin deck in the ring.

## Next Steps

- U104 FAIL does not block other work
- Ring evidence confirms trolley+ability (shadow-king) as the best settled build
- P3 early-lock will proceed with ability build pair, as per the noise recalibration directive (L9)
- No new U105+ lever testing triggered; queue order unchanged
