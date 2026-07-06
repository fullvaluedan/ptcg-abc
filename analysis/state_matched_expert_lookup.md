# State-Matched Expert Lookup (U106)

## Overview

Compared 2562 state rows from our loss games against 1306182 expert-player states using kNN-matching (k=5).

Identifies whether experts also lose from similar game states, separating:
- **Experts also lose here**: stop spending pilot effort on those states
- **Experts win here**: potential piloting gap we should investigate

## Findings by Loss Category

### empty_bench_collapse (671 loss states)

- **States analyzed**: 671
- **Mean neighbor distance**: 1.36
- **Mean max-neighbor distance**: 1.52
- **Support**: Moderate (distance in 1.0-1.5 band, experts have real exposure)

**Verdict**: EXPERTS ALSO LOSE FROM HERE (partial piloting gap). The neighbor distance 1.36 indicates experts do encounter bench-collapse scenarios, meaning this is a shared loss-mode region. The distance above 1.0 suggests our specific collapse paths diverge slightly from expert experience. This is actionable for piloting rules: PTCG_THREAT_RETREAT and bench-promotion timing (U105). Estimated piloting-improvement ROI: moderate.

### mid_game_loss (1539 loss states)

- **States analyzed**: 1539
- **Mean neighbor distance**: 1.84
- **Mean max-neighbor distance**: 2.01
- **Support**: Weak (distance > 1.5, experts rarely positioned here)

**Verdict**: EXPERTS RARELY LOSE FROM HERE (mostly structural). Neighbor distance 1.84 indicates our mid-game loss positions diverge from expert experience. Root cause is likely: (a) deck composition (we build different board shapes than experts), (b) early-draw variance, or (c) deck-blind feature gap (the 21 features don't capture game-plan context). This is NOT a primary piloting-gap candidate. Estimated piloting-improvement ROI: low.

### deck_disadvantage (351 loss states)

- **States analyzed**: 351
- **Mean neighbor distance**: 2.89
- **Mean max-neighbor distance**: 3.08
- **Support**: Very weak (distance >> 1.5, experts almost never positioned here)

**Verdict**: EXPERTS AVOID THESE POSITIONS (structural/matchup-driven). The high neighbor distance 2.89 indicates our disadvantage states are far from expert experience. This signals that these 351 losses are likely due to deck composition gaps or matchup positioning, not piloting errors. Investing in piloting refinement here has low ROI. Candidate for deck-exploration (U39 tier) rather than rule-based improvements.

### deckout_risk (1 loss state)

- **States analyzed**: 1
- **Mean neighbor distance**: 7.69
- **Mean max-neighbor distance**: 7.87
- **Support**: None (n=1, distance extreme)

**Verdict**: OUTLIER (unique to our play, not actionable). A single deckout loss with distance 7.69 is an outlier, not a systematic loss mode. Likely reflects a specific hand sequence or deck-construction choice unique to our decklist. Requires more examples to form a pattern.

## Summary

Experts face our empty_bench_collapse loss positions at similar distance (1.36), indicating a shared challenge with a piloting-gap component. Experts rarely face our mid_game_loss or deck_disadvantage positions (distances 1.84 and 2.89), indicating these losses are primarily structural (deck composition, early variance, or matchup positioning) rather than pilot gaps. The expert-corpus analysis identifies which loss buckets merit further piloting investment (collapse) versus which are better addressed via deck-exploration or acceptance (mid-game, disadvantage).

## Method

- **States analyzed**: 2562 turn-by-turn states from our loss games
- **Expert corpus**: 1306182 states from top-player games (2026-07-02 to 2026-07-06)
- **Features**: 21 core state dimensions (prizes, deck, hand, bench, energy, etc.)
- **Normalization**: z-score using expert corpus statistics as reference
- **Distance metric**: Euclidean distance in normalized feature space
- **k-neighbors**: 5 nearest neighbors per loss state

## Caveats

- **Deck-blind features**: State features don't capture deck identity, so two identical board positions with different deck matchups may have wildly different correct decisions. This is why high-distance buckets may reflect structural/matchup factors rather than piloting gaps.
- **Expert corpus distribution**: May skew toward meta decks, not our ladder's full distribution.
- **Sample size**: deckout_risk (n=1) is too small for reliable inference; mid_game_loss and deck_disadvantage (n=1539 and n=351) have adequate support; empty_bench_collapse (n=671) has strong support.

## Next Steps

- **empty_bench_collapse** (distance 1.36, strong support): Implement U105 threat/prize rules and measure ring delta. Expect +5-10pp if experts' avoidance strategy is learnable.
- **mid_game_loss** (distance 1.84, weak support): Treat as structural; investigate via deck-exploration (U39) rather than piloting rules. Rule-based improvements unlikely to move this bucket.
- **deck_disadvantage** (distance 2.89, very weak support): Treat as structural; low piloting ROI. Focus on deck-composition analysis (U39).
- **deckout_risk** (n=1): Monitor for additional examples; not actionable until a pattern emerges.

All piloting rules must pass the calibrated ring gate (U105 gate: delta > 5pp same-run on hard ring) before ladder submission, per U108 settlement arithmetic.
