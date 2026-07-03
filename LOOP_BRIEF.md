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
  L1. SHIP THE ABILITY A/B THIS ITERATION (highest-EV lever we own; it is already BUILT, validated, and
      staged): submission_trolley_ability.tar.gz has PTCG_ABILITY=1 baked, offline gauntlet +4.0pp
      (67.5% -> 71.5%, no regression, analysis/ability_ab.md), grader-verified, pre-registered vs the king
      (up, M=60, N=30). The pilot otherwise never activates an ability (0/554 vs top players,
      analysis/move_ranking_diverges_ability_gap.md). Ship it: board-check, reclaim slot 2 with a KING COPY
      (this evicts the settled-loss trolley_thick per L2, so the king stays the floor), then submit the
      ability build as the experiment so it is A/B'd against the king. Two submissions, board-check between,
      respect the 5/day quota.
  L2. trolley_thick has SETTLED as a LOSS. The live board on 2026-07-03 shows it at 446.2 vs the king's
      558.5, a -112 gap far past the M=60 LOSS threshold, with >24h elapsed. The pre-registered LOSS rule is
      MET: EVICT it NOW (do NOT wait for the 07-06 date). Reclaiming slot 2 to a king copy (L1's first
      submission) is the eviction. Then stop tracking trolley_thick. General rule going forward: settle any
      candidate the instant it is clearly outside the M=60 band, never idle days on a decided loser.
  L3. After L1/L2 settle: tune the SHIPPED heuristic + deck only, each candidate gated on beating 569.6
      offline before a slot.

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
