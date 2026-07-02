# Unattended autoloop brief: ptcg-abc (Pokemon TCG AI Battle Challenge)

You are an autonomous worker running UNATTENDED in a loop. A shell driver invokes
you once per iteration. Do ONE coherent increment of progress this run, then stop.
The driver calls you again for the next increment. There is no human to ask, so make
the best decision and proceed. Full autonomy was authorized by the user.

## Project
- Repo: C:\Users\danom\ptcg-abc  (work on branch feat/phase1-baseline; commit there)
- Plan: docs/plans/2026-07-02-001-feat-unified-number-one-plan.md (read it; it is the source of truth)
- Status: see the plan's Ground Truth Ledger plus state/current.md for landed / refuted / pending.
- Venv python: .venv/Scripts/python.exe   Tests: python -m pytest tests -q
- Gauntlet: python tools/gauntlet.py <agent> <opponents...> -n <N>
- Build submission: python tools/build_submission.py

## What to do THIS iteration (one increment, then stop)
ROADMAP: Execute docs/plans/2026-07-02-001-feat-unified-number-one-plan.md. READ IT FIRST; it supersedes
the 2026-07-01 plan as the roadmap (this brief's loop-mode, submission-discipline, and hard-constraints
sections still govern HOW you run). Core facts it encodes: the heuristic pilot is the PLAYER; the ladder
A/B is the SOLE arbiter; offline metrics only BLOCK; identical builds span ~130 points, so the settlement
margin is M=60 with the protocol below; the binding resource is settled verdicts (~18-22 remain), not slots.

Standing rules every iteration (mechanical, no judgment):
- Slot 1 always holds a king; slot 2 is the SINGLE live experiment. Never two experiments. Board-check
  (kaggle submissions) before any submit. One submit per iteration max.
- No submission without a complete pre-registration row in state/current.md via tools/loop_state.py
  (hypothesis, direction, margin, N, settle-by, filter values, committed WIN/LOSS/BAND actions). An
  incomplete row is a hard block.
- Settlement: >= 30 rated episodes AND >= 24h. WIN >= king+60 promote; LOSS <= king-60 evict with a king
  copy; band = one repeat, then the episode scoreboard decides at ~90% binomial confidence, else NEUTRAL
  and revert. Early-evict any candidate under 35% raw win rate after 15 episodes.
- Never submit a build that worsens any loss bucket by >= 2pp. Weak-bot gauntlet never gates. A proxy may
  gate only after retrodicting the known five-build ordering (569.6 > 554.5 > 514.7 > 510.1 > 382.5).
- Slot arbitration when tracks compete: in-flight settlement first, then floor reclaim, then the track
  with the nearest kill date. Candidate queue caps at 2 awaiting slots.
- Every 4th iteration: run tools/loop_state.py retest and, if a refuted hypothesis's recorded condition is
  met, run its re-test OFFLINE (ladder slots still only through the protocol).
- If the live pair's best ever sits below ~540, the next slot is a king copy, overriding every queue.

Execute the plan's phases in order, one unit per iteration, honoring latest-start dates and kill dates
(Jul 6 reclaim-or-halt-ladder-spend; Jul 8 census; Jul 9 spike; Jul 10 PIMC + rules probe; Aug 3
deck-aware kill; Aug 8 last new A/B; Aug 10 freeze; Aug 15 final pair locked):
  PHASE 0 (now): U20 scored-pair reclaim FIRST (board check, grader exec test on each exact tarball,
     slot 1 heuristic+trolley 569.6 evicts archaludon 382.5, slot 2 heuristic+trolley_thick evicts
     grimmsnarl 510.1 and doubles as the pre-registered deck A/B). Then U22 protocol codification, U23
     scoreboard, U24 proxy retrodiction, U25 cohort+census, U26 unit-zero spike, U27 PIMC diagnostic,
     U28 reconciliation record, U29 rules probe, U30 ship-safety hardening. All six verdicts by Jul 10.
  PHASE 1: U31 thick settle, U32 replay-trace spine, U33 card_effects + coverage gate, U34 ability A/B,
     U35 REAL CEM run (first hypothesis PRIO_ATTACH earlier; injected variance non-negotiable), U36
     selector+miner+seeds, U37 seeds consumer + guard stack.
  PHASE 2: U38 registry amendment + two-step attribution (step 1 gates ML ladder spend), U39 deck-space
     exploration (legality-validate every deck), U40 featurizer+dataset (only if spike AND census tier
     allow), U41 trainer+scorer seam, U42 BC-as-pilot, U43 cloned foil (rollout role parked behind the
     seat-identity contract), U44 loss-bucket refresh.
  PHASE 3: branch fixed by the U27 verdict, never revisited: favorable = U45 belief-weighted search
     (latest start Jul 27); unfavorable = U46 doubled deck-aware breadth.
  PHASE 4: U47 freeze + regressions, U48 optimal-stopping final-pair campaign per the pre-registered stop
     rule (every re-roll evicts the older submission; never roll past a good draw; no rolls after
     Aug 14 12:00 UTC).

SELF-IMPROVEMENT LOOP MODE (this governs how you run each iteration against the roadmap above):
  1. MEASURE FIRST. Re-run analysis/loss_classifier.py on the latest ~200 replays (ours + harvested
     top-player episodes) and read state/current.md. The iteration target is to reduce the TOP loss
     bucket. The plan phases say HOW; the live loss data decides WHAT. If the top bucket is not what the
     current phase addresses, work the bucket. state/current.md and state/hypotheses.md exist
     (tools/loop_state.py); keep both current every iteration.
  2. CHECK MEMORY. Read state/hypotheses.md before proposing a fix. Do NOT re-walk a refuted lever unless
     its recorded re-test condition is met (more data, a different deck). A refutation is stateful, not
     permanent: bench-dig flipped direction at a larger sample, so record the sample size and re-test
     condition with every refutation.
  3. MEASURE WITH A REAL ORACLE, not the weak-bot gauntlet (it is non-predictive). Score a candidate on
     (a) the diverse opponent pool INCLUDING a behavior-cloned top-player opponent (plan U43), and (b)
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

SECONDARY (every few iterations): U49 keep writeup.md current, every claim citing a committed analysis
file; regenerate the evidence appendix from state/ (the Strategy prize is 70/20/10; the writeup is the
actual goal). If the tmux loop itself is down, follow the manual daily fallback in the plan (board check,
one pre-registered decision, hand-updated ledger) and make loop restoration the next iteration's first unit.

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
