# PTCG_ABILITY: isolating the one-sided effect from the shared-process confound

LOOP_BRIEF.md's L1/L9 notes flag an unresolved caveat on the shipped ability lever
(`heuristic+trolley-ability`, current shadow-king): the offline gauntlet gate
(`analysis/ability_ab.md`, +4.0pp) and the bracket-ring gate
(`analysis/ability_ring_check.md`, +20.0pp) both bake `PTCG_ABILITY` into a whole
subprocess's environment. `agents/heuristics.py`'s `_ABILITY` flag is a single
process-global read fresh on every `choose()` call
(`agents/heuristics.py:1215-1216`), and every `deck:<name>` opponent in the
gauntlet pool is piloted by the SAME `heuristics.py` module in the SAME process
(`tools/opponents.py`'s `_deck_opponent` calls `heuristics.choose` directly). So
the recorded "on" arm actually gave BOTH seats the ability lever, not just the
pilot the lever is meant to help. This was flagged but never re-checked; this
unit closes that gap with `tools/measure_ability_isolated.py`, which toggles the
module global per-seat (monkeypatch immediately before each seat's callable
runs, same technique `tools/measure_attack_first.py` already uses for flip
checks) so an on/off arm the env-var-baked gauntlet could never produce (only
our pilot has the lever, the opponent does not) is directly measurable.

## Method

Same 8-deck opponent pool as `analysis/ability_ab.md`
(`meta_archaludon meta_grimmsnarl meta_grimmsnarl_tonakaiiii aggro control
ultraball trolley trolley_thick`, `heuristic + trolley` piloting our side).
Three arms per run: `off/off` (shipped default, both seats off), `on/on`
(mirrors the confounded env-var-baked A/B), `on/off` (isolated: only our seat
has the lever). The native engine has no seed hook (`tools/parallel_gauntlet.py`'s
own seed-honesty note applies here too), so repeat runs are independent draws,
not replays.

## Results (three independent runs, single process each)

| run | n/arm | off/off win% | on/on win% | on/off (isolated) win% | on/on diff_pp | on/off diff_pp |
| --- | --- | --- | --- | --- | --- | --- |
| seed 0 | 200 | 64.0 | 60.0 | 66.5 | -4.0 | +2.5 |
| seed 1 | 200 | 65.0 | 70.5 | 64.5 | +5.5 | -0.5 |
| seed 2 | 300 | 66.7 | 66.0 | 65.3 | -0.7 | -1.3 |

Wilson 95% CIs are wide (roughly +/-7pp at n=200, +/-5.5pp at n=300) and overlap
heavily across all three arms in every run. The isolated (`on/off`) diff_pp
oscillates around zero across the three runs (+2.5, -0.5, -1.3; mean +0.2), and
so does the confounded (`on/on`) diff_pp (-4.0, +5.5, -0.7; mean +0.3). Neither
arm shows a stable, noise-clearing positive effect at any sample size tried
here, including the largest (n=300/arm, 900 games total).

## Interpretation

The deconfounding worked as designed (an `on/off` arm now exists that the
original env-var-baked methodology structurally could not produce), but the
headline finding is not "the confound inflated the effect" or "the confound
was harmless" -- it is that **both the confounded and the isolated arms are
individually within the same kind of sampling noise this project has already
documented for the ladder board** (`state/current.md`'s noise_model, v2,
~150pt margin). Across all three runs (600 isolated-arm games total) the
isolated one-sided effect averages +0.2pp, not distinguishable from zero, let
alone from the +4.0pp originally reported. This does not refute the ability lever (the underlying motivation,
0/554 real ABILITY decisions agreeing with top players with the flag off,
analysis/move_ranking_diverges_ability_gap.md, is untouched by this check
and does not depend on gauntlet win rate at all) but it does mean **the
offline gauntlet gate's specific point estimate (+4.0pp) should not be read
as confirming a real, isolated, sizable win-rate edge** -- it was likely
dominated by run-to-run noise at that sample size, symmetric-mirror
confound or not.

## Disposition

No action against the shipped shadow-king build: per L9, ring evidence (not a
single gauntlet or ladder read) is already the standing decision gate for this
lever, and the underlying 0/554 blind-spot motivation is unaffected. This
closes the L1/L9 "not re-validated this iteration" caveat with a real
(negative-ish) answer: the offline gauntlet gate is noisy at its sample size,
in both the confounded and deconfounded framing, so it should be weighted
accordingly if a future unit revisits the ability lever's evidence base. No
ladder slot spent; this is a TRACK S offline analysis unit.

Tooling: `tools/measure_ability_isolated.py`, tests in
`tests/test_measure_ability_isolated.py` (3 tests, no native engine).
