---
title: "feat: learned state evaluator + ladder replays + follow-on ML units (ptcg-abc)"
date: 2026-07-02
type: feat
status: ready
depth: deep
origin: ML review of ptcg-abc, builds on 2026-06-30-001-feat-ptcg-ai-agent-plan.md
target_repo: ptcg-abc
---

# feat: learned state evaluator, ladder replay training data, follow-on ML units

## Summary

Phase A replaces hand-tuned constants in search/eval.py with a model trained on our games plus public ladder replays (unchanged from prior plan, units U1-U7). Phase B adds five follow-on ML upgrades, only started after Phase A ships and its A/B gate passes: move ordering, opponent deck detection, top-bot loss mining, an eval ensemble, and confidence-based search time allocation.

Every unit exports pure-Python, offline, no new runtime dependencies. Training deps stay dev-only.

## Hard constraints (never violate)

- No em dashes anywhere in code, comments, docs, or commit messages.
- Submitted agent runs fully offline. No sklearn, lightgbm, numpy, or network at match time. Models ship as JSON plus pure-Python scoring code.
- Training deps are dev-only, never in the submission bundle.
- Never commit data/ or engine binaries. data/training/ and data/replays/ are gitignored.
- Ladder replay JSON is never committed or redistributed. Kaggle token stays at ~/.kaggle/access_token.
- Stay on branch feat/phase2-learned-eval for Phase A, feat/phase3-followon for Phase B. Do not touch main.
- Every unit gates on tests passing. Integration units gate on gauntlet win rate. Never keep a change the gauntlet cannot confirm.
- After each unit, write a short plain-language note in autoloop_status.md explaining what was learned and why the gate passed or failed, so a coding novice can follow along.

---

## PHASE A: learned evaluator (unchanged from prior plan)

### U1: state-outcome logger in the gauntlet
- Opt-in flag on tools/gauntlet.py (PTCG_LOG_STATES=1 or --log-states). Logs one row per decision state per seat to data/training/states_<timestamp>.csv with game_id, seat, turn, features, source=gauntlet, label filled at game end.
- Tests: 2-game run with logging on, both labels present, expected column count, more than 20 rows.
- Commit: feat(training): state-outcome logging in gauntlet

### U2: feature extractor module
- src/ptcg_agent/features.py, same import-fallback pattern as heuristics.py.
- extract_features(state_dict, your_index) -> list[float], fixed order and length. FEATURE_NAMES list included.
- Features: prize differential, prizes remaining (both), deckCount (both, and diff), handCount (both), bench size (both), bench-empty flag, active HP fraction (both), mean bench HP fraction (both), attached energy (both, clamped), turn number (clamped 40), whose turn, our supporterPlayed/energyAttached flags.
- Never raises; malformed state returns a zero vector of the right length.
- Tests: normal board, empty bench, missing fields, constant length.
- Commit: feat(training): pure feature extractor for state evaluation

### U3: generate the first gauntlet dataset
- Gauntlet run with logging on, at least 2,000 games.
- tools/dataset_report.py: class balance 35-65 percent, no NaNs, per-feature min/max, counts per source.
- Commit: chore(training): dataset generation fast path and report tool

### U3a: ladder episode downloader
- tools/harvest_replays.py, Kaggle API, competition pokemon-tcg-ai-battle, downloads to data/replays/<episode_id>.json, skips existing files, flags --max-episodes (default 200) and --sleep (default 1.0s).
- Reuses parsing helpers from analysis/loss_classifier.py.
- Synthetic fixture replay under tests/fixtures/ (never real competition data).
- Commit: feat(training): ladder replay downloader

### U3b: replay-to-rows converter
- tools/replays_to_rows.py: per seat, per decision state, extract_features plus that seat's final result. Drop draws/errors. Output data/training/ladder_rows_<timestamp>.csv, source=ladder.
- GATE: if ladder class balance is outside 30-70 percent, downsample the majority class.
- Commit: feat(training): replay-to-rows converter with source tagging

### U4: train and export the model
- tools/train_eval.py, --sources default gauntlet,ladder. Split by GAME (not row), 80/20.
- Logistic regression (sklearn, dev-only), standardized features. Report AUC and accuracy. Must beat a prize-differential-only baseline.
- Train gauntlet-only and gauntlet-plus-ladder variants, compare AUC on a held-out gauntlet-only test set.
- GATE: keep merged model only if its AUC on gauntlet-only test data is at least equal to gauntlet-only model's. Document either way in analysis/ladder_data_ab.md.
- Export search/eval_model.json (feature names, means, stds, coefficients, intercept) and search/learned_eval.py (pure Python sigmoid scorer, value = 2*p - 1, terminal results bypass it, malformed state returns 0.0).
- Commit: feat(search): learned evaluator, trained and exported

### U5: integrate behind a flag and A/B in the gauntlet
- PTCG_LEARNED_EVAL=1 env switch in search/eval.py.
- A/B: at least 400 games per arm, flag on vs off. Record in analysis/learned_eval_ab.md.
- GATE: keep as default only if it beats hand-tuned eval by at least 4 percentage points at N=400/arm. Otherwise keep flag off, document why, continue.
- If it wins: rebuild submission, verify test_shipped_config.py and test_grader_submission.py pass, submit per the one-per-iteration policy.
- Commit: feat(search): learned eval behind flag plus A/B result

### U6: retrain generation and loss-mode check
- One retrain generation using the improved agent's games. Re-run A/B.
- Compare deckout/early_collapse loss rates before vs after using analysis/loss_classifier.py, record in analysis/learned_eval_loss_modes.md.
- Add deckout-specific features only if deckout losses did not improve; retrain once if triggered.
- Commit: feat(training): retraining generation and loss-mode validation

### U7: Strategy writeup section
- docs/writeup/learned_evaluator.md: motivation, data sources, model choice, leakage control, A/B methodology and numbers, loss-mode table, top 8 coefficients explained in plain language.
- Commit: docs(writeup): learned evaluator section

GATE for Phase A as a whole: U5's A/B must show the learned eval at least matching the hand-tuned eval (win or documented tie) before Phase B starts. If it clearly loses, stop and revisit feature set before building Phase B.

---

## PHASE B: follow-on ML units (start only after Phase A gate passes)

Branch: feat/phase3-followon (new branch off main after Phase A merges).

### U8: move-ordering model (policy prior)
- Biggest remaining upgrade. Reuses U1-U3b data: at each decision, record which candidate first move the eventual winner chose.
- Train a classifier (logistic regression, one-vs-rest or a simple ranking score) that scores candidate moves; search tries high-scored moves first.
- Export search/move_prior.json plus pure-Python scorer, same pattern as U4.
- GATE: gauntlet A/B on search speed (nodes/decisions per second) AND win rate, at least 400 games. Keep only if win rate does not drop and speed improves, or win rate improves outright.
- Commit: feat(search): learned move ordering, trained and exported

### U9: opponent deck/archetype detection
- Extends existing analysis/opponent_archetype.py. Train a small classifier on early-game observable features (first few turns' bench composition, energy types played) to predict opponent archetype.
- Use the prediction to pick matchup-specific heuristics already scaffolded in analysis/archetype.py.
- GATE: gauntlet A/B, at least 400 games, per-archetype win rate breakdown in analysis/archetype_detection_ab.md.
- Commit: feat(agents): opponent archetype detection and matchup adjustment

### U10: top-bot loss mining
- tools/harvest_replays.py gains a filter for episodes where a high-rated bot lost. Run loss_classifier.py on that subset only.
- Produce analysis/top_bot_loss_patterns.md: which loss buckets are most common among strong bots, and whether our agent shares those failure modes.
- No model training in this unit; it is a research unit that may generate new features or heuristics for a future unit.
- Commit: docs(analysis): top-bot loss mining report

### U11: eval ensemble
- Combine learned_eval.py and the existing hand-tuned search/eval.py as a weighted average instead of an on/off flag.
- New env var PTCG_EVAL_BLEND (0.0 = hand-tuned only, 1.0 = learned only, default from U5's A/B winner).
- Sweep blend weights (0.0, 0.25, 0.5, 0.75, 1.0) in the gauntlet, at least 200 games per weight, record the win-rate curve in analysis/eval_blend_sweep.md.
- GATE: keep the blend only if the best weight beats both pure endpoints. Otherwise keep the U5 winner unchanged.
- Commit: feat(search): eval ensemble with blend sweep

### U12: confidence-based search time allocation
- When the model's win-probability estimate is near 0.5 (uncertain), spend more of the search time budget on that decision; when it is near 0 or 1 (confident), spend less.
- Modify search/timebudget.py to accept a confidence signal from learned_eval.py.
- GATE: gauntlet A/B on win rate AND overage-bank usage (must not increase average bank spend), at least 400 games. Record in analysis/confidence_budget_ab.md.
- Commit: feat(search): confidence-based time allocation

## Definition of done

Phase A: U1-U7 committed on feat/phase2-learned-eval, all tests green, A/B and ladder comparisons recorded, submission verified offline-clean, writeup drafted.

Phase B: as many of U8-U12 as time allows, each with its own passing gate recorded in analysis/. Skip a unit rather than ship one that fails its gate.
