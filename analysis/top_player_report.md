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
| 1 | THIRD PTCG Club | 1258.4 | 304 | 56% |
| 2 | nasuo445 | 1177.8 | 251 | 61% |
| 3 | Majkel1337 | 1175.2 | 0 | n/a |
| 4 | iwashi | 1142.9 | 165 | 52% |
| 5 | zoroark190 | 1135.6 | 325 | 60% |
| 6 | Hase2727 | 1122.4 | 0 | n/a |
| 7 | Rmy | 1099.8 | 0 | n/a |
| 8 | Dũng Đỗ | 1095.3 | 400 | 64% |
| 9 | kazuki0123 | 1094.8 | 623 | 52% |
| 10 | junlee789 | 1093.5 | 54 | 65% |
| 11 | tonakaiiii | 1086.9 | 850 | 57% |
| 12 | Shardul Gharat | 1083.3 | 5 | 80% |
| 13 | Yushin Ito | 1081.7 | 341 | 54% |
| 14 | hoshippi | 1075.9 | 126 | 52% |
| 15 | 渡邊征央 | 1073.9 | 630 | 54% |
| 16 | aaa | 1067.9 | 19 | 37% |
| 17 | Claude and codex suck ;) | 1067.0 | 61 | 38% |
| 18 | noikaret | 1065.6 | 76 | 34% |
| 19 | aidy | 1065.2 | 187 | 48% |
| 20 | tsukammo | 1064.0 | 31 | 42% |

## Coverage

- Games considered (post recency filter): 4975
- Games matched to a top-N team: 3397
- Training rows written: 220292
- Date range of matched games: 2026-07-04 to 2026-07-04

## Archetype breakdown

- meta_grimmsnarl_tonakaiiii: 2024
- meta_grimmsnarl: 1271
- meta_archaludon: 752
- other: 401

## Unmapped team names

- Hase2727 (no game in the scanned dataset names this team)
- Majkel1337 (no game in the scanned dataset names this team)
- Rmy (no game in the scanned dataset names this team)

## Losses

| team | losses | dominant loss bucket | most common opponent |
|---|---|---|---|
| tonakaiiii | 369 | endgame_misplay | Dũng Đỗ |
| kazuki0123 | 300 | bad_determinization | tonakaiiii |
| 渡邊征央 | 289 | endgame_misplay | tonakaiiii |
| Yushin Ito | 157 | early_collapse | tonakaiiii |
| Dũng Đỗ | 145 | early_collapse | nasuo445 |
| THIRD PTCG Club | 133 | endgame_misplay | tonakaiiii |
| zoroark190 | 130 | endgame_misplay | Dũng Đỗ |
| aidy | 98 | endgame_misplay | kazuki0123 |
| nasuo445 | 98 | endgame_misplay | Dũng Đỗ |
| iwashi | 80 | slow_search | tonakaiiii |
| hoshippi | 61 | endgame_misplay | tonakaiiii |
| noikaret | 50 | bad_determinization | 渡邊征央 |
| Claude and codex suck ;) | 38 | bad_determinization | 渡邊征央 |
| junlee789 | 19 | endgame_misplay | 渡邊征央 |
| tsukammo | 18 | deck_matchup | 渡邊征央 |
| aaa | 12 | deckout | XP3RiX |
| Shardul Gharat | 1 | bad_determinization | tonakaiiii |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-05)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

