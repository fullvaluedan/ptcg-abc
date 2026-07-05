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
| 1 | Majkel1337 | 1257.2 | 0 | n/a |
| 2 | THIRD PTCG Club | 1153.6 | 304 | 56% |
| 3 | Yushin Ito | 1127.5 | 341 | 54% |
| 4 | nasuo445 | 1125.6 | 251 | 61% |
| 5 | tonakaiiii | 1123.4 | 850 | 57% |
| 6 | zoroark190 | 1116.0 | 325 | 60% |
| 7 | iwashi | 1114.4 | 165 | 52% |
| 8 | Ruko | 1110.6 | 0 | n/a |
| 9 | kashiwashira | 1089.3 | 266 | 57% |
| 10 | Rmy | 1088.5 | 0 | n/a |
| 11 | junlee789 | 1087.2 | 54 | 65% |
| 12 | Banjo | 1084.9 | 0 | n/a |
| 13 | genki toyama | 1083.2 | 0 | n/a |
| 14 | aaa | 1080.4 | 19 | 37% |
| 15 | WinDecks | 1074.2 | 667 | 51% |
| 16 | easonyanyan | 1070.0 | 267 | 56% |
| 17 | payanotty | 1069.4 | 0 | n/a |
| 18 | Hase2727 | 1069.1 | 0 | n/a |
| 19 | 渡邊征央 | 1067.6 | 630 | 54% |
| 20 | noikaret | 1063.8 | 76 | 34% |

## Coverage

- Games considered (post recency filter): 4975
- Games matched to a top-N team: 3367
- Training rows written: 189460
- Date range of matched games: 2026-07-04 to 2026-07-04

## Archetype breakdown

- meta_grimmsnarl_tonakaiiii: 2225
- other: 1334
- meta_archaludon: 352
- meta_grimmsnarl: 304

## Unmapped team names

- Banjo (no game in the scanned dataset names this team)
- Hase2727 (no game in the scanned dataset names this team)
- Majkel1337 (no game in the scanned dataset names this team)
- Rmy (no game in the scanned dataset names this team)
- Ruko (no game in the scanned dataset names this team)
- genki toyama (no game in the scanned dataset names this team)
- payanotty (no game in the scanned dataset names this team)

## Losses

| team | losses | dominant loss bucket | most common opponent |
|---|---|---|---|
| tonakaiiii | 369 | endgame_misplay | Dũng Đỗ |
| WinDecks | 329 | early_collapse | kazuki0123 |
| 渡邊征央 | 289 | endgame_misplay | tonakaiiii |
| Yushin Ito | 157 | early_collapse | tonakaiiii |
| THIRD PTCG Club | 133 | endgame_misplay | tonakaiiii |
| zoroark190 | 130 | endgame_misplay | Dũng Đỗ |
| easonyanyan | 117 | deckout | Dũng Đỗ |
| kashiwashira | 114 | endgame_misplay | WinDecks |
| nasuo445 | 98 | endgame_misplay | Dũng Đỗ |
| iwashi | 80 | slow_search | tonakaiiii |
| noikaret | 50 | bad_determinization | 渡邊征央 |
| junlee789 | 19 | endgame_misplay | 渡邊征央 |
| aaa | 12 | deckout | XP3RiX |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-05)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

