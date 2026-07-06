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
| 1 | Majkel1337 | 1235.3 | 0 | n/a |
| 2 | nasuo445 | 1163.2 | 251 | 61% |
| 3 | zoroark190 | 1162.9 | 325 | 60% |
| 4 | Yushin Ito | 1159.8 | 341 | 54% |
| 5 | kashiwashira | 1119.2 | 266 | 57% |
| 6 | Rmy | 1114.0 | 0 | n/a |
| 7 | payanotty | 1106.7 | 0 | n/a |
| 8 | LagrangianLocomotive | 1105.5 | 80 | 44% |
| 9 | tonakaiiii | 1104.2 | 850 | 57% |
| 10 | 渡邊征央 | 1102.4 | 630 | 54% |
| 11 | iwashi | 1102.1 | 165 | 52% |
| 12 | lmaffei | 1094.4 | 0 | n/a |
| 13 | やる気元気ミワハルキ | 1090.6 | 40 | 50% |
| 14 | kidekikish | 1081.8 | 0 | n/a |
| 15 | junlee789 | 1081.0 | 54 | 65% |
| 16 | koga_poke | 1077.2 | 0 | n/a |
| 17 | Hase2727 | 1076.0 | 0 | n/a |
| 18 | カドラバ Kadoraba | 1074.6 | 4 | 50% |
| 19 | btk15049 | 1073.0 | 683 | 51% |
| 20 | WinDecks | 1069.3 | 667 | 51% |

## Coverage

- Games considered (post recency filter): 4975
- Games matched to a top-N team: 3466
- Training rows written: 192242
- Date range of matched games: 2026-07-04 to 2026-07-04

## Archetype breakdown

- meta_grimmsnarl_tonakaiiii: 1939
- other: 1298
- meta_archaludon: 1035
- meta_grimmsnarl: 84

## Unmapped team names

- Hase2727 (no game in the scanned dataset names this team)
- Majkel1337 (no game in the scanned dataset names this team)
- Rmy (no game in the scanned dataset names this team)
- kidekikish (no game in the scanned dataset names this team)
- koga_poke (no game in the scanned dataset names this team)
- lmaffei (no game in the scanned dataset names this team)
- payanotty (no game in the scanned dataset names this team)

## Losses

| team | losses | dominant loss bucket | most common opponent |
|---|---|---|---|
| tonakaiiii | 369 | endgame_misplay | Dũng Đỗ |
| btk15049 | 334 | slow_search | tonakaiiii |
| WinDecks | 329 | early_collapse | kazuki0123 |
| 渡邊征央 | 289 | endgame_misplay | tonakaiiii |
| Yushin Ito | 157 | early_collapse | tonakaiiii |
| zoroark190 | 130 | endgame_misplay | Dũng Đỗ |
| kashiwashira | 114 | endgame_misplay | WinDecks |
| nasuo445 | 98 | endgame_misplay | Dũng Đỗ |
| iwashi | 80 | slow_search | tonakaiiii |
| LagrangianLocomotive | 45 | deckout | 渡邊征央 |
| やる気元気ミワハルキ | 20 | bad_determinization | tonakaiiii |
| junlee789 | 19 | endgame_misplay | 渡邊征央 |
| カドラバ Kadoraba | 2 | deck_matchup | 渡邊征央 |

## Staleness

- newest matched game is 1 day(s) old (as of 2026-07-06)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

