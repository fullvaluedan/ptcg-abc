---
title: "feat: U9 opponent archetype detection split into U9a/U9b/U9c (addendum to combined plan v2)"
date: 2026-07-03
type: feat
status: ready
depth: standard
origin: addendum to 2026-07-02-combined-learned-eval-plan-v2.md, expands U9 in place
target_repo: ptcg-abc
---

# U9a/U9b/U9c: opponent archetype detection, split from U9

## Why

U9's bullet list assumes two things that research this iteration found do not hold.

First, "use the prediction to pick matchup-specific heuristics already scaffolded in analysis/archetype.py" has
no target to plug into. A repo-wide grep for "matchup" outside analysis/loss_classifier.py's bucket NAME and
tools/deck_match.py's gauntlet-matrix docstring turns up nothing: there is no per-archetype heuristic adjustment
mechanism anywhere in agents/ or search/. What analysis/archetype.py actually contains is (1) infer_belief /
map_archetype, a signature match that only fires once the opponent has revealed an actual distinctive card, and
(2) exactly one hardcoded fallback for the pre-reveal window, `_field_default_decklist()`, which always guesses
the single most-adopted deck (`meta_archaludon`) until a reveal happens. That static fallback is the only real
"scaffolding" U9 can extend; a classifier's entire addressable value is sharpening that one pre-reveal guess,
not replacing the signature matcher (an exact card-id match is strictly stronger evidence than any learned
classifier once a distinctive card is actually visible).

Second, "early-game observable features (first few turns' bench composition, energy types played)" do not exist
as captured features anywhere. src/ptcg_agent/features.py (U2) is deliberately generic (bench SIZE and HP
fractions, no per-Pokemon identity, no energy TYPE breakdown) since it feeds the state evaluator, not archetype
detection. Same gap shape as U8: a new featurizer and a new data-capture step are needed before anything can
train, so this splits into a prerequisite data unit exactly like U8a did.

The ground truth label, unlike U8, already exists and is proven: analysis/opponent_archetype.py's
`revealed_opponent_pokemon()` + `archetype_label()` (used today for whole-game post-hoc win/loss tallying) reads
a FINISHED replay's full set of revealed opponent Pokemon and names the archetype. U9's real, buildable shape is
therefore a distillation task: can an early-turn-only feature snapshot (turns 1..K) predict the SAME label that
only becomes obvious from the whole game. That is a legitimate silver-label setup and does not need any new
ground-truth heuristic invented.

Data check this iteration: running the existing scan_dir/archetype_label pipeline over today's 143 downloaded
ladder replays (data/replays/) yields 140 usable (non-self-play) games across 20+ distinct labels, heavily
long-tailed (top label 18 games; most labels 1-4 games; see raw counts below). This is much sparser than the
plan's "per-archetype win-rate breakdown" framing implicitly assumed. U9a must collapse long-tail labels into a
top-K-plus-other bucket (mirrors tools/archetype_select.py's own MIN_GAMES/OTHER pattern) rather than attempt a
20-way classification at n=140.

Raw label counts from data/replays (2026-07-03): Mega Abomasnow ex 18, Dragapult ex 15, Mega Lucario ex 9, Mega
Starmie ex 8, Archaludon ex 8, Meowth ex 7, Alakazam 4, Dunsparce 4, Marnie's Grimmsnarl ex 4, then a long tail
of 1-3 game labels.

## Hard constraints (inherited)
- No em dashes anywhere.
- data/training/ and data/replays/ stay gitignored; never commit or redistribute ladder replay JSON.
- Submitted agent runs fully offline; no sklearn/numpy at match time; the exported scorer must be pure Python,
  same pattern as search/learned_eval.py and search/move_prior.py.
- This entire U9 chain is TRACK S (Strategy prize, offline). It never touches agents/heuristics.py or the deck
  csv and never claims ladder progress or spends a ladder slot, per LOOP_BRIEF.md. opponent_prior() (the only
  consumer of analysis/archetype.py's belief/fallback machinery) is imported solely by agents/agent_search.py,
  not the shipped agent_heuristic, so U9c stays TRACK S regardless of its gate outcome, exactly like U8c.

## U9a: early-turn feature capture + silver-label rows (prerequisite, new)
1. Add tests/test_early_archetype_features.py first: fixed FEATURE_NAMES/N_FEATURES, a `feature_version()` drift
   guard (mirrors tests/test_learned_eval.py and imitation_features's own version-guard pattern), never-raises
   on a malformed/short replay, and a cutoff check (features computed from steps with turn > cutoff must not
   change the output versus omitting those steps entirely).
2. New module analysis/early_archetype_features.py, pure over an injected card_index/is_pokemon predicate (same
   dependency-injection shape as opponent_archetype.py so it unit-tests without the card engine). Extracts a
   fixed-length vector from steps with turn <= cutoff_turn (default 6, i.e. each seat's first three turns):
   opponent bench count seen so far, opponent revealed-Pokemon count, distinct opponent basic-energy-type count
   revealed, first-player flag, and a small set of turn-of-first-reveal indicators (first Pokemon reveal turn,
   first energy reveal turn, clamped to cutoff_turn when no reveal yet). Never raises; malformed input returns a
   zero vector of the right length, same discipline as every other extractor in this repo.
3. New tool tools/replays_to_archetype_rows.py: for each replay under data/replays (skip self-play via
   tools/scout.py's `is_self_play`), compute the silver label via the EXISTING archetype_label(
   revealed_opponent_pokemon(replay, opp_seat, is_pokemon), name_of) over the WHOLE game, and the early-turn
   feature vector via early_archetype_features over the same replay capped at cutoff_turn. Collapse any label
   with fewer than MIN_LABEL_GAMES (5) appearances into "other", mirroring tools/archetype_select.py's own
   OTHER/MIN_GAMES pattern, rather than pretending a 20+-way classification is viable at this sample size.
   Output columns: (game_id, label, *early_archetype_features.FEATURE_NAMES, source=ladder).
4. Output: data/training/archetype_rows_<date>.csv. Small companion report (reuse or extend
   tools/dataset_report.py) noting per-label row counts and the collapse-to-other count, since a below-30-row
   "other" split cannot be hidden the way it could in a 2-class balance check.
5. Commit: feat(training): U9a early-turn archetype feature capture and silver-label rows

## U9b: train and export a small classifier
1. tools/train_archetype.py, same split-by-game skeleton as tools/train_eval.py and tools/train_move_prior.py:
   `game_split()` by game_id, never by row. Logistic regression (one-vs-rest, dev-only sklearn) over the
   collapsed label set from U9a, standardized features.
2. `export_model()` writes analysis/archetype_prior.json: {feature_names, feature_version, labels (the collapsed
   class list in a fixed order), mean, std, coef, intercept}, same shape as search/eval_model.json and
   search/move_prior.json.
3. GATE: held-out top-1 accuracy must beat the majority-class baseline (always predict the modal collapsed
   label) by a stated margin on held-out games. Given n=140 total games, document this plainly as a small-sample
   result in analysis/archetype_prior_train.md (confidence interval or at minimum the raw held-out counts, not
   just a bare percentage). A below-margin result is a valid negative result, same posture as U8b/U65: document
   and stop, do not force it into U9c.
4. Commit: feat(training): U9b early-game archetype classifier trained and exported

## U9c: wire into archetype.py's pre-reveal default, gauntlet A/B gate
1. analysis/archetype.py: new pure-Python scorer module (analysis/archetype_prior_scorer.py or inlined next to
   the existing lazy `_builtin_archetypes()` cache, same lazy-load/version-check/never-raise pattern as
   search/learned_eval.py and search/move_prior.py) that loads U9b's exported JSON and scores an early-turn
   feature vector to a predicted archetype name (or None below a confidence floor).
2. `_field_default_decklist()` gains a new path behind env flag PTCG_ARCHETYPE_PRIOR (default off, same posture
   as PTCG_FIELD_PRIOR/PTCG_MOVE_PRIOR/PTCG_ABILITY): when `infer_belief` is still empty (no distinctive reveal
   yet) AND the early-turn scorer returns a confident prediction, use THAT archetype's decklist instead of the
   static `_FIELD_DEFAULT_NAME` guess. Falls back to the existing static default when the flag is off, the model
   is missing, or the scorer declines to predict.
3. GATE (from the plan, unchanged in spirit): gauntlet A/B, at least 400 games, flag on vs off, per-archetype
   win-rate breakdown recorded in analysis/archetype_detection_ab.md. Keep only if win rate does not drop (ties
   or improves), matching the flip-default posture already used for PTCG_MOVE_PRIOR and PTCG_ABILITY.
4. This wires into agent_search only (opponent_prior's sole caller, per this iteration's grep of agents/), so it
   stays TRACK S regardless of gate outcome until a future search-revival unit makes agent_search the shipped
   agent, exactly like U8c.
5. Commit: feat(search): U9c early-game archetype prior wired behind a flag, gauntlet A/B recorded

## Definition of done
- U9a/U9b/U9c each committed with passing tests and their own gate recorded in analysis/.
- analysis/archetype_prior.json + its scorer follow the exact U4/U8b pattern (version guard, never raises, no
  runtime ML dependency).
- If U9b's gate fails (a small-n classifier that cannot beat the majority-class baseline), stop there and
  document; U9c does not wire an unproven model into the pre-reveal fallback, mirroring the U8b/U8c discipline.
