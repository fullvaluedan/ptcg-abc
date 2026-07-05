# Top-player leaderboard tracker

Plan U3c (addendum v2). Tracks the live top-N leaderboard teams and pulls
their newest games from the published episode dataset into a weighted
training corpus (source=top_player). Plan U62 adds a loss-side corpus
(source=top_player_loss) for the games those teams lost.

Recency window: --days 14 (games older than the dataset's own newest
game minus this window are dropped before matching).

## Teams covered

| rank | team | rating | corpus games | corpus win rate |
|---|---|---|---|---|
| 1 | Majkel1337 | 1253.2 | 0 | n/a |
| 2 | nasuo445 | 1204.2 | 251 | 61% |
| 3 | THIRD PTCG Club | 1163.1 | 304 | 56% |
| 4 | zoroark190 | 1121.2 | 325 | 60% |
| 5 | tonakaiiii | 1120.7 | 850 | 57% |
| 6 | iwashi | 1110.9 | 165 | 52% |
| 7 | disgruntled.coffee | 1102.8 | 23 | 78% |
| 8 | tw_shin | 1081.7 | 11 | 64% |
| 9 | genki toyama | 1080.5 | 0 | n/a |
| 10 | junlee789 | 1077.3 | 54 | 65% |
| 11 | Yushin Ito | 1075.7 | 341 | 54% |
| 12 | Rmy | 1074.0 | 0 | n/a |
| 13 | 渡邊征央 | 1070.4 | 630 | 54% |
| 14 | Hase2727 | 1069.1 | 0 | n/a |
| 15 | kashiwashira | 1069.0 | 266 | 57% |
| 16 | カドラバ Kadoraba | 1065.3 | 4 | 50% |
| 17 | noikaret | 1064.8 | 76 | 34% |
| 18 | BluezLee | 1062.7 | 339 | 47% |
| 19 | easonyanyan | 1061.7 | 267 | 56% |
| 20 | Pokemon Siuuuu | 1060.1 | 0 | n/a |

## Coverage

- Games considered (post recency filter): 4975
- Games matched to a top-N team: 3192
- Training rows written: 183961
- Date range of matched games: 2026-07-04 to 2026-07-04

## Archetype breakdown

- meta_grimmsnarl_tonakaiiii: 2217
- meta_archaludon: 714
- other: 667
- meta_grimmsnarl: 308

## Unmapped team names

- Hase2727 (no game in the scanned dataset names this team)
- Majkel1337 (no game in the scanned dataset names this team)
- Pokemon Siuuuu (no game in the scanned dataset names this team)
- Rmy (no game in the scanned dataset names this team)
- genki toyama (no game in the scanned dataset names this team)

## Losses

| team | losses | dominant loss bucket | most common opponent |
|---|---|---|---|
| tonakaiiii | 369 | endgame_misplay | Dũng Đỗ |
| 渡邊征央 | 289 | endgame_misplay | tonakaiiii |
| BluezLee | 180 | deck_matchup | btk15049 |
| Yushin Ito | 157 | early_collapse | tonakaiiii |
| THIRD PTCG Club | 133 | endgame_misplay | tonakaiiii |
| zoroark190 | 130 | endgame_misplay | Dũng Đỗ |
| easonyanyan | 117 | deckout | Dũng Đỗ |
| kashiwashira | 114 | endgame_misplay | WinDecks |
| nasuo445 | 98 | endgame_misplay | Dũng Đỗ |
| iwashi | 80 | slow_search | tonakaiiii |
| noikaret | 50 | bad_determinization | 渡邊征央 |
| junlee789 | 19 | endgame_misplay | 渡邊征央 |
| disgruntled.coffee | 5 | early_collapse | WinDecks |
| tw_shin | 4 | bad_determinization | tonakaiiii |
| カドラバ Kadoraba | 2 | deck_matchup | 渡邊征央 |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-05)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

