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
| 1 | Majkel1337 | 1258.8 | 283 | 67% |
| 2 | Yushin Ito | 1218.1 | 282 | 59% |
| 3 | nasuo445 | 1179.0 | 746 | 60% |
| 4 | zoroark190 | 1135.4 | 641 | 58% |
| 5 | bono | 1123.1 | 1 | 100% |
| 6 | ごんさくよねきち | 1107.6 | 70 | 51% |
| 7 | カドラバ Kadoraba | 1097.2 | 52 | 42% |
| 8 | kawachi | 1093.2 | 100 | 48% |
| 9 | nakazu | 1086.3 | 0 | n/a |
| 10 | aaa | 1081.1 | 159 | 47% |
| 11 | Jett Huang | 1080.0 | 3 | 0% |
| 12 | THIRD PTCG Club | 1071.4 | 474 | 53% |
| 13 | Ajishio | 1071.0 | 136 | 52% |
| 14 | WinDecks | 1069.8 | 268 | 49% |
| 15 | やる気元気ミワハルキ | 1069.8 | 112 | 61% |
| 16 | base_camp_2002 | 1069.2 | 0 | n/a |
| 17 | Claude and codex suck ;) | 1068.1 | 99 | 44% |
| 18 | Oleksandr_Savsunenko | 1054.2 | 0 | n/a |
| 19 | 豆包 | 1053.9 | 0 | n/a |
| 20 | 渡邊征央 | 1051.4 | 321 | 50% |

## Coverage

- Games considered (post recency filter): 5034
- Games matched to a top-N team: 2995
- Training rows written: 158888
- Date range of matched games: 2026-07-05 to 2026-07-05

## Archetype breakdown

- meta_grimmsnarl_tonakaiiii: 1333
- meta_grimmsnarl: 1134
- other: 1131
- meta_archaludon: 149

## Unmapped team names

- Oleksandr_Savsunenko (no game in the scanned dataset names this team)
- base_camp_2002 (no game in the scanned dataset names this team)
- nakazu (no game in the scanned dataset names this team)
- 豆包 (no game in the scanned dataset names this team)

## Losses

| team | losses | dominant loss bucket | most common opponent |
|---|---|---|---|
| nasuo445 | 298 | bad_determinization | THIRD PTCG Club |
| zoroark190 | 269 | bad_determinization | Majkel1337 |
| THIRD PTCG Club | 223 | bad_determinization | nasuo445 |
| 渡邊征央 | 161 | bad_determinization | zoroark190 |
| WinDecks | 138 | early_collapse | tonakaiiii |
| Yushin Ito | 116 | early_collapse | zoroark190 |
| Majkel1337 | 92 | endgame_misplay | nasuo445 |
| aaa | 85 | deckout | kazuki0123 |
| Ajishio | 65 | bad_determinization | nasuo445 |
| Claude and codex suck ;) | 55 | bad_determinization | nasuo445 |
| kawachi | 52 | bad_determinization | kashiwashira |
| やる気元気ミワハルキ | 44 | endgame_misplay | zoroark190 |
| ごんさくよねきち | 34 | bad_determinization | zoroark190 |
| カドラバ Kadoraba | 30 | bad_determinization | Claude and codex suck ;) |
| Jett Huang | 3 | early_collapse | btk15049 |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-06)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

