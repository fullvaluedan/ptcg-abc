# U107: Per-Build Loss Ledger

## Summary

Per-build loss segregation for submission refs: 54315802, 54315565.

**Status: COMPLETE** (backfill + filtering phases done).

## Refs Analyzed

- **shadow-king** (54315802, heuristic+trolley-ability): 65 episodes
- **reclaim-king** (54315565, heuristic+trolley): 39 episodes

## Per-Build Loss Distributions

### Shadow-King (54315802): 65 games

| Bucket | Count | % |
|--------|-------|---|
| early_collapse | 25 | 38.5% |
| deckout | 5 | 7.7% |
| deck_matchup | 1 | 1.5% |
| bad_determinization | 1 | 1.5% |
| slow_search | 0 | 0.0% |
| endgame_misplay | 0 | 0.0% |

### Reclaim-King (54315565): 39 games

| Bucket | Count | % |
|--------|-------|---|
| early_collapse | 19 | 48.7% |
| deckout | 2 | 5.1% |
| deck_matchup | 2 | 5.1% |
| bad_determinization | 1 | 2.6% |
| slow_search | 0 | 0.0% |
| endgame_misplay | 0 | 0.0% |

## Key Finding

Both shipped builds show early_collapse as the dominant loss bucket:
- shadow-king: 38.5% of losses
- reclaim-king: 48.7% of losses

This matches the historical aggregated loss distribution (48% early_collapse over 809 games),
confirming that early_collapse is the top targeting priority for both active builds.

## Implementation Status

- [DONE] harvest_replays.py: backfill_manifest() function added (U107 backfill phase)
- [DONE] tools/loop_state.py: classify_dirs_per_build() with full ref filtering (U107 filtering phase)
- [DONE] analysis/u107_generate_per_build_ledger.py: analysis script (generates per-build reports)
- [DONE] data/episode_to_ref.json: manifest created with 843 episodes (backfill completed)
- [DONE] analysis/u107_per_build_loss_ledger.json: per-build ledger output (final analysis)

## Prerequisite Met

This segregation unblocks honest loss-mode targeting in TRACK L going forward.
Future iterations can now attribute losses to the actual shipped agent, not a
historical mix of all ever-submitted builds.
