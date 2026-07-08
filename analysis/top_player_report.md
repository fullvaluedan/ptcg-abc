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
| 1 | Raihan Ramadistra | 1139.5 | 70 | 41% |
| 2 | THIRD PTCG Club | 1132.4 | 286 | 48% |
| 3 | Yushin Ito | 1132.2 | 433 | 59% |
| 4 | LiamK | 1128.7 | 124 | 56% |
| 5 | Majkel1337 | 1127.1 | 638 | 58% |
| 6 | nasuo445 | 1123.2 | 688 | 54% |
| 7 | aaa | 1111.5 | 176 | 52% |
| 8 | Rmy | 1109.5 | 443 | 51% |
| 9 | bono | 1098.4 | 585 | 58% |
| 10 | zoroark190 | 1093.2 | 456 | 53% |
| 11 | kazuki0123 | 1091.3 | 41 | 37% |
| 12 | WinDecks | 1086.7 | 265 | 53% |
| 13 | kashiwashira | 1082.0 | 71 | 55% |
| 14 | ごんさくよねきち | 1078.9 | 203 | 51% |
| 15 | Bozo Boys | 1078.0 | 72 | 51% |
| 16 | Michael Long | 1075.9 | 0 | n/a |
| 17 | 5.5 | 1063.3 | 97 | 47% |
| 18 | btk15049 | 1060.3 | 328 | 52% |
| 19 | wkonishi | 1059.3 | 16 | 25% |
| 20 | Boss's Orders Are All You Need | 1054.9 | 33 | 42% |

## Coverage

- Games considered (post recency filter): 5202
- Games matched to a top-N team: 3872
- Training rows written: 202553
- Date range of matched games: 2026-07-07 to 2026-07-07

## Archetype breakdown

- meta_grimmsnarl: 2280
- other: 1174
- meta_grimmsnarl_tonakaiiii: 906
- meta_archaludon: 665

## Unmapped team names

- Michael Long (no game in the scanned dataset names this team)

## Losses

| team | losses | dominant loss bucket | most common opponent |
|---|---|---|---|
| nasuo445 | 316 | bad_determinization | Majkel1337 |
| Majkel1337 | 266 | endgame_misplay | vibechu |
| bono | 244 | bad_determinization | Majkel1337 |
| Rmy | 216 | deckout | nasuo445 |
| zoroark190 | 215 | endgame_misplay | Majkel1337 |
| Yushin Ito | 179 | bad_determinization | nasuo445 |
| btk15049 | 157 | slow_search | bono |
| THIRD PTCG Club | 148 | endgame_misplay | nasuo445 |
| WinDecks | 125 | early_collapse | nasuo445 |
| ごんさくよねきち | 100 | endgame_misplay | nasuo445 |
| aaa | 84 | deckout | LiamKirwin |
| LiamK | 55 | slow_search | Majkel1337 |
| 5.5 | 51 | deck_matchup | Yushin Ito |
| Raihan Ramadistra | 41 | bad_determinization | bono |
| Bozo Boys | 35 | endgame_misplay | Rmy |
| kashiwashira | 32 | endgame_misplay | btk15049 |
| kazuki0123 | 26 | bad_determinization | Bozo Boys |
| Boss's Orders Are All You Need | 19 | endgame_misplay | Rmy |
| wkonishi | 12 | deck_matchup | 渡邊征央 |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-08)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

