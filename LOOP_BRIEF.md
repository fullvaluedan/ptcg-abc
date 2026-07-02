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
ROADMAP: Execute the plan at docs/plans/2026-07-01-001-feat-self-improving-agent-plan.md. READ IT; it is
the source of truth for HOW we climb toward #1. Its core reframe is proven by our own ladder data and
supersedes the old "strengthen the search agent" directive:

- The determinized SEARCH agent COSTS points on the ladder (search-active 514.7 vs the heuristic's 569.6
  on the same deck; see analysis/ladder_scored_pair_reclaim.md). So do NOT try to make the shipped agent
  the search agent, and do NOT re-walk the refuted search levers.
- The fast HEURISTIC pilot (agents/heuristics.py) is the PLAYER. The search stack is an OFFLINE TEACHER,
  used only to generate labels and validate ideas. OPTIMIZE THE PILOT.
- The LADDER A/B is the only ground truth. Offline gauntlets only FILTER, never decide.

Execute the phases IN ORDER, one coherent increment per iteration, and do not skip ahead:
  P0 (reclaim, U1): get our two best HEURISTIC builds into the latest-two-scored pair. Board-check first.
  P1 (self-preservation pilot + deck, U2+U3): put the bench-width + deckout-risk term in the PILOT's move
     ordering in agents/heuristics.py (NOT the search leaf, where it is structurally squeezed), coupled
     with a higher-basic-density deck so the guard has something to develop. SHIP THEM TOGETHER. Gate:
     board-out < ~35% offline AND ladder A/B beats 569.6.
  P2 (self-improvement engine, U4+U5+U6): U4 POPULATE the frozen + episode-dataset opponent pool in
     tools/opponents.py (EMPTY today; a blocker, or CEM overfits into a self-beater), U5 the held-out
     real-games move-ranking validator, U6 the CEM optimizer over the pilot+eval weight vector
     (injected-variance regularization each iteration is NON-NEGOTIABLE). Fitness = beat the diverse pool
     and match real top-player moves, NEVER beat-myself. Gate every candidate on ladder A/B.
  P3 (GATED search revival, U7 then U8+U9): run the Long et al. determinization diagnostic FIRST (U7);
     ONLY if favorable, U8 reach-probability-weighted determinization + a shallow opponent policy, and U9
     more-worlds-shallower + EPIMC. Keep the tuned heuristic as the LIVE fallback throughout.
  P4 (optional, U10+U11): self-play data gen then a numpy value-net leaf, only after CEM plateaus.

Two gaps to open first (both blockers): move the self-preservation term into agents/heuristics.py, and
populate the opponent pool. Any learned component ships as numpy weights in the tarball and must pass
tests/test_grader_submission.py (no __file__ at load, never raise, sequential engine).

SELF-IMPROVEMENT LOOP MODE (this governs how you run each iteration against the roadmap above):
  1. MEASURE FIRST. Re-run analysis/loss_classifier.py on the latest ~200 replays (ours + harvested
     top-player episodes) and read state/current.md. The iteration target is to reduce the TOP loss
     bucket. The plan phases say HOW; the live loss data decides WHAT. If the top bucket is not what the
     current phase addresses, work the bucket. If state/current.md or state/hypotheses.md do not exist
     yet, CREATE them this iteration (this is U12, the loop's memory): classify the latest replays and
     centralize the existing analysis/*refuted*.md and *falsified*.md findings into state/hypotheses.md.
  2. CHECK MEMORY. Read state/hypotheses.md before proposing a fix. Do NOT re-walk a refuted lever unless
     its recorded re-test condition is met (more data, a different deck). A refutation is stateful, not
     permanent: bench-dig flipped direction at a larger sample, so record the sample size and re-test
     condition with every refutation.
  3. MEASURE WITH A REAL ORACLE, not the weak-bot gauntlet (it is non-predictive). Score a candidate on
     (a) the diverse opponent pool INCLUDING a behavior-cloned top-player opponent (U13), and (b)
     move-ranking agreement vs held-out top-player decisions. Both are cheap; the ladder is the only
     truth but is rate-limited.
  4. SUBMIT ADAPTIVELY. Spend a ladder slot only when the oracle shows a >=2pp reduction in the target
     bucket AND move-ranking agreement is non-negative AND a slot is free AND the current best
     (shadow-king) is committed so you can revert. NEVER submit a build that worsens ANY bucket by >=2pp,
     even if the headline win rate is up.
  5. EXPLORE. Roughly every 4th iteration, instead of the greedy next fix, re-test a refuted hypothesis
     with more data or measure a candidate on a different deck.
  6. RECORD. Update state/current.md (loss distribution, active candidates awaiting ladder, shadow-king,
     reclaim-king, and a per-build ledger: oracle result, move-agreement delta, ladder score, sample
     size) and state/hypotheses.md every iteration.

Mechanical process: implement one coherent increment with ce-work, mirror existing patterns, write/update
tests (must pass), code-review the diff and apply safe fixes, ce-debug on failures, commit each green step
(stage only that step's files). Update the plan with ce-plan only if it is genuinely wrong.

SECONDARY (touch every few iterations): keep writeup.md current with the teacher-to-student architecture
and the self-improvement story (the Strategy prize is 70/20/10; the writeup is the actual goal).

Mechanical process each iteration: one coherent increment with ce-work, mirror existing patterns,
write/update tests, run them (must pass), code-review the diff and apply safe fixes, ce-debug on
failures, commit each green step (stage only that step's files, never git add -A).

SUBMISSION DISCIPLINE (mandatory): BEFORE any submit run
.venv/Scripts/kaggle.exe competitions submissions -c pokemon-tcg-ai-battle and NEVER submit a build
already on the ladder or one that is not a verified improvement. One submission per iteration max,
respect the 5/day quota, keep the ledger in autoloop_status.md.

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
