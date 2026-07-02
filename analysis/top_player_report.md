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
| 1 | The Debauchery Tea Party | 1221.4 | 159 | 60% |
| 2 | tonakaiiii | 1216.5 | 145 | 68% |
| 3 | ShumpeiNomura | 1170.1 | 150 | 60% |
| 4 | zoroark190 | 1151.7 | 112 | 55% |
| 5 | kazuki0123 | 1151.4 | 246 | 66% |
| 6 | Dick Jessen William | 1147.4 | 72 | 56% |
| 7 | Yushin Ito | 1146.4 | 201 | 50% |
| 8 | を | 1137.0 | 0 | n/a |
| 9 | THIRD PTCG Club | 1136.4 | 296 | 63% |
| 10 | easonyanyan | 1131.8 | 8 | 38% |
| 11 | Michael Krager | 1131.2 | 107 | 60% |
| 12 | aidy | 1125.3 | 208 | 50% |
| 13 | kashiwashira | 1125.0 | 121 | 54% |
| 14 | Ajishio | 1119.3 | 82 | 61% |
| 15 | btk15049 | 1117.7 | 6 | 17% |
| 16 | Nghia Tran | 1115.4 | 0 | n/a |
| 17 | kawachi | 1109.7 | 149 | 47% |
| 18 | Akira-Ninth | 1109.3 | 97 | 48% |
| 19 | yamy893 | 1105.1 | 103 | 51% |
| 20 | やる気元気ミワハルキ | 1104.9 | 0 | n/a |

## Coverage

- Games considered (post recency filter): 5734
- Games matched to a top-N team: 1911
- Training rows written: 99159
- Date range of matched games: 2026-06-30 to 2026-06-30

## Archetype breakdown

- meta_grimmsnarl: 1084
- meta_archaludon: 464
- other: 420
- meta_grimmsnarl_tonakaiiii: 294

## Unmapped team names

- Nghia Tran (no game in the scanned dataset names this team)
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
| kashiwashira | 56 | bad_determinization | monnosuke |
| Akira-Ninth | 50 | bad_determinization | ykuroka |
| yamy893 | 50 | deck_matchup | THIRD PTCG Club |
| zoroark190 | 50 | endgame_misplay | The Debauchery Tea Party |
| tonakaiiii | 47 | endgame_misplay | The Debauchery Tea Party |
| Michael Krager | 43 | early_collapse | monnosuke |
| Ajishio | 32 | bad_determinization | THIRD PTCG Club |
| Dick Jessen William | 32 | deck_matchup | jiatu.l |
| btk15049 | 5 | slow_search | kenkoooo |
| easonyanyan | 5 | bad_determinization | Yushin Ito |

## Staleness

- newest matched game is 1 day(s) old (as of 2026-07-02)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

