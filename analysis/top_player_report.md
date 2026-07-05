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
| 1 | Majkel1337 | 1250.2 | 0 | n/a |
| 2 | nasuo445 | 1217.6 | 251 | 61% |
| 3 | THIRD PTCG Club | 1151.9 | 304 | 56% |
| 4 | hoshippi | 1149.3 | 126 | 52% |
| 5 | zoroark190 | 1122.0 | 325 | 60% |
| 6 | tonakaiiii | 1117.6 | 850 | 57% |
| 7 | iwashi | 1114.4 | 165 | 52% |
| 8 | kenkoooo | 1111.5 | 45 | 38% |
| 9 | Yushin Ito | 1109.6 | 341 | 54% |
| 10 | Ebi | 1107.5 | 0 | n/a |
| 11 | payanotty | 1103.9 | 0 | n/a |
| 12 | Ramesh Arvind | 1084.4 | 0 | n/a |
| 13 | genki toyama | 1081.9 | 0 | n/a |
| 14 | Rmy | 1079.8 | 0 | n/a |
| 15 | junlee789 | 1077.5 | 54 | 65% |
| 16 | kawachi | 1075.8 | 22 | 36% |
| 17 | kashiwashira | 1073.1 | 266 | 57% |
| 18 | WinDecks | 1068.9 | 667 | 51% |
| 19 | Hase2727 | 1068.5 | 0 | n/a |
| 20 | 渡邊征央 | 1065.7 | 630 | 54% |

## Coverage

- Games considered (post recency filter): 4975
- Games matched to a top-N team: 3271
- Training rows written: 178003
- Date range of matched games: 2026-07-04 to 2026-07-04

## Archetype breakdown

- meta_grimmsnarl_tonakaiiii: 1939
- other: 1258
- meta_grimmsnarl: 497
- meta_archaludon: 352

## Unmapped team names

- Ebi (no game in the scanned dataset names this team)
- Hase2727 (no game in the scanned dataset names this team)
- Majkel1337 (no game in the scanned dataset names this team)
- Ramesh Arvind (no game in the scanned dataset names this team)
- Rmy (no game in the scanned dataset names this team)
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
| kashiwashira | 114 | endgame_misplay | WinDecks |
| nasuo445 | 98 | endgame_misplay | Dũng Đỗ |
| iwashi | 80 | slow_search | tonakaiiii |
| hoshippi | 61 | endgame_misplay | tonakaiiii |
| kenkoooo | 28 | slow_search | Nghia Tran |
| junlee789 | 19 | endgame_misplay | 渡邊征央 |
| kawachi | 14 | endgame_misplay | TEAM NAME |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-05)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

