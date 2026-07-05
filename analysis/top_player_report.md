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
| 1 | Majkel1337 | 1251.3 | 0 | n/a |
| 2 | zoroark190 | 1142.7 | 325 | 60% |
| 3 | tonakaiiii | 1136.1 | 850 | 57% |
| 4 | nasuo445 | 1131.2 | 251 | 61% |
| 5 | Yushin Ito | 1130.5 | 341 | 54% |
| 6 | junlee789 | 1111.1 | 54 | 65% |
| 7 | THIRD PTCG Club | 1109.3 | 304 | 56% |
| 8 | Rmy | 1102.7 | 0 | n/a |
| 9 | kashiwashira | 1092.6 | 266 | 57% |
| 10 | iwashi | 1092.2 | 165 | 52% |
| 11 | WinDecks | 1079.4 | 667 | 51% |
| 12 | easonyanyan | 1078.7 | 267 | 56% |
| 13 | btk15049 | 1076.4 | 683 | 51% |
| 14 | 渡邊征央 | 1074.0 | 630 | 54% |
| 15 | Shardul Gharat | 1072.0 | 5 | 80% |
| 16 | kenkoooo | 1071.3 | 45 | 38% |
| 17 | aaa | 1071.2 | 19 | 37% |
| 18 | payanotty | 1069.6 | 0 | n/a |
| 19 | genki toyama | 1065.6 | 0 | n/a |
| 20 | Ruko | 1060.2 | 0 | n/a |

## Coverage

- Games considered (post recency filter): 4975
- Games matched to a top-N team: 3783
- Training rows written: 222090
- Date range of matched games: 2026-07-04 to 2026-07-04

## Archetype breakdown

- meta_grimmsnarl_tonakaiiii: 2230
- other: 1258
- meta_archaludon: 1035
- meta_grimmsnarl: 349

## Unmapped team names

- Majkel1337 (no game in the scanned dataset names this team)
- Rmy (no game in the scanned dataset names this team)
- Ruko (no game in the scanned dataset names this team)
- genki toyama (no game in the scanned dataset names this team)
- payanotty (no game in the scanned dataset names this team)

## Losses

| team | losses | dominant loss bucket | most common opponent |
|---|---|---|---|
| tonakaiiii | 369 | endgame_misplay | Dũng Đỗ |
| btk15049 | 334 | slow_search | tonakaiiii |
| WinDecks | 329 | early_collapse | kazuki0123 |
| 渡邊征央 | 289 | endgame_misplay | tonakaiiii |
| Yushin Ito | 157 | early_collapse | tonakaiiii |
| THIRD PTCG Club | 133 | endgame_misplay | tonakaiiii |
| zoroark190 | 130 | endgame_misplay | Dũng Đỗ |
| easonyanyan | 117 | deckout | Dũng Đỗ |
| kashiwashira | 114 | endgame_misplay | WinDecks |
| nasuo445 | 98 | endgame_misplay | Dũng Đỗ |
| iwashi | 80 | slow_search | tonakaiiii |
| kenkoooo | 28 | slow_search | Nghia Tran |
| junlee789 | 19 | endgame_misplay | 渡邊征央 |
| aaa | 12 | deckout | XP3RiX |
| Shardul Gharat | 1 | bad_determinization | tonakaiiii |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-05)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

