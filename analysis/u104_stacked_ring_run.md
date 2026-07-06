# U104 Stacked Ring Run Results

**Run date:** 2026-07-06  
**Status:** FAIL (delta at gate threshold, does not exceed)

## Setup

Ring: calibrated bracket-band clone ring (tools/ring_calibrate.py, tau 0.857, analysis/ring_calibration.md).
Measurements: n=40 games per arm, round-robin against 9 clone opponents.

Three arms, all using heuristic with lever flags:
- Arm 1: deck=trolley, PTCG_ABILITY=on, PTCG_ATTACK_FIRST=off (baseline)
- Arm 2: deck=candidate_yushin_ito, PTCG_ABILITY=on, PTCG_ATTACK_FIRST=off
- Arm 3: deck=candidate_yushin_ito, PTCG_ABILITY=on, PTCG_ATTACK_FIRST=on

Decision gate (LOOP_BRIEF U104): arm 3 beats arm 1 by >+10.0pp same-run delta.

## Results

| Arm | Deck | Ability | Attack_First | Win Rate | Wins-Draws-Losses |
| --- | --- | --- | --- | --- | --- |
| 1 | trolley | on | off | 77.5% | 31-0-9 |
| 2 | yushin | on | off | 87.5% | 35-0-5 |
| 3 | yushin | on | on | 87.5% | 35-0-5 |

**Delta (arm 3 minus arm 1): +10.0pp exactly. Gate threshold: >+10.0pp. Result: FAIL (does not exceed).**

## Key findings

1. **Yushin deck advantage confirmed.** Arm 2 (yushin alone, no new lever) beats arm 1 (trolley) by +10.0pp. Same-run measurement, no confounding.

2. **Attack_first does not compose on yushin.** Arm 3 = Arm 2 (both 87.5%). Adding the attack_first flag to yushin changes nothing, in stark contrast to its +10pp effect in isolation on trolley (analysis/attack_first_ring_check.md). This indicates either: (a) the yushin deck has no exploitable ATTACH+ATTACK sequencing positions, (b) the once-per-turn attack_first logic fires on yushin but is equally net-neutral to the discretionary attach it skips, or (c) the leverage is deck-specific and does not transfer.

3. **Gate: FAIL.** Arm 3 delta equals the threshold (+10.0pp) but does not exceed it (>+10.0pp required). No promotion to ladder.

## Interpretation

The stacked ring run resolves the yushin contest (three +0.100 reads vs one +0.050 read on yushin from earlier deck-specific rings): this factorized same-run measurement puts yushin at +10.0pp, at the lower end of the contested range. Yushin emerges as a ring front-runner equal to trolley+attack_first in composition, but the attack_first lever does not stack beneficially on the yushin deck the way it did in isolation on trolley.

Practical implication: for Aug 10-16 lock-the-strongest-pair phase, ring evidence suggests a choice between (a) trolley+ability (~77.5% ring baseline, per this run; ability is ring-gated at +20pp per analysis/ability_ring_check.md), (b) yushin+ability (~87.5% ring, no lever), or (c) trolley+attack_first (not measured in this run but measured at +10pp in isolation per analysis/attack_first_ring_check.md, so trolley+attack_first likely ~87.5% if composed linearly). No new lever passes the +10pp gate.

## Next steps

Per the queue (LOOP_BRIEF near-term, item 2): U108 settlement arithmetic fix is next. The yushin +10pp ring finding is noted but does not trigger any ladder submission (gate FAIL and the ring-as-decision-gate rule). Endgame planning will compare ring scores across the candidate pairs; trolley and yushin are both viable deck bases depending on lever composition, all ring-gated.
