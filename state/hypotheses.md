# Loop state: hypotheses

The falsified-lever registry. Read this BEFORE proposing a fix: do not
re-walk a refuted lever unless its recorded re-test condition is met (a
larger sample or a different deck). A refutation is stateful, not
permanent. Machine-readable source of truth is the fenced `json STATE`
block at the bottom.

| lever | verdict | sample | deck | re-test when | source |
| --- | --- | --- | --- | --- | --- |
| gameplan_seeds_diffuse | refuted for target-card seeds; within-turn sequencing signal CONFIRMED | 5732 real episodes; grimmsnarl 1996/1763, archaludon 2294/2442 | meta_grimmsnarl + meta_archaludon | MET at the resolver level 2026-07-03 (U91 step 1): attach_target now resolves the receiving Pokemon (was the energy card id) and play_target now resolves (was structurally 0.0). Validated on bracket_4 real data (n=1500 episodes, 642 win / 707 loss appearances): both blocks 1.000 resolution, up from 0.470/0.285 and 0.000. 2026-07-03 (U91 step 2): two turn-scoped blocks (attach_before_attack, energy_banking, a DIFFERENT question than target-card seeds) both CONFIRMED on bracket_4's full dataset -- claim gate (n>=1400/side, bootstrap 90% CI excludes zero) AND prediction gate (KD4 train CI brackets held-out test mean) both passed: winners attach-before-attacking 3.4pp less (0.524 vs 0.558) and bank energy 4.4pp less (0.192 vs 0.236) than losers; game_length_turns CUT (claim CI straddles zero). 2026-07-03 (U93 step 1): built the literal flag-gated rule from the confirmed gap -- PTCG_ATTACK_FIRST (default off, agents/heuristics.py choose()): take an already-legal positive-value attack instead of a discretionary attach. Fires-vs-inert check (tools/measure_attack_first.py, mirrors measure_energy_seq's discipline) found it LIVE on trolley (3/20 real captured ATTACH+ATTACK positions flipped the pilot decision; analysis/attack_first_flip_check.md). Still open before a full re-mine of the two NAMED families: (1) the archetype-registry shadowing that currently classifies zero decks as meta_archaludon/meta_grimmsnarl in this dataset (bracket_1..6, added after this dataset was mined, win coverage ties alphabetically) or swap the mining target to a bracket family; (2) U93 step 2: the bracket-ring A/B (>=+5pp with gauntlet-direction agreement) before any ladder slot. 2026-07-04 (U93 step 2): both offline gates PASSED -- weak-bot gauntlet +5.5pp (analysis/attack_first_ab.md), bracket-ring +10.0pp agreeing in direction (analysis/attack_first_ring_check.md). Pre-registered as heuristic+trolley-attack_first (state/current.md, direction up, M=60, N=30, settle-by 2026-07-11); staged and grader-verified, awaiting a free ladder slot. | analysis/gameplans/seeds_real_run.md, analysis/gameplan_target_resolution_fixed.md, analysis/gameplan_claims_bracket_4.md |
| meta_deck_copy | refuted | 2 ladder A/Bs | meta_archaludon/meta_grimmsnarl | a deck-AWARE pilot on the same meta deck was NEVER measured (382.5/510.1 used the GENERIC pilot; review P0-1 / KD9): re-test via U38 step 1 once a deck-aware differentiator exists (a concentrated win-vs-loss seed, a card_effects/ability lever that changes meta-card decisions, or the U40/U41 learned per-archetype pilot). Also still stands: U13 cloned-opponent search showing the pilot can execute complex lines. | analysis/meta_decks_underperform_on_ladder.md |
| search_active_beats_heuristic | refuted | ladder A/B pair | trolley | MET 2026-07-02: the U27 PIMC determinization diagnostic is FAVORABLE (analysis/pimc_diagnostic.md), so the P3 U45 belief-weighted-search lane may re-confirm 514.7 vs 569.6 under the protocol as part of that lane, never before. | analysis/ladder_search_inert.md + analysis/ladder_scored_pair_reclaim.md |
| bench_floor_leaf_term | refuted | depth sweep | trolley | n/a in search leaf; the term was RE-HOMED into agents/heuristics.py (P1/U2) | analysis/bench_floor_search_lever_squeezed.md |
| thin_bench_threshold | refuted | guard sweep on trolley | trolley | MET by a higher-basic-density deck (P1/U3): the floor is deck-set, so re-measure on trolley_thick | analysis/thin_bench_threshold_is_flat.md |
| bench_dig | refuted | ladder replays (at scale) | trolley | a still-larger sample or a higher-basic deck may flip it again | analysis/bench_dig_refuted_at_scale.md |
| energy_seq | refuted | 1445 expert ATTACH decisions | n/a (move-ranking) | a richer wrong-target attach model, not the sequencing lever | analysis/energy_seq_refuted_by_expert_moves.md |
| missed_lethal | falsified | all lost-game MAIN decisions | n/a | n/a (artifact, not a real lever) | analysis/missed_lethal_falsified.md |
| cem_flat_gradient | resolved | 40 held-out expert episodes / 1427 MAIN decisions | n/a | resolved; a real cem_tune.py run is now the pending action | analysis/cem_signal_flat.md -> analysis/cem_gradient_restored.md |
| cem_prio_agreement_generalizes | refuted | 116 train / 30 held-out test MAIN decisions (seed 0, attempts 1-2); 32003 train / 10689 held-out test MAIN decisions (seed 0, attempt 3, teacher corpus); 10689 held-out per-dim probe reads (condition c check) | n/a (move-ranking) | conditions (a), (b), and (c) ALL now exhausted (larger sample tried at 92x scale, still negative held-out; pool-matches>0 tried, still flat/negative; the per-dim held-out gradient was measured directly and every load-bearing dim's default already beats both its bounds). Re-open only with a genuinely new weight-space region this genome does not yet express, not a re-run of this genome. | analysis/cem_run_prio.md, analysis/cem_run_prio_pooled.md, analysis/cem_run_prio_teacher.md, analysis/cem_gradient_condition_c.md |
| clone_imitation_beats_first_legal | refuted (4 converging attempts) | clone_groups_1783047584.npz, 1299-11092 held-out decisions per family across 4 families | meta_archaludon/meta_grimmsnarl/meta_grimmsnarl_tonakaiiii/other | model family and feature set already exhausted; a genuinely new label scheme or feature source outside imitation_features is required, not another model/objective swap over this dataset. | analysis/clone_quality.md, analysis/rank_clone_killtest.md |

## Detail

### gameplan_seeds_diffuse (refuted for target-card seeds; within-turn sequencing signal CONFIRMED)
- claim: Mining the target family's real expert episodes yields concentrated winning-play blocks the U37 consumer can bake as hard constants (opening, attach/play/evolve targets, first-attack/first-evolve timing).
- evidence: On the full 5732-episode dataset, meta_grimmsnarl (quality target, 1996 win / 1763 loss) emits ZERO seeds -- every block barred (play_target 0.0 resolution; both timing under the 0.90 resolution bar) or below its concentration bar (best evolve_target 0.489 < 0.70; opening 0.482 PLAY < 0.95). meta_archaludon emits one (evolve_target=card 190 @ 0.875) but its losing split modes to 190 too, so it is a deck-identity fact not a win-vs-loss edge. play_target structurally barred (0.0 resolution) for both. The --limit 200 smoke concentration was a small-N artifact. The mined-seeds channel is nearly empty; the deck-aware edge must come from the guard stack / card_effects / ranker.
- re-test at sample >= bracket_4, n=1500 episodes (step 1); bracket_4 full dataset, n=1472-1892 per side per block (step 2)

### meta_deck_copy (refuted)
- claim: Copying a proven 1300+ meta decklist lets the heuristic ride a higher ceiling past the ~570 floor.
- evidence: Archaludon 382.5 and Grimmsnarl 510.1 both landed WELL BELOW the trolley floor 569.6; the simple pilot cannot extract a meta deck's ceiling and plays WORSE with one.

### search_active_beats_heuristic (refuted)
- claim: Running determinized search on the ladder beats the plain heuristic.
- evidence: First search subs were INERT (fell back to heuristic, ~0.02s draws). Once force-loaded so search actually ran (search+trolley 54218335), it scored 514.7 vs the heuristic's 569.6 on the SAME deck. Search costs points.

### bench_floor_leaf_term (refuted)
- claim: The convex empty-bench leaf-eval term (eval._BENCH_FLOOR) shipped as a search lever cuts board-out.
- evidence: Fidelity/efficacy squeeze: at the shallow depth where the term changes a decision the rollout has already diverged; at the deeper depth where the rollout is faithful the term goes inert. No depth window where it both fires and is trustworthy. This is WHY the self-preservation term belongs in the PILOT move ordering, not the search leaf.

### thin_bench_threshold (refuted)
- claim: Raising THIN_BENCH (the develop-first guard width) cuts the ~40% empty-bench board-out floor.
- evidence: measure_benchguard --sweep: board-out is FLAT across THIN_BENCH values. The floor is DECK-SET (basic-Pokemon density), not guard-set, so widening the guard alone cannot move it.

### bench_dig (refuted)
- claim: When the bench is thin and we hold no Basic, DIGGING for one (playing a draw/search trainer) cuts board-out.
- evidence: Refuted at scale: in 94% of empty-bench decision moments we hold no benchable Basic to reorder, and digging did not cut the board-out at the larger sample. Note: bench-dig's DIRECTION flipped at a larger sample, so this refutation is sample-conditional.

### energy_seq (refuted)
- claim: PTCG_ENERGY_SEQ (front-load surplus energy onto the attacker) matches top players' attaches.
- evidence: Over 1445 real expert ATTACH decisions the pilot hits the exact target only 87 times (6.0%); the gap is mostly ORDERING (we PLAY/EVOLVE when the expert attaches), which energy-seq does not address. Refuted against the expert move breakdown.

### missed_lethal (falsified)
- claim: The endgame_misplay bucket means the heuristic passes up guaranteed knockouts (missed lethals).
- evidence: A detector replaying every ACTIVE MAIN decision through lethal_move found the lead was a DETECTOR ARTIFACT, not a real bug. The safety-1 lethal check already fires; do not re-walk this.

### cem_flat_gradient (resolved)
- claim: CEM cannot tune the pilot because both fitness channels are near-flat over the genome.
- evidence: True as of cem_signal_flat.md (max per-dim agreement delta 0.0049, 8/11 dims exactly 0). RESOLVED the same day by growing the genome: converting choose()'s fixed category ladder into 7 CEM-tunable PTCG_W_PRIO_* weights lifted the max delta to 0.0526 (>10x). A concrete above-baseline direction now exists (PRIO_ATTACH earlier: 0.2235->0.2495).

### cem_prio_agreement_generalizes (refuted)
- claim: A CEM PRIO genome tuned to maximize expert-move agreement on the train bucket keeps that agreement gain on held-out expert moves, earning a ladder A/B.
- evidence: The real U35 seed-0 run (agreement-only, --split train) found a genome that gains +0.060 on train (25->32 of 116 MAIN decisions) but LOSES -0.067 on the held-out test bucket (7->5 of 30). best_fitness was flat across all 12 iterations (weak gradient), and the held-out agreement delta is negative, so the pre-registered offline filter BLOCKS the candidate: no A/B, ship byte-identical. 1 of the 2 failing/neutral CEM candidates that trip the plan's CEM-plateau contingency. RE-TEST (2026-07-03, retest condition b): a reduced-scale pooled run (population 6-8, iterations 3-4, --pool-matches 10, --w-pool 0.5 --w-val 0.5, seed 0) found a best genome with train agreement 0.25 (29/116, up from default 0.2155/25) but held-out test agreement EXACTLY UNCHANGED at 7/30 (0 of 30 held-out decisions flipped) and a WORSE train-bucket pool win rate (0.567 vs default 0.700, n=30 each, noisy). Zero held-out transfer: BLOCKED again, ship byte-identical. This is CEM candidate 2 of 2 that trips the plan's CEM-plateau contingency (two consecutive non-WIN candidates), met ahead of the ~Jul 15 calendar checkpoint; recorded for the next weekly plan review per the plan-freeze rule, not acted on unilaterally this iteration. RE-TEST (2026-07-03, retest condition a, U83 teacher-corpus distill): a full-scale run (population 16, elite 4, iterations 6, --ring-matches 6 against the calibrated L5 ring, --teacher-labels data/training --limit 4000 --split train, seed 0) used a self-play teacher corpus roughly 92x (train) and 356x (held-out test) the size of the first two attempts' real-replay sample (32003 train / 10689 test scorable MAIN decisions). Held-out test agreement went default 0.8210 -> tuned 0.8189, delta -0.0022, still negative; full-population train agreement also went the wrong way (default 0.8077 -> tuned 0.8049). BLOCKED again, ship byte-identical. This is CEM candidate 3 of 3 non-WIN reads. RE-TEST (2026-07-04, retest condition c, direct per-dim held-out gradient check, no CEM sweep): extended analysis/measure_cem_gradient.py with a --teacher-labels/--split mode and ran it against the exact same held-out test split the three CEM sweeps blocked on (n=10689, baseline agreement 0.8210, matching cem_run_prio_teacher.md exactly). The genome IS non-flat (max per-dim delta 0.2738, over 5x the 2026-07-01 diagnostic's 0.0526), ruling out 'no signal at all'; but every load-bearing ordering dim's shipped default (PRIO_ATTACK, PRIO_ATTACH, PRIO_PLAY, PRIO_EVOLVE) sits at or above both of its own bound readings, so no single-axis move beats the current default anywhere in the 18-dim space (analysis/cem_gradient_condition_c.md). Conditions (a), (b), and (c) are all now exhausted.

### clone_imitation_beats_first_legal (refuted (4 converging attempts))
- claim: A model trained on top-team real MAIN decisions (tools/train_clone.py / tools/rank_clone_killtest.py) can beat always-pick-the-first-legal-option at predicting what a top player actually did, qualifying it as a clone opponent for the bracket ring (plan U71/U92).
- evidence: Three tools/train_clone.py attempts (linear, tree, both again after a local-rank feature fix) all collapsed to top-1 == first-legal on 100% of held-out decisions, exactly tying the baseline on every family; a position-excluded ablation made every family's model WORSE than first-legal (analysis/clone_quality.md). 2026-07-04 (U92 step 0 kill test): the last live hypothesis, training objective (pointwise log-loss vs pairwise-logistic RankNet, analysis.unit_zero_spike.PairwiseLinearRanker), was tested on the same dataset/split (clone_groups_1783047584.npz) with the full feature set restored. Every family still ties first-legal within +/-0.0015 (n_scored 1299-11092 per family): tools/rank_clone_killtest.py, analysis/rank_clone_killtest.md.

```json STATE
{
  "hypotheses": [
    {
      "claim": "Mining the target family's real expert episodes yields concentrated winning-play blocks the U37 consumer can bake as hard constants (opening, attach/play/evolve targets, first-attack/first-evolve timing).",
      "deck": "meta_grimmsnarl + meta_archaludon",
      "evidence": "On the full 5732-episode dataset, meta_grimmsnarl (quality target, 1996 win / 1763 loss) emits ZERO seeds -- every block barred (play_target 0.0 resolution; both timing under the 0.90 resolution bar) or below its concentration bar (best evolve_target 0.489 < 0.70; opening 0.482 PLAY < 0.95). meta_archaludon emits one (evolve_target=card 190 @ 0.875) but its losing split modes to 190 too, so it is a deck-identity fact not a win-vs-loss edge. play_target structurally barred (0.0 resolution) for both. The --limit 200 smoke concentration was a small-N artifact. The mined-seeds channel is nearly empty; the deck-aware edge must come from the guard stack / card_effects / ranker.",
      "name": "gameplan_seeds_diffuse",
      "retest_condition": "MET at the resolver level 2026-07-03 (U91 step 1): attach_target now resolves the receiving Pokemon (was the energy card id) and play_target now resolves (was structurally 0.0). Validated on bracket_4 real data (n=1500 episodes, 642 win / 707 loss appearances): both blocks 1.000 resolution, up from 0.470/0.285 and 0.000. 2026-07-03 (U91 step 2): two turn-scoped blocks (attach_before_attack, energy_banking, a DIFFERENT question than target-card seeds) both CONFIRMED on bracket_4's full dataset -- claim gate (n>=1400/side, bootstrap 90% CI excludes zero) AND prediction gate (KD4 train CI brackets held-out test mean) both passed: winners attach-before-attacking 3.4pp less (0.524 vs 0.558) and bank energy 4.4pp less (0.192 vs 0.236) than losers; game_length_turns CUT (claim CI straddles zero). 2026-07-03 (U93 step 1): built the literal flag-gated rule from the confirmed gap -- PTCG_ATTACK_FIRST (default off, agents/heuristics.py choose()): take an already-legal positive-value attack instead of a discretionary attach. Fires-vs-inert check (tools/measure_attack_first.py, mirrors measure_energy_seq's discipline) found it LIVE on trolley (3/20 real captured ATTACH+ATTACK positions flipped the pilot decision; analysis/attack_first_flip_check.md). Still open before a full re-mine of the two NAMED families: (1) the archetype-registry shadowing that currently classifies zero decks as meta_archaludon/meta_grimmsnarl in this dataset (bracket_1..6, added after this dataset was mined, win coverage ties alphabetically) or swap the mining target to a bracket family; (2) U93 step 2: the bracket-ring A/B (>=+5pp with gauntlet-direction agreement) before any ladder slot. 2026-07-04 (U93 step 2): both offline gates PASSED -- weak-bot gauntlet +5.5pp (analysis/attack_first_ab.md), bracket-ring +10.0pp agreeing in direction (analysis/attack_first_ring_check.md). Pre-registered as heuristic+trolley-attack_first (state/current.md, direction up, M=60, N=30, settle-by 2026-07-11); staged and grader-verified, awaiting a free ladder slot.",
      "retest_sample": "bracket_4, n=1500 episodes (step 1); bracket_4 full dataset, n=1472-1892 per side per block (step 2)",
      "sample_size": "5732 real episodes; grimmsnarl 1996/1763, archaludon 2294/2442",
      "source": "analysis/gameplans/seeds_real_run.md, analysis/gameplan_target_resolution_fixed.md, analysis/gameplan_claims_bracket_4.md",
      "verdict": "refuted for target-card seeds; within-turn sequencing signal CONFIRMED"
    },
    {
      "claim": "Copying a proven 1300+ meta decklist lets the heuristic ride a higher ceiling past the ~570 floor.",
      "deck": "meta_archaludon/meta_grimmsnarl",
      "evidence": "Archaludon 382.5 and Grimmsnarl 510.1 both landed WELL BELOW the trolley floor 569.6; the simple pilot cannot extract a meta deck's ceiling and plays WORSE with one.",
      "name": "meta_deck_copy",
      "retest_caveat": "the hand-coded aware pilot (U37 seeds + guards) is byte-identical to the generic pilot on both live meta decks (empty seeds channel, unconsumed archaludon seed, guards already shipped in the 382.5/510.1 copies), so step 1 has no hand-coded content to measure yet; first candidate is a real deck-aware differentiator.",
      "retest_condition": "a deck-AWARE pilot on the same meta deck was NEVER measured (382.5/510.1 used the GENERIC pilot; review P0-1 / KD9): re-test via U38 step 1 once a deck-aware differentiator exists (a concentrated win-vs-loss seed, a card_effects/ability lever that changes meta-card decisions, or the U40/U41 learned per-archetype pilot). Also still stands: U13 cloned-opponent search showing the pilot can execute complex lines.",
      "retest_kd9_amended": "2026-07-02",
      "sample_size": "2 ladder A/Bs",
      "source": "analysis/meta_decks_underperform_on_ladder.md",
      "verdict": "refuted"
    },
    {
      "claim": "Running determinized search on the ladder beats the plain heuristic.",
      "deck": "trolley",
      "evidence": "First search subs were INERT (fell back to heuristic, ~0.02s draws). Once force-loaded so search actually ran (search+trolley 54218335), it scored 514.7 vs the heuristic's 569.6 on the SAME deck. Search costs points.",
      "name": "search_active_beats_heuristic",
      "retest_condition": "MET 2026-07-02: the U27 PIMC determinization diagnostic is FAVORABLE (analysis/pimc_diagnostic.md), so the P3 U45 belief-weighted-search lane may re-confirm 514.7 vs 569.6 under the protocol as part of that lane, never before.",
      "retest_met": true,
      "sample_size": "ladder A/B pair",
      "source": "analysis/ladder_search_inert.md + analysis/ladder_scored_pair_reclaim.md",
      "verdict": "refuted"
    },
    {
      "claim": "The convex empty-bench leaf-eval term (eval._BENCH_FLOOR) shipped as a search lever cuts board-out.",
      "deck": "trolley",
      "evidence": "Fidelity/efficacy squeeze: at the shallow depth where the term changes a decision the rollout has already diverged; at the deeper depth where the rollout is faithful the term goes inert. No depth window where it both fires and is trustworthy. This is WHY the self-preservation term belongs in the PILOT move ordering, not the search leaf.",
      "name": "bench_floor_leaf_term",
      "retest_condition": "n/a in search leaf; the term was RE-HOMED into agents/heuristics.py (P1/U2)",
      "sample_size": "depth sweep",
      "source": "analysis/bench_floor_search_lever_squeezed.md",
      "verdict": "refuted"
    },
    {
      "claim": "Raising THIN_BENCH (the develop-first guard width) cuts the ~40% empty-bench board-out floor.",
      "deck": "trolley",
      "evidence": "measure_benchguard --sweep: board-out is FLAT across THIN_BENCH values. The floor is DECK-SET (basic-Pokemon density), not guard-set, so widening the guard alone cannot move it.",
      "name": "thin_bench_threshold",
      "retest_condition": "MET by a higher-basic-density deck (P1/U3): the floor is deck-set, so re-measure on trolley_thick",
      "retest_on_deck_change": true,
      "retest_sample": null,
      "sample_size": "guard sweep on trolley",
      "source": "analysis/thin_bench_threshold_is_flat.md",
      "verdict": "refuted"
    },
    {
      "claim": "When the bench is thin and we hold no Basic, DIGGING for one (playing a draw/search trainer) cuts board-out.",
      "deck": "trolley",
      "evidence": "Refuted at scale: in 94% of empty-bench decision moments we hold no benchable Basic to reorder, and digging did not cut the board-out at the larger sample. Note: bench-dig's DIRECTION flipped at a larger sample, so this refutation is sample-conditional.",
      "name": "bench_dig",
      "retest_condition": "a still-larger sample or a higher-basic deck may flip it again",
      "retest_sample": null,
      "sample_size": "ladder replays (at scale)",
      "source": "analysis/bench_dig_refuted_at_scale.md",
      "verdict": "refuted"
    },
    {
      "claim": "PTCG_ENERGY_SEQ (front-load surplus energy onto the attacker) matches top players' attaches.",
      "deck": "n/a (move-ranking)",
      "evidence": "Over 1445 real expert ATTACH decisions the pilot hits the exact target only 87 times (6.0%); the gap is mostly ORDERING (we PLAY/EVOLVE when the expert attaches), which energy-seq does not address. Refuted against the expert move breakdown.",
      "name": "energy_seq",
      "retest_condition": "a richer wrong-target attach model, not the sequencing lever",
      "sample_size": "1445 expert ATTACH decisions",
      "source": "analysis/energy_seq_refuted_by_expert_moves.md",
      "verdict": "refuted"
    },
    {
      "claim": "The endgame_misplay bucket means the heuristic passes up guaranteed knockouts (missed lethals).",
      "deck": "n/a",
      "evidence": "A detector replaying every ACTIVE MAIN decision through lethal_move found the lead was a DETECTOR ARTIFACT, not a real bug. The safety-1 lethal check already fires; do not re-walk this.",
      "name": "missed_lethal",
      "retest_condition": "n/a (artifact, not a real lever)",
      "sample_size": "all lost-game MAIN decisions",
      "source": "analysis/missed_lethal_falsified.md",
      "verdict": "falsified"
    },
    {
      "claim": "CEM cannot tune the pilot because both fitness channels are near-flat over the genome.",
      "deck": "n/a",
      "evidence": "True as of cem_signal_flat.md (max per-dim agreement delta 0.0049, 8/11 dims exactly 0). RESOLVED the same day by growing the genome: converting choose()'s fixed category ladder into 7 CEM-tunable PTCG_W_PRIO_* weights lifted the max delta to 0.0526 (>10x). A concrete above-baseline direction now exists (PRIO_ATTACH earlier: 0.2235->0.2495).",
      "name": "cem_flat_gradient",
      "retest_condition": "resolved; a real cem_tune.py run is now the pending action",
      "sample_size": "40 held-out expert episodes / 1427 MAIN decisions",
      "source": "analysis/cem_signal_flat.md -> analysis/cem_gradient_restored.md",
      "verdict": "resolved"
    },
    {
      "claim": "A CEM PRIO genome tuned to maximize expert-move agreement on the train bucket keeps that agreement gain on held-out expert moves, earning a ladder A/B.",
      "deck": "n/a (move-ranking)",
      "evidence": "The real U35 seed-0 run (agreement-only, --split train) found a genome that gains +0.060 on train (25->32 of 116 MAIN decisions) but LOSES -0.067 on the held-out test bucket (7->5 of 30). best_fitness was flat across all 12 iterations (weak gradient), and the held-out agreement delta is negative, so the pre-registered offline filter BLOCKS the candidate: no A/B, ship byte-identical. 1 of the 2 failing/neutral CEM candidates that trip the plan's CEM-plateau contingency. RE-TEST (2026-07-03, retest condition b): a reduced-scale pooled run (population 6-8, iterations 3-4, --pool-matches 10, --w-pool 0.5 --w-val 0.5, seed 0) found a best genome with train agreement 0.25 (29/116, up from default 0.2155/25) but held-out test agreement EXACTLY UNCHANGED at 7/30 (0 of 30 held-out decisions flipped) and a WORSE train-bucket pool win rate (0.567 vs default 0.700, n=30 each, noisy). Zero held-out transfer: BLOCKED again, ship byte-identical. This is CEM candidate 2 of 2 that trips the plan's CEM-plateau contingency (two consecutive non-WIN candidates), met ahead of the ~Jul 15 calendar checkpoint; recorded for the next weekly plan review per the plan-freeze rule, not acted on unilaterally this iteration. RE-TEST (2026-07-03, retest condition a, U83 teacher-corpus distill): a full-scale run (population 16, elite 4, iterations 6, --ring-matches 6 against the calibrated L5 ring, --teacher-labels data/training --limit 4000 --split train, seed 0) used a self-play teacher corpus roughly 92x (train) and 356x (held-out test) the size of the first two attempts' real-replay sample (32003 train / 10689 test scorable MAIN decisions). Held-out test agreement went default 0.8210 -> tuned 0.8189, delta -0.0022, still negative; full-population train agreement also went the wrong way (default 0.8077 -> tuned 0.8049). BLOCKED again, ship byte-identical. This is CEM candidate 3 of 3 non-WIN reads. RE-TEST (2026-07-04, retest condition c, direct per-dim held-out gradient check, no CEM sweep): extended analysis/measure_cem_gradient.py with a --teacher-labels/--split mode and ran it against the exact same held-out test split the three CEM sweeps blocked on (n=10689, baseline agreement 0.8210, matching cem_run_prio_teacher.md exactly). The genome IS non-flat (max per-dim delta 0.2738, over 5x the 2026-07-01 diagnostic's 0.0526), ruling out 'no signal at all'; but every load-bearing ordering dim's shipped default (PRIO_ATTACK, PRIO_ATTACH, PRIO_PLAY, PRIO_EVOLVE) sits at or above both of its own bound readings, so no single-axis move beats the current default anywhere in the 18-dim space (analysis/cem_gradient_condition_c.md). Conditions (a), (b), and (c) are all now exhausted.",
      "name": "cem_prio_agreement_generalizes",
      "retest_condition": "conditions (a), (b), and (c) ALL now exhausted (larger sample tried at 92x scale, still negative held-out; pool-matches>0 tried, still flat/negative; the per-dim held-out gradient was measured directly and every load-bearing dim's default already beats both its bounds). Re-open only with a genuinely new weight-space region this genome does not yet express, not a re-run of this genome.",
      "retest_sample": null,
      "sample_size": "116 train / 30 held-out test MAIN decisions (seed 0, attempts 1-2); 32003 train / 10689 held-out test MAIN decisions (seed 0, attempt 3, teacher corpus); 10689 held-out per-dim probe reads (condition c check)",
      "source": "analysis/cem_run_prio.md, analysis/cem_run_prio_pooled.md, analysis/cem_run_prio_teacher.md, analysis/cem_gradient_condition_c.md",
      "verdict": "refuted"
    },
    {
      "claim": "A model trained on top-team real MAIN decisions (tools/train_clone.py / tools/rank_clone_killtest.py) can beat always-pick-the-first-legal-option at predicting what a top player actually did, qualifying it as a clone opponent for the bracket ring (plan U71/U92).",
      "deck": "meta_archaludon/meta_grimmsnarl/meta_grimmsnarl_tonakaiiii/other",
      "evidence": "Three tools/train_clone.py attempts (linear, tree, both again after a local-rank feature fix) all collapsed to top-1 == first-legal on 100% of held-out decisions, exactly tying the baseline on every family; a position-excluded ablation made every family's model WORSE than first-legal (analysis/clone_quality.md). 2026-07-04 (U92 step 0 kill test): the last live hypothesis, training objective (pointwise log-loss vs pairwise-logistic RankNet, analysis.unit_zero_spike.PairwiseLinearRanker), was tested on the same dataset/split (clone_groups_1783047584.npz) with the full feature set restored. Every family still ties first-legal within +/-0.0015 (n_scored 1299-11092 per family): tools/rank_clone_killtest.py, analysis/rank_clone_killtest.md.",
      "name": "clone_imitation_beats_first_legal",
      "retest_condition": "model family and feature set already exhausted; a genuinely new label scheme or feature source outside imitation_features is required, not another model/objective swap over this dataset.",
      "retest_sample": null,
      "sample_size": "clone_groups_1783047584.npz, 1299-11092 held-out decisions per family across 4 families",
      "source": "analysis/clone_quality.md, analysis/rank_clone_killtest.md",
      "verdict": "refuted (4 converging attempts)"
    }
  ]
}
```
