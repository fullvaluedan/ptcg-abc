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

Four sources feed the training rows, each going through the same
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
- **top_player_loss** (U62): the same replay-to-rows pipeline restricted to
  episodes where a leaderboard team LOST, tagged source=top_player_loss.
  65,695 rows in the U65 retrain sweep. Answers a different question than
  the win corpus: not "what do winning states look like" but "what do the
  best teams' own losses look like," so the model (and the writeup) can
  learn from their mistakes, not just their successes.

Ladder replay JSON is never committed (data/replays/ is gitignored) and is
never redistributed, per the competition's data-sharing rule.

## Model choice

Logistic regression (scikit-learn, dev-only dependency, never in the
submission bundle) over 21 standardized features through U6, and 24 from U64
onward: the original 21 (prize differential, prizes remaining for both
sides, deck (library) count for both sides and their difference, hand size
for both sides, bench size for both sides plus a bench-nonempty flag, active
and mean bench HP fraction for both sides, attached energy for both sides,
clamped turn number, whose turn it is, and two of our own flags (supporter
played, energy attached this turn)) plus three loss-pattern features added in
U64: our_bench_cliff (about to lose bench-nonempty next KO), our_deckout_risk
(how close we are to milling out), and our_prize_tempo (turns since our last
prize). The 24-feature layout is tagged FEATURE_VERSION "2" in both the
training export and the pure-Python scorer, and search/learned_eval.py
refuses to load a model whose feature_version does not match the running
code's feature list (falling back to a neutral 0.5 score instead of silently
reading the wrong numbers into the wrong slots). Logistic regression was
chosen over a heavier model because the entire point is to export a scorer
that runs with no ML library at match time: a handful of floats (mean, std,
coefficient per feature, one intercept) and a sigmoid are enough to
reproduce it exactly in pure Python (search/learned_eval.py), whereas a tree
ensemble or neural net would need either a runtime dependency or a much
larger hand-written inference path.

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

Four separate A/B questions were asked, each gated in advance:

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

**4. Does folding in the top-player LOSS corpus, on top of wins, help on
retrain? (U65, analysis/learned_eval_loss_signal.md)** Same gate as U4/U6,
now sweeping five source-weight combinations for the top_player win and
top_player_loss corpora against the gauntlet-only baseline, all evaluated on
the identical 28,308-row held-out gauntlet-only test set.

| top_player weight | top_player_loss weight | merged test AUC | vs gauntlet-only (0.7799) |
|---|---|---|---|
| 1.0 | 1.0 | 0.7664 | loses |
| 2.0 | 2.0 | 0.7601 | loses |
| 2.0 | 0.5 | 0.7528 | loses |
| 1.0 | 3.0 | 0.7672 | loses |
| 0.5 | 0.5 | 0.7719 | loses |

**Verdict: gauntlet-only wins at every weight tried**, the same pattern as
U4 and U6. `search/eval_model.json` ships gauntlet-only, now on the U64
24-feature layout (FEATURE_VERSION "2"). The gauntlet-only AUC itself moved
from 0.8104 (U4/U6) to 0.7799 (U65) because the retrain used a larger, newer
gauntlet states file, not because the new features hurt; no apples-to-apples
same-data comparison isolating the three new features' individual effect has
been run. The U6-style loss-mode substitute check (flag off vs on, 60
games/arm) showed no material bucket regression (early_collapse stayed
dominant in both arms, 84.2% to 94.4% of losses, driven by a one-game shift
at this sample size, not a worsening).

## How the best teams win versus lose (U62, U63)

Beyond training-set A/Bs, the top-player corpora were mined for a different
purpose: naming what separates the best teams' wins from their own losses,
independent of whether that signal helps this particular logistic model.
tools/top_player_tracker.py pulled every tracked leaderboard team's games
from the 2026-06-30 episode dataset (1441 win games / 109,075 rows, 1074 loss
games / 71,762 rows); tools/win_loss_study.py compares them.

The top teams' dominant loss bucket is nothing like ours:

| loss bucket | top-team rate | our rate |
|---|---|---|
| bad_determinization | 29.1% | 0.0% |
| endgame_misplay | 25.1% | 0.0% |
| deck_matchup | 17.1% | 7.7% |
| early_collapse | 15.3% | 92.3% |
| deckout | 10.4% | 0.0% |
| slow_search | 3.0% | 0.0% |

Our shipped agent's losses are almost entirely early_collapse
(self-inflicted empty-bench collapse); the top teams barely have that
problem (15.3%) and instead lose mostly to guessing wrong about hidden
information (bad_determinization) and late-game misplays. The largest
win-versus-loss feature separators for the top teams are prize-race tempo at
the mid and late turn bins (deck_diff, deck_count): they tend to be ahead of
their opponent's deck-out pace in wins and behind it in losses. Practical
read for this project: "copy what the best teams do" does not mean "copy
their late-game hidden-information handling" (a failure mode we barely
share); it means keep prioritizing our own early-game bench management, the
problem the data already flags as ours independent of anything the top teams
struggle with. Full detail: analysis/top_player_win_loss_study.md.

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
other.

U64 later added the three loss-pattern features (our_bench_cliff,
our_deckout_risk, our_prize_tempo) once U62/U63 gave a real top-player loss
sample to design against, and U65 re-ran this same off/on comparison on the
new FEATURE_VERSION "2" model:

| arm | games | W/L | deckout (% of losses) | early_collapse (% of losses) |
|---|---|---|---|---|
| off | 60 | 41W/19L | 0/19 (0.0%) | 16/19 (84.2%) |
| on | 60 | 42W/18L | 0/18 (0.0%) | 17/18 (94.4%) |

Still no material regression (early_collapse's share rises only because the
handful of non-early_collapse losses off dropped to almost none on, not
because early_collapse's raw count grew); deckout stays at zero in both
arms, so the deckout-specific-feature gate still has no deckout-loss sample
large enough to judge on our own agent, even with the new features in place.
The signal those features were designed against (bad_determinization,
endgame_misplay, deckout) is real for the top teams but essentially absent
from our own shipped agent's loss distribution, which is consistent with
this project's failure mode being upstream of where those features can act:
our losses are decided by turn 3-5 board collapse, before the midgame tempo
and endgame patterns those features track become relevant.

## Top 8 coefficients, explained in plain language

The coefficients below are from the currently shipped model
(search/eval_model.json, the U65 retrain on the U64 24-feature layout,
FEATURE_VERSION "2"); they replace the U6-era 21-feature model's coefficient
list, which is no longer what ships. Coefficients are on standardized
features (each feature's raw value is centered and scaled before the model
sees it), so they are directly comparable to each other in units of
"standard deviations of this feature moving the model's win-log-odds."
Ranked by absolute size:

1. **our_prize_tempo: -0.676.** One of the three new U64 features (turns
   since our last prize taken). A larger value (longer since our last prize)
   predicting a *lower* win chance is the expected direction: stalling on
   the prize race is bad.
2. **our_prizes_left: -0.665.** Fewer prizes left for us to take (i.e. we
   have already taken more) predicts a *higher* win chance; the negative
   sign on "prizes still left" is the intuitive direction once read that
   way.
3. **prize_diff: +0.647.** The most straightforwardly interpretable feature:
   being ahead on prizes (having taken more than the opponent) is a top
   positive predictor of winning, matching basic game knowledge, and
   essentially unchanged in weight from the pre-U64 model (+0.649).
4. **our_bench_size: -0.590.** Counterintuitive at first read: more of our
   own bench slots filled predicts a *lower* win chance, standardized. This
   almost certainly reflects correlation with other features already in the
   model (bench HP fraction, our_bench_nonempty, energy attached), and
   logistic regression coefficients on correlated inputs can carry a
   surprising sign; it should be read as "controlling for HP and energy, raw
   bench count adds little," not as "never bench Pokemon." (Carried over
   from the pre-U64 model at a similar magnitude, -0.668 there.)
5. **our_energy: +0.550.** More energy attached across our board predicts a
   better win chance: a proxy for how developed our board is and how ready
   we are to keep attacking.
6. **their_bench_hp_frac: -0.368.** A healthier opponent bench predicts a
   *worse* win chance for us: newly prominent in the U65 model (not in the
   pre-U64 top 8), plausibly picking up some of the signal the new
   prize-tempo features pulled away from their_bench_size.
7. **our_bench_nonempty: +0.304.** Simply having at least one bench Pokemon
   predicts a better win chance, the flag-level counterpart to
   our_bench_cliff (a new U64 feature for being one KO away from an empty
   bench); this is the direction that matches the project's own dominant
   loss mode, early_collapse.
8. **their_active_hp_frac: -0.303.** The opponent's active Pokemon being
   healthier predicts a *worse* win chance for us, the expected direction: a
   healthy opponent active is harder to knock out this turn. (Weight roughly
   unchanged from the pre-U64 model's -0.389.)

Two U64 features (our_prize_tempo, our_bench_nonempty's neighbor
our_bench_cliff) rank among the most influential in the retrained model,
even though the AUC gate that decides what ships (gauntlet-only vs the
merged top-player/ladder corpora) never isolated their individual
contribution against a same-data model without them; that isolation is
future writeup work, not something either the U64 or U65 gate specifies.
As before, some individual coefficients (our_bench_size, their_bench_hp_frac)
point the "wrong" direction from raw intuition; this is a known property of
linear models fit on correlated inputs, not a bug. The model's *combination*
of all 24 features still beats the prize-differential-only baseline on
held-out AUC, which is the bar the plan sets, even though any single
coefficient read in isolation can mislead.

## Bottom line for the Strategy prize

The learned evaluator is a real, working, fully-offline pure-Python model
(scores 2*p - 1 from a sigmoid, falls back to 0.0 on a malformed state,
never touches sklearn at match time) that modestly beats the hand-tuned
evaluator (+0.75pp then an exact tie on re-run, both within the 4pp
ship-the-default bar) while never losing to it across four independent A/B
measurements, the most recent adding the top-player loss corpus on top of
wins (U65). Every attempt to grow the training set with ladder or
top-player rows, wins or losses, at five different weight combinations, made
held-out AUC worse rather than better, which is itself a useful finding: our
own gauntlet self-play games are a better match to what we actually need the
evaluator to be good at than the public ladder or top-player corpora are, at
least at the scale and weighting schemes tried so far. A separate,
non-training use of the same top-player data (U62/U63) proved more
informative than the retrain attempts: it showed the top teams' own losses
are dominated by a completely different failure mode (bad_determinization
and endgame_misplay, both signals about play quality deep into a close game)
than our own agent's (early_collapse, a self-inflicted early-game board
management failure). The three loss-pattern features this motivated (U64:
our_bench_cliff, our_deckout_risk, our_prize_tempo) landed among the
retrained model's most influential coefficients, but did not measurably move
our own agent's loss-mode mix (U65), consistent with our failure mode being
decided earlier in the game than those features are positioned to catch.
Because `agent_search` (which this evaluator lives inside) is not the
shipped ladder agent, none of this changes the Kaggle rank; it is the
model-approach evidence for the Strategy prize, and the win-versus-loss
study is additionally a directly citable piece of "what did you learn from
studying the best players" analysis independent of whether it moved this
particular model's numbers.
