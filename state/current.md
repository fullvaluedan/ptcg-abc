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

- **shadow-king** (best live build): heuristic+trolley (ref 54215558, ladder 569.6)
- **reclaim-king** (safe floor): heuristic+trolley (ref 54215558, ladder 569.6)

## Candidates awaiting a ladder slot

- cem-grown-genome (PRIO ordering): genome grown so CEM has a gradient (analysis/cem_gradient_restored.md); a real tools/cem_tune.py run is the pending next step, then offline-filter and gate on ladder A/B. Un-tuned build ships byte-identical.

## Per-build ledger

| build | oracle | move-agree delta | ladder | sample | note |
| --- | --- | --- | --- | --- | --- |
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
      "build": "cem-grown-genome (PRIO ordering)",
      "note": "genome grown so CEM has a gradient (analysis/cem_gradient_restored.md); a real tools/cem_tune.py run is the pending next step, then offline-filter and gate on ladder A/B. Un-tuned build ships byte-identical."
    }
  ],
  "ledger": [
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
