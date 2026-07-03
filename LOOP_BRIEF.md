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
  L1. DONE 2026-07-03: the ability ERROR (ref 54281824) was root-caused by direct tarball inspection (no
      episode log needed): the hand-run build command omitted --extra agents/card_effects.py, and
      heuristics.py has imported card_effects unconditionally since U33 (2e18145), so the module failed to
      load under the grader's exec-without-__file__ path. Fixed the command, rebuilt, verified via the
      grader test AND a direct extracted-tarball kaggle_environments env.run (reward=1, DONE, 25 steps),
      resubmitted (ref 54282097, COMPLETE 536.7 first reading), and submitted a king-copy cleanup (ref
      54282104, COMPLETE 691.5) to evict the dead ERRORed ref from the tracked latest-2 window. Generalized
      per (d): tests/test_grader_submission.py::test_extras_cover_flat_layout_imports now derives each
      shipped entrypoint's required flat-layout extras from its AST and asserts the declared list covers
      them; it immediately caught the same gap in _SEARCH_EXTRAS (fixed alongside, search stays unshipped).
      Fresh pre-registration settle-by 2026-07-08. Note the offline +4.0pp still had the documented confound
      (PTCG_ABILITY is process-global, so the "on" arm's opponents also played abilities) -- not
      re-validated this iteration; if the ladder verdict is a surprising LOSS, re-check that confound before
      trusting the offline gauntlet.
  L2. DONE 2026-07-03 01:00-01:01: trolley_thick settled LOSS and was evicted; slot 1 = king copy 54281812
      (settled 600.0, new best-ever). Standing rule stays: settle any candidate the instant it reads clearly
      outside the M=60 band; a mandatory per-iteration auto-settlement step (compute band position from the
      board and EXECUTE the pre-registered action, no prose interpretation) should be added to
      tools/loop_state.py as a small unit.
  L3. DONE with an honest FAIL: the top-20 clone ring (U70-U74) failed calibration (tau 0.429 < 0.7; clones
      could not beat first-legal). Verdict recorded; the ring has NO gate authority. Two diagnoses feed the
      next units: (a) top-20 play is too subtle for shallow imitation, and (b) top-20 was the WRONG BRACKET
      anyway: matchmaking pairs us with the ~450-750-rated field, so the sparring ring must model the
      opponents we actually face, not the champions.
  L4. U80 DAILY DATA REFRESH (new, cheap, do FIRST): Kaggle publishes an episode dump EVERY DAY (dataset
      slugs kaggle/pokemon-tcg-ai-battle-episodes-YYYY-MM-DD; an -index dataset updates nightly). Build
      tools/daily_refresh.py: find + download the newest dump (skip if already present), re-run the
      top-player tracker on it, pull OUR own fresh ladder replays (tools/harvest_replays.py), and re-run
      analysis/loss_classifier.py on the CURRENT king's real recent losses; write the ranked loss buckets to
      state/current.md. The current top leak, measured on live games AFTER the ability change, is the single
      most valuable number for choosing the next lever. Then wire the refresh into the loop as an
      every-Nth-iteration step. Stay isolated: dumps live in gitignored data/episodes/.
  L5. U81 BRACKET RING: rebuild the practice ring from the field we ACTUALLY face: from the fresh dumps,
      select games whose teams sit in the ~450-750 leaderboard band (plus every opponent named in our own
      143+ ladder replays), harvest their decks, and pilot them with simple models of THEIR play (these
      weaker bots are far easier to imitate than the top 20). Recalibrate with the U73 tool against our
      >=6 settled builds (569.6 > 554.5 > 514.7 > 510.1 > 452.2 > 387.0): tau >= 0.7 grants gate authority,
      else record the FAIL and the ladder stays sole judge. A ring that predicts OUR bracket is the missing
      instrument for every offline decision.
  L6. U82 CATEGORY MINING v2 (the one method that already paid: it found the 0/554 ability gap): mine the
      top-player corpora for CONDITIONAL category gaps vs our pilot: energy-attach target choice (active vs
      which bench), retreat timing, deck-search picks (what they fetch with ball/search effects), supporter
      choice by game state, promote choice after a knockout. Each confirmed gap becomes a flag-gated rule in
      agents/heuristics.py (mirror PTCG_ABILITY), offline-checked, then pre-registered for a ladder A/B only
      if the bracket ring (if calibrated) or a large offline effect supports it.
  L7. U83 TEACHER-STUDENT DISTILL (the expedite engine; uses the 20-core parallel gauntlet): run the full
      search stack (learned eval + move prior + confidence time allocation, all gates green) as an offline
      TEACHER at generous per-move budgets over thousands of self-play + bracket-ring games on OUR deck;
      log its chosen moves; distill them into the SHIPPED heuristic's tunable genome (PRIO weights + the U82
      rule flags) via CEM fit to teacher agreement + ring win rate. The teacher never ships (too slow, no
      grader risk); only the distilled weights do, through the normal gates. This converts raw simulation
      volume into shipped-pilot improvement without depending on thin top-player labels.
  L8. Standing: each shipped-path candidate that survives its gate gets a pre-registered ladder A/B; slot
      discipline and the M=60 protocol unchanged; the Aug 10-16 endgame noise campaign stays booked.

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
