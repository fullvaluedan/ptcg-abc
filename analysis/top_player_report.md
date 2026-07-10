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
| 1 | Yushin Ito | 1289.0 | 720 | 63% |
| 2 | MPGaming | 1174.3 | 240 | 58% |
| 3 | Majkel1337 | 1171.7 | 506 | 56% |
| 4 | LiamK | 1143.6 | 341 | 51% |
| 5 | nasuo445 | 1107.4 | 554 | 52% |
| 6 | Dũng Đỗ | 1105.4 | 247 | 53% |
| 7 | wkonishi | 1096.2 | 71 | 38% |
| 8 | bono | 1095.6 | 578 | 54% |
| 9 | Michael Long | 1092.9 | 264 | 55% |
| 10 | WinDecks | 1090.9 | 246 | 54% |
| 11 | taksai | 1083.0 | 0 | n/a |
| 12 | Sota Uchiyama | 1080.8 | 98 | 47% |
| 13 | zoroark190 | 1075.3 | 106 | 45% |
| 14 | Alberto Bonsanto | 1074.6 | 155 | 48% |
| 15 | 213tubo | 1073.8 | 351 | 46% |
| 16 | Rmy | 1067.3 | 201 | 42% |
| 17 | Raihan Ramadistra | 1067.0 | 422 | 55% |
| 18 | Tahsin Arafat | 1065.5 | 0 | n/a |
| 19 | OSELCOUN | 1060.9 | 122 | 43% |
| 20 | capbloo | 1059.4 | 650 | 56% |

## Coverage

- Games considered (post recency filter): 4870
- Games matched to a top-N team: 4180
- Training rows written: 233105
- Date range of matched games: 2026-07-09 to 2026-07-09

## Archetype breakdown

- meta_grimmsnarl: 3415
- meta_archaludon: 1218
- meta_grimmsnarl_tonakaiiii: 652
- other: 587

## Unmapped team names

- Tahsin Arafat (no game in the scanned dataset names this team)
- taksai (no game in the scanned dataset names this team)

## Losses

| team | losses | dominant loss bucket | most common opponent |
|---|---|---|---|
| capbloo | 285 | endgame_misplay | Majkel1337 |
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
| zoroark190 | 58 | endgame_misplay | bono |
| Sota Uchiyama | 52 | bad_determinization | Raihan Ramadistra |
| wkonishi | 44 | endgame_misplay | bono |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-10)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

