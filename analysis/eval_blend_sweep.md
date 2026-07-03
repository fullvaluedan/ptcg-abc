# Eval blend sweep: PTCG_EVAL_BLEND weight sweep (plan U11)

U5 settled PTCG_LEARNED_EVAL as an on/off switch between the hand-tuned
board_value and the learned evaluator, and its A/B showed learned barely ahead
(+0.75pp at N=400, analysis/learned_eval_ab.md), short of the 4pp bar needed
to flip the default. That A/B could only ever compare the two pure endpoints.
This unit generalizes the switch into a continuous weight
(search/eval.py's `PTCG_EVAL_BLEND`, `_effective_blend`) and asks the
question an on/off A/B cannot answer by construction: does some in-between
blend beat BOTH pure endpoints?

## Setup

- Agent under test: search (agent_search, not the shipped ladder agent).
- Opponents: deck:meta_archaludon, deck:meta_grimmsnarl,
  deck:meta_grimmsnarl_tonakaiiii, deck:aggro, deck:control, deck:ultraball,
  deck:trolley, deck:trolley_thick (same pool as U5's A/B).
- Weights swept: 0.0, 0.25, 0.5, 0.75, 1.0 (0.0 = hand-tuned board_value
  only, 1.0 = learned_eval only).
- Matches per weight: 200, via tools/eval_blend_sweep.py's
  run_parallel_gauntlet arms (each weight baked into PTCG_EVAL_BLEND in the
  worker subprocess env), checkpointed to
  data/training/eval_blend_sweep_checkpoint.json (gitignored) so a cut-off
  run resumes instead of restarting.

## Results

| weight | wins | losses | matches | win rate | 95% CI |
|---|---|---|---|---|---|
| 0.0 (hand-tuned only) | 141 | 59 | 200 | 70.5% | [63.8%, 76.4%] |
| 0.25 | 138 | 62 | 200 | 69.0% | [62.3%, 75.0%] |
| 0.5 | 142 | 58 | 200 | 71.0% | [64.4%, 76.8%] |
| 0.75 | 139 | 61 | 200 | 69.5% | [62.8%, 75.5%] |
| 1.0 (learned only) | 146 | 54 | 200 | 73.0% | [66.5%, 78.7%] |

Best weight: **1.0** (learned only), at 73.0%.

## Gate

Keep the blend only if the best weight beats BOTH pure endpoints (0.0 and
1.0). Otherwise keep the U5 winner (PTCG_LEARNED_EVAL default off) unchanged.

Verdict: **FAIL, keep U5's winner unchanged**. The best-scoring weight in
this sweep is 1.0 itself, one of the two pure endpoints, not an in-between
blend. No mixed weight (0.25, 0.5, 0.75) beat both 0.0 and 1.0, so
`endpoints_beaten` is False. search/eval.py's shipped default is unaffected:
`PTCG_LEARNED_EVAL` stays off by default and `PTCG_EVAL_BLEND` stays unset by
default, in which case `_effective_blend()` defers to `PTCG_LEARNED_EVAL`
exactly as before this unit, so this result changes no default behavior.

Two things worth noting about this specific result, without over-reading a
single N=200/arm sweep:

- Every weight's 95% CI overlaps every other weight's CI heavily (0.0's
  interval alone spans 63.8-76.4%, wider than the entire 69.0-73.0% spread
  across all five weights). At this sample size none of these five numbers
  are distinguishable from each other; the sweep answers "does a blend clear
  the gate's bar," not "which weight is truly best."
- 1.0 scoring highest here (73.0%) is directionally consistent with U5's own
  A/B, where "on" also edged out "off" (68.75% vs 68.00%), even though
  neither result clears its own gate's bar (U5 needed +4pp to flip the
  default; this sweep needed a blend to beat both endpoints, and the
  best-scoring weight was an endpoint, not a blend).

## Next

Per the plan's own U8b/U9b/U65 negative-result posture, no code path change
is made here: `_effective_blend`'s already-correct fallback-to-U5 behavior
(added by this unit) needed no further edit once the gate failed. This is
recorded as a negative result for the Strategy writeup: extending an on/off
flag into a continuous blend did not, at this sample size, surface a mixed
weight that beats both pure strategies. Like every U8/U9/U11 unit before it,
this touches only agent_search's offline evaluation, never the shipped
agent_heuristic ladder path, so it earns zero ladder rank points by design.
