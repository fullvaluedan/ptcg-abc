# Loop state: current

Machine-readable source of truth is the fenced `json STATE` block at the
bottom; the prose above is a rendered view regenerated on every write.
Update this every iteration (loss distribution, kings, candidates, ledger).

## Top loss bucket (what this iteration targets)

**early_collapse** over 47 classified replays (W/D/L 26/0/21).

| bucket | losses |
| --- | --- |
| early_collapse | 21 |

## Kings

- **shadow-king** (best live build): heuristic+trolley (ref 54252006, ladder 600.0)
- **reclaim-king** (safe floor): heuristic+trolley (ref 54252006, ladder 600.0)

## Candidates awaiting a ladder slot

- heuristic+trolley_thick (U3/U31 deck A/B): thicker-basic trolley (Kyogre 2->4, energy 35->33); cut mirror empty-bench collapse 80.8%->65.4% (n=240, p<0.001), no win-rate regression (analysis/collapse_rate_thick_deck.md). Tarball grader-verified. SUBMITTED to U20 slot 2 (ref 54252291, 2026-07-02) under a complete pre-registration; now IN-FLIGHT, settling by 2026-07-06.
- cem-grown-genome (PRIO ordering): REAL U35 run executed (seed 0, agreement-only, --split train; analysis/cem_run_prio.md). Best genome raises PRIO_ATTACK 0->3.13 and PRIO_ATTACH 3->3.74; gains +0.060 agreement on train (25->32/116) but LOSES -0.067 on the held-out test bucket (7->5/30). best_fitness flat across all 12 iterations (weak gradient). Held-out agreement delta NEGATIVE => pre-registered offline filter BLOCKS: no ladder A/B, ship byte-identical. This is CEM candidate 1 of the 2 failing/neutral candidates that trip the plan's CEM-plateau contingency (~Jul 15). Re-test only with a larger expert sample, the two-channel fitness on, or a genome with a non-flat held-out gradient.

## Noise model (U22)

- margin M = 60 (v1): WIN >= king+M, LOSS <= king-M, else BAND.
- basis: same-behavior pair 591.9/569.6 + KD2 king resubmission heuristic+trolley 569.6 -> 600.0 byte-identical (same-build spread ~30 either side; true estimate ~585)
- re-fit by: 2026-07-15

## Pre-registrations (machine-checked gate, U22)

A build may not be submitted without a complete row here (tools/loop_state.py check-submit --build <name>).

| build | hypothesis | dir | M | N | settle-by | complete |
| --- | --- | --- | --- | --- | --- | --- |
| heuristic+trolley_thick | trolley_thick basic-density cuts early_collapse (thin_bench_threshold deck-change re-test) | up | 60 | 30 | 2026-07-06 | yes |

- **heuristic+trolley_thick** filters: mirror empty-bench collapse 80.8->65.4 (n=240, p<0.001), no win-rate regression (analysis/collapse_rate_thick_deck.md); tarball grader-verified
  - WIN: promote heuristic+trolley_thick to shadow-king; reclaim-king stays heuristic+trolley
  - LOSS: evict trolley_thick, revert slot 2 to a king copy
  - BAND: one repeat resubmission, then U23 scoreboard at ~90% binomial confidence on shared brackets; else NEUTRAL, revert to king, record thin_bench_threshold re-test condition

## Calibrated proxies (U24 retrodiction gate)

A proxy may BLOCK a slot (never promote) only after it retrodicts the known five-build ordering (tools/loop_state.py check-gate --proxy <name>).

_none calibrated; every proxy gate is refused (default-deny)_

## Expert census tier (U25)

- cohort = winning seat (U25 resolved fork); dataset 2026-06-30 (5734 episodes)
- 5732 episodes scored, 167531 ranking groups
- target family **meta_grimmsnarl** -> tier **full** (analysis/expert_census.md)

## Target selector (U36, piece 1 of 3)

- mastery = expert_wins * expert_win_rate; both seats of 5732 decided episodes classified so losing appearances count (tools/archetype_select.py, analysis/archetype_select.md).
- mastery target **meta_archaludon** (1111.16) narrowly over meta_grimmsnarl (1059.86), DISAGREEING with the census adoption target.
- CAVEAT: closed mirror pool, win_rate ~ 0.50, so mastery still tracks volume. meta_grimmsnarl is the ONLY above-0.5 family (0.531); archaludon wins mastery at a BELOW-0.5 rate (0.484) on game count.
- Discriminating signal is win_rate (agrees with census on grimmsnarl). Recommend **grimmsnarl** as the U37 seeds target; archaludon as mastery runner-up / opponent-model anchor.
- U36 piece **2 of 3 LANDED**: analysis/gameplan_mine.py mines six stat blocks (opening_category, attach_target, play_target, evolve_target, first_attack_ordinal, first_evolve_ordinal), each contrasting the family's WINNING vs LOSING appearances, each with a resolution_rate; a block resolving under 0.90 on the winning split is barred. mode_share/consistency are what the emitter thresholds.
- U36 piece **3 of 3 LANDED**: analysis/gameplan_seeds.py reads the mined blocks and emits seeds for only the blocks that clear BOTH the miner's 0.90 resolution bar (not barred) AND a per-shape concentration bar: 0.70 mode_share for the three target blocks (attach/play/evolve), 0.95 unanimity for the opening commitment, 0.80 consistency for the two timing blocks. Every skip carries a reason (barred / no_mode / below_bar), never silently dropped. Emits an isolated machine seeds JSON (data/derived/gameplans/) plus a committed aggregates-only game-plan doc (analysis/gameplans/<family>_gameplan.md, generated when run on real data). Pure and cg-free (operates on the miner's blocks dict, touches no engine/replay/card data). 11 hermetic tests; full suite 558 pass. NEXT: run the miner+emitter on the real grimmsnarl expert episodes to produce the committed doc, then U37 seeds CONSUMER (bake as build-time dict constants behind a default-off lever, byte-identical unset).

## Search-branch verdict (U27)

- PIMC diagnostic verdict: **FAVORABLE** -> **U45 belief-weighted search** (analysis/pimc_diagnostic.md)
- leaf correlation 0.80-0.91 discriminating, disambiguation slope 0.023-0.037 (marginal), bias 0.46-0.68 (decided 2026-07-02, not revisited per KD7)

## Contract reconciliation record (U28)

- 11 forked contracts each have one binding ruling (docs/design/deck-aware-execution-design.md); recorded 2026-07-02 before any U40 code exists (KD4/KD5).
- W_generic ruling: DROPPED (fallback = pure ladder; no pooled block) (census tier FULL (167531 groups >> 2500) closes it by data).

## Final scoring semantics (U29)

- latest-2 tracked and used for final scoring; leaderboard shows best of the 2 (no best-ever net; a 3rd submit evicts the 3rd-newest) (analysis/final_scoring_semantics.md); recorded 2026-07-02, gates U48.
- deadline 2026-08-16 23:59 UTC, then ~2 weeks continued games (newer agents more frequent), then leaderboard final; daily limit 5 submissions/day.

## Card-effect coverage gate (U33 / MSR-3)

- card-knowledge layer agents/card_effects.py (TAG_VOCAB 8 tags, TAGS_VERSION 1); heuristic text predicates delegate to it, behavior-frozen by a pool-wide golden equivalence test (analysis/card_effects_layer.md).
- target deck **trolley_thick** coverage **1.0** (10/10 distinct: 6 TAGGED, 4 EMPTY); pool untagged fraction 0.4917 (207/421 effect cards), ratcheted by analysis/tag_coverage_baseline.json.
- GATE (advisory until the aware pilot lands): no deck-aware build (U37 seeds, U40/U41 ranker) may spend a ladder slot unless tag_coverage.deck_covered_100pct(target) is true.

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

```json STATE
{
  "active_candidates": [
    {
      "build": "heuristic+trolley_thick (U3/U31 deck A/B)",
      "note": "thicker-basic trolley (Kyogre 2->4, energy 35->33); cut mirror empty-bench collapse 80.8%->65.4% (n=240, p<0.001), no win-rate regression (analysis/collapse_rate_thick_deck.md). Tarball grader-verified. SUBMITTED to U20 slot 2 (ref 54252291, 2026-07-02) under a complete pre-registration; now IN-FLIGHT, settling by 2026-07-06."
    },
    {
      "build": "cem-grown-genome (PRIO ordering)",
      "note": "REAL U35 run executed (seed 0, agreement-only, --split train; analysis/cem_run_prio.md, artifact analysis/cem_runs/cem_run_prio_train_seed0.json). Best genome raises PRIO_ATTACK 0->3.13 and PRIO_ATTACH 3->3.74; gains +0.060 agreement on train (25->32/116) but LOSES -0.067 on the held-out test bucket (7->5/30). best_fitness flat across all 12 iterations (weak gradient). Held-out agreement delta NEGATIVE => pre-registered offline filter BLOCKS: no ladder A/B, ship byte-identical. CEM candidate 1 of the 2 failing/neutral that trip the CEM-plateau contingency (~Jul 15). Re-test only with a larger expert sample, the two-channel fitness on (--pool-matches>0), or a genome with a non-flat held-out gradient."
    }
  ],
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
    "board_reading": 470.9,
    "build": "heuristic+trolley_thick",
    "note": "U20 slot-2 deck A/B SUBMITTED (ref 54252291, 2026-07-02 03:59 UTC) after U22 gate ALLOW and grader exec test green. Pre-registered vs the trolley king: direction up, M=60, N>=30, settle-by 2026-07-06. Settlement needs >=30 rated episodes AND >=24h; early-evict under 35% raw win rate after 15 episodes. WIN>=king+60 promote; LOSS<=king-60 evict+revert to king copy; BAND one repeat then U23 scoreboard. BOARD 2026-07-02 (U27 iter): thick COMPLETE 536.4 vs reclaim king 54252006 491.7 (gap +44.7 in favor of thick, still inside BAND M=60). NOT settled: sub is <24h old, earliest settle 2026-07-03 04:00 UTC. BOARD 2026-07-02 (U28 iter): thick COMPLETE 552.0 vs reclaim king 54252006 472.1 (gap +79.9, now OUTSIDE BAND M=60 in favor of thick). Still NOT settled: sub is <24h old, earliest settle 2026-07-03 04:00 UTC; also needs >=30 rated episodes. No submit this iter. BOARD 2026-07-02 (U29 iter): thick COMPLETE 551.8 vs reclaim king 54252006 497.2 (gap +54.6, back inside BAND M=60). Still NOT settled: sub <24h old (earliest 2026-07-03 04:00 UTC) and needs >=30 rated episodes. No submit this iter. BOARD 2026-07-02 (U32 iter): thick COMPLETE 488.9 vs reclaim king 54252006 507.0 (gap -18.1, king now leads, still well inside BAND M=60; reading reversed from prior readings, consistent with same-build drift). Still NOT settled: sub <24h old (earliest 2026-07-03 04:00 UTC) and needs >=30 rated episodes. No submit this iter. BOARD 2026-07-02 (U33 iter): unchanged from U32, thick COMPLETE 488.9 vs reclaim king 54252006 507.0 (gap -18.1, king leads, well inside BAND M=60); no public-score movement. Still NOT settled (earliest 2026-07-03 04:00 UTC; needs >=30 rated episodes). Best-ever 600.0 clears the 540 floor guard. No submit this iter; quota untouched. BOARD 2026-07-02 (U35-prep iter): thick COMPLETE 480.6 vs reclaim king 54252006 507.0 (gap -26.4, king leads, well inside BAND M=60; same-build/deck drift continues). Still NOT settled (earliest 2026-07-03 04:00 UTC; needs >=30 rated episodes). Best-ever 600.0 clears the 540 floor guard. No submit this iter; quota untouched. BOARD 2026-07-02 (U35 iter): thick COMPLETE 470.9 vs reclaim king 54252006 512.2 (gap -41.3, king leads, inside BAND M=60; same-build/deck drift continues). Still NOT settled (earliest 2026-07-03 04:00 UTC; needs >=30 rated episodes). Best-ever 600.0 clears the 540 floor guard. No submit this iter; quota untouched. BOARD 2026-07-02 (U36 selector iter): unchanged from U35, thick COMPLETE 470.9 vs reclaim king 54252006 512.2 (gap -41.3, king leads, inside BAND M=60; no public-score movement). Still NOT settled (earliest 2026-07-03 04:00 UTC; needs >=30 rated episodes). Best-ever 600.0 clears the 540 floor guard. No submit this iter; quota untouched. BOARD 2026-07-02 (U36 emitter iter): unchanged, thick COMPLETE 470.9 vs reclaim king 54252006 512.2 (gap -41.3, king leads, inside BAND M=60; no public-score movement). Still NOT settled (earliest 2026-07-03 04:00 UTC; needs >=30 rated episodes). Best-ever 600.0 clears the 540 floor guard. No submit this iter; quota untouched.",
    "ref": "54252291"
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
    }
  ],
  "loss_distribution": {
    "buckets": {
      "bad_determinization": 0,
      "deck_matchup": 0,
      "deckout": 0,
      "early_collapse": 21,
      "endgame_misplay": 0,
      "slow_search": 0
    },
    "draws": 0,
    "games": 47,
    "losses": 21,
    "sample_size": 47,
    "sources": [
      "replays_tr558_full",
      "replays_trolley558",
      "replays_trolley_54215558",
      "replays_bg910_full"
    ],
    "top_bucket": "early_collapse",
    "wins": 26
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
    }
  ],
  "reclaim_king": {
    "build": "heuristic+trolley",
    "ladder": 600.0,
    "note": "safe floor to revert to before any A/B; two live copies exist (54215558=569.6, 54252006=600.0)",
    "ref": "54252006"
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
  "shadow_king": {
    "build": "heuristic+trolley",
    "ladder": 600.0,
    "note": "best live reading (byte-identical king copy); same-build true estimate ~585 from 569.6/600.0",
    "ref": "54252006"
  },
  "target_selector": {
    "formula": "mastery = expert_wins * expert_win_rate",
    "mastery_target": "meta_archaludon",
    "note": "U36 selector piece 1 of 3 (tools/archetype_select.py). Classifies BOTH seats of 5732 decided episodes so losing appearances count. By mastery the target is meta_archaludon (1111.16) narrowly over meta_grimmsnarl (1059.86), DISAGREEING with the census adoption target. But this is a closed mirror pool so win_rate ~ 0.50 and mastery still tracks volume: meta_grimmsnarl is the ONLY above-0.5 family (0.531) while archaludon wins mastery at a BELOW-0.5 rate (0.484) on game count. Discriminating signal is win_rate, which agrees with the census on grimmsnarl as the quality pick. Recommend grimmsnarl as the U37 seeds target, archaludon as mastery runner-up / opponent-model anchor. Miner (piece 2) LANDED: analysis/gameplan_mine.py mines six stat blocks (opening_category, attach_target, play_target, evolve_target, first_attack_ordinal, first_evolve_ordinal), each contrasting winning vs losing appearances, each with a resolution_rate; a winning-split resolution under 0.90 bars the block. Seeds emitter (piece 3) LANDED: analysis/gameplan_seeds.py emits a seed for a block only when it clears BOTH the miner's 0.90 resolution bar (not barred) AND its concentration bar (0.70 mode_share for attach/play/evolve, 0.95 unanimity for the opening, 0.80 consistency for the two timing blocks); skips carry a reason (barred/no_mode/below_bar), isolated seeds JSON + committed aggregates-only doc, pure/cg-free, 11 hermetic tests. NEXT: run miner+emitter on real grimmsnarl episodes for the committed doc, then U37 seeds CONSUMER.",
    "quality_target": "meta_grimmsnarl",
    "recorded": "2026-07-02",
    "source": "analysis/archetype_select.md"
  }
}
```
