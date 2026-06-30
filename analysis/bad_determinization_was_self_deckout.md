# The lone "bad_determinization" loss was a self-deckout (no developed-board race exists)

## Why this matters
Several iterations of NEXT guidance named "the residual developed-board
bad_determinization race" as the true SECOND lever to chase after the queued
trolley (early_collapse) submission. This iter traced that residual to the card
level and found it does not exist: the single loss bucketed as
bad_determinization across the entire current ladder dataset is a misbucketed
self-deckout, already addressed by the guard the trolley artifact ships.

## The dataset (per-agent, self-play excluded)
Classified every replay in the three per-agent pull dirs:

| agent (ref)        | W  | L  | early_collapse | deckout | endgame | bad_det |
|--------------------|----|----|----------------|---------|---------|---------|
| search   54208986  | 4  | 3  | 2              | 0       | 1       | 0       |
| deckout1 54209468  | 16 | 20 | 13             | 4 -> 5  | 2       | 1 -> 0  |
| deckout2 54211499  | 14 | 18 | 15             | 3       | 0       | 0       |
| total              | 34 | 41 | 30 (73%)       | 8 (20%) | 3 (7%)  | 0       |

After the fix below: bad_determinization is 0 of 41 losses. There is also no
slow_search and no deck_matchup loss anywhere. Every single loss is one of three
structural failures, and the two dominant ones are exactly what the queued
trolley submission targets: early_collapse via the Precious Trolley deck, deckout
via the v2 PLAY-action guard plus the narrowed _drills_deck predicate.

## The one loss, at the card level (episode 82885022, ref 54209468, we are seat 1)
Final observed board: our deck 1, opponent deck 20, our bench 3, our prizes 3
remaining (we took 3), opponent prizes 6 remaining (they took 0). Reward [1, -1],
we lost.

By elimination this can only be a deckout. The opponent took zero prizes, so we
did not lose the prize race. Our bench held 3 Pokemon, so it is not an
empty-bench collapse. The only remaining loss condition is the forced draw at
the start of a turn with an empty deck. We milled ourselves from 60 to 1 card by
turn 11 while ahead on prizes 3 to 0. This is the same self-mill pathology as the
deckout bucket, not a developed-board race that lost a prize fight.

It escaped the deckout bucket only because that bucket required my_deck_end to be
exactly 0. The deckout fires on the next turn's forced draw, after the last
observation we recorded, so the final observed deck count sits one mandatory draw
above zero (1, not 0). This game also predates the v2 PLAY-action guard (it ran
on 54209468, the v1 count-only guard that never fired because the mill is all
PLAY actions); the current code and the trolley artifact ship the v2 guard plus
the narrowed _drills_deck, which decline the draw and search trainers that drive
this mill.

## The fix (analysis-only, zero ladder risk)
classify_loss now also buckets a loss as deckout when the final observed deck is
at most one card AND the bench is not empty AND the opponent has not taken the
prizes to win (more than CLOSE_REMAINING prizes still remaining). The two guards
keep the relaxation honest: a genuine prize blowout that merely ends on one card
stays deck_matchup, and a near-empty deck with an empty bench stays
early_collapse (bench depletion is the proximate cause). Tests:
test_classify_one_card_ahead_on_prizes_is_deckout plus the two guard tests.

## What this changes about the plan
There is no developed-board race lever to chase. The honest report is that
early_collapse (deck thinness) and deckout (self-mill) account for 38 of 41
ladder losses, and both are already addressed by the queued trolley artifact. The
remaining 3 are endgame_misplay near-wins. Do not invent a phantom second lever
from the bad_determinization bucket; the real next signal is post-trolley ladder
data, which only a submit slot can produce.
