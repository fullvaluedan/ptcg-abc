# Deckout guard narrowed: decline only the deck-drilling engine, not every trainer

## Signal

Across iters the draw-decline guard v2 (submission 54211499) has read at or below
the COUNT-only guard v1 (54209468) on the live board (one read 506.0 vs 539.4),
inside v2's own heavy TrueSkill range (484 to 656), so the gap is not provable
from score alone. The mechanism, however, is examinable offline and points the
same way.

## Root cause in the v2 guard

Near a self-deckout (deckCount <= DRAW_CONSERVE_THRESHOLD = 8) v2's `choose_play`
declined to play EVERY Item and Supporter (`CONSERVED_TRAINER_TYPES`). Its own
comment stated the intent narrowly: "Near deckout we still develop Pokemon and
attack; only the card-advantage trainer is skipped." The type-only rule was
broader than that intent. Card data ships each card's effect text offline, so the
two can be reconciled exactly. Classifying our deck's trainers by effect text:

| id   | card                  | type       | effect                                   | drills deck? |
|------|-----------------------|------------|------------------------------------------|--------------|
| 1145 | Mega Signal           | Item       | search a Mega ex into your hand          | yes          |
| 1205 | Cyrano                | Supporter  | search up to 3 Pokemon into your hand    | yes          |
| 1227 | Lillie's Determination| Supporter  | shuffle hand, draw 6 (or 8)              | yes          |
| 1121 | Ultra Ball            | Item       | discard 2, search a Pokemon into hand    | yes          |
| 1235 | Waitress              | Supporter  | attach a Basic Energy from the top 6     | no (develop) |
| 1126 | Precious Trolley      | Item       | put Basics from deck onto your Bench      | no (develop) |
| 1158 | Maximum Belt          | Tool       | +50 damage (never touches the deck)       | no           |

The four "into your hand" / "draw" cards are the card-advantage engine that mills
us to zero turn after turn (the documented deckout loss). Waitress (attaches an
Energy, can power a lethal) and Precious Trolley (benches a Basic, the very
early_collapse fix) only develop the board. v2 wrongly declined those two near
deckout, forfeiting board development to save nothing it needed to save.

## Change

Replace the blunt type gate with `_drills_deck(card_id)`: an Item or Supporter is
declined near deckout when its effect text net-depletes the deck for no board
gain. That is (a) `\bdraw` or "into your hand" (the draw / search-to-hand engine),
or (b) a discard sourced from the deck ("of your deck" / "your deck for ...
discard"), which catches deck-destruction items (Hole-Digging Shovel, Brilliant
Blender) that the draw/search test alone would miss. Every other play (a Pokemon,
an energy attach, a bench-develop trainer, a discard-pile recycler such as Sacred
Ash or Energy Recycler that grows the deck) is kept. `\bdraw` excludes "withdraw"
(a switch effect). Missing text stays conservative (treated as a driller),
preserving the prior safe behavior. The discard-from-deck and recycler cards do
not appear in our shipped or portfolio decks today, so this is robustness for any
future deck rather than a change to the current ladder agent. This
sits between v1 (no play decline) and v2 (decline all): it stops only the genuine
mill engine while restoring development. It is the base the queued Precious
Trolley submission ships on, so the trolley tarball must be rebuilt after this
commit to carry the refinement.

## Verification

Unit tests in test_heuristic.py prove the classification per card, the recovered
Waitress and Precious Trolley plays near deckout, the still-declined search
trainers, the "withdraw" exclusion, and the conservative missing-text default.
Gauntlet heuristic vs baseline 150 matches 94.7% (CI 89.8 to 97.3), 0 invalid:
no regression (the change is inert above deck 8, which dominates self-play). The
real payoff is ladder-only, like every deckout-bucket change; confirm by
re-pulling replays once a refined submission has games and checking the deckout
bucket stays at zero while no game ends with a useless declined-trainer turn.
