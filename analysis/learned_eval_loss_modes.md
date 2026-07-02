# U6: retrain generation and loss-mode check

Plan U6 (docs/plans/2026-07-02-combined-learned-eval-plan-v2.md). One retrain
generation using the newly generated self-play games (gen2 batches, plan
U60's parallel gauntlet not yet needed for this leg since the gen2 data was
already on disk from a prior iteration), folded together with the ladder
replay rows and the weighted top_player win corpus (U3c). Re-run the U5 A/B.
Compare deckout/early_collapse loss rates.

## Retrain generation: gate rejected the merged model

See analysis/retrain_gen2_ab.md for the full setup and numbers. Same gate as
U4's ladder-merge redo: keep the merged model only if its held-out AUC (on a
gauntlet-only test set) is at least the gauntlet-only model's AUC.

| variant | train rows | test AUC |
|---|---|---|
| gauntlet-only | 112033 | 0.8104 |
| gauntlet+ladder+gen2 batches (1,2,3)+top_player (weighted 2.0) | 314815 | 0.7795 |

Verdict: **gauntlet-only wins**. The merged variant's AUC drops relative to
gauntlet-only (0.7795 vs 0.8104), almost certainly because the 173,663-row
top_player corpus (weighted 2x) shifts the training distribution away from
the gauntlet-only test set's distribution more than it helps. `search/eval_model.json`
is therefore **unchanged** by this retrain attempt: it is still the same
gauntlet-only model from U4.

## Consequence: there is no "before retrain" vs "after retrain" model to diff

Because the retrain did not produce a new model file, `search/eval_model.json`
before and after this unit's retrain attempt is the same file. The originally
planned "run measure_loss_modes.py against the old model, swap in the
retrained model, run it again" comparison has nothing to compare: both runs
would exercise the identical model.

As a substitute that still answers a real question with the tooling this unit
built, this instead compares the **currently shipped model's** deckout /
early_collapse loss rate with `PTCG_LEARNED_EVAL` off (hand-tuned eval,
current default) vs on (learned eval), 60 games per arm, same opponent pool
as the U5/U6 A/B (deck:meta_archaludon, deck:meta_grimmsnarl,
deck:meta_grimmsnarl_tonakaiiii, deck:aggro, deck:control, deck:ultraball,
deck:trolley, deck:trolley_thick).

| arm | games | W/L | deckout (% of losses) | early_collapse (% of losses) |
|---|---|---|---|---|
| off (PTCG_LEARNED_EVAL=0) | 60 | 46W/14L | 0/14 (0.0%) | 13/14 (92.9%) |
| on (PTCG_LEARNED_EVAL=1) | 60 | 47W/13L | 0/13 (0.0%) | 12/13 (92.3%) |

Diff (on minus off, rate of losses): deckout +0.0000, early_collapse -0.0055.

Both arms are dominated by the same failure mode, `early_collapse` (roughly
92% of losses either way), and neither arm produced a single deckout loss in
this sample. The learned eval does not visibly shift the loss-mode mix at
this sample size; the two arms are within noise of each other, consistent
with the U5 A/B's own small effect size (+0.75pp win rate, well under the
4pp flip threshold).

## Re-run of the U5-style A/B (plan U6 "re-run A/B")

400 games per arm, same opponent pool, via the newly parallel
`tools/run_ab.py` (now fans each arm out across worker subprocesses through
`tools/parallel_gauntlet.run_parallel_gauntlet`, plan U60): 16m12s wall clock
for 800 total games, versus roughly 2 hours estimated for the old fully
sequential path. Full result: analysis/u6_learned_eval_ab.json.

| arm | wins | losses | matches | win rate |
|---|---|---|---|---|
| off (PTCG_LEARNED_EVAL=0) | 273 | 127 | 400 | 68.25% |
| on (PTCG_LEARNED_EVAL=1) | 273 | 127 | 400 | 68.25% |

diff_pp (on minus off): 0.0 percentage points. Verdict: **keep default off**
(unchanged from U5; well under the 4pp gate). The exact tie in win/loss
counts is plausible sampling noise given the U5 A/B's own effect size was
already tiny (+0.75pp on a different 400-game sample) relative to this
sample's variance (win-count std at 68% over 400 games is roughly +/-9
wins), not a sign of a broken A/B: `PTCG_LEARNED_EVAL` was independently
verified to reach the flag correctly in each shard subprocess (env is a full
`os.environ.copy()` per arm, not a partial override).

## Deckout-specific-feature gate

Plan: "Add deckout-specific features only if deckout losses did not improve;
retrain once if triggered." This gate does not fire this round: there is no
completed retrain to compare against (the merged retrain was rejected above),
and the flag-off-vs-on substitute measurement above found zero deckout
losses in either 60-game sample, too small a bucket to judge "improved" or
"did not improve" either way. Deckout-specific features are deferred to U64
(docs/plans/2026-07-02-003-feat-offline-match-scale-topplayer-mining-plan.md),
which is explicitly scoped to add bench-cliff / deckout-risk / prize-tempo
features once the top-player loss corpus (U62) and win/loss study (U63) give
a real deckout-loss sample to design against.

## Summary

- search/eval_model.json is unchanged this unit (retrain gate rejected the
  merged variant; gauntlet-only remains the exported model).
- The U5 A/B re-run confirms the same "keep default off" verdict with the
  parallel A/B harness, at 7-8x the wall-clock speed of the old sequential
  path.
- early_collapse remains the dominant loss bucket for the search agent
  against this opponent pool in both eval modes; deckout is negligible at
  this sample size. This is the loss-mode baseline U62/U63/U64 build on.
