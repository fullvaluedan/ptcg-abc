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
  L3. DONE with an honest FAIL, then SUPERSEDED: the top-20 clone ring (U70-U74) failed calibration
      (tau 0.429 < 0.7; clones could not beat first-legal). Verdict recorded; that ring had NO gate
      authority. Two diagnoses fed L5, below, which fixed diagnosis (b) directly: top-20 was the WRONG
      BRACKET (matchmaking pairs us with the ~450-750-rated field, not the champions).
  L4. DONE 2026-07-03: tools/daily_refresh.py built and wired into the loop as an every-Nth-iteration step
      (find/download the newest daily dump, re-run the top-player tracker, pull fresh ladder replays,
      recompute the loss distribution into state/current.md). Current read (224 usable replays,
      post-ability-change): early_collapse still the #1 loss bucket, 60/125 losses (48%), well ahead of
      bad_determinization (22), deck_matchup (20), deckout (17), endgame_misplay (6). Re-run this
      periodically via the wired step; do not re-derive it by hand (see STOP re-deriving rule below).
  L5. DONE 2026-07-03, PASS: the bracket ring (U81) rebuilt the practice ring from the ~450-750 rating
      band we actually face (tools/bracket_select.py, tools/bracket_decks.py) instead of the top-20.
      Recalibrated with the U73 tool against all 6 settled builds: tau = 0.857 (>= 0.7), 6/6 covered
      (analysis/ring_calibration.md). This ring now HAS gate authority for future TRACK L candidates
      (never retroactive). U74 already used it once: re-graded the staged ability build, ring agrees
      with the offline gauntlet's direction (+20.0pp at n=20/arm vs the gauntlet's +4.0pp;
      analysis/ability_ring_check.md). Use `tools/ring_calibrate.py` / `tools/ability_ring_check.py` as
      the template for gating the next candidate this ring produces.
  L6. DONE 2026-07-03, MINED OUT: U82 category mining v2 checked every named conditional-gap candidate
      (energy-attach target, retreat timing/target, deck-search picks, promote choice) against the
      top-player corpus. Result: no further single-field shippable gap found. Retreat-target and
      promote-after-knockout matchup theories were each refuted twice, from two different angles
      (analysis/retreat_gap_conditional.md, analysis/promote_gap_conditional.md); deck-search picks are
      category-explained, not a pilot gap. All threads converge on the SAME missing capability: game-plan
      / archetype awareness. TRACK S already tested exactly that (U9a/U9b, see below) and it failed its
      gate at n=140 -- so this specific lever is closed for now, not just unexplored. Do not re-run U82's
      single-field miners again without a genuinely new category to check (mirrors the early_collapse
      STOP rule).
  L7. NEXT TRACK L ACTION (not yet started): U83 TEACHER-STUDENT DISTILL (the expedite engine; uses the
      20-core parallel gauntlet). Run the full search stack (learned eval + move prior + confidence time
      allocation, all gates green) as an offline TEACHER at generous per-move budgets over thousands of
      self-play + bracket-ring games on OUR deck; log its chosen moves; distill them into the SHIPPED
      heuristic's tunable genome (PRIO weights + the U82 rule flags, none of which had a live gap to flip
      right now, so this is a genome-tuning distillation rather than a new flag) via CEM fit to teacher
      agreement + the now-calibrated L5 ring win rate. The teacher never ships (too slow, no grader risk);
      only the distilled weights do, through the normal gates. This is the next real TRACK L prep unit
      while both ladder slots are occupied (settle-by 2026-07-08).
  L8. Standing: each shipped-path candidate that survives its gate gets a pre-registered ladder A/B; slot
      discipline and the M=60 protocol unchanged; the Aug 10-16 endgame noise campaign stays booked.

### TRACK S (STRATEGY prize = the $30k model-approach award; offline; NEVER claims ladder progress)
U60-U65, the Phase A DoD, and U8 (U8a/U8b/U8c) are all DONE as of 019dfa2 (move-prior default flipped on after
its gauntlet A/B: 68.5% vs 63.5%, +5.00pp). U9a/U9b are ALSO DONE (2026-07-03, 4ec3de6/17a2a22): U9a captured
early-turn features + silver labels (n=140 usable ladder games, long-tailed, collapsed to top-6-plus-other per
plan); U9b trained the classifier and recorded an honest gate FAIL (mean held-out margin +0.043 vs the required
+0.050, analysis/archetype_prior_train.md). Per the addendum's own discipline, U9c does NOT wire an unproven
model into search; no analysis/archetype_prior.json was exported. U11 (eval_blend_sweep) and U12
(confidence-based time allocation, gate PASSED, default on, 0deba9d) are ALSO already done, predating this
brief revision. So the entire U8-U12 roadmap from both plans is now COMPLETE, with two real negative results
(U9b) documented rather than forced through.
NEXT FOR TRACK S: no further coded units are defined without a weekly plan review (PLAN FREEZE below), so the
standing WRITEUP cadence is the live TRACK S action -- fold in the L5 bracket-ring PASS (it directly reverses
docs/writeup/offline_ladder_transfer.md's current "three failures, no working proxy" bottom line into a fourth,
successful attempt) and the U82 mining-closure story. Do not restart U9a/U9b/U9c or U11/U12; they are settled.
Specs: docs/plans/2026-07-02-combined-learned-eval-plan-v2.md,
docs/plans/2026-07-03-addendum-u9-archetype-detection-v1.md, and
docs/plans/2026-07-02-003-feat-offline-match-scale-topplayer-mining-plan.md (all fully executed).

### Standing calendar and writeup rules (from the 2026-07-03 report card)
- PLAN FREEZE: this two-track brief is the regime until 16 Aug; no new plan documents or re-pointings
  outside a weekly review. Track L is sized to the settlement budget (~1-2 ladder verdicts/day). Track S
  may iterate freely (its experiments settle in hours).
- WRITEUP IS FIRST-CLASS, STARTING NOW: roughly every 6th iteration advances docs/writeup/ (the Strategy
  prize is 70% model approach). The differentiated story to assemble from existing analysis/: machine-
  enforced pre-registration, the quantified same-build noise model, the offline-to-ladder transfer record
  (three named failures with diagnoses, THEN the L5 bracket ring PASS at tau 0.857 once the opponent pool
  was fixed to match our actual bracket, analysis/ring_calibration.md), the 173k-row top-player mining +
  win/loss study, and the U82 category-mining closure (every named conditional gap checked, converging on
  archetype awareness, which U9b's own honest gate FAIL then closed). Every claim cites a committed analysis
  file. docs/writeup/offline_ladder_transfer.md still ends on the stale "no working proxy" framing as of
  2026-07-03 and needs its Attempt 4 + bottom-line sections updated to match.
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
   ladder slot is free and a TRACK L action is ready, do TRACK L; otherwise prep the next TRACK L step offline
   (L7 U83 teacher-student distill is next, undone) and/or advance TRACK S (U8-U12 are all done; the writeup
   cadence is the live TRACK S action, see TRACK S section above). TRACK L is the rank lever; TRACK S is the
   Strategy-prize deliverable.
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
