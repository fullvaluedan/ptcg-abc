# The Archaludon deckout is mandatory-draw depletion, not voluntary over-mill: the guard-tuning lever is closed

Phase 4 diagnosis. The copied meta decks settled BELOW the trolley floor on the
ladder (archaludon 392.0, grimmsnarl 408.5, vs trolley 569.6 on the same
heuristic; see `analysis/meta_decks_underperform_on_ladder.md`). That doc named
DECKOUT as the Archaludon deck's #1 new leak and floated "deck-specific play
logic" / tuning the deckout guard as the only path that could unlock a meta deck.
This iteration tests that lever directly and closes it with data.

## The leak is real and deck-bound

`tools/collapse_rate.py` runs heuristic-vs-heuristic mirror games per deck and
classifies each loser (`analysis/loss_classifier.py`). Over n=60:

| deck       | deckout | early_collapse | other buckets                          |
|------------|---------|----------------|----------------------------------------|
| archaludon | 10/60   | 14/60          | deck_matchup 20, bad_determ 15, endgame 1 |
| trolley    | 0/60    | 49/60          | endgame 6, bad_determ 4, deck_matchup 1 |

The Archaludon deck self-decks 16.7% of mirror games; the trolley deck NEVER does.
That is exactly why the deckout guard reads as "closed" on the trolley line: the
lean deck cannot reach the state the guard exists to protect. The guard was tuned
and validated where it never fires.

## Raising the conserve threshold does NOT fix it

`DRAW_CONSERVE_THRESHOLD` (default 8) is the deck count at or below which the
heuristic refuses to play any deck-drilling Item or Supporter and develops instead.
The natural fix for "the trainer-heavy engine mills too fast" is to conserve
earlier. A monkeypatch sweep on the Archaludon deck (n=40 each) refutes it:

| threshold | deckout | early_collapse |
|-----------|---------|----------------|
| 8 (ship)  | 5/40    | 10             |
| 12        | 6/40    | 14             |
| 16        | 4/40    | 17             |
| 20        | 4/40    | 13             |

Deckout is threshold-insensitive (5, 6, 4, 4 is flat within small-sample noise),
and conserving earlier makes early_collapse WORSE (10 to 17): starving the draw
engine of plays leaves the bench empty more often. Trading one loss bucket for
another is not a win.

The decisive reading is the threshold=20 row. At that setting the heuristic
declines every drill from 20 cards down, i.e. for essentially the entire mid-to-
late game, and the deck STILL decks out at ~10%. If the deckout were voluntary
over-milling, refusing to drill from 20 cards would eliminate it. It does not. So
the deckout is dominated by the MANDATORY start-of-turn draw in long games the
heuristic never closes on prizes, which no voluntary-play guard can touch.

## The drill predicate is already complete for this deck

An audit of every Item/Supporter in `decks/meta_archaludon.csv` against
`_drills_deck` found no false negatives: Ultra Ball (1121), Pokegear 3.0 (1122),
Poke Pad (1152), Explorer's Guidance (1185), and Lillie's Determination (1227) are
all correctly flagged as drills. There is no unrecognized mill card the guard is
letting through. The one misclassification was a false POSITIVE, Night Stretcher
(1097), flagged as a drill because it puts a card "into your hand"; but it pulls
from the discard pile and never touches the deck, so declining it near deckout was
wrong. That is fixed in this commit (a discard-pile-to-hand recovery is carved out
of `_drills_deck`, mirroring the existing deck-recycler carve-out), but it is a
correctness fix, not a deckout fix: recovering a card from the discard pile does
not change the deck count either way, and the mandatory-draw mechanism above is
untouched by it. Its only effect is letting the agent recover a Pokemon to hand
near deckout instead of skipping the play. It is not claimed to move the ladder.

## Decision: the deckout-guard lever is closed; the real unlock is pilot tempo

The deckout on the Archaludon deck is not a tunable guard parameter. It is a
game-plan-execution failure: our heuristic cannot assemble the Archaludon ex metal
payoff and close on prizes before mandatory draws run its trainer-heavy deck to
zero. A skilled pilot digs for the payoff, stops, and wins on prizes; a threshold
knob cannot substitute for that. This agrees with, and sharpens,
`meta_decks_underperform_on_ladder.md`: the ~570-vs-1300 gap on a meta deck is a
pilot gap, and the pilot fix is a modeling effort (a search agent that reaches the
deck's real forward model, or deck-plan logic that sequences the metal engine to a
payoff), not another guard threshold.

Do NOT re-open this as "tune DRAW_CONSERVE_THRESHOLD / DECKOUT_THRESHOLD for the
Archaludon deck" (tested here, inert) and do NOT submit a tuned-guard + Archaludon
build expecting the deckout to shrink (it will not). The trolley deck (569.6) stays
the deployable deck; the meta decks stay as harvested reference and gauntlet foils.

## Reproduce

```
.venv/Scripts/python.exe tools/collapse_rate.py decks/meta_archaludon.csv decks/trolley.csv -n 60
# threshold sweep: monkeypatch agents.heuristics.DRAW_CONSERVE_THRESHOLD before measure_deck
```
