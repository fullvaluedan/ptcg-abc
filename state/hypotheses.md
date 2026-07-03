# Loop state: hypotheses

The falsified-lever registry. Read this BEFORE proposing a fix: do not
re-walk a refuted lever unless its recorded re-test condition is met (a
larger sample or a different deck). A refutation is stateful, not
permanent. Machine-readable source of truth is the fenced `json STATE`
block at the bottom.

| lever | verdict | sample | deck | re-test when | source |
| --- | --- | --- | --- | --- | --- |
| gameplan_seeds_diffuse | refuted | 5732 real episodes; grimmsnarl 1996/1763, archaludon 2294/2442 | meta_grimmsnarl + meta_archaludon | MET at the resolver level 2026-07-03 (U91): attach_target/play_target now resolve the receiving Pokemon / played hand card (were 0.470/0.285 and 0.000 barred); validated on bracket_4 real data (n=1500 episodes) at 1.000/1.000 resolution. Still open: a NARROWER cohort or new block shape to concentrate the now-resolvable distributions past the 0.70 share bar, AND the archetype-registry shadowing that currently keeps meta_archaludon/meta_grimmsnarl from classifying any deck in this dataset (analysis/gameplan_target_resolution_fixed.md) needs a fix or a family swap before those two named families can be re-mined end to end. | analysis/gameplans/seeds_real_run.md, analysis/gameplan_target_resolution_fixed.md |
| meta_deck_copy | refuted | 2 ladder A/Bs | meta_archaludon/meta_grimmsnarl | a deck-AWARE pilot on the same meta deck was NEVER measured (382.5/510.1 used the GENERIC pilot; review P0-1 / KD9): re-test via U38 step 1 once a deck-aware differentiator exists (a concentrated win-vs-loss seed, a card_effects/ability lever that changes meta-card decisions, or the U40/U41 learned per-archetype pilot). Also still stands: U13 cloned-opponent search showing the pilot can execute complex lines. | analysis/meta_decks_underperform_on_ladder.md |
| search_active_beats_heuristic | refuted | ladder A/B pair | trolley | MET 2026-07-02: the U27 PIMC determinization diagnostic is FAVORABLE (analysis/pimc_diagnostic.md), so the P3 U45 belief-weighted-search lane may re-confirm 514.7 vs 569.6 under the protocol as part of that lane, never before. | analysis/ladder_search_inert.md + analysis/ladder_scored_pair_reclaim.md |
| bench_floor_leaf_term | refuted | depth sweep | trolley | n/a in search leaf; the term was RE-HOMED into agents/heuristics.py (P1/U2) | analysis/bench_floor_search_lever_squeezed.md |
| thin_bench_threshold | refuted | guard sweep on trolley | trolley | MET by a higher-basic-density deck (P1/U3): the floor is deck-set, so re-measure on trolley_thick | analysis/thin_bench_threshold_is_flat.md |
| bench_dig | refuted | ladder replays (at scale) | trolley | a still-larger sample or a higher-basic deck may flip it again | analysis/bench_dig_refuted_at_scale.md |
| energy_seq | refuted | 1445 expert ATTACH decisions | n/a (move-ranking) | a richer wrong-target attach model, not the sequencing lever | analysis/energy_seq_refuted_by_expert_moves.md |
| missed_lethal | falsified | all lost-game MAIN decisions | n/a | n/a (artifact, not a real lever) | analysis/missed_lethal_falsified.md |
| cem_flat_gradient | resolved | 40 held-out expert episodes / 1427 MAIN decisions | n/a | resolved; a real cem_tune.py run is now the pending action | analysis/cem_signal_flat.md -> analysis/cem_gradient_restored.md |
| cem_prio_agreement_generalizes | refuted | 116/30 (attempt 1); 116/30 pooled (attempt 2); 32003/10689 teacher corpus (attempt 3, seed 0) | n/a (move-ranking) | conditions (a) and (b) now BOTH exhausted (larger sample tried at 92x scale, still negative held-out; pool-matches>0 tried, still flat/negative). Re-test only with (c) a genome region with a measured non-flat held-out gradient. | analysis/cem_run_prio.md, analysis/cem_run_prio_pooled.md, analysis/cem_run_prio_teacher.md |

## Detail

### gameplan_seeds_diffuse (refuted)
- claim: Mining the target family's real expert episodes yields concentrated winning-play blocks the U37 consumer can bake as hard constants (opening, attach/play/evolve targets, first-attack/first-evolve timing).
- evidence: On the full 5732-episode dataset, meta_grimmsnarl (quality target, 1996 win / 1763 loss) emits ZERO seeds -- every block barred (play_target 0.0 resolution; both timing under the 0.90 resolution bar) or below its concentration bar (best evolve_target 0.489 < 0.70; opening 0.482 PLAY < 0.95). meta_archaludon emits one (evolve_target=card 190 @ 0.875) but its losing split modes to 190 too, so it is a deck-identity fact not a win-vs-loss edge. play_target structurally barred (0.0 resolution) for both. The --limit 200 smoke concentration was a small-N artifact. The mined-seeds channel is nearly empty; the deck-aware edge must come from the guard stack / card_effects / ranker.

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
- evidence: The real U35 seed-0 run (agreement-only, --split train) found a genome that gains +0.060 on train (25->32 of 116 MAIN decisions) but LOSES -0.067 on the held-out test bucket (7->5 of 30). best_fitness was flat across all 12 iterations (weak gradient), and the held-out agreement delta is negative, so the pre-registered offline filter BLOCKS the candidate: no A/B, ship byte-identical. 1 of the 2 failing/neutral CEM candidates that trip the plan's CEM-plateau contingency. RE-TEST (2026-07-03, retest condition b): a reduced-scale pooled run (population 6-8, iterations 3-4, --pool-matches 10, --w-pool 0.5 --w-val 0.5, seed 0) found a best genome with train agreement 0.25 (29/116, up from default 0.2155/25) but held-out test agreement EXACTLY UNCHANGED at 7/30 (0 of 30 held-out decisions flipped) and a WORSE train-bucket pool win rate (0.567 vs default 0.700, n=30 each, noisy). Zero held-out transfer: BLOCKED again, ship byte-identical. This is CEM candidate 2 of 2 that trips the plan's CEM-plateau contingency (two consecutive non-WIN candidates), met ahead of the ~Jul 15 calendar checkpoint; recorded for the next weekly plan review per the plan-freeze rule, not acted on unilaterally this iteration.

```json STATE
{
  "hypotheses": [
    {
      "claim": "Mining the target family's real expert episodes yields concentrated winning-play blocks the U37 consumer can bake as hard constants (opening, attach/play/evolve targets, first-attack/first-evolve timing).",
      "deck": "meta_grimmsnarl + meta_archaludon",
      "evidence": "On the full 5732-episode dataset, meta_grimmsnarl (quality target, 1996 win / 1763 loss) emits ZERO seeds -- every block barred (play_target 0.0 resolution; both timing under the 0.90 resolution bar) or below its concentration bar (best evolve_target 0.489 < 0.70; opening 0.482 PLAY < 0.95). meta_archaludon emits one (evolve_target=card 190 @ 0.875) but its losing split modes to 190 too, so it is a deck-identity fact not a win-vs-loss edge. play_target structurally barred (0.0 resolution) for both. The --limit 200 smoke concentration was a small-N artifact. The mined-seeds channel is nearly empty; the deck-aware edge must come from the guard stack / card_effects / ranker.",
      "name": "gameplan_seeds_diffuse",
      "retest_condition": "MET at the resolver level 2026-07-03 (U91): attach_target now resolves the receiving Pokemon (was the energy card id) and play_target now resolves (was structurally 0.0). Validated on bracket_4 real data (n=1500 episodes, 642 win / 707 loss appearances): both blocks 1.000 resolution, up from 0.470/0.285 and 0.000. Still open before a full re-mine: (1) concentrate the now-resolvable distributions past the 0.70 share bar (a narrower cohort or a new block shape), (2) fix the archetype-registry shadowing that currently classifies zero decks as meta_archaludon/meta_grimmsnarl in this dataset (bracket_1..6, added after this dataset was mined, win coverage ties alphabetically) or swap the mining target to a bracket family.",
      "retest_sample": "bracket_4, n=1500 episodes, 642 winning / 707 losing appearances",
      "sample_size": "5732 real episodes; grimmsnarl 1996/1763, archaludon 2294/2442",
      "source": "analysis/gameplans/seeds_real_run.md, analysis/gameplan_target_resolution_fixed.md",
      "verdict": "refuted"
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
      "evidence": "The real U35 seed-0 run (agreement-only, --split train) found a genome that gains +0.060 on train (25->32 of 116 MAIN decisions) but LOSES -0.067 on the held-out test bucket (7->5 of 30). best_fitness was flat across all 12 iterations (weak gradient), and the held-out agreement delta is negative, so the pre-registered offline filter BLOCKS the candidate: no A/B, ship byte-identical. 1 of the 2 failing/neutral CEM candidates that trip the plan's CEM-plateau contingency. RE-TEST (2026-07-03, retest condition b): a reduced-scale pooled run (population 6-8, iterations 3-4, --pool-matches 10, --w-pool 0.5 --w-val 0.5, seed 0) found a best genome with train agreement 0.25 (29/116, up from default 0.2155/25) but held-out test agreement EXACTLY UNCHANGED at 7/30 (0 of 30 held-out decisions flipped) and a WORSE train-bucket pool win rate (0.567 vs default 0.700, n=30 each, noisy). Zero held-out transfer: BLOCKED again, ship byte-identical. This is CEM candidate 2 of 2 that trips the plan's CEM-plateau contingency (two consecutive non-WIN candidates), met ahead of the ~Jul 15 calendar checkpoint; recorded for the next weekly plan review per the plan-freeze rule, not acted on unilaterally this iteration. RE-TEST (2026-07-03, retest condition a, U83 teacher-corpus distill): a full-scale run (population 16, elite 4, iterations 6, --ring-matches 6 against the calibrated L5 ring, --teacher-labels data/training --limit 4000 --split train, seed 0) used a self-play teacher corpus roughly 92x (train) and 356x (held-out test) the size of the first two attempts' real-replay sample (32003 train / 10689 test scorable MAIN decisions). Held-out test agreement went default 0.8210 -> tuned 0.8189, delta -0.0022, still negative; full-population train agreement also went the wrong way (default 0.8077 -> tuned 0.8049), worse than either prior attempt since those at least improved train agreement before failing to transfer. Diagnosis: the sweep's own reported best fitness (0.8940) was dominated by a high-variance 6-game ring-win-rate read over only a 4000-decision slice, the same proxy-metric-moves-backwards failure shape as attempt 2, this time surviving a two-orders-of-magnitude larger corpus. BLOCKED again, ship byte-identical. This is CEM candidate 3 of 3 non-WIN reads across three different fitness formulations and label sources; re-open condition (a) is now closed (tried at scale, still negative), only (c) remains untried.",
      "name": "cem_prio_agreement_generalizes",
      "retest_condition": "conditions (a) and (b) now BOTH exhausted (a materially larger expert-move sample was tried at 92x/356x scale, still negative held-out; pool-matches>0 tried, still flat/negative). Re-test only with (c) a genome region with a measured non-flat held-out gradient.",
      "retest_sample": null,
      "sample_size": "116 train / 30 held-out test MAIN decisions (seed 0, attempts 1-2); 32003 train / 10689 held-out test MAIN decisions (seed 0, attempt 3, teacher corpus)",
      "source": "analysis/cem_run_prio.md, analysis/cem_run_prio_pooled.md, analysis/cem_run_prio_teacher.md",
      "verdict": "refuted"
    }
  ]
}
```
