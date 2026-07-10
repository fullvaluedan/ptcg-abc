# Matched-Action Extraction (plan U3 / U106b)

Supersedes analysis/state_matched_expert_lookup.py (U106), retired as unsound by LOOP_BRIEF.md P9 rule 4. That script's "experts also lose here" verdicts, invented per-state categories, and uncalibrated distance bands are not reused; this pass reports something narrower and checkable instead: what the nearest expert neighbor actually DID at each of our matched loss states.

## Scope note

This first pass reports expert action distributions only. Our OWN actions at these matched states are not extracted or compared here -- that is a recorded scope limit for this pass, not a silent gap. The win-only expert corpus also means this pass makes no claim about whether experts also lose from these states; it only reports what they did at the single nearest matched state.

## Method

- Our loss states: 17951 decision rows from 558 real ladder loss games (data/replays), labeled with the REAL analysis.loss_classifier bucket for that game.

- Expert corpus: 2503920 rows across every top_player_corpus_*.csv, no subsampling.

- Features: all 24 shared state features (ptcg_agent.features.FEATURE_NAMES).

- kNN: k=5, z-scored on the expert corpus's own mean/std; the SINGLE nearest neighbor's identity (game_id, seat, turn) is resolved to its real episode JSON and its chosen MAIN action extracted; mean/max distance across the k nearest is reported as a support signal alongside the action distribution.

- Action distribution weighting: per OUR game, not per raw state (see aggregate_by_cluster docstring) -- a chatty loss game cannot dominate a cluster's reported distribution.

- Deck-blind feature caveat (from the U65 audit, carried forward): these state features do not encode deck identity, so two states that look identical in feature space may call for different correct plays depending on the actual matchup. Every distribution below should be read as "what experts did near this board shape," not as a deck-aware recommendation.


## Findings by loss bucket

### bad_determinization

- States analyzed: 3076

- Mean nearest-neighbor distance: 1.1027

- Resolved-action support: 874 states across 58 of our games

- Expert action distribution (per-game weighted):

  - PLAY: 62.7%

  - ATTACH: 28.0%

  - EVOLVE: 8.3%

  - END: 0.6%

  - RETREAT: 0.2%

  - ABILITY: 0.1%

  - ATTACK: 0.0%



### deck_matchup

- States analyzed: 1942

- Mean nearest-neighbor distance: 1.1073

- Resolved-action support: 610 states across 32 of our games

- Expert action distribution (per-game weighted):

  - PLAY: 52.0%

  - ATTACH: 34.6%

  - EVOLVE: 9.3%

  - ABILITY: 2.6%

  - END: 1.6%



### deckout

- States analyzed: 4671

- Mean nearest-neighbor distance: 1.5793

- Resolved-action support: 409 states across 50 of our games

- Expert action distribution (per-game weighted):

  - PLAY: 65.6%

  - ATTACH: 27.4%

  - EVOLVE: 4.6%

  - ABILITY: 2.4%



### early_collapse

- States analyzed: 7082

- Mean nearest-neighbor distance: 0.8398

- Resolved-action support: 1179 states across 229 of our games

- Expert action distribution (per-game weighted):

  - PLAY: 63.4%

  - ATTACH: 28.2%

  - EVOLVE: 7.9%

  - ABILITY: 0.4%



### endgame_misplay

- States analyzed: 1180

- Mean nearest-neighbor distance: 1.1457

- Resolved-action support: 280 states across 22 of our games

- Expert action distribution (per-game weighted):

  - PLAY: 54.9%

  - ATTACH: 40.5%

  - EVOLVE: 4.3%

  - ABILITY: 0.3%



