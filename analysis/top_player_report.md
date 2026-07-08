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
| 1 | Majkel1337 | 1169.0 | 638 | 58% |
| 2 | bono | 1127.8 | 585 | 58% |
| 3 | Yushin Ito | 1123.4 | 433 | 59% |
| 4 | WinDecks | 1106.4 | 265 | 53% |
| 5 | wkonishi | 1100.4 | 16 | 25% |
| 6 | nasuo445 | 1099.1 | 688 | 54% |
| 7 | LiamK | 1097.9 | 124 | 56% |
| 8 | THIRD PTCG Club | 1097.6 | 286 | 48% |
| 9 | Michael Long | 1085.6 | 0 | n/a |
| 10 | tonakaiiii | 1078.4 | 144 | 42% |
| 11 | kazuki0123 | 1072.4 | 41 | 37% |
| 12 | btk15049 | 1070.1 | 328 | 52% |
| 13 | Rmy | 1068.7 | 443 | 51% |
| 14 | matsurih | 1068.5 | 124 | 50% |
| 15 | zoroark190 | 1066.8 | 456 | 53% |
| 16 | ごんさくよねきち | 1058.1 | 203 | 51% |
| 17 | 于笑非lilishyxf | 1057.2 | 0 | n/a |
| 18 | wally0593 | 1055.7 | 62 | 42% |
| 19 | aaa | 1055.3 | 176 | 52% |
| 20 | 豆本豆豆包 | 1052.9 | 144 | 42% |

## Coverage

- Games considered (post recency filter): 5202
- Games matched to a top-N team: 3942
- Training rows written: 207673
- Date range of matched games: 2026-07-07 to 2026-07-07

## Archetype breakdown

- meta_grimmsnarl: 2345
- other: 1103
- meta_grimmsnarl_tonakaiiii: 1050
- meta_archaludon: 658

## Unmapped team names

- Michael Long (no game in the scanned dataset names this team)
- 于笑非lilishyxf (no game in the scanned dataset names this team)

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
| tonakaiiii | 84 | bad_determinization | nasuo445 |
| 豆本豆豆包 | 84 | bad_determinization | Yushin Ito |
| matsurih | 62 | slow_search | bono |
| LiamK | 55 | slow_search | Majkel1337 |
| wally0593 | 36 | endgame_misplay | zoroark190 |
| kazuki0123 | 26 | bad_determinization | Bozo Boys |
| wkonishi | 12 | deck_matchup | 渡邊征央 |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-08)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

