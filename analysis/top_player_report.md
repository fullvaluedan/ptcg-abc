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
| 1 | Majkel1337 | 1228.5 | 283 | 67% |
| 2 | Yushin Ito | 1184.2 | 282 | 59% |
| 3 | zoroark190 | 1152.8 | 641 | 58% |
| 4 | Rmy | 1133.8 | 178 | 57% |
| 5 | nasuo445 | 1133.2 | 746 | 60% |
| 6 | kidekikish | 1116.2 | 102 | 54% |
| 7 | lmaffei | 1113.3 | 51 | 59% |
| 8 | 渡邊征央 | 1103.7 | 321 | 50% |
| 9 | やる気元気ミワハルキ | 1101.7 | 112 | 61% |
| 10 | payanotty | 1100.1 | 162 | 52% |
| 11 | aaa | 1097.4 | 159 | 47% |
| 12 | iwashi | 1096.1 | 318 | 52% |
| 13 | The Debauchery Tea Party | 1087.1 | 91 | 46% |
| 14 | NoOne | 1086.8 | 23 | 57% |
| 15 | kashiwashira | 1075.3 | 119 | 61% |
| 16 | tonakaiiii | 1072.3 | 563 | 56% |
| 17 | koga_poke | 1070.3 | 49 | 55% |
| 18 | Claude and codex suck ;) | 1070.1 | 99 | 44% |
| 19 | SamuelSanolume | 1066.4 | 1 | 100% |
| 20 | btk15049 | 1065.8 | 290 | 49% |

## Coverage

- Games considered (post recency filter): 5034
- Games matched to a top-N team: 3574
- Training rows written: 213269
- Date range of matched games: 2026-07-05 to 2026-07-05

## Archetype breakdown

- meta_grimmsnarl_tonakaiiii: 2376
- other: 847
- meta_grimmsnarl: 831
- meta_archaludon: 536

## Unmapped team names

- none

## Losses

| team | losses | dominant loss bucket | most common opponent |
|---|---|---|---|
| nasuo445 | 298 | bad_determinization | THIRD PTCG Club |
| zoroark190 | 269 | bad_determinization | Majkel1337 |
| tonakaiiii | 250 | bad_determinization | nasuo445 |
| 渡邊征央 | 161 | bad_determinization | zoroark190 |
| iwashi | 152 | slow_search | zoroark190 |
| btk15049 | 148 | slow_search | zoroark190 |
| Yushin Ito | 116 | early_collapse | zoroark190 |
| Majkel1337 | 92 | endgame_misplay | nasuo445 |
| aaa | 85 | deckout | kazuki0123 |
| Rmy | 77 | endgame_misplay | nasuo445 |
| payanotty | 77 | bad_determinization | aaa |
| Claude and codex suck ;) | 55 | bad_determinization | nasuo445 |
| The Debauchery Tea Party | 49 | bad_determinization | nasuo445 |
| kidekikish | 47 | deck_matchup | zoroark190 |
| kashiwashira | 46 | bad_determinization | Yushin Ito |
| やる気元気ミワハルキ | 44 | endgame_misplay | zoroark190 |
| koga_poke | 22 | deck_matchup | payanotty |
| lmaffei | 21 | bad_determinization | Yushin Ito |
| NoOne | 10 | bad_determinization | btk15049 |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-06)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

