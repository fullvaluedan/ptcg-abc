# Unattended autoloop brief: ptcg-abc (Pokemon TCG AI Battle Challenge)

You are working UNATTENDED in the ptcg-abc repo, invoked once per iteration by a shell driver.
Do ONE increment, then STOP. Full autonomy authorized.

SOURCE OF TRUTH: docs/plans/2026-07-02-combined-learned-eval-plan-v2.md
Read it fully before doing anything.

## RESUME STATE (2026-07-02, read this first)
Done: U1-U5, U3a/U3b/U3c, U4 ladder-merge, the top-player WIN corpus (173k rows), and U6 tooling (multi-source
retrain merge + loss-mode measurement).

NEXT UNIT IS U60 (parallel gauntlet), from
docs/plans/2026-07-02-003-feat-offline-match-scale-topplayer-mining-plan.md. Build it BEFORE running the U6
retrain: it fans the gauntlet across worker subprocesses (min(cores-2, 16)), each with its OWN temp state-log
CSV, a shard-namespaced game_id (shard<k>:<i>), and a DISTINCT seed; the parent merges and dedupes by game_id.
Mirror the subprocess fan-out in tools/cem_tune.py. Every A/B after it (the U6 run, U65) then settles in
minutes instead of ~30. U61 (raw-engine fast path) stays DEFERRED unless the measured U60 rate still binds.

Order after U60:
1. Run U6 (multi-source retrain: gauntlet + ladder + top_player win, weighted; loss-mode check) VIA
   parallel_gauntlet, then U7 writeup, then the Phase A gate.
2. U62 (top-player LOSS corpus: top team as the LOSING seat, source=top_player_loss, with loss_bucket +
   opponent) then U63 (the how-the-best-teams-win-vs-lose study). U63 SUPERSEDES the learned-eval Phase B U10
   (top-bot loss mining), so drop U10.
3. U64 (append + version loss-pattern features: bench-cliff, deckout-risk, prize tempo) and U65 (enriched
   retrain with the win corpus, the loss corpus as weighted NEGATIVE signal, and the U64 features; keep only if
   held-out AUC holds and no loss bucket worsens). U64 and U65 SHIP TOGETHER: a feature-length change
   invalidates search/eval_model.json, so re-verify tests/test_grader_submission.py.
4. Then Phase B (U8, U9, U11, U12).

Two plans live on this branch: U1-U12 in docs/plans/2026-07-02-combined-learned-eval-plan-v2.md, U60-U65 in
docs/plans/2026-07-02-003-feat-offline-match-scale-topplayer-mining-plan.md. Use the U-ID in each commit to
find the right spec.

## Project
- Repo: C:\Users\danom\ptcg-abc   Branch: feat/phase2-learned-eval (Phase A); feat/phase3-followon (Phase B). Never touch main.
- Venv python: .venv/Scripts/python.exe   Tests: python -m pytest tests -q
- Gauntlet: python tools/gauntlet.py <agent> <opponents...> -n <N>   Build: python tools/build_submission.py
- Kaggle: .venv/Scripts/kaggle.exe ; token at ~/.kaggle/access_token (never in code or logs)

## SETUP (guard once at the start of a run)
1. Ensure on branch feat/phase2-learned-eval (Phase A) or feat/phase3-followon (Phase B); create off HEAD if missing.
2. Confirm data/training/ and data/replays/ are gitignored (data/ is already ignored, which covers both).

## EACH ITERATION (one increment, then stop)
1. git log --oneline to find the last completed unit. Order NOW (honor the RESUME STATE above): U60 is next,
   then finish U6, U7, the Phase A gate, then U62, U63, then U64+U65 (ship together), then Phase B
   (U8, U9, U11, U12; U10 is replaced by U63). Unit specs live in the two plan docs named in the RESUME STATE.
2. Implement the NEXT undone unit exactly as the plan specifies. Mirror existing patterns in src/, agents/, search/, tools/.
3. Write or update that unit's tests. Run python -m pytest tests -q. Must pass before committing.
4. Review your own diff; apply only safe, verified fixes.
5. Commit ONLY that unit's files (never git add -A) with the exact commit message from the plan.
6. Append to autoloop_status.md: unit advanced, test result, gate pass/fail, whether you submitted, what is next.
7. TEACH AS YOU GO: in the same autoloop_status.md entry, add 3-5 plain-language sentences explaining what
   this unit taught (e.g. what AUC means, what the gate result implies) for a coding novice. No jargon
   without a one-line definition.
8. STOP. Do not start the next unit.

## PHASE GATE
Before starting U8, confirm Phase A's definition of done is met: U1-U7 committed, U5's A/B recorded with the
learned eval at least matching the hand-tuned eval (win or documented tie), submission verified offline-clean,
writeup drafted. If not met, do not start Phase B; keep working Phase A. If U5 clearly loses, stop and revisit
the feature set before Phase B.

## SUBMISSION (protect the scarce resource)
- At most ONE Kaggle submission per iteration, only if the new agent MEASURABLY beats the current best,
  respecting the 5/day quota. Board-check FIRST: .venv/Scripts/kaggle.exe competitions submissions -c
  pokemon-tcg-ai-battle. Never resubmit a build already on the ladder. Keep the ledger in autoloop_status.md.
- search/eval.py and the Phase B search upgrades feed agent_search, which is NOT the shipped ladder agent
  (agent_heuristic ships; search has been ladder-negative, 514.7 vs 569.6). So these units improve the OFFLINE
  search and the Strategy writeup (70% of the Strategy score); they only reach the ladder once a search-revival
  makes agent_search the shipped agent. Treat the gauntlet/offline A/B as the deliverable; do NOT spend a
  scarce ladder slot on a search-side build while agent_heuristic is the king.

## HARD RULES (never break)
- No em dashes anywhere in code, comments, docs, or commit messages.
- Submitted agent runs fully offline. No sklearn/lightgbm/numpy/network at match time. Models ship as JSON plus
  a pure-Python scorer next to main.py. Training deps (scikit-learn) are dev-only, never in the submission bundle.
- Never commit data/ or engine binaries. Never commit or redistribute ladder replay JSON. data/training/ and
  data/replays/ are gitignored.
- The grader loads main.py via exec() with NO __file__ (guard every repo-relative path with
  if "__file__" in globals()); the entrypoint must be the LAST callable defined; the agent must never raise;
  the native engine is a process-global singleton (sequential matches). tests/test_grader_submission.py gates
  every build.
- Respect every GATE in the plan. A failed gate means document it and move on, not force the change in.
- Any LLM API keys come from environment variables only. Never hardcode a key.

## Stop condition for THIS run
After one coherent increment (a committed unit, or a clearly bounded chunk of one), STOP and end your turn.
