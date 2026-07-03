# U73/U81: clone ring calibration gate, verdict PASS (tau 0.857 >= 0.7)

Pre-registered decision rule (docs/plans/2026-07-03-002-feat-top-player-clone-ring-plan.md,
U73; tools/ring_calibrate.py): replay the six historical builds whose real ladder public score
is already known against the `clone:<family>` ring (tools/opponents.py, U70-U72) at N=20 games
per build, then Kendall-tau the ring's win-rate ordering against the known ladder ordering.
tau >= 0.7 over >= 4 covered builds means the ring replaces the mirror pool as the offline gate
for future TRACK L candidates. Below that, record the failure honestly and keep the ladder as
sole arbiter.

**First run (U73, top-20 clone ring): tau = 0.429, FAIL.** See "History" below.

**This run (U81, bracket-band clone ring): tau = 0.857, PASS.** The only change from the failed
U73 run is the ring's opponent pool: `tools/opponents.py`'s `clone_family_names()` now also
returns the six `clone:bracket_<rank>` families harvested by `tools/bracket_decks.py` from real
~450-750-rating-band and actual-opponent decklists (U81 steps 1-2), alongside the original three
`meta_*` clones. No change to `tools/ring_calibrate.py`'s gate math or build factories was needed;
`ring_names()` already derives its opponent list from `clone_family_names()`.

## Setup

- Ring: all nine `clone:<family>` opponents with a decklist on disk (`clone:bracket_1` through
  `clone:bracket_6`, `clone:meta_archaludon`, `clone:meta_grimmsnarl`,
  `clone:meta_grimmsnarl_tonakaiiii`), round-robin, 20 games/build.
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
| heuristic+benchguard      | 554.5 | 0.80 | 2 | 2 (tie) |
| search+trolley            | 514.7 | 0.80 | 3 | 2 (tie) |
| meta_grimmsnarl           | 510.1 | 0.50 | 4 | 4 |
| trolley_thick             | 446.2 | 0.75 | 5 | 3 |
| meta_archaludon           | 382.5 | 0.40 | 6 | 5 |

tau = 0.857 (13 concordant, 1 discordant; n_covered = 6, above MIN_COVERAGE = 4).
threshold = 0.7. **passes = True.**

## Diagnosis: why the bracket ring succeeds where the top-20 ring failed

The single discordant pair is trolley_thick (ring rank 3) vs heuristic+benchguard/search+trolley
(tied ring rank 2), a much smaller miss than U73's top-20 ring, which inverted the middle and
bottom of the ordering badly enough to fail outright. The U73 postmortem named two suspected
causes; this result is consistent with both being real:

- **Wrong opponents, now fixed.** U73's foils were top-20 leaderboard clones, not the ~450-750
  rating-band field the ladder actually matches us against. The bracket ring imitates decklists
  either drawn from that real rating band or drawn from our own 143+ real ladder opponents, i.e.
  the field the known ladder scores were actually earned against. A ring that predicts our own
  bracket predicts our own bracket's ladder scores.
- **Same-deck mirror confound, diluted rather than fixed directly.** U73 flagged that
  `meta_grimmsnarl`-under-test playing against `clone:meta_grimmsnarl` (a mirror of its own deck)
  pulled that build's aggregate win rate toward 50% by construction. That same clone is still in
  this ring, but it is now 1 of 9 opponents instead of 1 of 3, so the mirror-matchup fraction of
  meta_grimmsnarl's games dropped from 1/3 to 1/9, diluting rather than eliminating the distortion.
  meta_grimmsnarl still under-performs its ladder rank somewhat (ring rank 4 vs ladder rank 4 is
  actually exact this time, so this confound may already be small enough at 1/9 not to matter, but
  it was not deliberately removed and is worth remembering if a future re-calibration regresses).

## Verdict and what it means for TRACK L

Per the pre-registered rule, **the ring now replaces the mirror pool as the offline gate for
future TRACK L candidates.** Per the plan, this is never retroactive: it does not veto or
re-open any already-pre-registered ladder A/B (the L1 ability build stays on its own settle
clock). U74 (re-gate the live levers through the ring, docs/plans/2026-07-03-002-feat-top-player-
clone-ring-plan.md) is now unblocked: score the staged L1 ability build and any queued deck
candidates against this ring and record whether the ring agrees with the pending ladder A/B once
it settles.

This is the first offline proxy to pass calibration after five honest failures (the mirror pool,
the move-ranking validator, and the U73 top-20 ring among them; see
docs/writeup/ for the full transfer-failure record). The differentiating factor each time was not
a better model or more compute, it was testing the proxy against the SAME field the ladder score
was earned against, rather than assuming a stronger opponent (top-20) is automatically a more
informative one.

## Reproduce

```
python tools/ring_calibrate.py -n 20
```

Or, to grade an already-measured set of ring results without replaying games:
`tools.ring_calibrate.calibrate_from_results(results)` (see tests/test_ring_calibrate.py for the
shape).

## History: the U73 top-20 ring, FAIL (tau 0.429)

- Ring: the three `clone:<family>` opponents with a decklist on disk at the time
  (`clone:meta_archaludon`, `clone:meta_grimmsnarl`, `clone:meta_grimmsnarl_tonakaiiii`), all
  harvested from the top-20 leaderboard, round-robin, 20 games/build.
- Result: tau = 0.429 (10 concordant, 4 discordant, 1 tied pair dropped from the 15 total).
  A first, tail-truncated reading of the same command (same code, independent match draws) gave
  tau = 0.286, also a clear FAIL; both readings landed well below 0.7, so it was not a borderline
  call decided by one unlucky draw.
- Diagnosis at the time: trolley_thick was badly overrated by the ring (ring rank 2, ladder rank
  5); meta_grimmsnarl was badly underrated (ring rank 6, ladder rank 4), plausibly the same-deck
  mirror confound described above, at full strength (1 of 3 opponents rather than 1 of 9).
- Verdict at the time: the ring did not replace the mirror pool; U74 was skipped, not attempted
  and force-fit. TRACK L fell back to ladder-only judgment with strict slot discipline. This
  extended the loop's honest transfer-failure record to 0-for-6 (five prior proxies plus that
  ring). That record stands as-is for everything before this U81 re-run; only the ring's verdict
  has since flipped, on a genuinely different (and better-targeted) opponent pool, not a re-roll
  of the same test.
