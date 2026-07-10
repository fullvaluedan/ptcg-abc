# Unattended autoloop brief: ptcg-abc (Pokemon TCG AI Battle Challenge)

You are working UNATTENDED in the ptcg-abc repo, invoked once per iteration by a shell driver.
Do ONE increment, then STOP. Full autonomy authorized.

SOURCE OF TRUTH for the CURRENT regime: the POSTURE INVERSION block directly below, then the TWO TRACKS
resume state. The 2026-07-02 combined v2 plan is fully executed (historical reference only).

## POSTURE INVERSION (2026-07-05, verified from the competition's own rules pages; SUPERSEDES any
## conflicting text below, including every "variance harvest", "keep the luckiest draw", "stop_target",
## M=60 settlement, and single-read WIN/LOSS narrative)
Verified live from the Simulation overview: after the Aug 16 lock, Kaggle CONTINUES running games from
Aug 17 to ~Aug 31 "until the leaderboard has reached convergence", and only then is the leaderboard final.
So a lucky score snapshot harvested before the deadline DECAYS toward true skill: the luck-harvest endgame
is DEAD. Verified from the Strategy hackathon pages: eight $30,000 prizes, ~151 submitting teams so far,
ONE Kaggle Writeup per team (max 2000 words, submitted via the site, drafts do not count), entry/team-merger
deadline Sep 6, submit by Sep 13 11:59PM UTC, judged 70% model approach / 20% deck / 10% report, leaderboard
rank is ONE bullet of five inside the 70%, lower-tier teams can win per the page itself, and the Simulation
track pays $0. THEREFORE:
P1. TRACK S (the Strategy writeup + the honest-methods story) is the PRIMARY EV line. Writeup milestones
    (Dan, 2026-07-05): all drafting stays IN THIS REPO and gets pushed to GitHub; conform ONE writeup to the
    real format (2000 words, title/subtitle, Track, self-made figures only, no Pokemon artwork, nothing
    attached we cannot publish); full draft by Aug 10; SUBMITTED on Kaggle by SEP 1 (Dan's hard deadline,
    12-day buffer to the official Sep 13; a reminder is scheduled).
P2. TRUE STRENGTH is the only rank lever that survives convergence. U39 DECK EXPLORATION is authorized and
    is the top offline build priority. CORRECTION (2026-07-05, supersedes the "Ring v2" directive that
    stood here): the escalation resolution above was WRONG on the facts. Verified against
    analysis/ring_calibration.md: the existing BRACKET ring (tau 0.857) was NOT calibrated only on same-deck
    trolley builds. Its 6-build calibration set already includes meta_archaludon (382.5) and meta_grimmsnarl
    (510.1), both DECK-CHANGED builds, and the ring correctly ranked them near the bottom. The ring already
    has deck-judging gate authority; there is no "Ring v2" to build, and no future unit should attempt to
    rebuild this ring. Do not re-open this question without first re-reading analysis/ring_calibration.md
    in full.
    THE REAL GAP: no NEW top-rated deck candidate has ever been scored through the existing calibrated ring.
    analysis/top_rated_mining.md (queue item 4) mined 800+-rated decklists, but 2 of its top 3 clusters are
    undocumented duplicates of decks already tested and refuted (meta_grimmsnarl, meta_grimmsnarl_tonakaiiii)
    and the rest were never deduped against decks/*.csv or scored. NEXT: dedupe the mined clusters by full
    60-card signature against every decks/*.csv, take the top few genuinely NEW candidates by play count,
    validate legality, score each (heuristic pilot, mirroring ring_calibrate.py's
    `"trolley_thick": lambda: opponents.get("deck:trolley_thick")` pattern) against
    tools.ring_calibrate.ring_names() via run_ring, and compare to trolley's calibrated ring win rate (0.85).
    Only a candidate that clears trolley's ring win rate by a material margin is pre-registered for a TRACK L
    ladder A/B. Queue items 5 and 6 (fuzzer, differential audit) are being built by the lead session, not
    the loop; item 10 (mirror benchmark) waits on this deck-candidate work, not on any ring rebuild.
P3. The Aug 10-16 window becomes LOCK-THE-STRONGEST-PAIR, executed EARLY (by Aug 12-13 so the pair accrues
    convergence episodes): two copies of the genuinely strongest build (or a within-margin hedge pair).
    Retire tools/endgame_stopping.py stop_target 611.6 as a decision rule. Ops guards: every campaign
    tarball passes tests/test_grader_submission.py before upload; confirm COMPLETE before any next roll;
    after Aug 13 submit nothing that has not already scored COMPLETE under an identical hash (a dead ERROR
    locked into the final pair is unrecoverable).
P4. MEASUREMENT: no lever settles from single ladder reads (M refit 240). Fresh reads are inflated vs aged
    reads: run the age-stratified refit (family means on <48h vs >72h reads) and re-derive the true king
    estimate from AGED reads before choosing the locked pair. The rebuilt ring is the decision gate.
P5. USAGE ECONOMY: gate board checks on the newest episode id advancing (tools/scout.py), max 2-4/day; no
    iteration spent logging an unchanged board; reserve usage headroom for Aug 10-16 and the writeup.
    MODEL NOTE (2026-07-05): this loop now runs on HAIKU to stretch usage limits. Bias every iteration
    toward small, mechanical, well-specified increments (data jobs, tests, ledger upkeep, applying a spec
    exactly as written). If a unit requires genuine design judgment (a new architecture, an ambiguous
    verdict call, rewriting a protocol), do NOT attempt it: write the question + context into
    autoloop_status.md under "NEEDS ESCALATION" and move to the next mechanical unit. Compute-heavy work
    (fuzzing, gauntlets, mining) belongs in plain Python via tmux (see ptcgcompute pattern), never inside
    an LLM iteration.
P6. RULES/COMPLIANCE standing: keep the repo publishable (MIT open-source obligation if we win covers
    training + inference + reproduction docs); never commit competition card data or Pokemon assets; delete
    competition data at competition end; episode-dump mining is compliant (rules 2.11 + external-data
    clause) but dumps stay team-private. One open rules conflict: Simulation Rules 2.2.b says teams "may
    select up to two Final Submissions" while the overview/FAQ say latest-2-auto; Dan checks the logged-in
    Submissions page for a selection UI before August (if selection exists, eviction risk relaxes).
P7. DAN'S DIRECTIVES (2026-07-05), three standing objectives, all offline and quota-free until their gates:
    U100 RULES-AS-IMPLEMENTED: understand how and when to play every card by probing the LOCAL engine
        itself (cg.api forward model), mechanic by mechanic: damage math with weakness/resistance, energy
        and retreat costs, status effects, prize flow, on-evolve and once-per-turn ability semantics,
        sub-select (CARD/COUNT/YES_NO) meanings, turn structure. Deliverables: docs/rules_as_implemented.md
        (plain-language, card-play oriented) plus tests/test_engine_mechanics.py pinning each VERIFIED
        mechanic as an executable test. The engine's behavior, not the printed text, is the real rulebook.
        STATUS CHECK (2026-07-06): tests/test_engine_mechanics.py currently has 20 of 21 test bodies as
        `pass  # TODO: implement game harness`, each sitting under a docstring/comment claiming the mechanic
        is "VERIFIED" (only test_damage_with_no_modifier_applied_as_base has a real assertion). pytest
        reports "21 passed" but an empty `pass` body cannot fail, so that count proves nothing. This is not
        done; do not report U100 as shipped or cite these tests as verification until each stub asserts a
        real value from a real cg.api game state. Build the missing fixture/harness (drive a real game to
        the state under test via cg.api, not a mock) rather than deleting the TODO comment without adding
        the assertion.
    U101 INVARIANT FUZZER (glitch hunt, part 1): run massive random-legal-play games across the 20 cores
        (reuse tools/parallel_gauntlet.py) asserting conservation invariants every step: total cards in
        deck+hand+discard+board+prizes, HP bounds, prize-count transitions, turn alternation, energy
        attached vs attached-this-turn flags. EVERY violation is logged to analysis/engine_quirks.md with a
        minimal reproduction. Dan's thesis: mistakes in the engine are opportunities, possibly by design.
    U102 CARD-TEXT DIFFERENTIAL AUDIT (glitch hunt, part 2): for every card and attack in the two meta
        decks plus our own deck (then widen), set up controlled forward-model states and compare the
        engine's actual outcome vs the printed text and damage. Catalog every divergence: engine does MORE
        than text says = candidate exploit; engine does LESS = trap to avoid. Exploits are LEGAL play-level
        moves (the engine is the rules; no platform manipulation, no egress); any exploitable quirk the
        shipped pilot can use ships as a flag-gated rule through the normal gates.
    U103 MIRROR BENCHMARK (Dan's success criterion, formalized 2026-07-05: TRUE SKILL = simulate the SAME
        deck and win the mirror OVER 50% of the time). Honest operationalization (the top players' actual
        bots are not downloadable, so the criterion is administered in two stages):
        (i) move-agreement with the deck OWNERS' held-out games on their deck (baseline 21.6% overall;
            report per-deck; a material rise licenses stage ii);
        (ii) LOCAL MIRROR >50%: same-deck mirror matches (their exact deck on BOTH seats), our improved
            pilot vs the best available model of that deck's play (the rebuilt ring's pilot for that deck;
            the current heuristic as a floor control). Must win >50% SUSTAINED (n>=400, CI excluding 0.5),
            and our-pilot-on-their-deck must also OUTPERFORM our-pilot-on-trolley vs the rebuilt ring (the
            deck ceiling unlocking, historically impossible: 409 vs 570);
        (iii) THE REAL TEST, run on the ladder: matchmaking pairs similar ratings, so a converged rating on
            their exact deck approaching the owner's (~1185) IS beating the actual them >50% (rating parity
            = >50% expected win rate, and at that band we get paired against the real top bots). A
            convergence-aware ladder run of the mirror deck is the final exam, only after (ii) passes and
            the rebuilt ring calibrates. Folds in the meta_deck_copy re-test (its recorded condition, a
            real deck-aware differentiator, is what U100-U102 build).

P8. BLINDSPOT AUDIT DIRECTIVES (2026-07-06, from a 15-agent adversarially-verified audit; each item below
    survived a refutation pass against state/hypotheses.md and findings.md 4B/4C. Four proposed levers were
    KILLED as already tried: move-level blunder mining as proposed (method reuses the falsified replay
    obs/action alignment), deck-space basics/energy sweeps (three probes already ran, all negative, closed),
    shipping the four mined decision gaps (each rule WAS built and failed its expert-agreement score), and
    re-adjudicating trolley_thick/yushin via resubmission (prior art exists for both). Do NOT reopen those.
    U104 STACKED RING RUN (highest priority, cheapest): the three ring-positive levers have never been
        measured together. ONE factorized in-process ring run, n=40 per arm, three arms: (1) trolley+ability
        (shadow-king config, baseline), (2) yushin+ability, (3) yushin+ability+attack_first. Promote-if:
        arm 3 beats arm 1 by more than +0.10 SAME-RUN delta (same-run deltas, not absolute rates, per
        analysis/candidate_decks_ring_gate.md). Notes: yushin is now contested (three +0.100 reads on
        2026-07-05, one +0.050 read on 2026-07-06), so this run doubles as the tiebreak (pooled 104/120 vs
        93/120); ability/attack_first liveness was only ever verified on the trolley deck, hence the
        factorized arms (check the yushin list actually contains once-per-turn-ability Pokemon); a WIN feeds
        the P3 lock-the-strongest-pair selection, not an immediate ladder slot.
    U105 THREAT AND PRIZE AWARENESS (the real capability gap): agents/heuristics.py has ZERO non-comment
        reads of prize state, never reads the opponent bench, and evaluates the opponent active only for OUR
        outgoing damage; should_retreat fires solely on own HP fraction (0.34), so an incoming OHKO is
        invisible and the pilot plays identically at 5-0 up and 0-5 down. The data is PROVEN available at
        match time (search/endgame.py reads player['prize'] from the raw obs, no cg import). Build TWO
        flag-gated rules, separately gated like the ability lever: (a) PTCG_THREAT_RETREAT: if the opponent
        active's best printed attack KOs our active and a bench survivor exists, allow retreat/promote
        independent of own-HP ratio; (b) PTCG_PRIZE_CLOSE: with 1-2 prizes remaining, prefer any legal
        attack line that takes the last prize. Gauntlet then calibrated ring, promote only on ring delta
        greater than +0.10. Cite the ability lever's RING read (+20pp) as precedent, never its +66.3 ladder
        WIN (reclassified noise).
    U106 STATE-MATCHED EXPERT LOOKUP (the one untried join): top_player corpora 20260703-20260706 (708k
        rows, 340MB) have ZERO analysis consumers and share the exact 27-column prefix with our state CSVs.
        kNN-join the state rows from our fresh loss games against expert outcomes on the 24 shared features.
        Guards (all four required): join all state rows from the loss games (15-20k rows, not 233), weight
        per game and normalize the 411k/296k win/loss corpus imbalance; report neighbor-distance support per
        loss bucket (thin support at early_collapse states is itself the informative result); interpret
        under the U65 caveat that the features are deck-blind; any resulting lever goes through the ring.
        Output: analysis/state_matched_expert_lookup.md separating "experts also lose from here" (stop
        spending pilot effort) from "experts win from here" (piloting gap, and what they did).
    U107 PER-BUILD LOSS LEDGER (prerequisite for honest targeting): the loss-bucket table driving iteration
        targeting mixes every retired build in the cumulative 809-replay pool, so bucket counts cannot be
        attributed to the shipped agent, and NO loss-mode measurement of the current shadow-king exists.
        tools/harvest_replays.py discards the episode-to-submission-ref association it already has at
        discovery time (discover_episode_ids pools ids across refs). Fix: persist an episode-to-ref manifest
        (at harvest time, plus a backfill via list_episodes per ref), add a per-build mode to
        tools/loop_state.py loss_distribution_from_dirs, rerun analysis/loss_classifier.py restricted to
        current-king and shadow-king episodes. Note state/current.md already has a section named "Per-build
        ledger" tracking ladder ratings; name the new thing differently (loss ledger by build).
    U108 SETTLEMENT ARITHMETIC FIX (governance): two past evictions violated the noise model. trolley_thick
        was evicted on a -112.3 read that state/current.md calls "far exceeds" M=240 when 112.3 is INSIDE
        the band (arithmetically BAND, not LOSS); attack_first was reverted on a NEUTRAL decided at only 3
        decisive episodes. Standing rule going forward: a ladder read inside the M band can NEVER evict a
        ring-positive build; ring evidence is the only eviction authority. Correct the state/current.md
        prose, record both as governance findings in findings.md 4D, and treat trolley_thick's collapse fix
        (-15.4pp empty-bench, 55% head-to-head) as ring-eligible again if a slot argument ever needs it.

P9. 30-DAY ROADMAP (2026-07-06): docs/ROADMAP-30D.md is the authoritative plan through Aug 5 and
    supersedes any conflicting ordering below. It came from a judged 3-posture design panel plus a gap
    calibrator; the honest math is in its section 0 (queued increments buy +60-120 of the +672 gap to
    number 1; the one stretch-tier mechanism is field-prior search, reopen condition formally MET in
    state/hypotheses.md via the favorable PIMC diagnostic). U104 is DONE and PASSED (+15.0pp,
    analysis/u104_stacked_ring_pass_run.md; earlier twin run read exactly +10.0 FAIL, hence the n=100
    confirmation below). Week-1 units, one per iteration, in this order:
    U111 fuzzer-contradiction adjudication FIRST (engine_quirks.md logs 193 card_conservation violations
         whose own itemizations sum to 60 while the checker claims 66; reconcile against
         tools/fuzz_invariants.py's 0-violations-over-2400-games result; one day, hard-capped; an
         unadjudicated engine contradiction poisons every downstream measurement).
    U112 stack confirmation at n=100/arm (same three U104 arms), then seat yushin+ability+attack_first
         per P3 slot governance and U108 (ring-positive replaces ring-inferior; no sub-band ladder read
         evicts it afterward).
    U110 hard ring (enriched arm with the hardest clones plus 800+-rated decks piloted by our stack; the
         standard ring saturates at 0.875-0.91 and our best build already reads 0.875, so gates above
         that are unresolvable without this).
    U105 threat/prize rules per P8: the 2026-07-07 INERT closure is SUPERSEDED (it measured an
         implementation bug: _opponent_best_attack_damage passed raw attack-ID ints into
         effective_damage, so threat damage read 0 for all 1057 cards; the unit test masked it by
         monkeypatching that exact function). Fixed 2026-07-08 with a non-mocked regression test; the
         fires-vs-inert re-run reads LIVE on both decks (trolley 3/12 flips, yushin 7/25 flips,
         analysis/u105_threat_prize_inert_check.md top section). NEXT for the compute session, not the
         loop: PTCG_THREAT_RETREAT ring A/B on the STANDARD calibrated ring (the hard ring does not
         exist, U110 unbuilt), n=100/arm, same-run delta vs the identical build with the flag off,
         promote-if more than +5pp, on the yushin deck first (its fire rate is higher and it is the
         best live build). PRIZE_CLOSE stays closed for a corrected reason: subsumed by choose()'s
         step-1 lethal FORCE, it can never flip a decision as written.
         PROCESS RULES from the 2026-07-08 audit, mechanical from now on: (1) a commit-msg hook now
         REJECTS em/en dashes in commit messages (the written rule was violated in 46% of subjects on
         Jul 7-8; if your commit fails, reword it, never bypass with --no-verify); (2) the writeup word
         budget is a HARD CEILING of 2000 with a freeze band: hold final_synthesis.md at 1900-1990
         words and never expand toward the line (7 commits thrashed expand/trim across it on Jul 6-8;
         2000 is a limit, not a target); (3) pre-registrations live in the JSON STATE block ONLY (the
         yushin row was silently lost by a prose regeneration, restored 2026-07-08; never hand-edit the
         prose tables); (4) U106's state_matched_expert_lookup verdicts are UNSOUND, do not build on
         them (win-only corpus so "experts also lose here" was never answerable, per-state invented
         buckets instead of real loss buckets, uncalibrated distance bands that an expert-to-expert
         null inverts, and 10k sampling while claiming 1.3M); the corrected follow-up is
         matched-ACTION extraction from the episode zips (data/episodes/, per-decision entry['action']
         exists; keep neighbor keys in knn_join), which is a compute-session job; (5) NEVER discard,
         stash, or checkout-over foreign uncommitted working-tree changes: a concurrent session's
         in-flight edits were wiped on 2026-07-08 (this correction block itself had to be reapplied);
         if the tree has modifications you did not make, leave those files alone and commit only your
         own unit's files.
    U109 oracle bound test: DONE 2026-07-07, FAIL, CLOSED. Oracle-search (determinize given each ring
         opponent's true decklist as opponent_prior, the best possible opponent model) tied the U112-
         confirmed stacked incumbent exactly (33-0-7 both arms, n=40/arm, delta +0.000) against the
         pre-registered +0.05 gate. Per docs/ROADMAP-30D.md section 6's Jul 13 kill criterion (met six
         days early, with an unambiguous zero-delta margin that needs no larger-n rerun): the SEARCH LANE
         IS DEAD for this competition. Do NOT start U113 (field-prior search, a/b/c) on the loop; a
         learned prior can only be worse than the oracle already tested. Analysis: analysis/u109_oracle_
         bound_test.md, findings.md 4B. Week-2-3 capacity reroutes to U106-driven rule mining, U103, and
         U102 per the roadmap's own reallocation plan. U106/U107/U103/U102 continue per the roadmap's
         week-2-3 table. Escalate to Dan: the Rules 2.2.b Submissions-page screenshot check (DAN-1) and
         every pair/exploit design decision (P5).

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
      RE-CHECKED 2026-07-04 (offline, no ladder slot): tools/measure_ability_isolated.py toggles
      agents.heuristics._ABILITY per seat (not per process), so an on/off arm (only our pilot has
      the lever) is directly measurable against the confounded on/on arm the original env-var-baked
      gauntlet could only produce. Three independent runs (n=200/200/300 per arm, 900 isolated-arm
      games total): isolated diff_pp +2.5, -0.5, -1.3 (mean +0.2); confounded diff_pp -4.0, +5.5,
      -0.7 (mean +0.3). Both oscillate around zero at every sample size tried; neither the confound
      nor its removal produces a stable positive effect. Conclusion: the +4.0pp offline gauntlet
      point estimate was itself noise-dominated, independent of the mirror-match confound; it should
      not be read as confirming a real win-rate edge. Does not change the shipped shadow-king
      disposition (L9: ring evidence, not gauntlet or ladder reads, is the standing decision gate;
      the underlying 0/554 blind-spot motivation is untouched). analysis/ability_isolated_confound_check.md.
      RE-CHECKED 2026-07-04 (offline, the OTHER offline signal): does the calibrated bracket ring's
      +20.0pp reading (analysis/ability_ring_check.md, L9's standing decision gate) share the
      gauntlet's mirror-match confound? No: code-traced and test-verified that ring's clone:<family>
      opponents (_clone_opponent) never call heuristics.choose() and so never read _ABILITY at all
      (it is read in exactly one place, choose()'s _resolve_ability closure); the ring's +20.0pp was
      already a genuinely one-sided measurement, unlike the gauntlet's +4.0pp. New regression test
      tests/test_opponents.py::test_clone_opponent_ignores_ability_flag_never_reads_it.
      analysis/ability_ring_confound_check.md.
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
  L9. NOISE RECALIBRATION (correction 2026-07-04, HIGH PRIORITY): the observed same-build spread is ~452 to
      691 (one king copy, ref 54282104, drifted 691.5 -> 494.8 on its OWN reads), so M=60 is FAR too tight and
      a single-read ladder A/B cannot confirm ANY lever we can build. Treat the "ability WIN" recorded below
      (561.1 vs a 494.8 LOW king draw, +66.3) as a NOISE ARTIFACT, not proof: 561.1 is mid-range of the king's
      own 452-691 reads. Log this as a top methodological finding in findings.md. NEW RULES:
      (a) the CALIBRATED BRACKET RING (tau 0.857), NOT single-read ladder A/Bs, is the lever DECISION gate.
      (b) FLOOR: keep the best ring-supported build in the scored pair. The ability build (ring +20pp) is it:
      NEXT quota window, submit the ABILITY build (not a plain king copy) to restore it as the scored floor,
      then HOLD. (c) STOP spending scored slots to confirm sub-band levers (the attack_first slots were wasted
      noise-chasing). (d) Ladder submissions are now for FLOOR MAINTENANCE and the Aug 10-16 endgame
      variance-harvest campaign ONLY; that campaign is the PRIMARY rank lever (the noise band exceeds any build
      gain we can make) and stays booked. Historical record follows (unchanged): U92 closed 2026-07-04 (FAIL); comprehension track (U90+U91+U93+U94) fully shipped and
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
- ANTI-CHURN (2026-07-05): do NOT spend an iteration board-checking a FROZEN board or logging another
  "board-check holds / Nth freeze" entry. Board-check at most ONCE per quota window (or when a pre-registered
  in-flight A/B is due to settle). If nothing on the board changed and no TRACK L build is awaiting a slot,
  spend the iteration on TRACK S (writeup) or a deck-exploration candidate, or do nothing. Repetitive freeze
  logging burns premium-model usage for zero value; the floor is held and the endgame is booked, so there is
  nothing to watch minute to minute.
- ONE loop only. Do NOT run parallel sessions: the ladder is quota-bound (5/day), slot-bound (2 scored slots),
  and noise-bound (observed same-build spread ~452-691, M refit to ~240), so more compute cannot buy rank,
  only more offline infra.
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
  pokemon-tcg-ai-battle. Resubmission of an EXISTING build is allowed for floor maintenance and the P3
  lock-the-strongest-pair operation (it is the mechanism); what stays forbidden is submitting a NEW lever
  without its pre-registration and gates. Keep the ledger in autoloop_status.md.
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
