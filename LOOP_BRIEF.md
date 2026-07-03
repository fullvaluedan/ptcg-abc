# Unattended autoloop brief: ptcg-abc (Pokemon TCG AI Battle Challenge)

You are working UNATTENDED in the ptcg-abc repo, invoked once per iteration by a shell driver.
Do ONE increment, then STOP. Full autonomy authorized.

SOURCE OF TRUTH: docs/plans/2026-07-02-combined-learned-eval-plan-v2.md
Read it fully before doing anything.

## RESUME STATE (2026-07-03): TWO TRACKS. Do not conflate them.
An audit found the loop had been optimizing an agent that does NOT ship: the shipped ladder agent is
agents/agent_heuristic.py + its deck (brain = agents/heuristics.py), and NONE of the learned-eval / CEM /
top-player stack is on a shipped path. So ~2 days of work could not move the ladder by construction. Fix: run
two explicit tracks and never let TRACK S masquerade as ladder progress.

### TRACK L (LADDER = rank; HIGHEST PRIORITY; only the SHIPPED agent counts)
A unit may claim LADDER progress ONLY if it changes a SHIPPED path (agents/heuristics.py or the deck csv) AND
beats the 569.6 king offline before it spends a slot. Actions in priority order:
  L1. DIAGNOSE AND FIX THE ABILITY ERROR (TOP PRIORITY). The flagship ability A/B (ref 54281824,
      submission_trolley_ability.tar.gz, submitted 2026-07-03 01:01 UTC) is SubmissionStatus.ERROR on the
      live board: it crashed the grader's validation despite passing tests/test_grader_submission.py. This
      is the SECOND live-grader ERROR (first: 54207787, the no-__file__ bug). Do NOT resubmit blind:
      (a) pull the failed episode's log/replay (kaggle competitions episodes 54281824, then the replay; the
      error message is usually in the episode json), (b) reproduce locally in a grader-parity harness (exec
      main.py with no __file__, fresh process, the EXACT tarball contents, simulate both seats including the
      validation self-play match), (c) fix the root cause, and (d) GENERALIZE the reproduction into
      tests/test_grader_submission.py so a third ERROR class is impossible. Only then rebuild, re-verify,
      and resubmit at a free slot under the existing pre-registration. Note the offline +4.0pp had a
      confound: PTCG_ABILITY is process-global, so the "on" arm's opponents also played abilities; when
      re-validating offline, use a per-agent flag or subprocess arms so the candidate is compared against a
      FIXED field.
  L2. DONE 2026-07-03 01:00-01:01: trolley_thick settled LOSS and was evicted; slot 1 = king copy 54281812
      (settled 600.0, new best-ever). Standing rule stays: settle any candidate the instant it reads clearly
      outside the M=60 band; a mandatory per-iteration auto-settlement step (compute band position from the
      board and EXECUTE the pre-registered action, no prose interpretation) should be added to
      tools/loop_state.py as a small unit.
  L3. BUILD THE CALIBRATED CLONE RING (U70-U74, docs/plans/2026-07-03-002-feat-top-player-clone-ring-plan.md):
      opponent bots cloned from the top-20 teams' recorded play, each piloting that team's harvested deck,
      then a CALIBRATION gate (U73) that must retrodict our known ladder ordering (correlation >= 0.7) before
      the ring replaces the mirror pool as the offline gate. This is the fix for the audited 0-for-4
      offline-to-ladder transfer failure; it outranks all other offline work after L1/L2 because every future
      slot decision depends on a gate that actually predicts the ladder. One unit per iteration:
      U70 dataset -> U71 train+qualify -> U72 clone:<family> opponents -> U73 calibrate -> U74 re-gate the
      live levers. Clone bots never ship, so no grader constraints apply to them.
  L4. After the ring passes (or honestly fails) U73: tune the SHIPPED heuristic + deck only, each candidate
      gated on beating the king against the RING (if calibrated) before a slot; if the ring fails
      calibration, record it and fall back to ladder-only judgment with strict slot discipline.

### TRACK S (STRATEGY prize = the $30k model-approach award; offline; NEVER claims ladder progress)
U60-U65, the Phase A DoD, and U8 (U8a/U8b/U8c) are all DONE as of 019dfa2 (move-prior default flipped on after
its gauntlet A/B: 68.5% vs 63.5%, +5.00pp). NEXT IS U9a, per
docs/plans/2026-07-03-addendum-u9-archetype-detection-v1.md (U9's own "matchup-specific heuristics already
scaffolded in analysis/archetype.py" turned out not to exist: the only pre-reveal scaffolding is one hardcoded
fallback decklist guess, `_field_default_decklist()`; and "early-game observable features" like bench
composition/energy types are not captured anywhere yet, same gap shape U8 had. The addendum found the ground
truth label already exists for free though: analysis/opponent_archetype.py's archetype_label() over a whole
finished replay, so U9a is a distillation-style data unit, not a fresh labeling scheme. It also found the real
ladder replay data (143 files) is long-tailed across 20+ archetypes at n=140 usable games, so U9a must collapse
rare labels into an "other" bucket, mirroring tools/archetype_select.py's own MIN_GAMES/OTHER pattern). Order:
U9a (early-turn feature capture + silver-label rows) then U9b (train + export analysis/archetype_prior.json)
then U9c (pure-Python scorer wired into archetype.py's pre-reveal fallback behind PTCG_ARCHETYPE_PRIOR + 400-game
gauntlet A/B gate), then U11, U12 (U10 already superseded by U62/U63). This work is real and on-target FOR THAT
PRIZE. It does NOT move the ladder as shipped, so it may NEVER be logged as ladder progress and NEVER spends a
ladder slot unless first wired into a SHIPPED agent and PROVEN >569.6 offline. Specs:
docs/plans/2026-07-02-combined-learned-eval-plan-v2.md,
docs/plans/2026-07-03-addendum-u9-archetype-detection-v1.md, and
docs/plans/2026-07-02-003-feat-offline-match-scale-topplayer-mining-plan.md.

### Standing calendar and writeup rules (from the 2026-07-03 report card)
- PLAN FREEZE: this two-track brief is the regime until 16 Aug; no new plan documents or re-pointings
  outside a weekly review. Track L is sized to the settlement budget (~1-2 ladder verdicts/day). Track S
  may iterate freely (its experiments settle in hours).
- WRITEUP IS FIRST-CLASS, STARTING NOW: roughly every 6th iteration advances docs/writeup/ (the Strategy
  prize is 70% model approach). The differentiated story to assemble from existing analysis/: machine-
  enforced pre-registration, the quantified same-build noise model, the HONEST 0-for-5 offline-to-ladder
  transfer record with the mirror-pool diagnosis, the 173k-row top-player mining + win/loss study, and (once
  U73 lands) the calibrated clone ring closing the loop. Every claim cites a committed analysis file.
- ENDGAME CAMPAIGN (calendar: 2026-08-10 to 08-16): reinstate the latest-2 noise campaign (unified plan
  U48): freeze the best build, then spend the full daily quota resubmitting it with an optimal-stopping rule
  against latest-2 scoring semantics (same-build spread is ~90-130 points, wider than any lever we have, so
  endgame draws are the cheapest rank points available). Refit the noise model on all accumulated same-build
  reads well before then.

### Shared rules
- ONE loop only. Do NOT run parallel sessions: the ladder is quota-bound (5/day), slot-bound (2 scored slots),
  and noise-bound (~90-130pt same-build band), so more compute cannot buy rank, only more offline infra.
- STOP re-deriving early_collapse (settled: deck-density-bound). No new empty-bench/collapse analyses unless a
  genuinely NEW mechanism is tested.
- Each iteration: if a ladder slot is free and a TRACK L action is ready, do TRACK L (it is the rank lever);
  otherwise advance TRACK S offline. Prep L1 (build + gauntlet + pre-register) even while slots are full so it
  ships the instant L2 frees a slot.

## Project
- Repo: C:\Users\danom\ptcg-abc   Branch: feat/phase2-learned-eval (Phase A); feat/phase3-followon (Phase B). Never touch main.
- Venv python: .venv/Scripts/python.exe   Tests: python -m pytest tests -q
- Gauntlet: python tools/gauntlet.py <agent> <opponents...> -n <N>   Build: python tools/build_submission.py
- Kaggle: .venv/Scripts/kaggle.exe ; token at ~/.kaggle/access_token (never in code or logs)

## SETUP (guard once at the start of a run)
1. Ensure on branch feat/phase2-learned-eval (Phase A) or feat/phase3-followon (Phase B); create off HEAD if missing.
2. Confirm data/training/ and data/replays/ are gitignored (data/ is already ignored, which covers both).

## EACH ITERATION (one increment, then stop)
1. git log --oneline to find the last completed unit, then pick per the TWO-TRACK RESUME STATE above: if a
   ladder slot is free and a TRACK L action (L1 ability A/B, L2 settle trolley_thick, L3 shipped tuning) is
   ready, do TRACK L; otherwise prep the next TRACK L step offline and/or advance TRACK S (U9a, U9b, U9c, then
   U11, U12 on feat/phase3-followon). TRACK L is the rank lever; TRACK S is the Strategy-prize deliverable.
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
