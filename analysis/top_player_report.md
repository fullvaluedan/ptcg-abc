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
| 1 | Majkel1337 | 1233.0 | 283 | 67% |
| 2 | nasuo445 | 1219.0 | 746 | 60% |
| 3 | Yushin Ito | 1191.1 | 282 | 59% |
| 4 | zoroark190 | 1126.4 | 641 | 58% |
| 5 | WinDecks | 1094.1 | 268 | 49% |
| 6 | Jett Huang | 1089.9 | 3 | 0% |
| 7 | bono | 1087.1 | 1 | 100% |
| 8 | Ajishio | 1082.6 | 136 | 52% |
| 9 | THIRD PTCG Club | 1081.2 | 474 | 53% |
| 10 | kawachi | 1073.3 | 100 | 48% |
| 11 | ごんさくよねきち | 1068.3 | 70 | 51% |
| 12 | やる気元気ミワハルキ | 1062.4 | 112 | 61% |
| 13 | iwashi | 1061.5 | 318 | 52% |
| 14 | カドラバ Kadoraba | 1061.1 | 52 | 42% |
| 15 | ShumpeiNomura | 1060.9 | 25 | 36% |
| 16 | aaa | 1060.4 | 159 | 47% |
| 17 | payanotty | 1058.7 | 162 | 52% |
| 18 | 豆本豆豆包 | 1057.8 | 0 | n/a |
| 19 | koga_poke | 1055.2 | 49 | 55% |
| 20 | LagrangianLocomotive | 1052.3 | 68 | 59% |

## Coverage

- Games considered (post recency filter): 5034
- Games matched to a top-N team: 3129
- Training rows written: 167889
- Date range of matched games: 2026-07-05 to 2026-07-05

## Archetype breakdown

- meta_grimmsnarl_tonakaiiii: 1393
- meta_grimmsnarl: 1202
- other: 1131
- meta_archaludon: 223

## Unmapped team names

- 豆本豆豆包 (no game in the scanned dataset names this team)

## Losses

| team | losses | dominant loss bucket | most common opponent |
|---|---|---|---|
| nasuo445 | 298 | bad_determinization | THIRD PTCG Club |
| zoroark190 | 269 | bad_determinization | Majkel1337 |
| THIRD PTCG Club | 223 | bad_determinization | nasuo445 |
| iwashi | 152 | slow_search | zoroark190 |
| WinDecks | 138 | early_collapse | tonakaiiii |
| Yushin Ito | 116 | early_collapse | zoroark190 |
| Majkel1337 | 92 | endgame_misplay | nasuo445 |
| aaa | 85 | deckout | kazuki0123 |
| payanotty | 77 | bad_determinization | aaa |
| Ajishio | 65 | bad_determinization | nasuo445 |
| kawachi | 52 | bad_determinization | kashiwashira |
| やる気元気ミワハルキ | 44 | endgame_misplay | zoroark190 |
| ごんさくよねきち | 34 | bad_determinization | zoroark190 |
| カドラバ Kadoraba | 30 | bad_determinization | Claude and codex suck ;) |
| LagrangianLocomotive | 28 | bad_determinization | zoroark190 |
| koga_poke | 22 | deck_matchup | payanotty |
| ShumpeiNomura | 16 | endgame_misplay | WinDecks |
| Jett Huang | 3 | early_collapse | btk15049 |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-06)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

