---
title: "feat: U8 move-ordering model split into U8a/U8b/U8c (addendum to combined plan v2)"
date: 2026-07-03
type: feat
status: ready
depth: standard
origin: addendum to 2026-07-02-combined-learned-eval-plan-v2.md, expands U8 in place
target_repo: ptcg-abc
---

# U8a/U8b/U8c: move-ordering model (policy prior), split from U8

## Why

U8's bullet list assumes "Reuses U1-U3b data" is free. Research this iteration found it is not: U1's gauntlet
state logger (tools/gauntlet.py `_StateLogger.wrap`) captures `move` locally but discards it, only persisting
features+label to CSV; U3b's replay converter (tools/replays_to_rows.py `rows_from_replay`) has the same gap,
reading the replay step but never storing which option index the eventual winner chose or how many candidates
existed. The candidate-move / chosen-move schema does not exist in any current CSV and must be built first.
Splitting into three sub-units mirrors how U62-U65 split cleanly into mining / study / feature+retrain, so each
piece passes its own gate independently rather than one large, uncommittable unit.

Also found: agents/imitation_features.py already contains a working, documented per-option feature vector
(FEATURE_NAMES, ~30 features: option-type one-hots, card-type crosses, a card_effects tag multi-hot) built for
an EARLIER, now-parked plan (docs/plans/2026-07-02-001-feat-unified-number-one-plan.md, units U40/U41, a
top-player pairwise ranker). It was preserved as WIP in commit 733add5 ("preserve U40 imitation featurizer WIP
before phase2 pivot") before this repo pivoted to the combined-learned-eval-plan-v2 track, and was never
trained, exported, or tested (no tests/test_imitation_features.py exists today). Its featurizer is a clean fit
for U8's "classifier that scores candidate moves" requirement: U8a REUSES
`agents.imitation_features.option_features` / `decision_features` directly rather than re-deriving a second
per-option feature vector, after adding test coverage for it. Do NOT revive U41/U42 (the pairwise-ranker
training/scoring modules the parked plan sketched but never built); U8b/U8c build training/export/scoring
fresh, against U8a's own row schema, following the U4 JSON-export pure-Python-scorer pattern instead.

## Hard constraints (inherited)
- No em dashes anywhere.
- data/training/ and data/replays/ stay gitignored.
- Submitted agent runs fully offline; no sklearn/numpy at match time; search/move_prior.py must be pure Python,
  same pattern as search/learned_eval.py.
- This entire U8 chain is TRACK S (Strategy prize, offline). It never touches agents/heuristics.py or the deck
  csv and never claims ladder progress or spends a ladder slot, per LOOP_BRIEF.md.

## U8a: candidate-move + chosen-move data capture (prerequisite, new)
1. Add tests/test_imitation_features.py first: pin FEATURE_NAMES/N_FEATURES, `decision_features()` returns
   None for <=1 option and len(options) rows of length N_FEATURES otherwise, `option_features()` never raises
   on a malformed obs/opt, and a `feature_version()` drift check (mirrors tests/test_learned_eval.py's own
   version-guard test pattern).
2. tools/gauntlet.py `_StateLogger.wrap()`: where `move` is currently captured then discarded, when the
   decision has more than 1 option, call `agents.imitation_features.decision_features(obs)` and buffer one row
   per option (game_id, seat, turn, decision_id, n_options, option_index, is_chosen 0/1, *feature row, source).
   Emit ALL candidate rows per decision, not just the chosen one: a within-decision ranker needs the
   non-chosen options from the SAME decision as negatives, not just positives across decisions. At
   `flush_game` time, keep only decisions belonging to the eventual winner's seat (mirror the existing
   winner-seat bookkeeping already used for the label column), matching U8's own spec ("which candidate move
   the eventual winner chose").
3. tools/replays_to_rows.py `rows_from_replay()`: same schema addition, reading `obs["select"]["option"]` and
   `entry.get("action")` (proven present via analysis/loss_classifier.py `parse_replay`, ~line 175) as the
   chosen index, gated to winner-seat decisions only, same is_chosen-per-option-row format.
4. Output: data/training/move_rows_<date>.csv, columns (game_id, seat, decision_id, n_options, option_index,
   is_chosen, *imitation_features.FEATURE_NAMES, source). Extend tools/dataset_report.py (or add a small
   companion check) for class balance (is_chosen is naturally ~1/n_options positive) and decision_id
   uniqueness within a game.
5. Commit: feat(training): U8a move-ordering candidate/chosen-move data capture

## U8b: train and export the move-ordering model
1. tools/train_move_prior.py, same load/split/export skeleton as tools/train_eval.py: `game_split()` by
   game_id (never by row, same leakage guard as U4). Fit target is `is_chosen` over the pooled option rows
   (each option row is one training example); this is the plan's own "logistic regression, one-vs-rest or a
   simple ranking score" simplification, not a true listwise ranker.
2. `export_model()` writes search/move_prior.json: {feature_names (imitation_features.FEATURE_NAMES),
   feature_version (imitation_features.feature_version()), mean, std, coef, intercept}, same shape as
   search/eval_model.json.
3. GATE: held-out top-1 accuracy (does the model's argmax option match is_chosen within its decision_id group)
   must beat the random-baseline mean(1/n_options) rate by a stated margin on held-out games; record in
   analysis/move_prior_train.md. A below-margin result is a valid negative result, same posture as U65's
   sweep: document and stop, do not force it into U8c.
4. Commit: feat(training): U8b move-ordering model trained and exported

## U8c: pure-Python scorer, search wiring, ladder-scale A/B gate
1. search/move_prior.py: same lazy-load/version-check/never-raise pattern as search/learned_eval.py, scoring a
   list of option feature rows (from `imitation_features.decision_features`) to a list of scores.
2. search/rollout.py `search_decision()`: behind a new env flag PTCG_MOVE_PRIOR (default off, same posture as
   PTCG_LEARNED_EVAL and PTCG_ABILITY), reorder `range(n)` by move_prior score before the existing
   per-candidate rollout loop. Ordering-only change first; a top-K evaluation cap is a separate, higher-risk
   follow-on the plan does not require for U8's gate.
3. GATE (from the plan, unchanged): gauntlet A/B on search speed (nodes/decisions per second) AND win rate, at
   least 400 games. Keep only if win rate does not drop and speed improves, or win rate improves outright.
4. This wires into agent_search, NOT agent_heuristic; per LOOP_BRIEF.md this stays TRACK S regardless of gate
   outcome (agent_search has been ladder-negative, 514.7 vs the 569.6 king) until a future search-revival unit
   makes agent_search the shipped agent.
5. Commit: feat(search): U8c learned move ordering wired behind a flag, gauntlet A/B recorded

## Definition of done
- U8a/U8b/U8c each committed with passing tests and their own gate recorded in analysis/.
- search/move_prior.json + search/move_prior.py follow the exact U4 / learned_eval.py pattern (version guard,
  never raises, no runtime ML dependency).
- If U8b's gate fails, stop there and document; U8c does not proceed on an unproven model (mirrors the Phase
  gate discipline already used for U5 and U65).
