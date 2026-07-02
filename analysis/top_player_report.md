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
| 1 | The Debauchery Tea Party | 1216.7 | 159 | 60% |
| 2 | tonakaiiii | 1197.2 | 145 | 68% |
| 3 | Dick Jessen William | 1174.3 | 72 | 56% |
| 4 | Yushin Ito | 1172.0 | 201 | 50% |
| 5 | ShumpeiNomura | 1167.7 | 150 | 60% |
| 6 | kazuki0123 | 1163.7 | 246 | 66% |
| 7 | THIRD PTCG Club | 1142.3 | 296 | 63% |
| 8 | zoroark190 | 1138.9 | 112 | 55% |
| 9 | aidy | 1138.3 | 208 | 50% |
| 10 | suguuuuu & hiehie | 1126.6 | 107 | 55% |
| 11 | btk15049 | 1124.7 | 6 | 17% |
| 12 | kawachi | 1123.6 | 149 | 47% |
| 13 | kashiwashira | 1121.9 | 121 | 54% |
| 14 | Akira-Ninth | 1117.3 | 97 | 48% |
| 15 | Ajishio | 1114.3 | 82 | 61% |
| 16 | Michael Krager | 1112.4 | 107 | 60% |
| 17 | やる気元気ミワハルキ | 1109.7 | 0 | n/a |
| 18 | を | 1103.8 | 0 | n/a |
| 19 | Moegi | 1102.6 | 147 | 60% |
| 20 | ykuroka | 1094.6 | 110 | 54% |

## Coverage

- Games considered (post recency filter): 5734
- Games matched to a top-N team: 2104
- Training rows written: 109075
- Date range of matched games: 2026-06-30 to 2026-06-30

## Archetype breakdown

- meta_grimmsnarl: 1088
- meta_archaludon: 721
- other: 412
- meta_grimmsnarl_tonakaiiii: 294

## Unmapped team names

- やる気元気ミワハルキ (no game in the scanned dataset names this team)
- を (no game in the scanned dataset names this team)

## Losses

| team | losses | dominant loss bucket | most common opponent |
|---|---|---|---|
| THIRD PTCG Club | 110 | bad_determinization | Moegi |
| aidy | 105 | deck_matchup | kazuki0123 |
| Yushin Ito | 100 | early_collapse | ShumpeiNomura |
| kazuki0123 | 83 | bad_determinization | ShumpeiNomura |
| kawachi | 79 | bad_determinization | Yushin Ito |
| The Debauchery Tea Party | 64 | bad_determinization | THIRD PTCG Club |
| ShumpeiNomura | 60 | bad_determinization | kazuki0123 |
| Moegi | 59 | endgame_misplay | tonakaiiii |
| kashiwashira | 56 | bad_determinization | monnosuke |
| ykuroka | 51 | deck_matchup | nattomaki |
| Akira-Ninth | 50 | bad_determinization | ykuroka |
| zoroark190 | 50 | endgame_misplay | The Debauchery Tea Party |
| suguuuuu & hiehie | 48 | slow_search | capbloo |
| tonakaiiii | 47 | endgame_misplay | The Debauchery Tea Party |
| Michael Krager | 43 | early_collapse | monnosuke |
| Ajishio | 32 | bad_determinization | THIRD PTCG Club |
| Dick Jessen William | 32 | deck_matchup | jiatu.l |
| btk15049 | 5 | slow_search | kenkoooo |

## Staleness

- newest matched game is 1 day(s) old (as of 2026-07-02)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

