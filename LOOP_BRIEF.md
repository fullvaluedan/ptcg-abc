# Unattended autoloop brief: ptcg-abc (Pokemon TCG AI Battle Challenge)

You are an autonomous worker running UNATTENDED in a loop. A shell driver invokes
you once per iteration. Do ONE coherent increment of progress this run, then stop.
The driver calls you again for the next increment. There is no human to ask, so make
the best decision and proceed. Full autonomy was authorized by the user.

## Project
- Repo: C:\Users\danom\ptcg-abc  (work on branch feat/phase2-learned-eval; commit there)
- Plan: docs/plans/2026-07-02-002-feat-learned-evaluator-plan.md (READ IT; it is the source of truth)
- Status: starting from U1. Execute U1 -> U7 IN ORDER, one unit per iteration.
- Venv python: .venv/Scripts/python.exe   Tests: python -m pytest tests -q
- Gauntlet: python tools/gauntlet.py <agent> <opponents...> -n <N>
- Build submission: python tools/build_submission.py

## What to do THIS iteration (one increment, then stop)
ROADMAP: Execute docs/plans/2026-07-02-002-feat-learned-evaluator-plan.md. READ IT FIRST; it is the source
of truth. Goal: replace the hand-tuned constants in search/eval.py with a learned win-probability model
trained on our own gauntlet games, shipped as JSON weights plus a pure-Python scorer (fully offline, no new
deps at match time). It is also the core Strategy-prize writeup (a self-improving evaluator trained on the
agent's own games, validated by measured win rate).

Execute the units IN ORDER, one coherent increment per iteration, do not skip ahead:
  U1 state-outcome logger in tools/gauntlet.py (opt-in flag, one row per decision state per seat, labelled
     at game end; data/training/ gitignored).
  U2 pure feature extractor src/ptcg_agent/features.py (fixed-order vector + FEATURE_NAMES, never raises,
     zero-vector on malformed; mirror the heuristics.py import-fallback so it ships flat).
  U3 generate the first dataset (>=2000 games vs the pool with logging on; tools/dataset_report.py sanity
     checks: class balance 35-65%, no NaNs, per-feature min/max).
  U4 train + export: tools/train_eval.py (dev-only sklearn), split by GAME not row (80/20), logistic
     regression, must beat the prize-diff-only baseline on AUC or the unit FAILS; export search/eval_model.json;
     pure search/learned_eval.py returns value = 2*p-1, terminal states short-circuit before the model.
  U5 integrate behind PTCG_LEARNED_EVAL=1 in search/eval.py + gauntlet A/B (>=400 games/arm), record in
     analysis/learned_eval_ab.md. GATE: keep the learned eval as default only if it beats hand-tuned by >4pp.
     A negative result is still writeup material; proceed to U6 either way. (Submission handling: see the
     SUBMISSION note below before spending any ladder slot.)
  U6 retrain generation + loss-mode check (regenerate with the improved agent, retrain once, re-run the A/B;
     run analysis/loss_classifier.py before/after on deckout + early_collapse; add deckout features ONLY if
     deckout losses did not drop).
  U7 Strategy writeup docs/writeup/learned_evaluator.md (motivation, data gen, model choice, leakage control,
     A/B methodology + numbers, loss-mode before/after table, top-8 coefficients interpreted).

Each unit gates on tests passing; integration units (U5, U6) gate on gauntlet win rate. Never keep a change
the gauntlet cannot confirm. Do NOT build the GBT upgrade or a policy/move-ranking model in this plan (both
are explicitly deferred).

CONTEXT (accurate, not a blocker): search/eval.py feeds agent_search, which is NOT the shipped ladder agent
(agent_heuristic ships, and search has been ladder-negative: 514.7 vs 569.6). So a U5 win improves the
OFFLINE search and is strong Strategy-writeup material; it only reaches the ladder if a later search-revival
makes agent_search the shipped agent. Build and flag the learned eval per the plan regardless (it is gated
and reversible behind PTCG_LEARNED_EVAL).

## SUBMISSION note (protect the scarce resource)
- Do the offline work fully. But DO NOT spend a ladder slot on a search-eval build while agent_heuristic is
  the shipped king: a search/eval.py change cannot move the shipped heuristic's ladder score, and settled
  submission slots are the binding resource (few remain before the 16 Aug final). Record the U5/U6 offline
  A/B result as the deliverable and writeup material; queue the ladder submit ONLY if a search-revival has
  made agent_search the shipped agent.
- BEFORE any submit run .venv/Scripts/kaggle.exe competitions submissions -c pokemon-tcg-ai-battle. Never
  submit a build already on the ladder or one that is not a verified improvement. One submission per
  iteration max, respect the 5/day quota, keep the ledger in autoloop_status.md.

Mechanical process each iteration: implement one coherent increment with ce-work, mirror existing patterns,
write/update tests (must pass), code-review the diff and apply safe fixes, ce-debug on failures, commit each
green step (stage only that step's files, never git add -A).

## Hard constraints (never violate)
- No em dashes anywhere in code, comments, docs, or commit messages.
- The submitted agent runs fully offline. The trained model ships as JSON weights plus pure-Python scoring
  bundled next to main.py. No sklearn/lightgbm/numpy/network at match time. Training deps (scikit-learn) are
  dev-only, in a dev requirements file, never in the submission bundle.
- Keep competition data isolated: never commit data/ or the cg engine binaries, never redistribute. Training
  CSVs go under data/training/ (gitignored); commit only the exported model JSON (small) and code.
- Any LLM API keys come from environment variables only. Never hardcode a key.
- Stay on branch feat/phase2-learned-eval. Do not touch main.
- The grader loads main.py via exec() with NO __file__ (guard every repo-relative path with
  if "__file__" in globals()); the entrypoint must be the LAST callable defined; the agent must never raise;
  the native engine is a process-global singleton (sequential matches). tests/test_grader_submission.py
  gates every build.

## Logging
- Append one or two lines to autoloop_status.md: the unit you advanced, the test/gauntlet result, whether
  you submitted, and what is next.

## Stop condition for THIS run
- After one coherent increment (a committed unit, or a clearly bounded chunk of one), STOP and end your turn.
  Do not try to build the whole plan in one run.
