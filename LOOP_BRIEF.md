# Unattended autoloop brief: ptcg-abc (Pokemon TCG AI Battle Challenge)

You are an autonomous worker running UNATTENDED in a loop. A shell driver invokes
you once per iteration. Do ONE coherent increment of progress this run, then stop.
The driver calls you again for the next increment. There is no human to ask, so make
the best decision and proceed. Full autonomy was authorized by the user.

## Project
- Repo: C:\Users\danom\ptcg-abc  (work on branch feat/phase1-baseline; commit there)
- Plan: docs/plans/2026-06-30-001-feat-ptcg-ai-agent-plan.md (read it; it is the source of truth)
- Status so far: U1, U2, U3 are built, tested, and committed. Continue from U4 onward.
- Venv python: .venv/Scripts/python.exe   Tests: python -m pytest tests -q
- Gauntlet: python tools/gauntlet.py <agent> <opponents...> -n <N>
- Build submission: python tools/build_submission.py

## What to do THIS iteration (one increment, then stop)
1. Read the plan and run git log --oneline to find the next undone implementation unit.
2. Implement that unit following the plan, using the ce-work skill. Mirror the existing
   patterns in src/, agents/, tools/. Write or update tests.
3. Run the tests. They must pass before you commit.
4. Use the code-review skill on your diff and apply safe, verified fixes.
5. If tests fail and you cannot quickly fix them, use the ce-debug skill to find the
   root cause, then fix.
6. If you find the plan is wrong or incomplete, use the ce-plan skill to update only the
   relevant unit.
7. Commit each green unit locally with a clean conventional message. Stage only that
   unit's files, never git add -A.
8. Submission policy (full autonomy): if the unit yields an agent that MEASURABLY beats
   the current best agent in the gauntlet (confirm with tools/gauntlet.py), and it is
   heuristic level or stronger, build the submission and submit with the kaggle CLI. At
   most ONE Kaggle submission per iteration, never an agent that did not beat the current
   best, and respect the 5 per day quota (if today's budget is spent, skip and keep building).

## Hard constraints (never violate)
- No em dashes anywhere in code, comments, docs, or commit messages.
- The submitted agent must run fully offline. No network or API calls at match time.
- Keep competition data isolated: never commit data/ or the cg engine binaries, never
  redistribute competition data.
- Any LLM API keys (council) come from environment variables only. Never hardcode a key.
  If a key is missing, skip that step.
- Stay on branch feat/phase1-baseline. Do not touch main.

## Logging
- Append one or two lines to autoloop_status.md: the unit you advanced, the test result,
  whether you submitted, and what is next.

## Stop condition for THIS run
- After one coherent increment (a committed unit, or a clearly bounded chunk of one),
  STOP and end your turn. Do not try to build the whole project in one run.
