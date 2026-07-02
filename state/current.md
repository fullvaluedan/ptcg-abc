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
- cem-grown-genome (PRIO ordering): genome grown so CEM has a gradient (analysis/cem_gradient_restored.md); a real tools/cem_tune.py run is the pending next step, then offline-filter and gate on ladder A/B. Un-tuned build ships byte-identical.

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

## Per-build ledger

| build | oracle | move-agree delta | ladder | sample | note |
| --- | --- | --- | --- | --- | --- |
| heuristic+trolley (reclaim) | n/a | n/a | 600.0 | 0 | U20 slot-1 king reclaim; byte-identical to the 569.6 king; settled 600.0, drifted to 594.7 on 2026-07-02 board check => same-build noise band ~25-30/side (KD2 calibration) Board 2026-07-02: 556.7 (600.0 settled then 594.7 then 556.7; same-build drift within the ~30/side band). |
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
      "note": "genome grown so CEM has a gradient (analysis/cem_gradient_restored.md); a real tools/cem_tune.py run is the pending next step, then offline-filter and gate on ladder A/B. Un-tuned build ships byte-identical."
    }
  ],
  "in_flight": {
    "board_reading": 497.1,
    "build": "heuristic+trolley_thick",
    "note": "U20 slot-2 deck A/B SUBMITTED (ref 54252291, 2026-07-02) after U22 gate ALLOW and grader exec test green on the exact tarball; evicts below-floor meta copy grimmsnarl 489.6. Pre-registered vs the trolley king (594.7): direction up, M=60, N>=30, settle-by 2026-07-06. Settlement needs >=30 rated episodes AND >=24h; early-evict under 35% raw win rate after 15 episodes. WIN>=king+60 promote; LOSS<=king-60 evict+revert to king copy; BAND one repeat then U23 scoreboard. BOARD 2026-07-02: reads COMPLETE 497.1 vs reclaim king 556.7 (gap 59.6 approx king-60, trending LOSS); NOT yet settled (sub <24h old, need >=30 episodes AND >=24h, earliest 2026-07-03).",
    "ref": "54252291"
  },
  "ledger": [
    {
      "build": "heuristic+trolley (reclaim)",
      "ladder": 600.0,
      "move_agreement_delta": "n/a",
      "note": "U20 slot-1 king reclaim; byte-identical to the 569.6 king; settled 600.0, drifted to 594.7 on 2026-07-02 board check => same-build noise band ~25-30/side (KD2 calibration) Board 2026-07-02: 556.7 (600.0 settled then 594.7 then 556.7; same-build drift within the ~30/side band).",
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
  "shadow_king": {
    "build": "heuristic+trolley",
    "ladder": 600.0,
    "note": "best live reading (byte-identical king copy); same-build true estimate ~585 from 569.6/600.0",
    "ref": "54252006"
  }
}
```
