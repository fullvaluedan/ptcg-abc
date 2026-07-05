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
| 1 | Majkel1337 | 1242.9 | 0 | n/a |
| 2 | nasuo445 | 1187.9 | 251 | 61% |
| 3 | THIRD PTCG Club | 1175.6 | 304 | 56% |
| 4 | tonakaiiii | 1156.0 | 850 | 57% |
| 5 | disgruntled.coffee | 1115.0 | 23 | 78% |
| 6 | iwashi | 1112.2 | 165 | 52% |
| 7 | zoroark190 | 1111.9 | 325 | 60% |
| 8 | TEAM NAME | 1108.6 | 75 | 37% |
| 9 | tw_shin | 1096.7 | 11 | 64% |
| 10 | genki toyama | 1089.4 | 0 | n/a |
| 11 | kazuki0123 | 1084.3 | 623 | 52% |
| 12 | Yushin Ito | 1077.0 | 341 | 54% |
| 13 | Rmy | 1075.9 | 0 | n/a |
| 14 | hoshippi | 1071.9 | 126 | 52% |
| 15 | WinDecks | 1071.6 | 667 | 51% |
| 16 | ごんさくよねきち | 1071.3 | 5 | 40% |
| 17 | junlee789 | 1070.4 | 54 | 65% |
| 18 | noikaret | 1068.9 | 76 | 34% |
| 19 | BluezLee | 1067.2 | 339 | 47% |
| 20 | Hase2727 | 1065.8 | 0 | n/a |

## Coverage

- Games considered (post recency filter): 4975
- Games matched to a top-N team: 3385
- Training rows written: 186033
- Date range of matched games: 2026-07-04 to 2026-07-04

## Archetype breakdown

- meta_grimmsnarl_tonakaiiii: 1320
- meta_grimmsnarl: 1133
- other: 1068
- meta_archaludon: 714

## Unmapped team names

- Hase2727 (no game in the scanned dataset names this team)
- Majkel1337 (no game in the scanned dataset names this team)
- Rmy (no game in the scanned dataset names this team)
- genki toyama (no game in the scanned dataset names this team)

## Losses

| team | losses | dominant loss bucket | most common opponent |
|---|---|---|---|
| tonakaiiii | 369 | endgame_misplay | Dũng Đỗ |
| WinDecks | 329 | early_collapse | kazuki0123 |
| kazuki0123 | 300 | bad_determinization | tonakaiiii |
| BluezLee | 180 | deck_matchup | btk15049 |
| Yushin Ito | 157 | early_collapse | tonakaiiii |
| THIRD PTCG Club | 133 | endgame_misplay | tonakaiiii |
| zoroark190 | 130 | endgame_misplay | Dũng Đỗ |
| nasuo445 | 98 | endgame_misplay | Dũng Đỗ |
| iwashi | 80 | slow_search | tonakaiiii |
| hoshippi | 61 | endgame_misplay | tonakaiiii |
| noikaret | 50 | bad_determinization | 渡邊征央 |
| TEAM NAME | 47 | early_collapse | btk15049 |
| junlee789 | 19 | endgame_misplay | 渡邊征央 |
| disgruntled.coffee | 5 | early_collapse | WinDecks |
| tw_shin | 4 | bad_determinization | tonakaiiii |
| ごんさくよねきち | 3 | deck_matchup | Yushin Ito |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-05)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

