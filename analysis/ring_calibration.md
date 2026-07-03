# U73: clone ring calibration gate, verdict FAIL (tau 0.429 < 0.7)

Pre-registered decision rule (docs/plans/2026-07-03-002-feat-top-player-clone-ring-plan.md,
U73; tools/ring_calibrate.py): replay the six historical builds whose real ladder public score
is already known against the `clone:<family>` ring (tools/opponents.py, U70-U72) at N=20 games
per build, then Kendall-tau the ring's win-rate ordering against the known ladder ordering.
tau >= 0.7 over >= 4 covered builds means the ring replaces the mirror pool as the offline gate
for future TRACK L candidates. Below that, record the failure honestly and keep the ladder as
sole arbiter. This run: **tau = 0.429, FAIL.**

## Setup

- Ring: the three `clone:<family>` opponents with a decklist on disk (`clone:meta_archaludon`,
  `clone:meta_grimmsnarl`, `clone:meta_grimmsnarl_tonakaiiii`), round-robin, 20 games/build.
- Builds: `tools/ring_calibrate.BUILD_FACTORIES`, reproducing each historical submission's
  behavior in-process (the current heuristic for the four builds that postdate the bench guard;
  `agents.heuristics.THIN_BENCH` patched to 0 for the pre-benchguard trolley build; `agent_search`
  wrapped to pilot the trolley deck for the search build). See the module docstring for exactly
  which knob reproduces which build.
- Command: `python tools/ring_calibrate.py -n 20`.

## Result

| build                  | known ladder score | ring win rate | ladder rank | ring rank |
|-------------------------|--------------------:|---------------:|:-----------:|:---------:|
| heuristic+trolley        | 569.6 | 0.85 | 1 | 1 |
| heuristic+benchguard      | 554.5 | 0.70 | 2 | 3 (tie) |
| search+trolley            | 514.7 | 0.70 | 3 | 3 (tie) |
| meta_grimmsnarl           | 510.1 | 0.45 | 4 | 6 |
| trolley_thick             | 446.2 | 0.80 | 5 | 2 |
| meta_archaludon           | 382.5 | 0.65 | 6 | 5 |

tau = 0.429 (10 concordant, 4 discordant, 1 tied pair dropped from the 15 total; n_covered = 6,
above MIN_COVERAGE = 4). threshold = 0.7. **passes = False.**

A first, tail-truncated reading of the same command (same code, independent match draws) gave
tau = 0.286, also a clear FAIL; both readings land well below 0.7, so this is not a borderline
call decided by one unlucky draw.

## Diagnosis: the two builds driving the mismatch

The ring gets the top of the ordering right (heuristic+trolley ranks first in both) but inverts
the middle and bottom badly enough to fail:

- **trolley_thick is badly overrated by the ring** (ring rank 2, ladder rank 5). Plausible cause:
  the ring foils only test the deck's raw power against first-legal-plus-safety play, not the
  specific failure modes (early collapse / self-deckout patterns) that separate trolley_thick
  from trolley on the real ladder field. The ring cannot see whatever the wider live field
  punishes that these three clone decks do not.
- **meta_grimmsnarl is badly underrated by the ring** (ring rank 6, ladder rank 4). This has a
  likely structural confound rather than a real quality signal: one of the three ring opponents
  (`clone:meta_grimmsnarl`) pilots the *same* decklist as the meta_grimmsnarl build under test.
  A third of meta_grimmsnarl's ring games are effectively a mirror matchup against a clone of its
  own deck, which is not true for any other build in this table (none of trolley, trolley_thick,
  or archaludon has a same-deck clone in the ring). A same-deck mirror pulls the aggregate win
  rate toward 50% regardless of the deck's real quality, exactly the kind of self-beater
  distortion the whole clone-ring project (U70-U72) set out to move away from. This is worth
  fixing before any future calibration attempt: either exclude a build's own-deck clone from its
  ring opponents, or accept the confound and note it every time.

## Verdict and what it means for TRACK L

Per the pre-registered rule, the ring does **not** replace the mirror pool as the offline gate.
U74 (re-gate the live levers through the ring) is explicitly conditioned on U73 passing
(docs/plans/2026-07-03-002-feat-top-player-clone-ring-plan.md: "only if U73 passes"), so U74 is
skipped, not attempted and force-fit.

This extends rather than breaks the loop's honest transfer-failure record: every offline proxy
tried so far (the mirror pool, the move-ranking validator, and now the calibrated clone ring)
has failed to retrodict the real ladder ordering well enough to be trusted as a gate. Per the
loop brief's L4, TRACK L now falls back to ladder-only judgment with strict slot discipline:
future SHIPPED heuristic/deck candidates are judged by the live ladder A/B alone, not blocked or
promoted by any offline proxy score. This honest 0-for-6 record (five prior proxies plus this
one) is itself real Strategy-writeup material: an evaluation methodology that keeps testing its
own assumptions and reports negative results plainly, rather than rationalizing a convenient
proxy into "good enough," is the differentiated story docs/writeup/ is meant to tell.

## Reproduce

```
python tools/ring_calibrate.py -n 20
```

Or, to grade an already-measured set of ring results without replaying games:
`tools.ring_calibrate.calibrate_from_results(results)` (see tests/test_ring_calibrate.py for the
shape).
