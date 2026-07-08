# U107: Per-Build Loss Ledger (2026-07-08)

## Summary

Segregated the loss distribution from a mixed 809-replay pool (all retired builds) to the current 104-replay pool (shadow-king + reclaim-king only), enabling honest per-build targeting and measurement attribution.

## Implementation

**Infrastructure (already complete via prior commits):**
1. `tools/harvest_replays.py`: Persists episode-to-ref manifest to `data/episode_to_ref.json` on every harvest
2. `tools/loop_state.py::classify_dirs_per_build()`: Filters episode digests by ref via the manifest
3. `tools/loop_state.py::loss_distribution_from_dirs()`: Accepts optional ref_filter parameter
4. CLI: `python -m tools.loop_state refresh data/replays --ref-filter "54315802,54315565"`

**This iteration (U107 completion):**
- Ran loss_distribution_from_dirs with ref_filter=[54315802, 54315565] (shadow-king + reclaim-king)
- Updated state/current.md's loss_distribution block with current-build-only metrics

## Results

### Loss Distribution (Current Builds Only)

**Dataset:** 104 replays from two refs
- 54315802: heuristic+trolley-ability (shadow-king, floor restoration)
- 54315565: heuristic+trolley (reclaim-king, safe floor)

**Outcome:** W/D/L 48/0/56 (54.2% loss rate)

| Bucket | Count |
|--------|-------|
| early_collapse | 44 |
| deckout | 7 |
| deck_matchup | 3 |
| bad_determinization | 2 |
| endgame_misplay | 0 |
| slow_search | 0 |

### Comparison to Mixed Pool

| Metric | Mixed (938 replays) | Current (104 replays) | Delta |
|--------|---------------------|----------------------|-------|
| Total replays | 938 | 104 | -90% |
| Top bucket | early_collapse | early_collapse | (same) |
| Losses | 518 | 56 | (proportional) |
| early_collapse % | 67.6% (350/518) | 78.6% (44/56) | +11.0pp |

The current-build pool shows a **higher concentration** of early_collapse failures (78.6% vs 67.6%), indicating this is the real bottleneck for the current shipped pilot, not an artifact of historical mix.

## Use

Targeting for weeks 3-4 now uses this cleaner ledger, attributing losses to the actual shipped agent rather than historical predecessors. Enables accurate hypothesis testing on early_collapse fixes (deck density, bench setup, archetype awareness).

Gate: PASS (ledger computed, attributed, and recorded in state/current.md).
