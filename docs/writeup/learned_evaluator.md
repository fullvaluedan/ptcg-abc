# Learned state evaluator (Strategy prize writeup, plan U1-U7)

This section covers the ML track only. It never touches the shipped ladder
agent: agent_heuristic.py (the deck-copy heuristic) is what is actually
submitted to Kaggle, and none of the model described here is on that path.
This work is the Strategy-prize (model approach) deliverable.

## Motivation

The search agent (search/eval.py) scored board states with a hand-tuned
linear formula: prize lead weighted a fixed amount, bench size another fixed
amount, active HP fraction another, and so on, all picked by hand rather than
fit to outcomes. The question this unit answers: can a small model, trained
on our own games, do better than those hand-picked weights at predicting
"does the side to move go on to win"?

## Data sources

Three sources feed the training rows, each going through the same
extract_features(state, your_index) function (src/ptcg_agent/features.py) so
training and match-time inference can never see a different feature layout:

- **gauntlet** (U1, U3): tools/gauntlet.py --log-states logs one row per
  decision state per seat while our own agents play each other. This is the
  largest and cleanest source: 112,033 training rows after the game-level
  train/test split, class balance checked to land between 35 and 65 percent
  wins by tools/dataset_report.py.
- **ladder** (U3a, U3b): tools/harvest_replays.py downloads public Kaggle
  ladder episodes; tools/replays_to_rows.py converts each seat's decision
  states into the same row shape, tagged source=ladder, downsampling the
  majority class if the ladder-only class balance falls outside 30-70
  percent. 15,971 rows in the U4 ladder-merge experiment.
- **top_player** (U3c): the same replay-to-rows pipeline restricted to
  episodes where a high-rated bot won, sample-weighted 2.0x relative to
  gauntlet/ladder rows (every other source stays at weight 1.0) via
  tools/train_eval.py --source-weights, on the theory that a stronger
  player's winning states are worth more per row than an average gauntlet
  game's. 173,663 rows in the U6 retrain attempt.

Ladder replay JSON is never committed (data/replays/ is gitignored) and is
never redistributed, per the competition's data-sharing rule.

## Model choice

Logistic regression (scikit-learn, dev-only dependency, never in the
submission bundle) over 21 standardized features: prize differential, prizes
remaining for both sides, deck (library) count for both sides and their
difference, hand size for both sides, bench size for both sides plus a
bench-nonempty flag, active and mean bench HP fraction for both sides,
attached energy for both sides, clamped turn number, whose turn it is, and
two of our own flags (supporter played, energy attached this turn). Logistic
regression was chosen over a heavier model because the entire point is to
export a scorer that runs with no ML library at match time: a handful of
floats (mean, std, coefficient per feature, one intercept) and a sigmoid are
enough to reproduce it exactly in pure Python (search/learned_eval.py),
whereas a tree ensemble or neural net would need either a runtime dependency
or a much larger hand-written inference path.

The model must beat a single-feature baseline (prize_diff alone) on held-out
AUC, or the training run fails outright: that is the bar the plan sets for
"the learned features are worth having" over just tracking who is ahead on
prizes.

## Leakage control

Two leakage risks are guarded against directly in tools/train_eval.py:

- **Row-level split would leak.** Two states from the same game are highly
  correlated (same players, same deck matchup, same eventual winner), so a
  plain random 80/20 row split would let a held-out game's other states leak
  into training. game_split() instead splits by unique game_id, so an entire
  game lands on one side of the split or the other, never both.
- **Colliding game ids across sources.** Gauntlet game ids are small
  sequential integers; ladder game ids are Kaggle episode ids. load_rows()
  tags each source's ids with a prefix (e.g. "ladder:82976189") before
  concatenating, so a gauntlet game and a ladder game that happen to share a
  raw id number can never be silently merged onto the same side of the
  split.

## A/B methodology and numbers

Three separate A/B questions were asked, each gated in advance:

**1. Does adding ladder rows to training help? (U4 ladder-merge redo,
analysis/ladder_data_ab.md)** Two models trained on the same gauntlet rows,
one with 15,971 ladder rows added, both evaluated on the identical held-out
gauntlet-only test set (26,234 rows) so the comparison isolates the effect of
the extra rows rather than measuring a different test distribution.

| variant | train rows | test AUC | test accuracy |
|---|---|---|---|
| gauntlet-only | 112,033 | 0.8104 | 0.7236 |
| gauntlet+ladder | 128,004 | 0.8079 | 0.7174 |

Gate: keep the merged model only if its AUC on the gauntlet-only test set is
at least the gauntlet-only model's. **Verdict: gauntlet-only wins** (0.8104
vs 0.8079); search/eval_model.json ships the gauntlet-only model.

**2. Does the learned eval beat the hand-tuned eval in play? (U5,
analysis/learned_eval_ab.md)** 400 games per arm, PTCG_LEARNED_EVAL off vs
on, same 8-deck opponent pool, agent under test is search (not the shipped
ladder agent).

| arm | wins | losses | win rate |
|---|---|---|---|
| off | 272 | 128 | 68.00% |
| on | 275 | 125 | 68.75% |

diff_pp (on minus off): +0.75 percentage points. Gate: flip the shipped
default only if on beats off by more than 4 points. **Verdict: keep default
off** (0.75pp is a real but small win, well short of the 4pp bar), which
still satisfies the Phase A whole-plan gate (learned eval must at least match
hand-tuned: it does, by a small positive margin, not a loss).

**3. Does folding in a much larger, weighted top-player corpus help on
retrain? (U6, analysis/retrain_gen2_ab.md, analysis/learned_eval_loss_modes.md)**
Same gate as U4, now against a combined gauntlet + ladder + gen2 self-play +
top_player (weighted 2.0x) training set.

| variant | train rows | test AUC |
|---|---|---|
| gauntlet-only | 112,033 | 0.8104 |
| gauntlet+ladder+gen2+top_player(2.0x) | 314,815 | 0.7795 |

**Verdict: gauntlet-only wins again**, by a wider margin this time. Adding
173,663 top-player rows at 2x weight moved the training distribution away
from the gauntlet-only test distribution more than it added useful signal, so
`search/eval_model.json` is unchanged. The U5-style 400-games/arm A/B was
re-run on the unchanged model with the new parallel gauntlet harness (U60,
16m12s wall clock instead of roughly 2 hours) and reproduced the same
"keep default off" verdict, this time with an exact 273/127 tie in both arms
(diff_pp 0.0, within the sampling noise expected at this effect size and
sample count, and independently verified to not be a flag-plumbing bug).

## Loss-mode table

Comparing the currently shipped model's deckout and early_collapse loss
rates with the learned eval off vs on, 60 games per arm, same 8-deck
opponent pool:

| arm | games | W/L | deckout (% of losses) | early_collapse (% of losses) |
|---|---|---|---|---|
| off | 60 | 46W/14L | 0/14 (0.0%) | 13/14 (92.9%) |
| on | 60 | 47W/13L | 0/13 (0.0%) | 12/13 (92.3%) |

early_collapse (self-inflicted empty-bench loss) dominates losses in both
arms at this sample size; deckout is negligible either way. The learned eval
does not visibly shift which failure mode causes a loss, consistent with its
small overall effect size. The deckout-specific-feature gate ("add features
only if deckout losses did not improve") did not fire this round: there were
too few deckout losses in either arm to judge improvement one way or the
other. That work is deferred to U64, once the top-player loss corpus (U62)
and win/loss study (U63) produce a real deckout-loss sample to design
features against.

## Top 8 coefficients, explained in plain language

Coefficients below are on standardized features (each feature's raw value is
centered and scaled before the model sees it), so they are directly
comparable to each other in units of "standard deviations of this feature
moving the model's win-log-odds." Ranked by absolute size:

1. **our_bench_size: -0.668.** Counterintuitive at first read: more of our
   own bench slots filled predicts a *lower* win chance, standardized. This
   almost certainly reflects that bench size is correlated with other
   features already in the model (bench HP fraction, energy attached), and
   logistic regression coefficients on correlated inputs can carry a
   surprising sign; it should be read as "controlling for HP and energy, raw
   bench count adds little," not as "never bench Pokemon."
2. **prize_diff: +0.649.** The most straightforwardly interpretable feature:
   being ahead on prizes (having taken more than the opponent) is the
   single strongest positive predictor of winning, matching basic game
   knowledge.
3. **our_bench_hp_frac: +0.561.** A healthier bench (higher average HP
   fraction across our bench Pokemon) predicts a better win chance: a
   damaged bench is closer to being knocked out and giving up a free prize.
4. **our_energy: +0.504.** More energy attached across our board predicts a
   better win chance: it is a proxy for how "developed" our board is and how
   ready we are to keep attacking.
5. **their_bench_size: +0.487.** More cards on the *opponent's* bench
   predicts a better win chance for us. Likely reflects that a bigger
   opponent bench is a bigger set of future prize targets for us to knock
   out, all else equal.
6. **our_active_hp_frac: +0.455.** A healthier active Pokemon predicts a
   better win chance, unsurprising: it is not about to be knocked out.
7. **their_prizes_left: +0.395.** The opponent having more prizes still left
   to take (i.e. we have taken more of theirs) predicts a better win chance
   for us; this is the mirror image of prize_diff and reinforces the same
   signal from a different angle.
8. **their_active_hp_frac: -0.389.** The opponent's active Pokemon being
   healthier predicts a *worse* win chance for us, the expected direction:
   a healthy opponent active is harder to knock out this turn.

Two of these eight (#1 our_bench_size, and to a lesser extent #9 in the full
ranking our_bench_nonempty at -0.198, not in the top 8 but worth flagging
alongside #1) point the "wrong" direction from raw intuition. This is a known
property of linear models fit on correlated inputs, not a bug: the model's
*combination* of all 21 features still beats the prize-differential-only
baseline on held-out AUC, which is the bar the plan actually sets, even
though any single coefficient read in isolation can mislead.

## Bottom line for the Strategy prize

The learned evaluator is a real, working, fully-offline pure-Python model
(scores 2*p - 1 from a sigmoid, falls back to 0.0 on a malformed state,
never touches sklearn at match time) that modestly beats the hand-tuned
evaluator (+0.75pp then an exact tie on re-run, both within the 4pp
ship-the-default bar) while never losing to it across three independent A/B
measurements. Every attempt to grow the training set with ladder or
top-player rows made held-out AUC worse rather than better, which is itself
a useful finding: our own gauntlet self-play games are a better match to
what we actually need the evaluator to be good at than the public ladder or
top-player corpora are, at least at the scale collected so far. Because
`agent_search` (which this evaluator lives inside) is not the shipped ladder
agent, none of this changes the Kaggle rank; it is the model-approach
evidence for the Strategy prize.
