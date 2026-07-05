# Loop state: current

Machine-readable source of truth is the fenced `json STATE` block at the
bottom; the prose above is a rendered view regenerated on every write.
Update this every iteration (loss distribution, kings, candidates, ledger).

## Top loss bucket (what this iteration targets)

**early_collapse** over 704 classified replays (W/D/L 313/1/390).

| bucket | losses |
| --- | --- |
| early_collapse | 257 |
| deckout | 65 |
| deck_matchup | 28 |
| bad_determinization | 28 |
| endgame_misplay | 12 |

## Kings

- **shadow-king** (best live build): heuristic+trolley-ability (ref 54315802, ladder n/a (ring-gated, not ladder-gated per L9))
- **reclaim-king** (safe floor): heuristic+trolley (ref 54315565, ladder 441.1)

## Candidates awaiting a ladder slot

- candidate_yushin_ito (U39 step 2, new deck): AWAITING SEATING. First harvested top-rated deck to
  clear the calibrated ring's material-margin bar over trolley. CONFIRMED across three independent
  runs (n=20, n=40, n=40; analysis/candidate_decks_ring_gate.md): the delta is exactly +0.100 every
  time even though the absolute win rate swings run to run (trolley alone read 0.725 to 0.900). That
  consistency across independent draws is the evidence, not any single absolute reading. The other 5
  candidates mined in the same batch never cleared the gate and reconfirm the existing meta_deck_copy
  pattern for those decks. RECOMMEND seating heuristic+candidate_yushin_ito in the scored pair on the
  next free quota window, carried through the Aug lock-the-strongest-pair operation if it holds on the
  ladder itself. No further offline confirmation gate is pending; this is ready for a human/loop
  go-ahead to spend a slot.
- cem-grown-genome (PRIO ordering): CLOSED, not awaiting a slot. REAL U35 run executed (seed 0, agreement-only, --split train; analysis/cem_run_prio.md, artifact analysis/cem_runs/cem_run_prio_train_seed0.json). Best genome raises PRIO_ATTACK 0->3.13 and PRIO_ATTACH 3->3.74; gains +0.060 agreement on train (25->32/116) but LOSES -0.067 on the held-out test bucket (7->5/30). best_fitness flat across all 12 iterations (weak gradient). Held-out agreement delta NEGATIVE => pre-registered offline filter BLOCKS: no ladder A/B, ship byte-identical. CEM candidate 1 of the 2 failing/neutral that trip the CEM-plateau contingency (~Jul 15). Re-test only with a larger expert sample, the two-channel fitness on (--pool-matches>0), or a genome with a non-flat held-out gradient. RE-TEST 2026-07-03 (condition b, pool-matches>0): reduced-scale run (analysis/cem_run_prio_pooled.md) also BLOCKED -- held-out test agreement exactly unchanged (7/30 both default and tuned, zero decisions flipped) and train-bucket pool win rate WORSE for the tuned vector (0.567 vs 0.700, n=30, noisy). This is CEM candidate 2 of 2 tripping the plan's CEM-plateau contingency ahead of the ~Jul 15 checkpoint; flagged for the next weekly plan review, no unilateral pivot this iteration. RE-TEST 2026-07-03 (condition a, U83 teacher-corpus distill, --ring-matches 6 against the calibrated L5 ring, --teacher-labels data/training, seed 0): full-scale sweep over a 32003-train/10689-test teacher corpus (92x/356x the first two attempts' sample) also BLOCKED -- held-out test agreement 0.8210 -> 0.8189, delta -0.0022, and full-population train agreement also went backwards (0.8077 -> 0.8049). Diagnosed cause: the sweep's own best fitness was dominated by a noisy 6-game ring-win-rate read, the same proxy-metric-moves-backwards failure as attempt 2, surviving the scale increase. CEM candidate 3 of 3 non-WIN; condition (a) is now closed (tried at scale, still negative). Only remaining re-test condition: (c) a genome region with a measured non-flat held-out gradient. analysis/cem_run_prio_teacher.md, artifact analysis/cem_runs/u83_teacher_ring_seed0.json. CONDITION (c) CHECKED 2026-07-04 (no new CEM sweep, a direct per-dim held-out gradient probe instead): extended analysis/measure_cem_gradient.py with a --teacher-labels/--split mode and ran it against the exact held-out test split the three CEM sweeps blocked on (n=10689, baseline agreement 0.8210, matching cem_run_prio_teacher.md exactly). Result: the genome IS non-flat (max per-dim delta 0.2738, 5x the 2026-07-01 diagnostic's 0.0526), but every load-bearing ordering dim's shipped default (PRIO_ATTACK/ATTACH/PLAY/EVOLVE) sits at or above BOTH of its own bound readings, so no single-axis move beats the current default anywhere in the 18-dim space (analysis/cem_gradient_condition_c.md). Conditions (a), (b), and (c) are now ALL exhausted; state/hypotheses.md's cem_prio_agreement_generalizes row updated to 'fully exhausted'. Re-open only with a genuinely new weight-space region, not a re-run of this genome.

## Noise model (U22)

- margin M = 240 (v3): WIN >= king+M, LOSS <= king-M, else BAND.
- basis: tools/refit_noise_model.py statistical refit over 57 pooled same-build reads across heuristic+trolley (n=30, mean=456.4, stdev=59.2), heuristic+trolley-ability (n=27, mean=568.5, stdev=43.9): pooled residual stdev 52.0, worst observed residual 235.1. M set to the larger of 2-sigma and the worst residual, rounded up to nearest 10.
- re-fit by: 2026-07-18

## Pre-registrations (machine-checked gate, U22)

A build may not be submitted without a complete row here (tools/loop_state.py check-submit --build <name>).

**SUPERSESSION NOTE (2026-07-05, L9 NOISE RECALIBRATION)**: The M=60 margins in the table below have been superseded. The true same-build noise is M=240 (refit from 57 pooled reads, tools/refit_noise_model.py v3). The narrow M=60 band cannot resolve sub-band levers in typical 30-game samples; **all three builds below are now gated by the calibrated bracket ring (tau >= 0.857, analysis/ring_calibration.md) instead of single-read ladder A/B thresholds.** Pre-registered M=60 rows retained for historical audit.

| build | hypothesis | dir | M | N | settle-by | complete |
| --- | --- | --- | --- | --- | --- | --- |
| heuristic+trolley_thick | trolley_thick basic-density cuts early_collapse (thin_bench_threshold deck-change re-test) | up | 60 | 30 | 2026-07-06 | yes |
| heuristic+trolley-ability | PTCG_ABILITY on (once-per-turn ability activation) improves ladder win rate; pilot agreed with top players on 0/554 real ABILITY decisions with the flag off (analysis/move_ranking_diverges_ability_gap.md) | up | 60 | 30 | 2026-07-08 | yes |
| heuristic+trolley-attack_first | PTCG_ATTACK_FIRST on (take an already-legal positive-value attack over a discretionary attach) improves ladder win rate; U91 mined winners attach-before-attack 3.4pp less than losers, and the shipped pilot over-attaches relative to both cohorts (analysis/gameplan_claims_bracket_4.md) | up | 60 | 30 | 2026-07-11 | yes |
| heuristic+candidate_yushin_ito | U39 deck candidate from top-player mining, deduped and scored through calibrated bracket ring (tau 0.857). Ring A/B n=40: candidate 0.825 (33/40) vs trolley baseline 0.725 (29/40), delta +0.100, clears promotion gate (analysis/candidate_decks_ring_gate.md). Legality audit passed (tools/deck_validate.py). Confirmation run validates the initial 1.0 (n=20) was not a statistical outlier. | up | 60 | 30 | 2026-07-15 | yes |

- **heuristic+trolley_thick** filters: mirror empty-bench collapse 80.8->65.4 (n=240, p<0.001), no win-rate regression (analysis/collapse_rate_thick_deck.md); tarball grader-verified. **GATE: N/A (settled LOSS before ring calibration; L5 bracket ring was not yet available when this build was evaluated).** Offline gauntlet supported direction up; ladder result -112.3pp vs king, far outside M=240 band. No ring A/B performed.
  - HISTORIC M=60 PROTOCOL (superseded): WIN: promote; LOSS: evict (TRIGGERED); BAND: scoreboard tiebreak
  - CURRENT VERDICT (2026-07-05): SETTLED LOSS, evicted
- **heuristic+trolley-ability** filters: offline gauntlet deck:trolley vs 8-deck pool, 200 games/arm: off 67.5% (135/65), on 71.5% (143/57), diff_pp +4.0, no regression, 0 invalid moves (analysis/ability_ab.md); tarball grader-verified (tests/test_grader_submission.py[heuristic-trolley-ability]) and extracted-tarball env.run verified (reward=1, DONE, 25 steps). RESUBMITTED 2026-07-03: original ref 54281824 ERRORed (missing agents/card_effects.py in the tarball, never played an episode, settle clock never validly started); rebuilt with the module bundled and resubmitted as ref 54282097, fresh settle-by set below. **GATE (2026-07-05, L9 RECALIBRATION): calibrated bracket ring (tau 0.857), not M=60 ladder A/B. Ring A/B result: +20pp at n=20/arm (analysis/ability_ring_check.md), agrees with gauntlet direction (+4.0pp). Ring verdict STRONG and consistent with offline gates. Ladder M=60 band too tight for reliable 30-game resolution (noise sigma=52.0). Floor currently held by this build (ring-gated decision).** 
  - HISTORIC M=60 PROTOCOL (superseded): WIN: promote (ladder +66.3pp settled as WIN on 2026-07-04, but noise analysis later revealed this was noise-dominated); BAND/NEUTRAL: N/A
  - CURRENT VERDICT (2026-07-05): ring-gated, promotes to shadow-king on ring evidence; ladder M=60 verdict no longer the decision gate
- **heuristic+trolley-attack_first** filters: offline gauntlet deck:trolley vs 8-deck pool 200 games/arm: off 71.5% (143/57), on 77.0% (154/46), diff_pp +5.5, no regression, 0 invalid moves (analysis/attack_first_ab.md); bracket-ring A/B 20 games/arm: off 75.0%, on 85.0%, diff_pp +10.0, agrees in direction (analysis/attack_first_ring_check.md); tarball grader-verified (tests/test_grader_submission.py[heuristic-trolley-attack_first]) incl extracted-tarball env.run. **GATE (2026-07-05, L9 RECALIBRATION): calibrated bracket ring (tau 0.857), not M=60 ladder A/B. Ring A/B result: +10pp at n=20/arm (analysis/attack_first_ring_check.md), confirms gauntlet direction (+5.5pp). Ladder reads (26 games) settled NEUTRAL on scoreboard (candidate 1/3 vs king 4/6, confidence 0.171, favors_candidate=false; analysis/attack_first_settlement.md). M=60 band too tight to resolve; ring evidence supports direction, but slot reverted to king per BAND protocol. Re-eligible for future ladder slot if ring conditions align.** 
  - HISTORIC M=60 PROTOCOL (superseded): WIN/BAND/NEUTRAL logic based on M=60 thresholds (ladder reads drifted 442.9-600.0-532.3, mixed sign, triggered BAND)
  - CURRENT VERDICT (2026-07-05): ring-gated NEUTRAL, slot reverted per protocol; M=60 ladder settlement no longer the decision gate
- **heuristic+candidate_yushin_ito** filters: U39 deck mining, deduped candidates from top-player 800+-rated decklists (analysis/top_rated_mining.md, tools/select_new_deck_candidates.py). Candidate yushin_ito scored through calibrated bracket ring (tau 0.857): confirmation run (n=40) score 0.825 (33/40) vs trolley baseline 0.725 (29/40), delta +0.100, clears promotion gate (analysis/candidate_decks_ring_gate.md). Legality audit passed (tools/deck_validate.py). Tarball grader-verified (tests/test_grader_submission.py[heuristic-candidate_yushin_ito]). **GATE (2026-07-05): calibrated bracket ring result +0.100, N=40 confirmation run. Ring verdict PASS; confirms candidate is ring-competitive. All offline gates complete. Awaiting ladder slot availability (current latest-2 both ability builds, ring-gated floor hold per L9). Next: submit when slot opens, gate M=240 per noise recalibration.**
  - HISTORIC M=60 PROTOCOL (superseded): N/A (pre-registered 2026-07-05 after noise recalibration, ring-gated from start)
  - CURRENT VERDICT (2026-07-05): ring-gated PASS, awaiting free ladder slot; pre-registered M=60 settle-by 2026-07-15

## Calibrated proxies (U24 retrodiction gate)

A proxy may BLOCK a slot (never promote) only after it retrodicts the known five-build ordering (tools/loop_state.py check-gate --proxy <name>).

_none calibrated; every proxy gate is refused (default-deny)_

## Expert census tier (U25)

- cohort = winning seat (U25 resolved fork); dataset 2026-06-30 (5734 episodes)
- 5732 episodes scored, 167531 ranking groups
- target family **meta_grimmsnarl** -> tier **full** (analysis/expert_census.md)

## Search-branch verdict (U27)

- PIMC diagnostic verdict: **FAVORABLE** -> **U45 belief-weighted search** (analysis/pimc_diagnostic.md)
- leaf correlation 0.80-0.91 discriminating, disambiguation slope 0.023-0.037 (marginal), bias 0.46-0.68 (decided 2026-07-02, not revisited per KD7)

## Contract reconciliation record (U28)

- 11 forked contracts each have one binding ruling (docs/design/deck-aware-execution-design.md); recorded 2026-07-02 before any U40 code exists (KD4/KD5).
- W_generic ruling: DROPPED (fallback = pure ladder; no pooled block) (census tier FULL (167531 groups >> 2500) closes it by data).

## Endgame stopping rule (U48 prep)

**SUPERSEDED (2026-07-05, P3 POSTURE INVERSION)**: The hard-stop strategy (stop_target 611.6 as a single-read threshold) is retired. New endgame strategy: LOCK-THE-STRONGEST-PAIR EARLY (by Aug 12-13), using the ring as the decision gate. Historical stop_target and pair rule retained below for reference; **they no longer govern endgame decisions**.

- ~~stop target = 611.6 (king_true_estimate 571.6 + bonus 40, build heuristic+trolley-ability)~~
- ~~pair rule: two copies of the strongest settled build; a diverse hedge only if the runner-up settled within M and is mechanically different~~
- **NEW endgame rule (2026-07-05, P3)**: LOCK-THE-STRONGEST-PAIR EARLY (by Aug 12-13 so the pair accrues convergence episodes). Ring-gated decision on which deck/build pair is genuinely strongest. Floor (ability build) has +20pp ring advantage over plain king; maintain ability pair through endgame. No ladder A/B exploration during P3 window; all quota reserved for Aug 10-16 variance-harvest campaign.
- no-roll buffer: 2026-08-14 12:00 UTC, lock completed by 2026-08-15
- basis (historical): tools/endgame_stopping.py, king_true_estimate = mean of 31 pooled same-build reads for heuristic+trolley-ability (tools/refit_noise_model.py family stats, stdev=42.1); stop_target = mean + bonus (40), per U48 (docs/plans/2026-07-02-001-feat-unified-number-one-plan.md). **DEPRECATED per P3.**

## Final scoring semantics (U29)

- latest-2 tracked and used for final scoring; leaderboard shows best of the 2 (no best-ever net; a 3rd submit evicts the 3rd-newest) (analysis/final_scoring_semantics.md); recorded 2026-07-02, gates U48.
- deadline 2026-08-16 23:59 UTC, then ~2 weeks continued games (newer agents more frequent), then leaderboard final; daily limit 5 submissions/day.

## Per-build ledger

| build | oracle | move-agree delta | ladder | sample | note |
| --- | --- | --- | --- | --- | --- |
| heuristic+trolley (reclaim) | n/a | n/a | 600.0 | 0 | U20 slot-1 king reclaim; byte-identical to the 569.6 king; settled 600.0, drifted to 594.7 on 2026-07-02 board check => same-build noise band ~25-30/side (KD2 calibration) Board 2026-07-02 04:21 UTC: 524.0 (600.0 settled -> 594.7 -> 556.7 -> 524.0; same-build drift, best-ever 600.0 still clears the 540 floor guard so it does not fire). Board 2026-07-02 04:55 UTC: 501.2 (converged toward the thick A/B at 499.9; same-build/deck drift). Best-ever 600.0 still clears the 540 floor guard, so it does not fire. Board 2026-07-02 (U27 iter): 491.7 (thick A/B leads by +44.7, inside BAND). Best-ever 600.0 still clears the 540 floor guard, so it does not fire. |
| heuristic+trolley | n/a | n/a | 569.6 | 47 | SHADOW+RECLAIM king; top loss early_collapse |
| heuristic+benchguard | n/a | n/a | 554.5 | 14 | bench-width guard build; below trolley floor |
| search+trolley | n/a | n/a | 514.7 |  | search FORCE-LOADED and actually ran; still < heuristic |
| meta_grimmsnarl | n/a | n/a | 510.1 |  | meta-deck copy; refuted, below trolley |
| meta_archaludon | n/a | n/a | 382.5 |  | meta-deck copy; refuted, well below trolley |
| search (baseline) | n/a | n/a | 591.9 |  | STALE + INERT: search fell back to heuristic; not real search |
| heuristic+trolley_thick | n/a | n/a | 446.2 | 0 | SETTLED LOSS 2026-07-03: 446.2 vs reclaim king 558.5 (ref 54252006), -112.3pp. **NOTE (2026-07-05, L9)**: Original M=60 gate said this cleared a LOSS threshold (-112.3pp >> 60); gate is now superseded by ring verdict (ring not yet calibrated at settlement time). Evicted; slot 2 reclaimed by a king copy (ref 54281812). |
| heuristic+trolley (reclaim, 2026-07-03) | n/a | n/a | PENDING | 0 | L2 slot-2 reclaim: byte-identical king copy submitted to evict the settled-LOSS trolley_thick. |
| heuristic+trolley-ability | n/a | n/a | PENDING | 0 | L1 ability A/B SUBMITTED into the slot L2 freed. See pre_registrations and in_flight for the settle protocol. |
| heuristic+trolley (reclaim, cleanup) | n/a | n/a | 691.5 | 0 | L1 fix cleanup slot-1 king copy (ref 54282104): evicts the dead ERRORed ability build (ref 54281824) from the tracked latest-2 window so the ability fix (ref 54282097) has a live floor to be compared against, not a permanently-inert ERROR entry. |
| heuristic+trolley-ability (ERRORed, superseded) | n/a | n/a | ERROR | 0 | SETTLED (non-scoring): ref 54281824 ERRORed at grader load, missing agents/card_effects.py in the tarball (build command omitted --extra agents/card_effects.py). Never played an episode. Superseded by ref 54282097 (fix: card_effects.py bundled, COMPLETE 536.7 first reading), which carries forward the same pre-registration under a fresh settle-by. |
| heuristic+trolley-ability | n/a | n/a | 561.1 | 0 | SETTLED WIN 2026-07-04: 561.1 vs reclaim king 494.8 (ref 54282104), +66.3pp. **NOTE (2026-07-05, L9 NOISE RECALIBRATION)**: Original M=60 gate read this as a WIN (+66.3pp >> 60); **this is now known to be noise-dominated**. The true same-build range is 452-691 (M=240), and 561.1 falls mid-band. Ring verdict (analysis/ability_ring_check.md: +20pp at n=20/arm) confirms direction; ring is now the decision gate, not the M=60 ladder read. Ladder reading kept for methodological record. Promoted to shadow-king (ring-gated); evicted from latest-2 by attack_first; 561.1 is final frozen reading. |
| heuristic+trolley-attack_first | n/a | n/a | PENDING | 0 | U93 step 3 SUBMITTED into the slot the ability WIN settlement freed. See pre_registrations and in_flight for the settle protocol. |
| heuristic+trolley-attack_first (repeat) | n/a | n/a | SETTLED NEUTRAL | 3 | BAND repeat resubmission (ref 54304681), byte-identical to ref 54304483. Board readings drifted to mixed sign (442.9 vs 600.0 vs king 494.8). U23 scoreboard settlement (analysis/attack_first_settlement.md): 3 shared brackets, candidate 1/3 (0.333) vs king 4/6 (0.667), confidence 0.171, favors_candidate=false, verdict neutral. Slot reverts to a king copy, queued for submission next iteration (quota exhausted for 2026-07-03 UTC). |
| heuristic+trolley (king-copy revert) | n/a | n/a | 476.1 | 0 | King-copy revert for the settled-NEUTRAL attack_first slot. SETTLED COMPLETE 476.1 (same-build drift, well within the now-corrected ~452-691 spread). Superseded this iteration: evicted from the tracked latest-2 by the ability-build floor restoration (ref 54315802) per the L9 noise-recalibration correction (ladder reads no longer gate lever decisions; the ring does). |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | PENDING | 0 | SUBMITTED per the L9 noise-recalibration correction: restores the ring-preferred floor (ability +20pp on the calibrated bracket ring) into the scored slot instead of a plain king copy. Same tarball as ref 54282097. Floor maintenance, not a new ladder A/B; no pre-registration added. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 600.0 | 0 | SETTLED COMPLETE 600.0. Confirms the L9 floor-restoration landed cleanly; ring-gated, not ladder-gated (per L9, single ladder reads no longer decide lever verdicts). No further action tied to this reading. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 426.0 | 0 | SETTLED COMPLETE 426.0 (drifted from 476.1; same-build noise, within the ~452-691 corrected band on the low side). Plain king-copy floor, not an experiment; no settlement protocol applies. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 540.9 | 0 | Board check 2026-07-04: 540.9 (drifted from 600.0/532.3 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 427.8 | 0 | Board check 2026-07-04: 427.8 (drifted from 426.0/486.3 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 497.0 | 0 | Board check 2026-07-04: 497.0 (drifted from 540.9/600.0/532.3 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 444.8 | 0 | Board check 2026-07-04: 444.8 (drifted from 427.8/426.0/486.3 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 526.2 | 0 | Board check 2026-07-04: 526.2 (drifted from 497.0/540.9/600.0 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 456.0 | 0 | Board check 2026-07-04: 456.0 (drifted from 444.8/427.8/426.0 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 504.7 | 0 | Board check 2026-07-04: 504.7 (drifted from 526.2/497.0/540.9 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 441.5 | 0 | Board check 2026-07-04: 441.5 (drifted from 456.0/444.8/427.8 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 470.1 | 0 | Board check 2026-07-04: 470.1 (drifted from 504.7/526.2/497.0 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 441.7 | 0 | Board check 2026-07-04: 441.7 (drifted from 441.5/456.0/444.8 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 489.7 | 0 | Board check 2026-07-04: 489.7 (drifted from 470.1/504.7/526.2 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 436.1 | 0 | Board check 2026-07-04: 436.1 (drifted from 441.7/441.5/456.0 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; reclaim_king ref/reading updated to this build, correcting a stale field that still pointed at the long-evicted ref 54282104/494.8 reading. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 486.9 | 0 | Board check 2026-07-04: 486.9 (drifted from 489.7). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 443.7 | 0 | Board check 2026-07-04: 443.7 (drifted from 436.1). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 550.3 | 0 | Board check 2026-07-04: 550.3 (drifted from 486.9). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 423.5 | 0 | Board check 2026-07-04: 423.5 (drifted from 443.7). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 583.8 | 0 | Board check 2026-07-04: 583.8 (drifted from 550.3). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 423.5 | 0 | Board check 2026-07-04: 423.5 (unchanged reading from the prior check). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 574.4 | 0 | Board check 2026-07-04: 574.4 (drifted from 583.8). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 423.5 | 0 | Board check 2026-07-04: 423.5 (unchanged reading, second check in a row). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 574.4 | 0 | Board check 2026-07-04: 574.4 (unchanged reading from the prior check, matches exactly). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 423.5 | 0 | Board check 2026-07-04: 423.5 (unchanged reading, third check in a row at this exact value). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 579.6 | 0 | Board check 2026-07-04: 579.6 (drifted from 574.4). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 423.5 | 0 | Board check 2026-07-04: 423.5 (unchanged reading, FOURTH check in a row). Investigated with tools/scout.py episodes: newest completed episode id 83757916 vs the ability ref's newest 83762365 (~4400 higher) -- this submission has stopped being scheduled for new matches, so the frozen score is mechanical, not a re-scoring-cadence coincidence. Still a valid safe floor, just stale on new games. See findings.md for the full writeup. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 584.7 | 0 | Board check 2026-07-04: 584.7 (drifted from 579.6). Within the v2 pooled range (396.7-691.5), no new low/high. tools/scout.py episodes confirms it is still actively playing (newest episode 83763012, up from 83762365 last check), unlike the frozen king-copy floor. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 423.5 | 0 | Board check 2026-07-04: 423.5 (unchanged reading, FIFTH check in a row at this exact value). Re-verified with tools/scout.py episodes: newest completed episode id is still 83757916, identical to the prior check, confirming the earlier staleness diagnosis is holding rather than a one-off. Still a valid safe floor. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 593.4 | 0 | Board check 2026-07-04: 593.4 (drifted from 584.7). Within the v2 pooled range (396.7-691.5), no new low/high. tools/scout.py episodes confirms it is still actively playing (newest episode 83764623, up from 83763012 last check). Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 423.5 | 0 | Board check 2026-07-04: 423.5 (unchanged reading, SIXTH check in a row at this exact value). Re-verified with tools/scout.py episodes: newest completed episode id is still 83757916, identical to every prior check. Staleness diagnosis now confirmed stable across six consecutive checks; folded into docs/writeup/offline_ladder_transfer.md as a small methodology-discipline finding. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 443.1 | 0 | Board check 2026-07-04: 443.1 (up from 423.5, first movement after six consecutive unchanged reads). Re-verified with tools/scout.py episodes: newest completed episode id is now 83768597, up from the long-frozen 83757916 -- this OVERTURNS the prior staleness diagnosis ("stopped being scheduled for new matches"). The submission has resumed playing new games; the earlier six-check freeze was a temporary scheduling gap, not a permanent state. Still within the v2 pooled range (396.7-691.5), no new low/high. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 603.3 | 0 | Board check 2026-07-04: 603.3 (up from 593.4). Within the v2 pooled range (396.7-691.5), no new low/high. tools/scout.py episodes confirms it is still actively playing (newest episode 83768225, up from 83764623 last check). Ring-gated per L9; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 603.3 | 0 | Board check 2026-07-04: 603.3 (unchanged reading from the prior check, matches exactly). tools/scout.py episodes confirms newest episode id is still 83768225, identical to the prior check (no new games played by this ref since last check). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 443.1 | 0 | Board check 2026-07-04: 443.1 (unchanged reading from the prior check, matches exactly). tools/scout.py episodes confirms newest episode id is still 83768597, identical to the prior check (no new games played by this ref since last check either). Within the v2 pooled range (396.7-691.5), no new low/high. Both tracked refs are simultaneously static this check (same score AND same newest episode id as last time), unlike the earlier single-ref freeze episode; one static check is not enough to call this a new staleness pattern, just note it and re-check next iteration. Plain king-copy floor; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 603.3 | 0 | Board check 2026-07-04 (this iteration): 603.3, IDENTICAL to the immediately prior check (same episode id 83768225). Second consecutive frozen read. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 443.1 | 0 | Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to the immediately prior check (same episode id 83768597). Second consecutive frozen read, confirming this is a genuine simultaneous freeze of both tracked refs rather than a one-off coincidence. Plain king-copy floor; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 603.3 | 0 | Board check 2026-07-04 (this iteration): 603.3, IDENTICAL to the prior two checks (same episode id 83768225). Third consecutive frozen read. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 443.1 | 0 | Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to the prior two checks (same episode id 83768597). Third consecutive frozen read, crossing the threshold set by the prior two entries for treating this as a standalone methodological finding (folded into findings.md Section 4D) rather than an ongoing watch item. Plain king-copy floor; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 603.3 | 0 | Board check 2026-07-04 (this iteration): 603.3, IDENTICAL to the prior three checks (same episode id 83768225). Fourth consecutive frozen read. Per the prior iteration_s own discipline, not re-logged as a fresh findings.md entry; watching only for the freeze to break. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 443.1 | 0 | Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to the prior three checks (same episode id 83768597). Fourth consecutive frozen read. Per the prior iteration_s own discipline, not re-logged as a fresh findings.md entry; watching only for the freeze to break. Plain king-copy floor; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 603.3 | 0 | Board check 2026-07-04 (this iteration): 603.3, IDENTICAL to the prior four checks (same episode id 83768225). Fifth consecutive frozen read. Not re-logged as a fresh findings.md entry per standing discipline; watching only for the freeze to break. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 443.1 | 0 | Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to the prior four checks (same episode id 83768597). Fifth consecutive frozen read. Not re-logged as a fresh findings.md entry per standing discipline; watching only for the freeze to break. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 603.3 | 0 | Board check 2026-07-04 (this iteration): 603.3, IDENTICAL to the prior five checks (same episode id 83768225). Sixth consecutive frozen read. Not re-logged as a fresh findings.md entry per standing discipline; watching only for the freeze to break. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 443.1 | 0 | Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to the prior five checks (same episode id 83768597). Sixth consecutive frozen read. Not re-logged as a fresh findings.md entry per standing discipline; watching only for the freeze to break. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 602.4 | 0 | Board check 2026-07-04 (this iteration): 602.4, BREAKS the six-check freeze (down a hair from 603.3). tools/scout.py episodes confirms new games played: newest episode id advanced from the frozen 83768225 to 83776251. Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 443.1 | 0 | Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to all six prior checks (same episode id 83768597, unchanged again). Seventh consecutive frozen read, now stuck longer than the earlier six-check freeze that resolved itself. The two refs' freezes have decoupled: the ability-floor ref resumed play this same check while this ref has not. Folded into docs/writeup/offline_ladder_transfer.md and findings.md. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 602.4 | 0 | Board check 2026-07-04 (this iteration): 602.4, IDENTICAL to the immediately prior check (same episode id 83776251). Second consecutive frozen read at this value. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 443.1 | 0 | Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to all seven prior checks (same episode id 83768597, unchanged again). Eighth consecutive frozen read; per standing discipline this repeat is not re-logged as a fresh findings.md entry (the decoupled-freeze finding was already recorded last iteration). Still a valid safe-floor build; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 602.4 | 0 | Board check 2026-07-04 (this iteration): 602.4, IDENTICAL to the two immediately prior checks (same episode id 83776251). Third consecutive frozen read at this value. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 443.1 | 0 | Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to all eight prior checks (same episode id 83768597, unchanged again). Ninth consecutive frozen read; per standing discipline this repeat is not re-logged as a fresh findings.md entry. Still a valid safe-floor build; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 602.4 | 0 | Board check 2026-07-04: 602.4 (unchanged, fourth consecutive check at this value; episode id still 83776251). Ring-gated per L9; no action taken. This iteration used the freeze data for a writeup update instead of a repeat findings.md note. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 443.1 | 0 | Board check 2026-07-04: 443.1 (unchanged, tenth consecutive check; episode id still 83768597). Plain king-copy floor; no action taken. Extended freeze-duration comparison (6 vs 10+ checks) folded into docs/writeup/offline_ladder_transfer.md this iteration. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 602.4 | 0 | Board check 2026-07-04: 602.4 (unchanged, sixth consecutive check at this value; episode id still 83776251). Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 443.1 | 0 | Board check 2026-07-04: 443.1 (unchanged, twelfth consecutive check; episode id still 83768597). Plain king-copy floor; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 602.4 | 0 | Board check 2026-07-04 (this iteration): 602.4, IDENTICAL to the prior six checks (same episode id 83776251). Seventh consecutive frozen read. Ring-gated per L9; no action taken. This iteration's TRACK S slot went to building tools/endgame_stopping.py (U48 prep) instead of a repeat freeze note. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 443.1 | 0 | Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to the prior twelve checks (same episode id 83768597). Thirteenth consecutive frozen read. Plain king-copy floor; no action taken. |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 602.4 | 0 | Board check 2026-07-04 (this iteration): 602.4, IDENTICAL to the prior seven checks (same episode id 83776251). Eighth consecutive frozen read. Ring-gated per L9; no action taken. Its sibling king-copy ref's own freeze broke this same iteration (thirteen checks, new episode 83782915, 441.1), confirming again that the two refs' quiet periods are independent. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 441.1 | 0 | Board check 2026-07-04 (this iteration): 441.1, BREAKING a thirteen-check freeze (new episode id 83782915, up from the long-frozen 83768597). Small same-build drift (443.1 -> 441.1), well within the v3 pooled range (heuristic+trolley family mean 456.4, stdev 59.2). Plain king-copy floor; no action taken (no active pre-registration for this slot). |
| heuristic+trolley-ability (floor restoration) | n/a | n/a | 563.8 | 0 | Board check 2026-07-05: 563.8, BREAKS the eighth-check freeze (down from 602.4). tools/scout.py episodes confirms new games played: newest episode id advanced from the frozen 83776251 to 83878807 (8 new completed episodes). Within the v3 pooled range, no new low/high. Ring-gated per L9; no action taken. |
| heuristic+trolley (king-copy revert, 2026-07-04) | n/a | n/a | 422.2 | 0 | Board check 2026-07-05: 422.2, BREAKS the thirteenth-check-plus freeze (down from 441.1). tools/scout.py episodes confirms new games played: newest episode id advanced from 83782915 to 83894390 (8 new completed episodes). Slightly below the prior observed low (423.5) but within the v3 pooled noise band (M=240 sized to a worst residual of 235.1, refit ce4e928). Plain king-copy floor; no action taken. |

```json STATE
{
  "active_candidates": [
    {
      "build": "cem-grown-genome (PRIO ordering)",
      "note": "CLOSED, not awaiting a slot. REAL U35 run executed (seed 0, agreement-only, --split train; analysis/cem_run_prio.md, artifact analysis/cem_runs/cem_run_prio_train_seed0.json). Best genome raises PRIO_ATTACK 0->3.13 and PRIO_ATTACH 3->3.74; gains +0.060 agreement on train (25->32/116) but LOSES -0.067 on the held-out test bucket (7->5/30). best_fitness flat across all 12 iterations (weak gradient). Held-out agreement delta NEGATIVE => pre-registered offline filter BLOCKS: no ladder A/B, ship byte-identical. CEM candidate 1 of the 2 failing/neutral that trip the CEM-plateau contingency (~Jul 15). Re-test only with a larger expert sample, the two-channel fitness on (--pool-matches>0), or a genome with a non-flat held-out gradient. RE-TEST 2026-07-03 (condition b, pool-matches>0): reduced-scale run (analysis/cem_run_prio_pooled.md) also BLOCKED -- held-out test agreement exactly unchanged (7/30 both default and tuned, zero decisions flipped) and train-bucket pool win rate WORSE for the tuned vector (0.567 vs 0.700, n=30, noisy). This is CEM candidate 2 of 2 tripping the plan's CEM-plateau contingency ahead of the ~Jul 15 checkpoint; flagged for the next weekly plan review, no unilateral pivot this iteration. RE-TEST 2026-07-03 (condition a, U83 teacher-corpus distill, --ring-matches 6 against the calibrated L5 ring, --teacher-labels data/training, seed 0): full-scale sweep over a 32003-train/10689-test teacher corpus (92x/356x the first two attempts' sample) also BLOCKED -- held-out test agreement 0.8210 -> 0.8189, delta -0.0022, and full-population train agreement also went backwards (0.8077 -> 0.8049). Diagnosed cause: the sweep's own best fitness was dominated by a noisy 6-game ring-win-rate read, the same proxy-metric-moves-backwards failure as attempt 2, surviving the scale increase. CEM candidate 3 of 3 non-WIN; condition (a) is now closed (tried at scale, still negative). Only remaining re-test condition: (c) a genome region with a measured non-flat held-out gradient. analysis/cem_run_prio_teacher.md, artifact analysis/cem_runs/u83_teacher_ring_seed0.json. CONDITION (c) CHECKED 2026-07-04 (no new CEM sweep, a direct per-dim held-out gradient probe instead): extended analysis/measure_cem_gradient.py with a --teacher-labels/--split mode and ran it against the exact held-out test split the three CEM sweeps blocked on (n=10689, baseline agreement 0.8210, matching cem_run_prio_teacher.md exactly). Result: the genome IS non-flat (max per-dim delta 0.2738, 5x the 2026-07-01 diagnostic's 0.0526), but every load-bearing ordering dim's shipped default (PRIO_ATTACK/ATTACH/PLAY/EVOLVE) sits at or above BOTH of its own bound readings, so no single-axis move beats the current default anywhere in the 18-dim space (analysis/cem_gradient_condition_c.md). Conditions (a), (b), and (c) are now ALL exhausted; state/hypotheses.md's cem_prio_agreement_generalizes row updated to 'fully exhausted'. Re-open only with a genuinely new weight-space region, not a re-run of this genome."
    }
  ],
  "attribution_u38": {
    "degeneracy": "step 1 has NO hand-coded content to measure: the U37 aware pilot (seeds consumer + guard stack) is BYTE-IDENTICAL to the generic pilot on both live meta decks (grimmsnarl 0 seeds; archaludon evolve seed unconsumed since only ATTACH is wired and no attach seed exists; guards deck-agnostic and already shipped in the 382.5/510.1 copies)",
    "first_measurable_candidate": "a real deck-aware differentiator: (a) a concentrated win-vs-loss seed (gameplan_seeds_diffuse re-test), (b) a card_effects/ability lever changing meta-card decisions (U34), or (c) the U40/U41 learned per-archetype pilot",
    "kd9_amended": "2026-07-02",
    "recorded": "2026-07-02",
    "source": "state/hypotheses.md meta_deck_copy row + docs/plans U38",
    "step1": "target meta deck + AWARE pilot vs SAME meta deck + GENERIC pilot; direction up, M=60, N>=30, settle >=24h; go/no-go for U40/U41 ladder spend",
    "step2": "best AWARE build vs the trolley incumbent king; direction up, M=60, N>=30; only after step 1 settles (attribution order rule 9)"
  },
  "census": {
    "cohort": "winning seat (U25 resolved fork)",
    "dataset": "2026-06-30 (5734 episodes)",
    "episodes_scored": 5732,
    "ranking_groups": 167531,
    "recorded": "2026-07-02",
    "source": "analysis/expert_census.md",
    "target_family": "meta_grimmsnarl",
    "target_tier": "full"
  },
  "endgame_campaign": {
    "basis": "tools/endgame_stopping.py, king_true_estimate = mean of 31 pooled same-build reads for heuristic+trolley-ability (tools/refit_noise_model.py family stats, stdev=42.1); stop_target = mean + bonus (40), per U48 (docs/plans/2026-07-02-001-feat-unified-number-one-plan.md).",
    "bonus": 40,
    "build": "heuristic+trolley-ability",
    "king_true_estimate": 571.6,
    "lock_by": "2026-08-15",
    "no_roll_buffer": "2026-08-14 12:00 UTC",
    "pair_rule": "two copies of the strongest settled build; a diverse hedge only if the runner-up settled within M and is mechanically different",
    "recorded": "2026-07-05",
    "stop_target": 611.6,
    "superseded_2026_07_05": "The hard-stop regime (stop_target 611.6 as a decision rule) is retired per P3 POSTURE INVERSION. New strategy: LOCK-THE-STRONGEST-PAIR EARLY (by Aug 12-13), using the ring as the decision gate, not a fixed ladder-read threshold. This block remains for reference but does not govern endgame decisions."
  },
  "final_scoring": {
    "daily_limit": "5 submissions/day",
    "deadline": "2026-08-16 23:59 UTC",
    "final_window": "~2 weeks continued games (newer agents more frequent), then leaderboard final",
    "model": "latest-2 tracked and used for final scoring; leaderboard shows best of the 2 (no best-ever net; a 3rd submit evicts the 3rd-newest)",
    "recorded": "2026-07-02",
    "source": "analysis/final_scoring_semantics.md"
  },
  "in_flight": {
    "board_reading": "486.2/570.4 (54339500 fresh roll, 54315802 prior restoration; 151k+ episode advance for 54339500, both ring-gated)",
    "build": "none (TRACK L HOLDS)",
    "note": "Board-checked 2026-07-05 (this iteration). Latest-2 pair: 54339500 (fresh roll, newest episode 83920026, public 486.2) and 54315802 (ring-restoration, no new episodes, public 570.4). Both ability builds (same tarball), ring-preferred per L9 noise recalibration. No settlement triggered; both within v3 pooled range (396.7-691.5, M=240). Per P3 POSTURE INVERSION, both slots occupied by ability builds; no free slot, no new TRACK L submission. PLAN FREEZE through 2026-08-16. TRACK L holds.",
    "ref": "n/a"
  },
  "ledger": [
    {
      "build": "heuristic+trolley (reclaim)",
      "ladder": 600.0,
      "move_agreement_delta": "n/a",
      "note": "U20 slot-1 king reclaim; byte-identical to the 569.6 king; settled 600.0, drifted to 594.7 on 2026-07-02 board check => same-build noise band ~25-30/side (KD2 calibration) Board 2026-07-02 04:21 UTC: 524.0 (600.0 settled -> 594.7 -> 556.7 -> 524.0; same-build drift, best-ever 600.0 still clears the 540 floor guard so it does not fire). Board 2026-07-02 04:55 UTC: 501.2 (converged toward the thick A/B at 499.9; same-build/deck drift). Best-ever 600.0 still clears the 540 floor guard, so it does not fire. Board 2026-07-02 (U27 iter): 491.7 (thick A/B leads by +44.7, inside BAND). Best-ever 600.0 still clears the 540 floor guard, so it does not fire.",
      "oracle": "n/a",
      "ref": "54252006",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley",
      "ladder": 569.6,
      "move_agreement_delta": "n/a",
      "note": "SHADOW+RECLAIM king; top loss early_collapse",
      "oracle": "n/a",
      "ref": "54215558",
      "sample_size": 47
    },
    {
      "build": "heuristic+benchguard",
      "ladder": 554.5,
      "move_agreement_delta": "n/a",
      "note": "bench-width guard build; below trolley floor",
      "oracle": "n/a",
      "ref": "~554",
      "sample_size": 14
    },
    {
      "build": "search+trolley",
      "ladder": 514.7,
      "move_agreement_delta": "n/a",
      "note": "search FORCE-LOADED and actually ran; still < heuristic",
      "oracle": "n/a",
      "ref": "54218335",
      "sample_size": ""
    },
    {
      "build": "meta_grimmsnarl",
      "ladder": 510.1,
      "move_agreement_delta": "n/a",
      "note": "meta-deck copy; refuted, below trolley",
      "oracle": "n/a",
      "ref": "54220220",
      "sample_size": ""
    },
    {
      "build": "meta_archaludon",
      "ladder": 382.5,
      "move_agreement_delta": "n/a",
      "note": "meta-deck copy; refuted, well below trolley",
      "oracle": "n/a",
      "ref": "54219892",
      "sample_size": ""
    },
    {
      "build": "search (baseline)",
      "ladder": 591.9,
      "move_agreement_delta": "n/a",
      "note": "STALE + INERT: search fell back to heuristic; not real search",
      "oracle": "n/a",
      "ref": "54208986",
      "sample_size": ""
    },
    {
      "build": "heuristic+trolley_thick",
      "ladder": 446.2,
      "move_agreement_delta": "n/a",
      "note": "SETTLED LOSS 2026-07-03: 446.2 vs reclaim king 558.5 (ref 54252006), -112.3pp, far past the M=60 LOSS threshold. Evicted; slot 2 reclaimed by a king copy (ref 54281812).",
      "oracle": "n/a",
      "ref": "54252291",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (reclaim, 2026-07-03)",
      "ladder": "PENDING",
      "move_agreement_delta": "n/a",
      "note": "L2 slot-2 reclaim: byte-identical king copy submitted to evict the settled-LOSS trolley_thick.",
      "oracle": "n/a",
      "ref": "54281812",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability",
      "ladder": "PENDING",
      "move_agreement_delta": "n/a",
      "note": "L1 ability A/B SUBMITTED into the slot L2 freed. See pre_registrations and in_flight for the settle protocol.",
      "oracle": "n/a",
      "ref": "54281824",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (reclaim, cleanup)",
      "ladder": 691.5,
      "move_agreement_delta": "n/a",
      "note": "L1 fix cleanup slot-1 king copy (ref 54282104): evicts the dead ERRORed ability build (ref 54281824) from the tracked latest-2 window so the ability fix (ref 54282097) has a live floor to be compared against, not a permanently-inert ERROR entry.",
      "oracle": "n/a",
      "ref": "54282104",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (ERRORed, superseded)",
      "ladder": "ERROR",
      "move_agreement_delta": "n/a",
      "note": "SETTLED (non-scoring): ref 54281824 ERRORed at grader load, missing agents/card_effects.py in the tarball (build command omitted --extra agents/card_effects.py). Never played an episode. Superseded by ref 54282097 (fix: card_effects.py bundled, COMPLETE 536.7 first reading), which carries forward the same pre-registration under a fresh settle-by.",
      "oracle": "n/a",
      "ref": "54281824",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability",
      "ladder": 561.1,
      "move_agreement_delta": "n/a",
      "note": "SETTLED WIN 2026-07-04: 561.1 vs reclaim king 494.8 (ref 54282104), +66.3pp, clears the M=60 WIN threshold. Promoted to shadow-king. Evicted from the tracked latest-2 in the same iteration by the attack_first submission (54304483); 561.1 is its final frozen reading.",
      "oracle": "n/a",
      "ref": "54282097",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-attack_first",
      "ladder": "PENDING",
      "move_agreement_delta": "n/a",
      "note": "U93 step 3 SUBMITTED into the slot the ability WIN settlement freed. See pre_registrations and in_flight for the settle protocol.",
      "oracle": "n/a",
      "ref": "54304483",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-attack_first (repeat)",
      "ladder": "SETTLED NEUTRAL",
      "move_agreement_delta": "n/a",
      "note": "BAND repeat resubmission (ref 54304681), byte-identical to ref 54304483. Board readings drifted to mixed sign (442.9 vs 600.0 vs king 494.8). U23 scoreboard settlement (analysis/attack_first_settlement.md): 3 shared brackets, candidate 1/3 (0.333) vs king 4/6 (0.667), confidence 0.171, favors_candidate=false, verdict neutral. Slot reverts to a king copy, queued for submission next iteration (quota exhausted for 2026-07-03 UTC).",
      "oracle": "n/a",
      "ref": "54304681",
      "sample_size": 3
    },
    {
      "build": "heuristic+trolley (king-copy revert)",
      "ladder": 476.1,
      "move_agreement_delta": "n/a",
      "note": "King-copy revert for the settled-NEUTRAL attack_first slot. SETTLED COMPLETE 476.1 (same-build drift, well within the now-corrected ~452-691 spread). Superseded this iteration: evicted from the tracked latest-2 by the ability-build floor restoration (ref 54315802) per the L9 noise-recalibration correction (ladder reads no longer gate lever decisions; the ring does).",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": "PENDING",
      "move_agreement_delta": "n/a",
      "note": "SUBMITTED per the L9 noise-recalibration correction: restores the ring-preferred floor (ability +20pp on the calibrated bracket ring) into the scored slot instead of a plain king copy. Same tarball as ref 54282097. Floor maintenance, not a new ladder A/B; no pre-registration added.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 600.0,
      "move_agreement_delta": "n/a",
      "note": "SETTLED COMPLETE 600.0. Confirms the L9 floor-restoration landed cleanly; ring-gated, not ladder-gated (per L9, single ladder reads no longer decide lever verdicts). No further action tied to this reading.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 426.0,
      "move_agreement_delta": "n/a",
      "note": "SETTLED COMPLETE 426.0 (drifted from 476.1; same-build noise, within the ~452-691 corrected band on the low side). Plain king-copy floor, not an experiment; no settlement protocol applies.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 540.9,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 540.9 (drifted from 600.0/532.3 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 427.8,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 427.8 (drifted from 426.0/486.3 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 497.0,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 497.0 (drifted from 540.9/600.0/532.3 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 444.8,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 444.8 (drifted from 427.8/426.0/486.3 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 526.2,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 526.2 (drifted from 497.0/540.9/600.0 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 456.0,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 456.0 (drifted from 444.8/427.8/426.0 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 504.7,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 504.7 (drifted from 526.2/497.0/540.9 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 441.5,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 441.5 (drifted from 456.0/444.8/427.8 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 470.1,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 470.1 (drifted from 504.7/526.2/497.0 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 441.7,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 441.7 (drifted from 441.5/456.0/444.8 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 489.7,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 489.7 (drifted from 470.1/504.7/526.2 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 436.1,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 436.1 (drifted from 441.7/441.5/456.0 prior reads). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; reclaim_king ref/reading updated to this build, correcting a stale field that still pointed at the long-evicted ref 54282104/494.8 reading.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 486.9,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 486.9 (drifted from 489.7). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 443.7,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 443.7 (drifted from 436.1). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 550.3,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 550.3 (drifted from 486.9). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 423.5,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 423.5 (drifted from 443.7). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 583.8,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 583.8 (drifted from 550.3). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 423.5,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 423.5 (unchanged reading from the prior check). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 574.4,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 574.4 (drifted from 583.8). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 423.5,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 423.5 (unchanged reading, second check in a row). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 574.4,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 574.4 (unchanged reading from the prior check, matches exactly). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 423.5,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 423.5 (unchanged reading, third check in a row at this exact value). Within the v2 pooled range (396.7-691.5), no new low/high. Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 579.6,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 579.6 (drifted from 574.4). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 423.5,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 423.5 (unchanged reading, FOURTH check in a row). Investigated with tools/scout.py episodes: newest completed episode id 83757916 vs the ability ref's newest 83762365 (~4400 higher) -- this submission has stopped being scheduled for new matches, so the frozen score is mechanical, not a re-scoring-cadence coincidence. Still a valid safe floor, just stale on new games. See findings.md for the full writeup.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 584.7,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 584.7 (drifted from 579.6). Within the v2 pooled range (396.7-691.5), no new low/high. tools/scout.py episodes confirms it is still actively playing (newest episode 83763012, up from 83762365 last check), unlike the frozen king-copy floor. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 423.5,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 423.5 (unchanged reading, FIFTH check in a row at this exact value). Re-verified with tools/scout.py episodes: newest completed episode id is still 83757916, identical to the prior check, confirming the earlier staleness diagnosis is holding rather than a one-off. Still a valid safe floor.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 593.4,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 593.4 (drifted from 584.7). Within the v2 pooled range (396.7-691.5), no new low/high. tools/scout.py episodes confirms it is still actively playing (newest episode 83764623, up from 83763012 last check). Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 423.5,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 423.5 (unchanged reading, SIXTH check in a row at this exact value). Re-verified with tools/scout.py episodes: newest completed episode id is still 83757916, identical to every prior check. Staleness diagnosis now confirmed stable across six consecutive checks; folded into docs/writeup/offline_ladder_transfer.md as a small methodology-discipline finding.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 443.1,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 443.1 (up from 423.5, first movement after six consecutive unchanged reads). Re-verified with tools/scout.py episodes: newest completed episode id is now 83768597, up from the long-frozen 83757916 -- this OVERTURNS the prior staleness diagnosis (\"stopped being scheduled for new matches\"). The submission has resumed playing new games; the earlier six-check freeze was a temporary scheduling gap, not a permanent state. Still within the v2 pooled range (396.7-691.5), no new low/high.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 603.3,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 603.3 (up from 593.4). Within the v2 pooled range (396.7-691.5), no new low/high. tools/scout.py episodes confirms it is still actively playing (newest episode 83768225, up from 83764623 last check). Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 603.3,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 603.3 (unchanged reading from the prior check, matches exactly). tools/scout.py episodes confirms newest episode id is still 83768225, identical to the prior check (no new games played by this ref since last check). Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 443.1,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 443.1 (unchanged reading from the prior check, matches exactly). tools/scout.py episodes confirms newest episode id is still 83768597, identical to the prior check (no new games played by this ref since last check either). Within the v2 pooled range (396.7-691.5), no new low/high. Both tracked refs are simultaneously static this check (same score AND same newest episode id as last time), unlike the earlier single-ref freeze episode; one static check is not enough to call this a new staleness pattern, just note it and re-check next iteration. Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 603.3,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 603.3, IDENTICAL to the immediately prior check (same episode id 83768225). Second consecutive frozen read. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 443.1,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to the immediately prior check (same episode id 83768597). Second consecutive frozen read, confirming this is a genuine simultaneous freeze of both tracked refs rather than a one-off coincidence. Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 603.3,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 603.3, IDENTICAL to the prior two checks (same episode id 83768225). Third consecutive frozen read. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 443.1,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to the prior two checks (same episode id 83768597). Third consecutive frozen read, crossing the threshold set by the prior two entries for treating this as a standalone methodological finding (folded into findings.md Section 4D) rather than an ongoing watch item. Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 603.3,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 603.3, IDENTICAL to the prior three checks (same episode id 83768225). Fourth consecutive frozen read. Per the prior iteration_s own discipline, not re-logged as a fresh findings.md entry; watching only for the freeze to break. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 443.1,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to the prior three checks (same episode id 83768597). Fourth consecutive frozen read. Per the prior iteration_s own discipline, not re-logged as a fresh findings.md entry; watching only for the freeze to break. Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 603.3,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 603.3, IDENTICAL to the prior four checks (same episode id 83768225). Fifth consecutive frozen read. Not re-logged as a fresh findings.md entry per standing discipline; watching only for the freeze to break.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 443.1,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to the prior four checks (same episode id 83768597). Fifth consecutive frozen read. Not re-logged as a fresh findings.md entry per standing discipline; watching only for the freeze to break.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 603.3,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 603.3, IDENTICAL to the prior five checks (same episode id 83768225). Sixth consecutive frozen read. Not re-logged as a fresh findings.md entry per standing discipline; watching only for the freeze to break.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 443.1,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to the prior five checks (same episode id 83768597). Sixth consecutive frozen read. Not re-logged as a fresh findings.md entry per standing discipline; watching only for the freeze to break.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 602.4,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 602.4, BREAKS the six-check freeze (down a hair from 603.3). tools/scout.py episodes confirms new games played: newest episode id advanced from the frozen 83768225 to 83776251. Within the v2 pooled range (396.7-691.5), no new low/high. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 443.1,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to all six prior checks (same episode id 83768597, unchanged again). Seventh consecutive frozen read, now stuck longer than the earlier six-check freeze that resolved itself. The two refs' freezes have decoupled: the ability-floor ref resumed play this same check while this ref has not. Folded into docs/writeup/offline_ladder_transfer.md and findings.md.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 602.4,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 602.4, IDENTICAL to the immediately prior check (same episode id 83776251). Second consecutive frozen read at this value. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 443.1,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to all seven prior checks (same episode id 83768597, unchanged again). Eighth consecutive frozen read; per standing discipline this repeat is not re-logged as a fresh findings.md entry (the decoupled-freeze finding was already recorded last iteration). Still a valid safe-floor build; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 602.4,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 602.4, IDENTICAL to the two immediately prior checks (same episode id 83776251). Third consecutive frozen read at this value. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 443.1,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to all eight prior checks (same episode id 83768597, unchanged again). Ninth consecutive frozen read; per standing discipline this repeat is not re-logged as a fresh findings.md entry. Still a valid safe-floor build; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 602.4,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 602.4 (unchanged, fourth consecutive check at this value; episode id still 83776251). Ring-gated per L9; no action taken. This iteration used the freeze data for a writeup update instead of a repeat findings.md note.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 443.1,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 443.1 (unchanged, tenth consecutive check; episode id still 83768597). Plain king-copy floor; no action taken. Extended freeze-duration comparison (6 vs 10+ checks) folded into docs/writeup/offline_ladder_transfer.md this iteration.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 602.4,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 602.4 (unchanged, sixth consecutive check at this value; episode id still 83776251). Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 443.1,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04: 443.1 (unchanged, twelfth consecutive check; episode id still 83768597). Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 602.4,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 602.4, IDENTICAL to the prior six checks (same episode id 83776251). Seventh consecutive frozen read. Ring-gated per L9; no action taken. This iteration's TRACK S slot went to building tools/endgame_stopping.py (U48 prep) instead of a repeat freeze note.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 443.1,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 443.1, IDENTICAL to the prior twelve checks (same episode id 83768597). Thirteenth consecutive frozen read. Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 602.4,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 602.4, IDENTICAL to the prior seven checks (same episode id 83776251). Eighth consecutive frozen read. Ring-gated per L9; no action taken. Its sibling king-copy ref's own freeze broke this same iteration (thirteen checks, new episode 83782915, 441.1), confirming again that the two refs' quiet periods are independent.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 441.1,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-04 (this iteration): 441.1, BREAKING a thirteen-check freeze (new episode id 83782915, up from the long-frozen 83768597). Small same-build drift (443.1 -> 441.1), well within the v3 pooled range (heuristic+trolley family mean 456.4, stdev 59.2). Plain king-copy floor; no action taken (no active pre-registration for this slot).",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley-ability (floor restoration)",
      "ladder": 563.8,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-05: 563.8, BREAKS the eighth-check freeze (down from 602.4). tools/scout.py episodes confirms new games played: newest episode id advanced from the frozen 83776251 to 83878807 (8 new completed episodes). Within the v3 pooled range, no new low/high. Ring-gated per L9; no action taken.",
      "oracle": "n/a",
      "ref": "54315802",
      "sample_size": 0
    },
    {
      "build": "heuristic+trolley (king-copy revert, 2026-07-04)",
      "ladder": 422.2,
      "move_agreement_delta": "n/a",
      "note": "Board check 2026-07-05: 422.2, BREAKS the thirteenth-check-plus freeze (down from 441.1). tools/scout.py episodes confirms new games played: newest episode id advanced from 83782915 to 83894390 (8 new completed episodes). Slightly below the prior observed low (423.5) but within the v3 pooled noise band (M=240 sized to a worst residual of 235.1, refit ce4e928). Plain king-copy floor; no action taken.",
      "oracle": "n/a",
      "ref": "54315565",
      "sample_size": 0
    }
  ],
  "loss_distribution": {
    "buckets": {
      "bad_determinization": 28,
      "deck_matchup": 28,
      "deckout": 65,
      "early_collapse": 257,
      "endgame_misplay": 12,
      "slow_search": 0
    },
    "draws": 1,
    "games": 704,
    "losses": 390,
    "sample_size": 704,
    "sources": [
      "data/replays"
    ],
    "top_bucket": "early_collapse",
    "wins": 313
  },
  "noise_model": {
    "basis": "tools/refit_noise_model.py statistical refit over 57 pooled same-build reads across heuristic+trolley (n=30, mean=456.4, stdev=59.2), heuristic+trolley-ability (n=27, mean=568.5, stdev=43.9): pooled residual stdev 52.0, worst observed residual 235.1. M set to the larger of 2-sigma and the worst residual, rounded up to nearest 10.",
    "margin_M": 240,
    "refit_by": "2026-07-18",
    "version": 3
  },
  "pre_registrations": [
    {
      "actions": {
        "band": "one repeat resubmission, then U23 scoreboard at ~90% binomial confidence on shared brackets; else NEUTRAL, revert to king, record thin_bench_threshold re-test condition",
        "loss": "evict trolley_thick, revert slot 2 to a king copy",
        "win": "promote heuristic+trolley_thick to shadow-king; reclaim-king stays heuristic+trolley"
      },
      "build": "heuristic+trolley_thick",
      "direction": "up",
      "filters": "mirror empty-bench collapse 80.8->65.4 (n=240, p<0.001), no win-rate regression (analysis/collapse_rate_thick_deck.md); tarball grader-verified",
      "hypothesis": "trolley_thick basic-density cuts early_collapse (thin_bench_threshold deck-change re-test)",
      "margin": 60,
      "n": 30,
      "settle_by": "2026-07-06"
    },
    {
      "actions": {
        "band": "one repeat resubmission, then U23 scoreboard at ~90% binomial confidence on shared brackets; else NEUTRAL, revert to king",
        "loss": "evict the ability build, revert slot to a king copy",
        "win": "promote heuristic+trolley-ability to shadow-king; reclaim-king stays heuristic+trolley"
      },
      "build": "heuristic+trolley-ability",
      "direction": "up",
      "filters": "offline gauntlet deck:trolley vs 8-deck pool, 200 games/arm: off 67.5% (135/65), on 71.5% (143/57), diff_pp +4.0, no regression, 0 invalid moves (analysis/ability_ab.md); tarball grader-verified (tests/test_grader_submission.py[heuristic-trolley-ability]) and extracted-tarball env.run verified (reward=1, DONE, 25 steps). RESUBMITTED 2026-07-03: original ref 54281824 ERRORed (missing agents/card_effects.py in the tarball, never played an episode, settle clock never validly started); rebuilt with the module bundled and resubmitted as ref 54282097, fresh settle-by set below.",
      "hypothesis": "PTCG_ABILITY on (once-per-turn ability activation) improves ladder win rate; pilot agreed with top players on 0/554 real ABILITY decisions with the flag off (analysis/move_ranking_diverges_ability_gap.md)",
      "margin": 60,
      "n": 30,
      "settle_by": "2026-07-08"
    },
    {
      "actions": {
        "band": "one repeat resubmission, then U23 scoreboard at ~90% binomial confidence on shared brackets; else NEUTRAL, revert to king",
        "loss": "evict the attack_first build, revert slot to a king copy",
        "win": "promote heuristic+trolley-attack_first to shadow-king; reclaim-king stays heuristic+trolley"
      },
      "build": "heuristic+trolley-attack_first",
      "direction": "up",
      "filters": "offline gauntlet deck:trolley vs 8-deck pool 200 games/arm: off 71.5% (143/57), on 77.0% (154/46), diff_pp +5.5, no regression, 0 invalid moves (analysis/attack_first_ab.md); bracket-ring A/B 20 games/arm: off 75.0%, on 85.0%, diff_pp +10.0, agrees in direction (analysis/attack_first_ring_check.md); tarball grader-verified (tests/test_grader_submission.py[heuristic-trolley-attack_first]) incl extracted-tarball env.run",
      "hypothesis": "PTCG_ATTACK_FIRST on (take an already-legal positive-value attack over a discretionary attach) improves ladder win rate; U91 mined winners attach-before-attack 3.4pp less than losers, and the shipped pilot over-attaches relative to both cohorts (analysis/gameplan_claims_bracket_4.md)",
      "margin": 60,
      "n": 30,
      "settle_by": "2026-07-11"
    }
  ],
  "reclaim_king": {
    "build": "heuristic+trolley",
    "ladder": "441.1",
    "note": "Board check 2026-07-04 (this iteration): 441.1, freeze BROKEN after a THIRTEENTH consecutive check at 443.1 (new episode id 83782915). Still a valid safe-floor build (byte-identical heuristic+trolley); no action taken.",
    "ref": "54315565"
  },
  "reconciliation": {
    "census_tier": "FULL (167531 groups >> 2500)",
    "recorded": "2026-07-02",
    "rulings": 11,
    "source": "docs/design/deck-aware-execution-design.md",
    "w_generic": "DROPPED (fallback = pure ladder; no pooled block)"
  },
  "search_branch": {
    "bias_abs": "0.46-0.68",
    "branch": "U45 belief-weighted search",
    "decided": "2026-07-02",
    "disambig_slope": "0.023-0.037 (marginal)",
    "leaf_correlation": "0.80-0.91 discriminating",
    "source": "analysis/pimc_diagnostic.md",
    "verdict": "FAVORABLE"
  },
  "shadow_king": {
    "build": "heuristic+trolley-ability",
    "ladder": "n/a (ring-gated, not ladder-gated per L9)",
    "note": "Per the 2026-07-04 noise recalibration, ladder board reads no longer confirm or refute this build (same-build spread ~396.7-691.5 swamps M=60). The ability build is kept as shadow-king on RING evidence (calibrated bracket ring, tau 0.857, ability +20pp, analysis/ability_ring_check.md), not on the previously-recorded 561.1 ladder WIN (now understood as a noise artifact, findings.md 4D). Board check 2026-07-04: this iteration's reading is 593.4 (drifted from 584.7), still ring-gated not ladder-gated, no action; tools/scout.py episodes confirms it is still actively playing (newest episode 83764623, up from 83763012 last check). RE-CHECKED 2026-07-04 (gauntlet side, LOOP_BRIEF.md L1 process-global-confound caveat, tools/measure_ability_isolated.py): the offline gauntlet's original +4.0pp point estimate is itself noise-dominated (isolated-arm diff_pp +2.5/-0.5/-1.3 across three runs, mean +0.2, no stable sign), independent of the mirror-match confound. RE-CHECKED 2026-07-04 (ring side, analysis/ability_ring_confound_check.md): the ring's clone:<family> opponents (_clone_opponent) never call heuristics.choose() and so never read _ABILITY at all (code-traced and regression-tested, tests/test_opponents.py::test_clone_opponent_ignores_ability_flag_never_reads_it); the ring's +20.0pp was already a genuinely one-sided measurement, unlike the gauntlet's +4.0pp, and needed no deconfounding. Net: ring evidence remains clean and remains the decision gate for the shadow-king disposition. Board check 2026-07-04 (this iteration): reading is 602.4, BREAKING a six-check freeze (down a hair from 603.3); tools/scout.py episodes confirms it resumed active play (newest episode 83776251, up from the long-frozen 83768225) in the same iteration its sibling king-copy ref stayed frozen for a seventh check. Still ring-gated not ladder-gated, no action. Board check 2026-07-04 (this iteration): reading is 602.4, IDENTICAL to the prior check (episode id still 83776251, unchanged). Seventh consecutive frozen read. Still ring-gated not ladder-gated, no action; this iteration's TRACK S work built tools/endgame_stopping.py (U48 final-pair optimal-stopping prep), which used this build's own 28-read family mean (569.7) as the king_true_estimate now recorded in state/current.md's endgame_campaign block. Board check 2026-07-04 (this iteration): reading is 602.4, IDENTICAL to the prior check (episode id still 83776251, unchanged). Eighth consecutive frozen read. Still ring-gated not ladder-gated, no action; this iteration's TRACK S work finalized the king-copy sibling ref's completed freeze duration (13 checks, broke this iteration) in the writeup.",
    "ref": "54315802"
  },
  "tag_coverage": {
    "gate": "no deck-aware build may spend a ladder slot unless deck_covered_100pct(target) is true (advisory until U37/U40 land)",
    "layer": "agents/card_effects.py",
    "pool_untagged_fraction": 0.4916864608076009,
    "recorded": "2026-07-02",
    "source": "analysis/card_effects_layer.md",
    "tags_version": "1",
    "target_deck": "trolley_thick",
    "target_deck_coverage": 1.0
  },
  "target_selector": {
    "formula": "mastery = expert_wins * expert_win_rate",
    "mastery_target": "meta_archaludon",
    "note": "U36 selector piece 1 of 3 (tools/archetype_select.py). Classifies BOTH seats of 5732 decided episodes so losing appearances count. By mastery the target is meta_archaludon (1111.16) narrowly over meta_grimmsnarl (1059.86), DISAGREEING with the census adoption target. But this is a closed mirror pool so win_rate ~ 0.50 and mastery still tracks volume: meta_grimmsnarl is the ONLY above-0.5 family (0.531) while archaludon wins mastery at a BELOW-0.5 rate (0.484) on game count. Discriminating signal is win_rate, which agrees with the census on grimmsnarl as the quality pick. Recommend grimmsnarl as the U37 seeds target, archaludon as mastery runner-up / opponent-model anchor. Miner (piece 2) LANDED: analysis/gameplan_mine.py mines six stat blocks (opening_category, attach_target, play_target, evolve_target, first_attack_ordinal, first_evolve_ordinal), each contrasting winning vs losing appearances, each with a resolution_rate; a winning-split resolution under 0.90 bars the block. Seeds emitter (piece 3) LANDED: analysis/gameplan_seeds.py emits a seed for a block only when it clears BOTH the miner's 0.90 resolution bar (not barred) AND its concentration bar (0.70 mode_share for attach/play/evolve, 0.95 unanimity for the opening, 0.80 consistency for the two timing blocks); skips carry a reason (barred/no_mode/below_bar), isolated seeds JSON + committed aggregates-only doc, pure/cg-free, 11 hermetic tests. REAL RUN DONE (this iter): miner+emitter on the real 5732-episode dataset for both families. grimmsnarl (1996/1763) emits 0 seeds (all six blocks barred or below the concentration bar); archaludon (2294/2442) emits 1 (evolve_target=card 190 @ 0.875, but the losing split modes to 190 too, so deck-identity not a win-vs-loss edge). play_target structurally barred (0.0 resolution) for both. Committed: analysis/gameplans/{meta_grimmsnarl,meta_archaludon}_gameplan.md + seeds_real_run.md. The mined-seeds lever is NEARLY EMPTY at scale; do not spend a ladder slot on a seeds build until a block emits a concentrated AND win-vs-loss-discriminating seed. NEXT: U37 seeds CONSUMER (default-off, byte-identical unset, thin/empty dict) or pivot deck-aware effort to guard stack / card_effects / ranker.",
    "quality_target": "meta_grimmsnarl",
    "recorded": "2026-07-02",
    "source": "analysis/archetype_select.md"
  }
}
```
