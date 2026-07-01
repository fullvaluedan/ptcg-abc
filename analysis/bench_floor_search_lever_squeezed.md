# The search bench-floor lever is dead on arrival: a fidelity/efficacy squeeze

## Finding

The convex empty-bench leaf-eval term (`eval._BENCH_FLOOR`, cf462e0) cannot be
shipped as a net-positive search lever. It is not merely inert on the shipped
stack (that was already known); it is caught in a squeeze that no rollout-depth
setting escapes. At the shallow depth where the term actually changes a decision,
the depth-cut rollout has already diverged from the accurate terminal rollout on
most positions, so activating the term means accepting a blind regression of the
search's core value estimate. At the deeper depth where the rollout stays faithful
to the terminal result, the term goes inert again. There is no depth window where
the bench floor both fires AND the rollout it rides on is trustworthy.

This closes the standing "SECOND submission" plan (flip `PTCG_ROLLOUT_DEPTH`
positive TOGETHER WITH `PTCG_BENCH_FLOOR`). Do not spend a ladder slot on it.

## Why the term is inert by default

The leaf-eval terms (the bench floor, plus the active-weighted and attached-energy
health terms) are read only at a rollout LEAF. With the shipped `_ROLLOUT_DEPTH =
None` every line rolls to a TERMINAL result, so a leaf is reached only at the
engine's 400-step cap and `board_value` is consulted ~0 times per decision. The
bench floor is therefore off on the deployed policy regardless of its own flag.
The only way to make it fire is to cut rollouts short with a positive
`PTCG_ROLLOUT_DEPTH`, which trusts `board_value` at the cut instead of playing the
line out. That cut is the risk this measurement quantifies.

## Evidence (tools/measure_bench_floor.py, trolley deck, shipped forward model)

The tool holds the determinizations fixed (12 worlds, a fresh `Random(_SEED)` per
run) so the ONLY variable between the off and on runs is the bench-floor term. It
reports two numbers per depth: how many captured decisions the floor flips
(efficacy), and how often the depth-cut argmax agrees with the terminal argmax on
the same fixed worlds (fidelity).

```
value_depth 8 :  bench-floor flipped 2/5 decisions,  depth-8 tracked terminal 1/5
value_depth 16:  bench-floor flipped 0/2 decisions,  depth-16 tracked terminal 2/2
```

Read the contrast:

- At depth 8 the floor is LIVE (2 of 5 chosen moves change), but the depth-8
  rollout disagrees with the faithful terminal rollout on 4 of 5 positions. Turning
  the floor on here rides a value estimate that is wrong 80% of the time. Any
  decision it flips is as likely to be flipped toward a worse move as a better one.

- At depth 16 the rollout tracks the terminal decision perfectly (2 of 2), but the
  floor no longer changes any decision. The deeper the cut, the closer to terminal,
  the more the shaping term is dominated by the real playout, until it vanishes.

The squeeze is structural, not a tuning miss: the bench floor is a leaf-shaping
term, and shaping only matters when the leaf substitutes for the true result, which
is exactly when the leaf is least trustworthy on this engine.

## Decision

Keep `eval._BENCH_FLOOR` and `agent_search._ROLLOUT_DEPTH` at their shipped-off
defaults permanently, not provisionally. The bench-maintenance win stays where it
was measured to work: the PILOT guard (`heuristics.THIN_BENCH`, the unconditional
thin-bench MAIN defer, e44245a), which cut OUR isolated board-out 43 -> 34pct
(tools/measure_benchguard.py) at the shipped terminal-rollout stack with no rollout
fidelity cost. The next free ladder slot goes to the bench-guarded search build
(e44245a, still unshipped) on the shipped terminal-rollout stack, NOT to the
eval-floor + rollout-depth joint lever.

## Caveat

This measurement can only REFUTE a lever, never confirm a win (offline weak-bot
play is not ladder-predictive per meta.md). It does not claim the bench floor would
hurt the score; it shows the term cannot be activated without degrading the search's
own value estimate, which removes any principled reason to spend a slot on it.
