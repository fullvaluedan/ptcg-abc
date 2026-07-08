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
| 1 | Majkel1337 | 1159.5 | 638 | 58% |
| 2 | Yushin Ito | 1134.1 | 433 | 59% |
| 3 | Michael Long | 1119.5 | 0 | n/a |
| 4 | Hase2727 | 1111.2 | 0 | n/a |
| 5 | bono | 1110.9 | 585 | 58% |
| 6 | zoroark190 | 1101.5 | 456 | 53% |
| 7 | nasuo445 | 1095.1 | 688 | 54% |
| 8 | THIRD PTCG Club | 1091.6 | 286 | 48% |
| 9 | WinDecks | 1085.5 | 265 | 53% |
| 10 | btk15049 | 1081.6 | 328 | 52% |
| 11 | LiamK | 1077.0 | 124 | 56% |
| 12 | ShumpeiNomura | 1076.2 | 102 | 48% |
| 13 | tonakaiiii | 1074.1 | 144 | 42% |
| 14 | kazuki0123 | 1074.0 | 41 | 37% |
| 15 | Rmy | 1073.1 | 443 | 51% |
| 16 | kidekikish | 1070.3 | 86 | 40% |
| 17 | Sota Uchiyama | 1070.2 | 33 | 36% |
| 18 | koga_poke | 1062.6 | 338 | 53% |
| 19 | HIROYA KIKUCHI | 1060.9 | 0 | n/a |
| 20 | Bozo Boys | 1058.5 | 72 | 51% |

## Coverage

- Games considered (post recency filter): 5202
- Games matched to a top-N team: 3886
- Training rows written: 198328
- Date range of matched games: 2026-07-07 to 2026-07-07

## Archetype breakdown

- meta_grimmsnarl: 1778
- other: 1103
- meta_archaludon: 1098
- meta_grimmsnarl_tonakaiiii: 1083

## Unmapped team names

- HIROYA KIKUCHI (no game in the scanned dataset names this team)
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
| koga_poke | 159 | deck_matchup | Yushin Ito |
| btk15049 | 157 | slow_search | bono |
| THIRD PTCG Club | 148 | endgame_misplay | nasuo445 |
| WinDecks | 125 | early_collapse | nasuo445 |
| tonakaiiii | 84 | bad_determinization | nasuo445 |
| LiamK | 55 | slow_search | Majkel1337 |
| ShumpeiNomura | 53 | early_collapse | Yushin Ito |
| kidekikish | 52 | deck_matchup | nasuo445 |
| Bozo Boys | 35 | endgame_misplay | Rmy |
| kazuki0123 | 26 | bad_determinization | Bozo Boys |
| Sota Uchiyama | 21 | bad_determinization | Akira-Ninth |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-08)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

