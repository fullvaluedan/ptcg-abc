# Loop state: hypotheses

The falsified-lever registry. Read this BEFORE proposing a fix: do not
re-walk a refuted lever unless its recorded re-test condition is met (a
larger sample or a different deck). A refutation is stateful, not
permanent. Machine-readable source of truth is the fenced `json STATE`
block at the bottom.

| lever | verdict | sample | deck | re-test when | source |
| --- | --- | --- | --- | --- | --- |
| meta_deck_copy | refuted | 2 ladder A/Bs | meta_archaludon/meta_grimmsnarl | only if U13 cloned-opponent search shows the pilot can execute complex lines | analysis/meta_decks_underperform_on_ladder.md |
| search_active_beats_heuristic | refuted | ladder A/B pair | trolley | MET 2026-07-02: the U27 PIMC determinization diagnostic is FAVORABLE (analysis/pimc_diagnostic.md), so the P3 U45 belief-weighted-search lane may re-confirm 514.7 vs 569.6 under the protocol as part of that lane, never before. | analysis/ladder_search_inert.md + analysis/ladder_scored_pair_reclaim.md |
| bench_floor_leaf_term | refuted | depth sweep | trolley | n/a in search leaf; the term was RE-HOMED into agents/heuristics.py (P1/U2) | analysis/bench_floor_search_lever_squeezed.md |
| thin_bench_threshold | refuted | guard sweep on trolley | trolley | MET by a higher-basic-density deck (P1/U3): the floor is deck-set, so re-measure on trolley_thick | analysis/thin_bench_threshold_is_flat.md |
| bench_dig | refuted | ladder replays (at scale) | trolley | a still-larger sample or a higher-basic deck may flip it again | analysis/bench_dig_refuted_at_scale.md |
| energy_seq | refuted | 1445 expert ATTACH decisions | n/a (move-ranking) | a richer wrong-target attach model, not the sequencing lever | analysis/energy_seq_refuted_by_expert_moves.md |
| missed_lethal | falsified | all lost-game MAIN decisions | n/a | n/a (artifact, not a real lever) | analysis/missed_lethal_falsified.md |
| cem_flat_gradient | resolved | 40 held-out expert episodes / 1427 MAIN decisions | n/a | resolved; a real cem_tune.py run is now the pending action | analysis/cem_signal_flat.md -> analysis/cem_gradient_restored.md |

## Detail

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

```json STATE
{
  "hypotheses": [
    {
      "claim": "Copying a proven 1300+ meta decklist lets the heuristic ride a higher ceiling past the ~570 floor.",
      "deck": "meta_archaludon/meta_grimmsnarl",
      "evidence": "Archaludon 382.5 and Grimmsnarl 510.1 both landed WELL BELOW the trolley floor 569.6; the simple pilot cannot extract a meta deck's ceiling and plays WORSE with one.",
      "name": "meta_deck_copy",
      "retest_condition": "only if U13 cloned-opponent search shows the pilot can execute complex lines",
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
    }
  ]
}
```
