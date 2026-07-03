# U74: re-gating the staged PTCG_ABILITY lever through the calibrated clone ring

Plan: docs/plans/2026-07-03-002-feat-top-player-clone-ring-plan.md, U74. Immediate payoff once
U73/U81's ring calibration passed (tau 0.857, analysis/ring_calibration.md): score the staged
ability-on vs ability-off builds against the ring and record a free predictiveness data point
against the pending ladder A/B. Ring results never veto an already-pre-registered ladder A/B
(state/current.md's heuristic+trolley-ability vs heuristic+trolley, direction up, M=60, N=30,
settle-by 2026-07-08); this only gates FUTURE candidates and checks the ring's own track record.

## Method

`tools/ability_ring_check.py`: heuristic + trolley deck, `_ABILITY` (agents/heuristics.py) forced
on or off in-process (module constant is read once at import, so the env var toggle used for the
real submission build has no effect after import; monkeypatched the same way
`tools/ring_calibrate.py`'s `_no_benchguard_trolley_agent` patches `THIN_BENCH`), round-robin
against every `clone:<family>` opponent currently on disk (`tools.opponents.clone_family_names()`,
now the U81 bracket-band ring: 6 top-20 clones plus 6 bracket_1..6 clones), 20 games/arm.

## Result

| arm | wins | n | win rate |
| --- | --- | --- | --- |
| ability off | 13 | 20 | 65.0% |
| ability on | 17 | 20 | 85.0% |

diff_pp (on minus off) = +20.0.

## Reading

The ring's directional call (on beats off) agrees with the offline weak-bot gauntlet's directional
call (+4.0pp, analysis/ability_ab.md, off 67.5% vs on 71.5%, 200 games/arm). Both offline signals
point the same way as the pre-registered ladder hypothesis. The ring's margin (+20pp at n=20 per
arm) is much larger than the gauntlet's (+4.0pp at n=200 per arm); at this sample size that is
consistent with either a genuinely bigger edge against the bracket-band field specifically (the
ring's whole thesis) or plain small-n noise, and the two numbers are not directly comparable since
they come from different opponent pools and match counts. This is not a claim that the ring
predicts the ladder's exact margin, only its direction.

**Predictiveness record (fill in once the ladder settles, no later than 2026-07-08):** the
pre-registered ladder A/B compares heuristic+trolley-ability (ref 54282097) against the
heuristic+trolley king. If the ladder settles WIN, this ring check is the ring's second
directionally-correct call (after retrodicting the six known historical builds at tau 0.857). If
the ladder settles LOSS, this is the ring's first live miss and should be logged honestly next to
the tau 0.857 calibration, since a ring that retrodicts history but misses a live call still has
real predictive limits worth recording. Per the plan's explicit rule, whichever way the ladder
settles, it is NOT retroactively overturned by this ring reading; the ring only gates future
candidates.
