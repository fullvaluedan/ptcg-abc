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
      trusting the offline gauntlet. SETTLED 2026-07-04, WIN: board check ref 54282097 (ability) 561.1 vs
      ref 54282104 (reclaim-king) 494.8, diff +66.3pp, clears M=60 via the standing instant-settlement rule
      (tools/loop_state.py auto-settle). Promoted to shadow-king (state/current.md). ref 54282097 is now
      evicted from the tracked latest-2 (see L9 same-iteration attack_first submission below); 561.1 is its
      final frozen reading, not an ongoing one. The process-global-confound caveat above was never
      re-checked, so treat this WIN as directionally real but not confound-clean.
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
  L7. DONE 2026-07-03, BLOCKED (honest FAIL): U83 TEACHER-STUDENT DISTILL ran to completion. Built a teacher
      (the full search stack, all gates green) as an offline harvester over self-play + bracket-ring games on
      OUR deck (20-core parallel harvest, 1157 train / 398 held-out test distinct games logged via
      TeacherLogger), then ran a real CEM sweep (population 16, elite 4, iterations 6, --ring-matches 6
      against the calibrated L5 ring, --teacher-labels data/training, seed 0; best training-side fitness
      0.8940). `tools/cem_held_out_gate.py` scored it against the held-out test split, now 10689 scorable
      MAIN decisions (92x/356x the two prior CEM attempts' 116/30 real-replay sample): default agreement
      0.8210, tuned agreement 0.8189, delta -0.0022, verdict BLOCKED, the same as the first two attempts.
      This is CEM candidate 3 of 3 non-WIN reads, and it specifically answers the second attempt's own
      named re-open condition (a materially larger sample) with a negative result: full-population train
      agreement also went backwards for the tuned vector (0.8077 -> 0.8049), and the diagnosed mechanism is
      that the sweep's own best fitness was dominated by a noisy 6-game ring-win-rate read rather than a
      real agreement gradient, the same proxy-metric-moves-backwards failure attempt 2 found, surviving the
      scale increase. No ladder A/B; shipped PRIO_* weights stay at their hand-set defaults.
      analysis/cem_run_prio_teacher.md, docs/writeup/genome_tuning.md, state/hypotheses.md
      (cem_prio_agreement_generalizes). Only remaining re-test condition: (c) a genome region with a
      measured non-flat held-out gradient, not yet tried; the comprehension track below (U90/U91) is this
      project's live source for a candidate lever that might supply one. The 20-worker teacher harvest and
      its corpus remain useful infrastructure regardless (a future genome region can reuse the same held-out
      split without re-harvesting).
  L8. COMPREHENSION TRACK (U90-U94, Dan-directed, supersedes the "top-20 too subtle" verdict): the clone
      autopsy proved the U71 FAIL was an INSTRUMENT DEFECT, not unlearnable play. Three defects, all verified
      in analysis/clone_quality.md and tools/train_clone.py: (a) pointwise per-row log-loss whose zero-risk
      optimum IS the first-legal baseline (models picked option 0 in 13019/13019 then 11092/11092 held-out
      decisions), (b) the baseline policy handed to the model as features (opt_is_first/opt_index_norm) while
      the gate was margin-over-first-legal, (c) semantically blind features (8 regex tags, no card identity,
      no energy costs, no evolution lines). Learnable structure EXISTS unexploited: first-of-played-category
      beats first-legal by 20-27pp on every family; END_TURN is never option 0 yet was the real choice 4.3%
      of the time. AMEND state/hypotheses.md: the U71 refutation's re-test condition is a ranking objective.
      Units in order, one per iteration, interleaving with U83 (U90/U91 outputs feed U83's genome):
      U90 CARD SEMANTICS V2 + ON-EVOLVE PROBE (cheapest, best ladder hope): probe how the engine surfaces
          on-evolve abilities (Punk Up / Assemble Alloy, the engines of BOTH meta decks) and whether our
          pilot ever triggers that class (same shape as the 0/554 ability find that paid +4pp); extend
          agents/card_effects.py TAG_VOCAB (v2, additive, golden tests keep passing) until ZERO untagged
          effect cards remain on the two meta decklists (today 4 and 5 blind, including Boss's Orders).
      U91 PLAYBOOK MINER V2 (step 1 DONE 2026-07-03, step 2 DONE 2026-07-03, step 3 not started): step 1 fixed
          attach_target to resolve the RECEIVING Pokemon (analysis/replay_trace.attach_receiver_id, mirrors
          heuristics._attach_slot_card_id) and root-caused + fixed play_target's 0.000 resolution
          (analysis/replay_trace.play_hand_card_id, mirrors heuristics.play_card_id; the bug was a PLAY option
          carrying no "area" key at all, only a bare hand index). Validated on real data (bracket_4, n=1500
          episodes): both blocks jumped from 0.470/0.285 and 0.000-barred to 1.000/1.000 resolution
          (analysis/gameplan_target_resolution_fixed.md). Discovered a real side-blocker: meta_archaludon/
          meta_grimmsnarl no longer classify ANY deck in the mined dataset because the L5 bracket_1..6
          archetype csvs (added after this dataset was mined) now shadow them in classify_family's
          alphabetical tie-break; still unfixed, still blocks a like-for-like re-mine of those two named
          families. Step 2 (analysis/gameplan_mine.py, analysis/gameplan_claim_gate.py): added three
          turn-scoped blocks (attach_before_attack, energy_banking, game_length_turns) and the CLAIM GATE
          (n>=200/side, bootstrap 90% CI excluding zero) / PREDICTION GATE (KD4 train-mined CI must bracket
          the held-out test mean) machinery. Ran end to end on bracket_4's full dataset (the resolvers'
          validated family, since the two named meta families are still blocked): attach_before_attack and
          energy_banking both CONFIRMED (winners attach-before-attacking 3.4pp less, bank energy 4.4pp less,
          n>=1400/side, both gates pass); game_length_turns CUT (claim CI straddles zero). Full writeup:
          analysis/gameplan_claims_bracket_4.md. Real footgun found and documented: build_signatures(None)
          silently mines ZERO appearances for bracket families; --decks-dir decks is required. Step 3 (U93
          step 1, DONE 2026-07-03): built the literal flag-gated rule the plan names -- PTCG_ATTACK_FIRST
          (default off) in agents/heuristics.py's choose(): when a positive-value attack is already legal
          THIS decision without a further attach, take it now instead of the discretionary attach. 6 new
          tests (tests/test_heuristic.py). Ran the same fires-vs-inert discipline as measure_energy_seq/
          measure_bench_dig BEFORE spending a bracket-ring slot: tools/measure_attack_first.py captured 20
          real trolley ATTACH+ATTACK positions (up to 10 matches), 8 with a positive-value attack on the
          table, 3/20 flipped the end-to-end pilot decision. Verdict LIVE, not inert (analysis/
          attack_first_flip_check.md). STILL TODO (U93 step 2): the bracket-ring A/B (>=+5pp with
          gauntlet-direction agreement) before any ladder slot; the archetype-registry shadowing fix is
          still open for whoever wants the two named meta families back. DONE 2026-07-04: fixed
          (analysis/expert_cohort.py's classify_family now breaks exact-cover ties in favor of a
          non-"bracket_"-prefixed name, so a harvested bracket deck that happens to duplicate a named
          family's signature -- bracket_4 == meta_archaludon, bracket_1 == meta_grimmsnarl_tonakaiiii,
          both confirmed by direct signature diff -- can no longer shadow it just because "bracket_" sorts
          first alphabetically; bracket_2/3/5/6, which have no such duplicate, still classify as
          themselves unchanged). Verified two ways: 2 new unit tests
          (tests/test_expert_cohort.py::test_classify_family_bracket_name_never_shadows_a_tied_canonical_name)
          and a real run over a 400-episode slice of the 2026-06-30 dataset with --decks-dir decks, where
          meta_archaludon/meta_grimmsnarl now get 219/13 real episode counts instead of 0. This reopens
          the "still open" item above: the two named meta families can be re-mined directly now (no need
          to go via bracket_4 as a stand-in).
      U92 CLONE REBUILT: step 0 (DONE 2026-07-04, FAIL, CLOSED): the half-day KILL TEST -- rerun the U26
          pairwise RankNet (analysis/unit_zero_spike.py's PairwiseLinearRanker, generalized to any feature
          width so it could be pointed at agents.imitation_features rows) against FIRST-LEGAL on the exact
          clone dataset and train/test split tools/train_clone.py already gated (clone_groups_1783047584.npz,
          feature_version 3). Held the feature set and split fixed and changed ONLY the training objective
          (pairwise ranking loss instead of per-row log-loss). Result: every family still ties first-legal to
          within noise (meta_archaludon -0.0015, meta_grimmsnarl -0.0001, meta_grimmsnarl_tonakaiiii +0.0000,
          other -0.0015; tools/rank_clone_killtest.py, analysis/rank_clone_killtest.md), the same collapse all
          three prior tools/train_clone.py attempts hit. This is a FOURTH converging negative result and it
          specifically answers this unit's own re-open condition (a different training objective) with FAIL:
          the objective was never the bottleneck, so tools/train_clone2.py is NOT worth building. U92 is
          CLOSED; do not restart it without a genuinely new lever (a different label scheme or feature source,
          not another model/objective swap over the same option-order-dominated data). NEXT comprehension-track
          unit is U94 (writeup chapter), interleaved with TRACK L per the standing rule.
      U93 TRANSFER TO THE SHIPPED PILOT (the only ladder-moving piece): each playbook lever that applies to
          OUR deck (on-evolve usage if the probe finds a miss; energy front-load ordering; attach-recipient
          policy) ships as a flag-gated rule, pre-registered, bracket-ring A/B >=+5pp with gauntlet direction
          agreement BEFORE any ladder slot, then the M=60 ladder protocol. Step 1 DONE 2026-07-03: the
          sequencing rule (PTCG_ATTACK_FIRST) is built and confirmed LIVE on trolley (3/20 real-position
          decision flips, analysis/attack_first_flip_check.md). Step 2 DONE 2026-07-04: both required offline
          gates PASSED -- weak-bot gauntlet +5.5pp, no regression (analysis/attack_first_ab.md); calibrated
          bracket-ring +10.0pp, agrees in direction (analysis/attack_first_ring_check.md, new
          tools/attack_first_ring_check.py mirroring ability_ring_check.py). Tarball built and grader-verified
          (tests/test_grader_submission.py[heuristic-trolley-attack_first]); pre-registered as
          heuristic+trolley-attack_first (state/current.md, up, M=60, N=30, settle-by 2026-07-11). Step 3
          DONE 2026-07-04: L1's ability build settled WIN this same iteration (board check 561.1 vs
          reclaim-king 494.8, +66.3pp, clears M=60), which froze its final reading and made it safe to spend
          the slot; submitted heuristic+trolley-attack_first (ref 54304483, PENDING) into the slot the
          settlement freed. This is the eviction-by-submission-order mechanic, not a manual revert: the
          older of the two live submissions (54282097, the just-settled ability build) dropped out of the
          tracked latest-2 automatically once the new build landed, leaving [54304483 attack_first, 54282104
          reclaim-king] as the live pair. Pre-registration unchanged: up, M=60, N=30, settle-by 2026-07-11.
          NEXT: board-check until PENDING resolves, then settle per the M=60 protocol the instant it reads
          clearly outside the band (do not wait idly for the settle-by date if it clears sooner).
      U94 WRITEUP CHAPTER: DONE 2026-07-04. docs/writeup/comprehension.md written: the full arc (autopsy, WHY
          layer, playbooks, U93 transfer, honest FAILs) with an 18-row claims ledger, every row citing a
          committed analysis/state file. Added tests/test_comprehension_writeup.py (4 tests) that parses the
          ledger table and asserts every cited path actually exists on disk, so a future rename/removal of a
          source file fails a test instead of leaving a dangling claim; this is the "machine-audited" part,
          not just a table. Comprehension track (U90+U91+U93+U94, U92 closed FAIL) is now fully written up.
          NEXT: no further comprehension-track units are defined; fold future TRACK L levers this track
          produces in as addenda rather than opening U95+ without a plan review.
  L9. Standing: each shipped-path candidate that survives its gate gets a pre-registered ladder A/B; slot
      discipline and the M=60 protocol unchanged; the Aug 10-16 endgame noise campaign stays booked and must
      not be displaced. U92 closed 2026-07-04 (FAIL); comprehension track (U90+U91+U93+U94) fully shipped and
      written up as of U94. heuristic+trolley-ability settled WIN 2026-07-04 (561.1 vs 494.8, +66.3pp) and is
      now shadow-king (state/current.md); it is off the board (evicted by the attack_first submission), so
      its 561.1 reading is final. DONE 2026-07-03 (board-check iteration): attack_first's first reading (ref
      54304483, COMPLETE 526.8 at the time) settled BAND (diff +32.0 vs the frozen king 494.8), so per the
      pre-registered BAND action submitted a byte-identical repeat (ref 54304681, PENDING). SETTLED NEUTRAL
      2026-07-03 (this iteration): both readings drifted under same-build noise to a MIXED sign (54304483 ->
      442.9, 54304681 -> 600.0, king 494.8), so ran the pre-registered U23 scoreboard tiebreak
      (analysis/episode_scoreboard.py) on real downloaded replays (tools/scout.py pull for all three refs):
      3 shared brackets, candidate 1/3 decisive (0.333) vs king 4/6 decisive (0.667), confidence 0.171,
      favors_candidate=false, verdict neutral (analysis/attack_first_settlement.md). Per the BAND action this
      reverts the slot to a byte-identical heuristic+trolley king copy; built and grader-verified
      (test_grader_submission.py[heuristic-trolley]) but NOT YET SUBMITTED -- Kaggle's daily quota was already
      exhausted for 2026-07-03 UTC (6 real submissions landed that UTC day, not the 2 a prior note tracked;
      confirmed via the raw API error body: "used its daily Submission allowance (5) today"). This is a
      small-sample ladder NEUTRAL (3 decisive shared-bracket episodes, far under N=30), not a refutation of the
      attack_first lever's offline gates (+5.5pp gauntlet, +10.0pp ring), so it stays re-eligible for a future
      slot without new offline work. NEXT TRACK L action: submit the already-built, already grader-verified
      king-copy revert tarball as the FIRST action next iteration once the quota window resets (~00:00 UTC
      2026-07-04), then update kings/ledger to reflect it landing. After that, no TRACK L build is awaiting a
      slot; fall back to TRACK S (writeup cadence, see below) or prep the next TRACK L candidate.

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
- KEEP findings.md CURRENT: whenever a unit produces a real finding (a refutation, a confirmed lever, a
  calibration verdict, a pivot, a meta-lesson), append a dated one-liner to the right section of the
  repo-root findings.md with its source analysis file. findings.md is the durable raw material for a later
  report on how the approach evolved; it is a synthesis/index, not a re-dump of the analysis docs. No em
  dashes.
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
