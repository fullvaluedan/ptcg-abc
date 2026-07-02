---
title: "feat: learned state evaluator for ptcg-abc (replaces hand-tuned eval shaping)"
date: 2026-07-02
type: feat
status: ready
depth: deep
origin: ML review of ptcg-abc, builds on 2026-06-30-001-feat-ptcg-ai-agent-plan.md
target_repo: ptcg-abc
---

# feat: learned state evaluator (win-probability model inside determinized search)

## Summary

Replace the hand-tuned constants in search/eval.py (HP_SHAPING, ACTIVE_HP_WEIGHT, BOARD_SHAPING, ENERGY_SHAPING, bench-floor tuning) with a model trained on our own gauntlet games. The model predicts win probability from a board state. It slots into the existing rollout value function behind an env flag so the gauntlet can A/B it against the current eval. The search, heuristics, agents, and submission pipeline stay unchanged.

Model class is logistic regression first, gradient-boosted trees second. Both train in seconds on CPU, and both export to a pure-Python predictor (JSON weights plus a small scorer file) so the submission stays fully offline with zero new dependencies. No neural nets, no GPU, no sklearn inside the submission.

This is also the core of the Strategy writeup: a self-improving evaluator trained on the agent's own games, validated by measured win rate, is a defensible and original model approach (70% of the Strategy score).

## Why this and not something else

- The determinized search and forward model already work. The weakest link is the value function, which is hand-guessed numbers.
- Loss analysis already exists (analysis/loss_classifier.py). The dominant loss modes (deckout, early collapse) are exactly what a learned evaluator can weigh correctly, because the training data contains games lost those ways.
- Self-play RL or a neural policy is 10x the work for uncertain gain and hurts the offline/size constraints. Do not build those in this plan.

## Hard constraints (inherited, never violate)

- No em dashes anywhere in code, comments, docs, or commit messages.
- The submitted agent runs fully offline. The trained model ships as JSON weights plus pure-Python scoring code bundled next to main.py. No sklearn, lightgbm, numpy, or network at match time.
- Training dependencies (scikit-learn or lightgbm) are dev-only. Add them to a dev requirements file, never to the submission bundle.
- Never commit data/ or engine binaries. Training data CSVs go under data/training/ which is gitignored. Commit only the exported model JSON (small) and code.
- Stay on branch feat/phase2-learned-eval. Do not touch main.
- Every unit gates on tests passing, and integration units gate on gauntlet win rate. Never keep a change the gauntlet cannot confirm.

## Data model

One training row per non-terminal decision state, from our seat's point of view:

- features: fixed-order numeric vector extracted by a new pure module (U2)
- label: 1 if our seat won that game, 0 if lost. Drop draws and unfinished games.

Weight late-game states normally; do not oversample. Record turn number as a feature so the model learns phase-dependent value on its own.

## Feature set v1 (all computable from the observation dict we already pass to eval)

1. prize differential (theirs remaining minus ours remaining)
2. our prizes remaining, their prizes remaining (raw)
3. our deckCount, their deckCount, and the differential
4. our handCount, their handCount
5. our bench size, their bench size
6. our bench size clamped at 1 (the survival cliff, as a 0/1 feature: bench empty or not)
7. active HP fraction (ours, theirs)
8. mean bench HP fraction (ours, theirs)
9. total attached energy (ours, theirs) clamped at ENERGY_NORM
10. turn number, clamped at 40
11. whose turn it is (0/1)
12. per-turn flags for our seat: supporterPlayed, energyAttached

Keep the extractor pure and dependency-free so it ships in the submission unchanged, same pattern as heuristics.py.

## Implementation units

### U1: state-outcome logger in the gauntlet

- Add an opt-in flag to tools/gauntlet.py (env var PTCG_LOG_STATES=1 or a --log-states flag) that, during each game, appends one row per decision state for BOTH seats to data/training/states_<timestamp>.csv.
- Row format: game_id, seat, turn, feature columns (from U2 extractor), label filled in at game end.
- Buffer rows in memory per game, write after the result is known so every row gets its label in one pass.
- Gitignore data/training/.
- Tests: run a tiny 2-game gauntlet with logging on, assert the CSV exists, has both labels present, has the expected column count, and has more than 20 rows.
- Commit: feat(training): state-outcome logging in gauntlet

### U2: feature extractor module

- New file: src/ptcg_agent/features.py (mirror the import-fallback pattern used by heuristics.py so it also works flat inside a submission).
- One function: extract_features(state_dict, your_index) -> list[float], fixed order, fixed length, documented at top of file. Also FEATURE_NAMES list for the CSV header and the writeup.
- Handle missing/None fields defensively; never raise. On any malformed state return a zero vector of the right length.
- Tests: build minimal fake state dicts covering normal board, empty bench, missing fields; assert vector length is constant and values are in expected ranges.
- Commit: feat(training): pure feature extractor for state evaluation

### U3: generate the first dataset

- Run the gauntlet with logging on: current best agent vs the opponent pool, large N (target at least 2,000 games, which at roughly 82 decisions per game gives 150k+ rows per seat). Use the measured 65 games/sec raw loop if the gauntlet is too slow through env.run; if so, add a fast path that drives battle_select directly with logging.
- Deduplicate nothing; near-duplicate states are fine for these model classes.
- Sanity checks (write as a small script tools/dataset_report.py): class balance between 35 and 65 percent, no NaNs, per-feature min/max printed.
- Log a one-line summary to autoloop_status.md.
- Commit: chore(training): dataset generation fast path and report tool (data itself stays uncommitted)

### U4: train and export the model

- New dev-only script: tools/train_eval.py.
- Split by GAME, not by row (all rows from one game go to the same side of the split) to avoid leakage. 80/20 split.
- Train logistic regression (sklearn, dev-only dependency) with standardized features. Report test-set AUC and accuracy. Baseline to beat: a single-feature model using prize differential only. The full model must beat that baseline on AUC or the unit fails.
- Export to search/eval_model.json: feature names, means, stds, coefficients, intercept. Nothing else.
- New file search/learned_eval.py: pure Python, no deps. Loads the JSON, computes sigmoid(w·x_standardized + b), returns win probability in [0,1]. Same import-fallback pattern as the rest of search/.
- Map probability to the existing value scale: value = 2*p - 1 so it is drop-in compatible with WIN=1.0, LOSS=-1.0. Terminal results still short-circuit to exact WIN/LOSS/DRAW before the model is consulted; the model only scores non-terminal rollout cutoffs.
- Tests: predictor loads the committed JSON, returns values in [-1,1], terminal states bypass it, malformed state returns 0.0 not an exception.
- Commit: feat(search): learned evaluator, trained and exported

### U5: integrate behind a flag and A/B in the gauntlet

- In search/eval.py, add env switch PTCG_LEARNED_EVAL=1 that routes non-terminal scoring to learned_eval, otherwise the existing shaping runs unchanged.
- Gauntlet A/B: same agent, same opponents, same N (at least 400 games per arm), one arm with the flag on, one off. Record both win rates and the difference in analysis/learned_eval_ab.md.
- GATE: keep the learned eval as default only if it beats the hand-tuned eval by a margin larger than noise (rule of thumb at N=400 per arm: at least 4 percentage points). If it loses or ties, keep the flag off, write up why in analysis/, and proceed to U6 anyway (a negative result is still writeup material).
- If it wins: flip the default, rebuild the submission with tools/build_submission.py, verify test_shipped_config.py and test_grader_submission.py pass with eval_model.json and learned_eval.py bundled, then submit per the existing one-per-iteration policy.
- Commit: feat(search): learned eval behind flag plus A/B result

### U6: retrain loop and loss-mode check

- Regenerate data with the improved agent playing (fresh gauntlet run with logging), retrain, re-export, re-run the A/B. One retraining generation is enough for this plan; do not loop indefinitely.
- Run analysis/loss_classifier.py on fresh ladder replays. Compare deckout and early_collapse loss rates before vs after. Record in analysis/learned_eval_loss_modes.md.
- Add deckout-specific features ONLY if deckout losses did not drop: our deckCount as a fraction, and turns-until-self-deckout estimate. Retrain once with them if triggered.
- Commit: feat(training): retraining generation and loss-mode validation

### U7: Strategy writeup section

- Draft docs/writeup/learned_evaluator.md covering: motivation (hand-tuned shaping replaced by data), data generation (self-generated gauntlet games, N games, N rows), model choice and why (offline, tiny, interpretable coefficients), leakage control (game-level split), the A/B methodology and numbers, and the loss-mode before/after table.
- Include the top 8 coefficients with plain-language interpretation. Interpretability is a scoring asset.
- Commit: docs(writeup): learned evaluator section

## Later, only if U5 wins clearly (do not build now)

- GBT upgrade: train lightgbm, export trees to JSON, write a pure-Python tree walker. Try only if logistic regression wins its A/B but AUC is under 0.72.
- Move-ranking model (policy prior) to order candidate first moves and prune rollouts. Bigger win, bigger job. Separate plan.

## Definition of done

- U1 through U7 committed on feat/phase2-learned-eval, all tests green.
- analysis/learned_eval_ab.md contains a win-rate A/B with N of at least 400 per arm.
- Submission bundle verified offline-clean with the model files included (or the flag off with a documented negative result).
- Writeup section drafted.
