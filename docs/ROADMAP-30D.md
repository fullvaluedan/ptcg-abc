# 30-Day Roadmap: 2026-07-07 to 2026-08-05 (then the lock window to Aug 16)

Written 2026-07-06 from a 4-design judge panel (ceiling / grind / asymmetric postures plus a gap
calibrator), each design adversarially scored for ceiling, feasibility, ledger consistency, and
measurement honesty. This document is the authoritative plan; LOOP_BRIEF.md P9 points here.
No em dashes anywhere in this repo.

## 0. The honest math first (read this before the plan)

- The gap: our true rating is ~571 (31 pooled same-build reads). Number 1 is 1242. That is +672
  rating points, roughly 6.7 logit units at the calibrated ~100-points-per-logit scale. An agent at
  1242 beats today's median opponent 99.7% of the time.
- The calibrated exchange rate (the only anchor measured on both sides): +20pp on the bracket ring
  bought +112 pooled rating (ability lever), so ~5.6 rating points per ring percentage point.
- The entire queued incremental inventory (U104 stack, U105 rules, everything priced) buys +60 to
  +120 of the needed +672. Flag rules on a fixed priority ladder are a converging geometric series.
- Convergence is NOT the bottleneck: the field's top agent hit 1024 on day ONE of the competition.
  A genuinely stronger agent converges within ~50-100 games. The bottleneck is true strength.
- Instrument warning: the bracket ring saturates near 0.875-0.91 and our best build already reads
  0.875, so ring gates above that are unresolvable without a harder ring (U110 below).

Tiered targets, priced honestly:

| Tier | Converged rating | Field position | Probability if plan executes |
|---|---|---|---|
| Floor (banked) | 630-690 | p40-p55 | high, U104 stack already ring-PASSED |
| Target | 700-780 | p55-p70 | moderate, needs the search lane to hit |
| Stretch | 800-950 | p75-p95 | 8-15%, needs field-prior search to transfer above the calibration band |
| Number 1 | 1242 | p100 | 1-2%. No currently known mechanism reaches it. See section 5. |

Nobody can honestly promise number 1 in 30 days from p22. This plan maximizes the probability and
keeps the Strategy prize (the actual money: $30k, 70% judged on model approach, ladder-independent)
fed by every workstream win or lose.

## 1. Week 1, Jul 7-13: falsify cheap, bank the stack, fix the instruments

| # | Item | Owner | Gate |
|---|---|---|---|
| U109 | ORACLE BOUND TEST: inject each ring clone's TRUE decklist into determinize's existing opponent_prior parameter (search/determinize.py lines 188/214, already plumbed). One ring run upper-bounds what ANY learned field prior could ever achieve, before a day is spent modeling. | compute session | Oracle search beats the U104 stacked incumbent on the ring by more than +0.05 same-run at n=40/arm. FAIL kills the entire search lane on Jul 13 (see kill criteria). |
| U110 | HARD RING: extend the calibrated ring with an enriched hard arm (the 2-3 hardest clones plus 800+-rated harvested decks piloted by our stacked build) so gates can resolve above the 0.875 saturation point. Report loss-rate against hardest clones as the secondary metric. | compute session | Hard-ring arm produces a spread (best builds separated by more than 5pp) where the standard ring reads them within 2pp of each other. |
| U111 | FUZZER CONTRADICTION ADJUDICATION: analysis/engine_quirks.md logs 193 card_conservation violations, but its own itemizations sum to 60 while the checker reports 66 (likely double-counting attached energy). Reconcile against tools/fuzz_invariants.py (0 violations over 2400 games). One day, hard-capped. | loop | engine_quirks.md updated with a verdict: checker bug (fix and close) or real divergence (escalate to U102 as the highest-priority probe). |
| U112 | STACK CONFIRMATION + SEATING: re-run U104's three arms at n=100/arm (the first run read exactly +10.0 FAIL, the second +15.0 PASS, so run-to-run swing is ~5pp and n=40 is a 1-sigma read). If confirmed, seat yushin+ability+attack_first per P3 slot governance. | compute session, then loop for the tarball | Confirmed delta more than +0.10 at n=100. Seating honors U108: the ring-positive stack replaces the ring-inferior slot occupant; no ladder read inside M=240 can evict it afterward. |
| U105 | THREAT/PRIZE RULES (benefits both the heuristic AND the future search eval): PTCG_THREAT_RETREAT and PTCG_PRIZE_CLOSE per LOOP_BRIEF P8. | loop | Each rule separately: fires-vs-inert check, gauntlet direction agreement, then hard-ring delta more than +5pp same-run. |
| DAN-1 | Rules 2.2.b check: screenshot the logged-in Submissions page for a final-submission selection UI. One screenshot, reprices all August decisions (if selection exists, eviction risk relaxes and late experimentation is cheap). | Dan, 5 minutes | Answer recorded in analysis/final_scoring_semantics.md. |

## 2. Weeks 2-3, Jul 14-27: the class-change bet (only if U109 passed)

The one mechanism with stretch-tier ceiling, and the recorded reopen condition for the closed search
lever (analysis/search_recovered_on_ladder.md: "a determinization prior that models the real opponent
field instead of the mirror"). The registry already marks the retest condition MET via the favorable
PIMC diagnostic (state/hypotheses.md, U45 lane). New-since-closure assets that make it buildable now:
708k-row expert corpus (zero consumers), archetype classifier, harvested real bracket decklists,
100% card_effects tag coverage of both big meta decks.

| # | Item | Owner | Gate |
|---|---|---|---|
| U113a | FIELD PRIOR v1: opponent deck posterior from observed cards. Start census-weighted (bracket decklist frequency from tools/bracket_decks.py harvests), update as opponent cards reveal. Pure Python, ships in the tarball. | compute session builds/trains, loop wires | Determinization hidden-state accuracy on held-out real ladder games beats the mirror prior by a pre-registered margin (measure with the U27 PIMC diagnostic channel). |
| U113b | SEARCH EVAL UPGRADE: port the prize-differential eval (search/eval.py) plus U105's threat terms into the search leaf eval. | loop | Offline gauntlet direction agreement, then hard-ring same-run delta vs the stacked heuristic incumbent. |
| U113c | INTEGRATED SEARCH BUILD: field prior + upgraded eval + time-bank management (the 600s bank is our least-used asset; budget per-decision draw by game phase). | compute session | Hard-ring delta more than +0.10 same-run vs the stacked heuristic at n=100/arm. Checkpoint Jul 19 (mid), kill Jul 27 (final, see kill criteria). |
| U106 | STATE-MATCHED EXPERT LOOKUP (runs in parallel on the loop, feeds U113b and rule mining): kNN-join our loss states to expert outcomes per LOOP_BRIEF P8 guards. | loop | analysis/state_matched_expert_lookup.md separating deck-losses from piloting-losses with support counts per bucket. |
| U103 | MIRROR LADDER stage i: move-agreement on deck owners' held-out games with the stacked pilot (baseline 21.6%). Stage ii only if stage i rises materially: local mirror above 50% at n=400, CI excluding 0.5. This is the ONLY licensed route back into meta-deck territory. | compute session | Stage gates as recorded in LOOP_BRIEF P7 U103. A stage-ii pass licenses exactly one pre-registered ladder slot for the mirror deck. |
| U102 | DIFFERENTIAL AUDIT, capped: engine-vs-text adjudication for every card appearing in more than 10% of harvested field decks (the cards we actually face). ENGINE_DOES_MORE = candidate legal exploit, route through the ring; ENGINE_DOES_LESS = trap, document. | compute session, rules design NEVER assigned to the loop (P5) | Every audited card gets a MATCHES/MORE/LESS verdict with a committed probe. Capped at top-15 cards if U111 closed as a checker bug. |
| U107 | PER-BUILD LOSS LEDGER per LOOP_BRIEF P8 (persist episode-to-ref manifest, per-build loss modes). Feeds honest targeting for weeks 3-4. | loop | Loss-mode table for the CURRENT stacked build specifically, not the mixed 809-pool. |

## 3. Week 4, Jul 28-Aug 5: measure, decide, rehearse

| # | Item | Owner | Gate |
|---|---|---|---|
| U114 | STACKED RING RUN v3: one factorized run combining everything that individually cleared its gate (deck, ability, attack_first, U105 rules, any U102 exploit rule, search build if alive). Arms isolate each addition. This produces the lock-pair shortlist. | compute session | Hard-ring, n=100/arm, same-run deltas. |
| U115 | CONVERGENCE RESIDUAL SIGMA: fit rating-read spread vs episode count from the 57+ pooled same-build reads plus fresh trajectories. Output: residual sigma after the ~2-week convergence window. Prices the identical-vs-hedge pair decision. | compute session | analysis/convergence_sigma.md with a CI, surviving the age-stratified-refit correction. |
| U116 | PAIR PRE-REGISTRATION: combine the shortlist, residual sigma, and the DAN-1 answer into the E[max] arithmetic (two copies of the strongest build by default; a hedge only if the runner-up's ring CI overlaps AND E[max of two] beats E[best single]). Named tarballs and hashes, committed BEFORE any slot is spent. | Dan-interactive | Signed pre-registration in state/current.md by Aug 5. |
| U117 | LOCK REHEARSAL: build both final tarballs, pass tests/test_grader_submission.py on the exact bytes, submit one rehearsal copy, confirm COMPLETE before any further roll (the card_effects ERROR cascade is the cautionary precedent). Commit the minute-by-minute Aug 12-13 checklist. | loop | Rehearsal scored COMPLETE under identical hash. |
| WRITEUP | Full 2000-word Strategy draft in docs/writeup/ by Aug 5: the measurement regime, the refuted-ledger discipline, the transfer-failure corrections, the field-prior arc (hit or miss), the exploit-hunt honest accounting. Sep 1 self-imposed submit unchanged (hard deadline Sep 13). | Dan-interactive + loop conformance pass | Draft committed, within 2000 words, no Pokemon artwork, self-made figures only. |

## 4. Aug 6-16 (outside the 30 days, the finish)

Lock the pre-registered pair Aug 12-13 (buffer to the Aug 16 deadline for ERROR recovery within the
5/day quota). Newer refs play more frequently through the ~2-week convergence window, so the pair
converges to true strength by the final leaderboard. Standing U108 rule all the way down: no ladder
read inside M=240 evicts a ring-positive build.

## 5. What number 1 would actually require (so the ambition stays calibrated)

1242 means beating the opponents who currently go 50-50 with us 999 times in 1000. The known paths
that COULD compound there, none currently priced above a few percent: (a) the field-prior search
transferring far above the ring's calibration band AND stacking with a U103 mirror-deck unlock,
(b) a real ENGINE_DOES_MORE exploit from U102 that applies every game (this is why the audit stays
funded despite a low median), (c) the top teams erring in the final window while our pair is locked
clean. If a mid-July result makes stretch look conservative (oracle bound far above incumbent, or a
confirmed exploit), re-plan immediately in a Dan-interactive session; do not wait for the calendar.

## 6. Kill criteria (dated, non-negotiable)

- Jul 13: U109 oracle fails to beat the stacked incumbent by +0.05 => the search lane is DEAD for
  this competition (the ceiling was never there); weeks 2-3 capacity reroutes to U106-driven rule
  mining, U103, and U102.
- Jul 13: U111 not adjudicated => stop everything on the loop until it is (an unadjudicated engine
  contradiction poisons every downstream measurement).
- Jul 19: U113 mid-checkpoint: field prior not beating the mirror prior on hidden-state accuracy =>
  descope to U113b only (eval upgrade without the prior).
- Jul 27: U113c not clearing the hard-ring gate => freeze the pilot at the best ring-confirmed
  config; all remaining capacity to endgame ops and the writeup.
- Aug 5: U116 pair pre-registration must exist. Any lever not ring-cleared by this date is dead
  regardless of promise (a late unproven lever can only evict a good pair member).
- Standing: any week whose gate depends on a single ladder read is misdesigned; rewrite it.
- Standing: exploit-rule design and pair arithmetic are never assigned to the unattended loop (P5).

## 7. Sources

analysis/u104_stacked_ring_pass_run.md, analysis/u104_stacked_ring_run.md (the FAIL-at-+10.0 twin),
analysis/search_recovered_on_ladder.md, analysis/pimc_diagnostic.md, state/hypotheses.md (search
retest MET), analysis/ring_calibration.md, analysis/ability_ring_check.md + analysis/noise_model_refit.md
(the 5.6 rating/ring-pp anchor), analysis/final_scoring_semantics.md, analysis/engine_quirks.md
(the 66-vs-60 itemization contradiction), data/episodes/manifest.csv (top agent at 1024.6 on day 1),
LOOP_BRIEF.md P7-P8, findings.md.
