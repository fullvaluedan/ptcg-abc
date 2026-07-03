# Loop state: current

Machine-readable source of truth is the fenced `json STATE` block at the
bottom; the prose above is a rendered view regenerated on every write.
Update this every iteration (loss distribution, kings, candidates, ledger).

## Top loss bucket (what this iteration targets)

**early_collapse** over 224 classified replays (W/D/L 98/1/125).

| bucket | losses |
| --- | --- |
| early_collapse | 60 |
| bad_determinization | 22 |
| deck_matchup | 20 |
| deckout | 17 |
| endgame_misplay | 6 |

## Kings

- **shadow-king** (best live build): heuristic+trolley-ability (ref 54282097, ladder 561.1)
- **reclaim-king** (safe floor): heuristic+trolley (ref 54282104, ladder 494.8)

## Candidates awaiting a ladder slot

- cem-grown-genome (PRIO ordering): CLOSED, not awaiting a slot. REAL U35 run executed (seed 0, agreement-only, --split train; analysis/cem_run_prio.md, artifact analysis/cem_runs/cem_run_prio_train_seed0.json). Best genome raises PRIO_ATTACK 0->3.13 and PRIO_ATTACH 3->3.74; gains +0.060 agreement on train (25->32/116) but LOSES -0.067 on the held-out test bucket (7->5/30). best_fitness flat across all 12 iterations (weak gradient). Held-out agreement delta NEGATIVE => pre-registered offline filter BLOCKS: no ladder A/B, ship byte-identical. CEM candidate 1 of the 2 failing/neutral that trip the CEM-plateau contingency (~Jul 15). Re-test only with a larger expert sample, the two-channel fitness on (--pool-matches>0), or a genome with a non-flat held-out gradient. RE-TEST 2026-07-03 (condition b, pool-matches>0): reduced-scale run (analysis/cem_run_prio_pooled.md) also BLOCKED -- held-out test agreement exactly unchanged (7/30 both default and tuned, zero decisions flipped) and train-bucket pool win rate WORSE for the tuned vector (0.567 vs 0.700, n=30, noisy). This is CEM candidate 2 of 2 tripping the plan's CEM-plateau contingency ahead of the ~Jul 15 checkpoint; flagged for the next weekly plan review, no unilateral pivot this iteration. RE-TEST 2026-07-03 (condition a, U83 teacher-corpus distill, --ring-matches 6 against the calibrated L5 ring, --teacher-labels data/training, seed 0): full-scale sweep over a 32003-train/10689-test teacher corpus (92x/356x the first two attempts' sample) also BLOCKED -- held-out test agreement 0.8210 -> 0.8189, delta -0.0022, and full-population train agreement also went backwards (0.8077 -> 0.8049). Diagnosed cause: the sweep's own best fitness was dominated by a noisy 6-game ring-win-rate read, the same proxy-metric-moves-backwards failure as attempt 2, surviving the scale increase. CEM candidate 3 of 3 non-WIN; condition (a) is now closed (tried at scale, still negative). Only remaining re-test condition: (c) a genome region with a measured non-flat held-out gradient. analysis/cem_run_prio_teacher.md, artifact analysis/cem_runs/u83_teacher_ring_seed0.json.

## Noise model (U22)

- margin M = 60 (v1): WIN >= king+M, LOSS <= king-M, else BAND.
- basis: same-behavior pair 591.9/569.6 + KD2 king resubmission heuristic+trolley 569.6 -> 600.0 byte-identical (same-build spread ~30 either side; true estimate ~585)
- re-fit by: 2026-07-15

## Pre-registrations (machine-checked gate, U22)

A build may not be submitted without a complete row here (tools/loop_state.py check-submit --build <name>).

| build | hypothesis | dir | M | N | settle-by | complete |
| --- | --- | --- | --- | --- | --- | --- |
| heuristic+trolley_thick | trolley_thick basic-density cuts early_collapse (thin_bench_threshold deck-change re-test) | up | 60 | 30 | 2026-07-06 | yes |
| heuristic+trolley-ability | PTCG_ABILITY on (once-per-turn ability activation) improves ladder win rate; pilot agreed with top players on 0/554 real ABILITY decisions with the flag off (analysis/move_ranking_diverges_ability_gap.md) | up | 60 | 30 | 2026-07-08 | yes |
| heuristic+trolley-attack_first | PTCG_ATTACK_FIRST on (take an already-legal positive-value attack over a discretionary attach) improves ladder win rate; U91 mined winners attach-before-attack 3.4pp less than losers, and the shipped pilot over-attaches relative to both cohorts (analysis/gameplan_claims_bracket_4.md) | up | 60 | 30 | 2026-07-11 | yes |

- **heuristic+trolley_thick** filters: mirror empty-bench collapse 80.8->65.4 (n=240, p<0.001), no win-rate regression (analysis/collapse_rate_thick_deck.md); tarball grader-verified
  - WIN: promote heuristic+trolley_thick to shadow-king; reclaim-king stays heuristic+trolley
  - LOSS: evict trolley_thick, revert slot 2 to a king copy
  - BAND: one repeat resubmission, then U23 scoreboard at ~90% binomial confidence on shared brackets; else NEUTRAL, revert to king, record thin_bench_threshold re-test condition
- **heuristic+trolley-ability** filters: offline gauntlet deck:trolley vs 8-deck pool, 200 games/arm: off 67.5% (135/65), on 71.5% (143/57), diff_pp +4.0, no regression, 0 invalid moves (analysis/ability_ab.md); tarball grader-verified (tests/test_grader_submission.py[heuristic-trolley-ability]) and extracted-tarball env.run verified (reward=1, DONE, 25 steps). RESUBMITTED 2026-07-03: original ref 54281824 ERRORed (missing agents/card_effects.py in the tarball, never played an episode, settle clock never validly started); rebuilt with the module bundled and resubmitted as ref 54282097, fresh settle-by set below.
  - WIN: promote heuristic+trolley-ability to shadow-king; reclaim-king stays heuristic+trolley
  - LOSS: evict the ability build, revert slot to a king copy
  - BAND: one repeat resubmission, then U23 scoreboard at ~90% binomial confidence on shared brackets; else NEUTRAL, revert to king
- **heuristic+trolley-attack_first** filters: offline gauntlet deck:trolley vs 8-deck pool 200 games/arm: off 71.5% (143/57), on 77.0% (154/46), diff_pp +5.5, no regression, 0 invalid moves (analysis/attack_first_ab.md); bracket-ring A/B 20 games/arm: off 75.0%, on 85.0%, diff_pp +10.0, agrees in direction (analysis/attack_first_ring_check.md); tarball grader-verified (tests/test_grader_submission.py[heuristic-trolley-attack_first]) incl extracted-tarball env.run
  - WIN: promote heuristic+trolley-attack_first to shadow-king; reclaim-king stays heuristic+trolley
  - LOSS: evict the attack_first build, revert slot to a king copy
  - BAND: one repeat resubmission, then U23 scoreboard at ~90% binomial confidence on shared brackets; else NEUTRAL, revert to king
  - SETTLED NEUTRAL 2026-07-03 (board-check iteration): first reading (54304483) and its repeat (54304681) drifted to a mixed sign (442.9 vs 600.0 against king 494.8), so the pre-registered scoreboard tiebreak ran. Real replays pulled for both refs plus the king (analysis/attack_first_settlement.md): U23 scoreboard on 3 shared brackets gives candidate 1/3 (0.333) vs king 4/6 (0.667), confidence 0.171, favors_candidate=false, verdict neutral. Per the BAND action: revert slot to a king copy. Build+grader-verified this iteration but the Kaggle daily quota was already exhausted (6 submissions landed on 2026-07-03 UTC, not the 2 previously tracked); the king-copy revert submission is queued for the next iteration once the quota window resets (~00:00 UTC 2026-07-04). This NEUTRAL is a small-sample ladder read (3 decisive shared-bracket episodes, far under N=30), not a refutation of the offline gates (+5.5pp gauntlet, +10.0pp ring), so the lever stays re-eligible for a future slot without new offline work.

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
| heuristic+trolley_thick | n/a | n/a | 446.2 | 0 | SETTLED LOSS 2026-07-03: 446.2 vs reclaim king 558.5 (ref 54252006), -112.3pp, far past the M=60 LOSS threshold. Evicted; slot 2 reclaimed by a king copy (ref 54281812). |
| heuristic+trolley (reclaim, 2026-07-03) | n/a | n/a | PENDING | 0 | L2 slot-2 reclaim: byte-identical king copy submitted to evict the settled-LOSS trolley_thick. |
| heuristic+trolley-ability | n/a | n/a | PENDING | 0 | L1 ability A/B SUBMITTED into the slot L2 freed. See pre_registrations and in_flight for the settle protocol. |
| heuristic+trolley (reclaim, cleanup) | n/a | n/a | 691.5 | 0 | L1 fix cleanup slot-1 king copy (ref 54282104): evicts the dead ERRORed ability build (ref 54281824) from the tracked latest-2 window so the ability fix (ref 54282097) has a live floor to be compared against, not a permanently-inert ERROR entry. |
| heuristic+trolley-ability (ERRORed, superseded) | n/a | n/a | ERROR | 0 | SETTLED (non-scoring): ref 54281824 ERRORed at grader load, missing agents/card_effects.py in the tarball (build command omitted --extra agents/card_effects.py). Never played an episode. Superseded by ref 54282097 (fix: card_effects.py bundled, COMPLETE 536.7 first reading), which carries forward the same pre-registration under a fresh settle-by. |
| heuristic+trolley-ability | n/a | n/a | 561.1 | 0 | SETTLED WIN 2026-07-04: 561.1 vs reclaim king 494.8 (ref 54282104), +66.3pp, clears the M=60 WIN threshold. Promoted to shadow-king. Evicted from the tracked latest-2 in the same iteration by the attack_first submission (54304483); 561.1 is its final frozen reading. |
| heuristic+trolley-attack_first | n/a | n/a | PENDING | 0 | U93 step 3 SUBMITTED into the slot the ability WIN settlement freed. See pre_registrations and in_flight for the settle protocol. |
| heuristic+trolley-attack_first (repeat) | n/a | n/a | SETTLED NEUTRAL | 3 | BAND repeat resubmission (ref 54304681), byte-identical to ref 54304483. Board readings drifted to mixed sign (442.9 vs 600.0 vs king 494.8). U23 scoreboard settlement (analysis/attack_first_settlement.md): 3 shared brackets, candidate 1/3 (0.333) vs king 4/6 (0.667), confidence 0.171, verdict neutral. Reverting slot to a king copy next iteration (quota exhausted this UTC day). |

```json STATE
{
  "active_candidates": [
    {
      "build": "cem-grown-genome (PRIO ordering)",
      "note": "CLOSED, not awaiting a slot. REAL U35 run executed (seed 0, agreement-only, --split train; analysis/cem_run_prio.md, artifact analysis/cem_runs/cem_run_prio_train_seed0.json). Best genome raises PRIO_ATTACK 0->3.13 and PRIO_ATTACH 3->3.74; gains +0.060 agreement on train (25->32/116) but LOSES -0.067 on the held-out test bucket (7->5/30). best_fitness flat across all 12 iterations (weak gradient). Held-out agreement delta NEGATIVE => pre-registered offline filter BLOCKS: no ladder A/B, ship byte-identical. CEM candidate 1 of the 2 failing/neutral that trip the CEM-plateau contingency (~Jul 15). Re-test only with a larger expert sample, the two-channel fitness on (--pool-matches>0), or a genome with a non-flat held-out gradient. RE-TEST 2026-07-03 (condition b, pool-matches>0): reduced-scale run (analysis/cem_run_prio_pooled.md) also BLOCKED -- held-out test agreement exactly unchanged (7/30 both default and tuned, zero decisions flipped) and train-bucket pool win rate WORSE for the tuned vector (0.567 vs 0.700, n=30, noisy). This is CEM candidate 2 of 2 tripping the plan's CEM-plateau contingency ahead of the ~Jul 15 checkpoint; flagged for the next weekly plan review, no unilateral pivot this iteration. RE-TEST 2026-07-03 (condition a, U83 teacher-corpus distill, --ring-matches 6 against the calibrated L5 ring, --teacher-labels data/training, seed 0): full-scale sweep over a 32003-train/10689-test teacher corpus (92x/356x the first two attempts' sample) also BLOCKED -- held-out test agreement 0.8210 -> 0.8189, delta -0.0022, and full-population train agreement also went backwards (0.8077 -> 0.8049). Diagnosed cause: the sweep's own best fitness was dominated by a noisy 6-game ring-win-rate read, the same proxy-metric-moves-backwards failure as attempt 2, surviving the scale increase. CEM candidate 3 of 3 non-WIN; condition (a) is now closed (tried at scale, still negative). Only remaining re-test condition: (c) a genome region with a measured non-flat held-out gradient. analysis/cem_run_prio_teacher.md, artifact analysis/cem_runs/u83_teacher_ring_seed0.json."
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
  "final_scoring": {
    "daily_limit": "5 submissions/day",
    "deadline": "2026-08-16 23:59 UTC",
    "final_window": "~2 weeks continued games (newer agents more frequent), then leaderboard final",
    "model": "latest-2 tracked and used for final scoring; leaderboard shows best of the 2 (no best-ever net; a 3rd submit evicts the 3rd-newest)",
    "recorded": "2026-07-02",
    "source": "analysis/final_scoring_semantics.md"
  },
  "in_flight": {
    "board_reading": "n/a",
    "build": "heuristic+trolley (king-copy revert, queued)",
    "note": "heuristic+trolley-attack_first SETTLED NEUTRAL this iteration via the U23 scoreboard tiebreak (analysis/attack_first_settlement.md): 3 shared-bracket decisive episodes, candidate 0.333 vs king 0.667, confidence 0.171, favors_candidate=false. Per the pre-registered BAND action, the slot reverts to a byte-identical heuristic+trolley king copy; that tarball is built and grader-verified (test_grader_submission.py[heuristic-trolley]) but NOT YET SUBMITTED: the Kaggle daily quota was already exhausted for 2026-07-03 UTC (6 real submissions that day, not the 2 the prior note tracked; the API returned 'used its daily Submission allowance (5) today'). Submit the queued king copy as the first action next iteration once the quota window resets (~00:00 UTC 2026-07-04), then update kings/ledger.",
    "ref": "queued, not yet submitted"
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
    }
  ],
  "loss_distribution": {
    "buckets": {
      "bad_determinization": 22,
      "deck_matchup": 20,
      "deckout": 17,
      "early_collapse": 60,
      "endgame_misplay": 6,
      "slow_search": 0
    },
    "draws": 1,
    "games": 224,
    "losses": 125,
    "sample_size": 224,
    "sources": [
      "data/replays"
    ],
    "top_bucket": "early_collapse",
    "wins": 98
  },
  "noise_model": {
    "basis": "same-behavior pair 591.9/569.6 + KD2 king resubmission heuristic+trolley 569.6 -> 600.0 byte-identical (same-build spread ~30 either side; true estimate ~585)",
    "margin_M": 60,
    "refit_by": "2026-07-15",
    "version": 1
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
    "ladder": "494.8",
    "note": "board check 2026-07-04: 494.8 (was 691.5 first reading 2026-07-03); same-build ladder drift, ref/build unchanged, still the reclaim-king safe floor.",
    "ref": "54282104"
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
    "ladder": "561.1",
    "note": "WIN settled 2026-07-04 (board check): candidate 561.1 vs reclaim-king 494.8 (ref 54282104), diff +66.3pp, clears the M=60 WIN threshold on the standing instant-settlement rule (tools/loop_state.py auto-settle). Promoted per its own pre-registration's WIN action. Reading is now FROZEN: submitting heuristic+trolley-attack_first (ref 54304483) into the other slot this same iteration evicted 54282097 from the tracked latest-2 (it was the older of the two live submissions by 28s), so this is its last live board reading, not an ongoing one.",
    "ref": "54282097"
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
