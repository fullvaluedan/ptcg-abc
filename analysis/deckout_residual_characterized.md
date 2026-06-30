# Residual deckout: characterized at card level, and why it is not the next lever

Fresh ladder pull (Kaggle UTC 2026-06-30 ~22:20, quota 5/5 spent) for the three
heuristic-family submissions:

| submission | guard shipped | replays | W/D/L | early_collapse | deckout | other |
|------------|---------------|---------|-------|----------------|---------|-------|
| 54208986 search | (search, inert on ladder) | 7 | 4/0/3 | 2 | 0 | endgame 1 |
| 54209468 v1 | count-only cap (DECKOUT_THRESHOLD 5) | 36 | 16/0/20 | 13 | 4 | endgame 2, bad_det 1 |
| 54211499 v2 | blunt: decline all Item/Supporter at deck<=8 | 32 | 14/0/18 | 15 | 3 | (none) |

`early_collapse` (empty-bench deck thinness) is the overwhelming #1 leak on every
agent, on the largest dataset pulled so far. That reconfirms the queued
`submission_trolley.tar.gz` (Precious Trolley benches a Basic for free the turn the
collapse fires) as the correct next-slot submission. Nothing here changes that.

## The deckout residual, card by card

`deckout` (`my_deck_end == 0`) is the #2 residual at 3 to 4 per agent and, unlike
the lone `bad_determinization` loss, it is large enough to inspect. Resolving the
card we played at each of our decisions in all seven deckout losses splits them
into three distinct signatures, only one of which is actionable.

1. Stale-guard over-draw. Both submitted agents predate the guard narrowing
   (07c0677, 2026-07-01 05:28 local; v1 and v2 were submitted 06-30). v1 carries
   only the COUNT cap, which never fires on a PLAY action, so it replays Mega
   Signal / Cyrano / Lillie's Determination freely (e.g. 82888657 drew deck 17 to
   0 over turns 16 to 20). v2's blunt type gate is broader but still type-only.
   These are behaviors of code older than HEAD, not of the agent the next slot
   ships.

2. Unwinnable stall (the genuine residual a draw guard cannot fix). 82908912 ends
   6 to 6 on prizes after 43 turns with the opponent still holding 24 cards: a
   hard board stall our attacker cannot break. The guard worked here, it stopped
   drilling from deck 12 (turns 22 onward show no drill plays), and we still deck
   out on the MANDATORY end-of-turn draw alone, roughly one card per turn, because
   we cannot close the prize race before the deck runs dry. No draw-conserve rule
   recovers this game; only a deck or line that can punch through a wall would, and
   every such deck candidate has already been falsified (see deck_design.md,
   portfolio_decks_not_ladder_viable.md, bench_fetcher_survey.md).

3. The current-code fail-open (the one actionable defect). Direct tests of HEAD's
   narrowed `choose_play` confirm it is correct on resolvable cards: a lone
   drilling Supporter at deck 3 is declined (skip), a non-drilling develop play
   (Precious Trolley) is preferred, and it stays inert above the threshold. But
   when a PLAY option's card id cannot be resolved from the observation,
   `play_card_id` returns None, `_drills_deck(None)` returns False (the type gate
   excludes a None id), so the guard treated the play as safe and would play it
   even at deck 3. That is a fail-open: near deckout an unidentifiable play could
   be a drilling trainer, and the guard cannot prove otherwise.

## Fix applied

`choose_play` now counts a play as a safe non-drilling fallback only when its card
id resolves AND `_drills_deck` clears it (`cid is not None and not
_drills_deck(cid)`). An unidentifiable play near deckout is treated as a potential
driller and skipped, the same conservative stance `_drills_deck` already takes when
a trainer's effect text is missing. In real play your own hand always carries card
ids, so `play_card_id` resolves and the new branch never fires: the change is inert
on the ladder and in self-play (gauntlet heuristic vs baseline 84.2% over 120, 0
invalid, within the historical 85 to 89% band), and only bites a degenerate
observation. Two tests lock it: the unidentifiable play is declined near deckout
(turn ends) and is still played with a healthy deck (guard inert).

## Conclusion: deckout is not the climb lever

The resolvable deckout case is already guarded in current code, and the real
residual is the unwinnable stall, which a draw guard cannot fix. Future iterations
should not spend a slot tightening the deckout guard further (it would not move the
score and risks declining legitimate development). The #1 lever stays
`early_collapse`, addressed by the queued Precious Trolley submission. The next
lever to characterize after trolley has ladder games is still the developed-board
`bad_determinization` race, not deckout.
