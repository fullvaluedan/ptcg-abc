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
| 1 | Yushin Ito | 1308.8 | 720 | 63% |
| 2 | MPGaming | 1178.9 | 240 | 58% |
| 3 | LiamK | 1140.5 | 341 | 51% |
| 4 | Majkel1337 | 1139.3 | 506 | 56% |
| 5 | taksai | 1136.2 | 0 | n/a |
| 6 | nasuo445 | 1127.2 | 554 | 52% |
| 7 | Alberto Bonsanto | 1100.4 | 155 | 48% |
| 8 | Raihan Ramadistra | 1098.2 | 422 | 55% |
| 9 | 213tubo | 1093.0 | 351 | 46% |
| 10 | Dũng Đỗ | 1092.2 | 247 | 53% |
| 11 | wkonishi | 1090.7 | 71 | 38% |
| 12 | bono | 1090.5 | 578 | 54% |
| 13 | Michael Long | 1089.2 | 264 | 55% |
| 14 | zoroark190 | 1081.9 | 106 | 45% |
| 15 | WinDecks | 1079.9 | 246 | 54% |
| 16 | Rmy | 1071.1 | 201 | 42% |
| 17 | Sota Uchiyama | 1067.7 | 98 | 47% |
| 18 | wally0593 | 1062.8 | 95 | 39% |
| 19 | kazuki0123 | 1061.4 | 50 | 48% |
| 20 | OSELCOUN | 1060.8 | 122 | 43% |

## Coverage

- Games considered (post recency filter): 4870
- Games matched to a top-N team: 3951
- Training rows written: 207923
- Date range of matched games: 2026-07-09 to 2026-07-09

## Archetype breakdown

- meta_grimmsnarl: 2910
- meta_archaludon: 1218
- meta_grimmsnarl_tonakaiiii: 652
- other: 587

## Unmapped team names

- taksai (no game in the scanned dataset names this team)

## Losses

| team | losses | dominant loss bucket | most common opponent |
|---|---|---|---|
| Yushin Ito | 269 | bad_determinization | nasuo445 |
| bono | 268 | deckout | Yushin Ito |
| nasuo445 | 267 | bad_determinization | capbloo |
| Majkel1337 | 223 | endgame_misplay | Yushin Ito |
| Raihan Ramadistra | 192 | early_collapse | capbloo |
| 213tubo | 191 | bad_determinization | Yushin Ito |
| LiamK | 167 | slow_search | Yushin Ito |
| Michael Long | 118 | deckout | Yushin Ito |
| Dũng Đỗ | 116 | early_collapse | capbloo |
| Rmy | 116 | deckout | Yushin Ito |
| WinDecks | 113 | early_collapse | ごんさくよねきち |
| MPGaming | 100 | bad_determinization | Yushin Ito |
| Alberto Bonsanto | 80 | early_collapse | nasuo445 |
| OSELCOUN | 70 | slow_search | Raihan Ramadistra |
| wally0593 | 58 | endgame_misplay | capbloo |
| zoroark190 | 58 | endgame_misplay | bono |
| Sota Uchiyama | 52 | bad_determinization | Raihan Ramadistra |
| wkonishi | 44 | endgame_misplay | bono |
| kazuki0123 | 26 | bad_determinization | Raihan Ramadistra |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-10)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

