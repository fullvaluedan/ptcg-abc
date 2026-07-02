# How the best teams win vs lose

Plan U63 (docs/plans/2026-07-02-003-feat-offline-match-scale-topplayer-mining-plan.md).
Contrasts the top-N leaderboard teams' wins against their losses (plan U62's win
and loss corpora) and, where available, our own loss-bucket measurement
(tools/measure_loss_modes.py), to name what makes the difference.

Sources: win corpus `C:\Users\danom\ptcg-abc\data\training\top_player_corpus_20260702.csv`, loss corpus `C:\Users\danom\ptcg-abc\data\training\top_player_loss_corpus_20260702.csv`, ours `C:\Users\danom\ptcg-abc\data\training\loss_modes_on.json`.

- Top-team win games: 1441 (109075 decision rows)
- Top-team loss games: 1074 (71762 decision rows)

## How the top teams lose, versus how we lose

| loss bucket | top-team rate | top-team count | our rate | our count |
|---|---|---|---|---|
| bad_determinization | 29.1% | 312 | 0.0% | 0 |
| endgame_misplay | 25.1% | 270 | 0.0% | 0 |
| deck_matchup | 17.1% | 184 | 7.7% | 1 |
| early_collapse | 15.3% | 164 | 92.3% | 12 |
| deckout | 10.4% | 112 | 0.0% | 0 |
| slow_search | 3.0% | 32 | 0.0% | 0 |

## What separates their wins from their losses

| turn range | feature | win mean | loss mean | delta (win minus loss) |
|---|---|---|---|---|
| mid | deck_diff | -3.220 | 0.334 | -3.554 |
| mid | their_deck_count | 31.063 | 29.173 | +1.890 |
| mid | our_deck_count | 27.843 | 29.507 | -1.664 |
| late | deck_diff | 0.052 | -1.336 | +1.388 |
| late | their_deck_count | 17.055 | 18.324 | -1.269 |
| late | our_energy | 3.572 | 2.354 | +1.218 |
| late | our_prizes_left | 3.100 | 4.304 | -1.204 |
| late | our_hand_count | 10.192 | 8.993 | +1.199 |

## Who beats them

Opponent is the team name only; the loss corpus carries no decklist, so archetype-level attribution is not available at this granularity.

| opponent | top-team losses to them |
|---|---|
| kazuki0123 | 63 |
| THIRD PTCG Club | 40 |
| tonakaiiii | 39 |
| The Debauchery Tea Party | 38 |
| aidy | 37 |
| monnosuke | 36 |
| Yushin Ito | 35 |
| Moegi | 35 |
| ShumpeiNomura | 32 |
| pztriatomic | 26 |
| Takaaki Matsuda | 24 |
| Michael Krager | 23 |
| Shun | 20 |
| カドラバ Kadoraba | 20 |
| tomatomato | 20 |
