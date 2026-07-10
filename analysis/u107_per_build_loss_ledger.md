# Per-Build Loss Ledger (U107)

Loss distribution segregated by submission ref so targeting is attributed
to the actual shipped agent, not a historical mix of all builds.

## Summary

### Ref 54315802
- Sample: 65 games (W/D/L 33/0/32)
- Top bucket: **early_collapse**

### Ref 54315565
- Sample: 39 games (W/D/L 15/0/24)
- Top bucket: **early_collapse**

## Per-Bucket Breakdown

### Ref 54315802 (n=65)

| Bucket | Count | % |
| --- | --- | --- |
| bad_determinization | 1 | 1.5% |
| deck_matchup | 1 | 1.5% |
| deckout | 5 | 7.7% |
| early_collapse | 25 | 38.5% |
| endgame_misplay | 0 | 0.0% |
| slow_search | 0 | 0.0% |

### Ref 54315565 (n=39)

| Bucket | Count | % |
| --- | --- | --- |
| bad_determinization | 1 | 2.6% |
| deck_matchup | 2 | 5.1% |
| deckout | 2 | 5.1% |
| early_collapse | 19 | 48.7% |
| endgame_misplay | 0 | 0.0% |
| slow_search | 0 | 0.0% |

## Targeting Priority

Each build targets its own top loss bucket for the next unit.
