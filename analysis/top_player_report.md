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
| 1 | Majkel1337 | 1147.5 | 638 | 58% |
| 2 | Yushin Ito | 1132.0 | 433 | 59% |
| 3 | bono | 1119.9 | 585 | 58% |
| 4 | Rmy | 1103.7 | 443 | 51% |
| 5 | THIRD PTCG Club | 1100.3 | 286 | 48% |
| 6 | nasuo445 | 1100.1 | 688 | 54% |
| 7 | WinDecks | 1093.3 | 265 | 53% |
| 8 | tonakaiiii | 1091.1 | 144 | 42% |
| 9 | senkin13 | 1085.5 | 3 | 33% |
| 10 | wkonishi | 1083.2 | 16 | 25% |
| 11 | zoroark190 | 1080.1 | 456 | 53% |
| 12 | ShumpeiNomura | 1076.2 | 102 | 48% |
| 13 | matsurih | 1075.9 | 124 | 50% |
| 14 | LiamK | 1074.6 | 124 | 56% |
| 15 | Hase2727 | 1067.5 | 0 | n/a |
| 16 | kazuki0123 | 1066.1 | 41 | 37% |
| 17 | Bozo Boys | 1065.4 | 72 | 51% |
| 18 | btk15049 | 1064.2 | 328 | 52% |
| 19 | Michael Long | 1063.2 | 0 | n/a |
| 20 | Sota Uchiyama | 1061.8 | 33 | 36% |

## Coverage

- Games considered (post recency filter): 5202
- Games matched to a top-N team: 3735
- Training rows written: 191801
- Date range of matched games: 2026-07-07 to 2026-07-07

## Archetype breakdown

- meta_grimmsnarl: 1835
- other: 1103
- meta_grimmsnarl_tonakaiiii: 1083
- meta_archaludon: 760

## Unmapped team names

- Hase2727 (no game in the scanned dataset names this team)
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
| tonakaiiii | 84 | bad_determinization | nasuo445 |
| matsurih | 62 | slow_search | bono |
| LiamK | 55 | slow_search | Majkel1337 |
| ShumpeiNomura | 53 | early_collapse | Yushin Ito |
| Bozo Boys | 35 | endgame_misplay | Rmy |
| kazuki0123 | 26 | bad_determinization | Bozo Boys |
| Sota Uchiyama | 21 | bad_determinization | Akira-Ninth |
| wkonishi | 12 | deck_matchup | 渡邊征央 |
| senkin13 | 2 | early_collapse | bono |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-08)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

