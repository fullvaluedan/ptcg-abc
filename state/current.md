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

- **shadow-king** (best live build): heuristic+trolley (ladder 569.6; original ref 54215558, live-reclaim copy 54252006)
- **reclaim-king** (safe floor): heuristic+trolley (ladder 569.6; original ref 54215558, live-reclaim copy 54252006)

## In-flight / scored slots

- 2026-07-02: U20 slot-1 king reclaim SUBMITTED (ref 54252006, heuristic+trolley, byte-identical to the 569.6 king). Floor-guard action: prior active pair best was 489.6 < 540, so a king copy overrode the queue. Evicts the oldest active meta copy (archaludon 387.0). Doubles as the KD2 same-build noise-calibration resubmission. Slot 2 (trolley_thick deck A/B, evicting grimmsnarl 489.6) is NEXT once this reads at or above the floor.

## Candidates awaiting a ladder slot

- heuristic+trolley_thick (U3/U31 deck A/B): thicker-basic trolley (Kyogre 2->4, energy 35->33); cut mirror empty-bench collapse 80.8%->65.4% (n=240, p<0.001), no win-rate regression (analysis/collapse_rate_thick_deck.md). Tarball grader-verified. QUEUED for U20 slot 2; needs a pre-registered A/B row (margin M=60, N>=30, settle-by) before submit.
- cem-grown-genome (PRIO ordering): genome grown so CEM has a gradient (analysis/cem_gradient_restored.md); a real tools/cem_tune.py run is the pending next step, then offline-filter and gate on ladder A/B. Un-tuned build ships byte-identical.

## Per-build ledger

| build | oracle | move-agree delta | ladder | sample | note |
| --- | --- | --- | --- | --- | --- |
| heuristic+trolley (reclaim 54252006) | n/a | n/a | pending | 0 | U20 slot-1 king reclaim 2026-07-02; same build as 569.6 king; noise-calibration copy |
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
      "note": "thicker-basic trolley (Kyogre 2->4, energy 35->33); cut mirror empty-bench collapse 80.8%->65.4% (n=240, p<0.001), no win-rate regression (analysis/collapse_rate_thick_deck.md). Tarball grader-verified. QUEUED for U20 slot 2; needs a pre-registered A/B row (M=60, N>=30, settle-by) before submit."
    },
    {
      "build": "cem-grown-genome (PRIO ordering)",
      "note": "genome grown so CEM has a gradient (analysis/cem_gradient_restored.md); a real tools/cem_tune.py run is the pending next step, then offline-filter and gate on ladder A/B. Un-tuned build ships byte-identical."
    }
  ],
  "in_flight": {
    "build": "heuristic+trolley (U20 slot-1 king reclaim)",
    "ref": "54252006",
    "submitted": "2026-07-02",
    "reason": "floor guard: prior active pair best 489.6 < 540 forced a king copy over the queue; evicts oldest active meta copy archaludon 387.0; doubles as KD2 same-build noise calibration",
    "next": "U20 slot 2 = heuristic+trolley_thick deck A/B (evict grimmsnarl 489.6), pre-registered, once this reads at/above the floor"
  },
  "ledger": [
    {
      "build": "heuristic+trolley (reclaim)",
      "ladder": "pending",
      "move_agreement_delta": "n/a",
      "note": "U20 slot-1 king reclaim 2026-07-02; same build as 569.6 king; noise-calibration copy",
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
  "reclaim_king": {
    "build": "heuristic+trolley",
    "ladder": 569.6,
    "note": "safe floor to revert to before any A/B",
    "ref": "54215558"
  },
  "shadow_king": {
    "build": "heuristic+trolley",
    "ladder": 569.6,
    "note": "best live build; search costs points (514.7<569.6), meta copies below",
    "ref": "54215558"
  }
}
```
