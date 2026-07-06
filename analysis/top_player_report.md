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
| 1 | Majkel1337 | 1243.1 | 283 | 67% |
| 2 | nasuo445 | 1220.6 | 746 | 60% |
| 3 | Yushin Ito | 1190.3 | 282 | 59% |
| 4 | zoroark190 | 1177.7 | 641 | 58% |
| 5 | bono | 1128.6 | 1 | 100% |
| 6 | kawachi | 1105.4 | 100 | 48% |
| 7 | Kotaro OKUYAMA | 1101.5 | 29 | 48% |
| 8 | Claude and codex suck ;) | 1096.6 | 99 | 44% |
| 9 | aaa | 1095.2 | 159 | 47% |
| 10 | THIRD PTCG Club | 1095.0 | 474 | 53% |
| 11 | btk15049 | 1083.8 | 290 | 49% |
| 12 | やる気元気ミワハルキ | 1081.7 | 112 | 61% |
| 13 | Rmy | 1080.2 | 178 | 57% |
| 14 | iwashi | 1072.7 | 318 | 52% |
| 15 | kidekikish | 1064.6 | 102 | 54% |
| 16 | 渡邊征央 | 1063.0 | 321 | 50% |
| 17 | WinDecks | 1061.3 | 268 | 49% |
| 18 | ShumpeiNomura | 1056.1 | 25 | 36% |
| 19 | payanotty | 1054.8 | 162 | 52% |
| 20 | llkarill | 1052.8 | 32 | 34% |

## Coverage

- Games considered (post recency filter): 5034
- Games matched to a top-N team: 3523
- Training rows written: 198911
- Date range of matched games: 2026-07-05 to 2026-07-05

## Archetype breakdown

- meta_grimmsnarl_tonakaiiii: 1813
- meta_grimmsnarl: 1352
- other: 996
- meta_archaludon: 461

## Unmapped team names

- none

## Losses

| team | losses | dominant loss bucket | most common opponent |
|---|---|---|---|
| nasuo445 | 298 | bad_determinization | THIRD PTCG Club |
| zoroark190 | 269 | bad_determinization | Majkel1337 |
| THIRD PTCG Club | 223 | bad_determinization | nasuo445 |
| 渡邊征央 | 161 | bad_determinization | zoroark190 |
| iwashi | 152 | slow_search | zoroark190 |
| btk15049 | 148 | slow_search | zoroark190 |
| WinDecks | 138 | early_collapse | tonakaiiii |
| Yushin Ito | 116 | early_collapse | zoroark190 |
| Majkel1337 | 92 | endgame_misplay | nasuo445 |
| aaa | 85 | deckout | kazuki0123 |
| Rmy | 77 | endgame_misplay | nasuo445 |
| payanotty | 77 | bad_determinization | aaa |
| Claude and codex suck ;) | 55 | bad_determinization | nasuo445 |
| kawachi | 52 | bad_determinization | kashiwashira |
| kidekikish | 47 | deck_matchup | zoroark190 |
| やる気元気ミワハルキ | 44 | endgame_misplay | zoroark190 |
| llkarill | 21 | endgame_misplay | aidy |
| ShumpeiNomura | 16 | endgame_misplay | WinDecks |
| Kotaro OKUYAMA | 15 | endgame_misplay | payanotty |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-06)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

