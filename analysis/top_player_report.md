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
| 1 | tonakaiiii | 1283.1 | 846 | 58% |
| 2 | Yushin Ito | 1199.9 | 548 | 53% |
| 3 | chamboabi | 1156.6 | 16 | 50% |
| 4 | 渡邊征央 | 1155.1 | 0 | n/a |
| 5 | kazuki0123 | 1153.7 | 815 | 55% |
| 6 | btk15049 | 1128.7 | 266 | 55% |
| 7 | Akira-Ninth | 1124.7 | 371 | 51% |
| 8 | aidy | 1121.3 | 296 | 43% |
| 9 | yamy893 | 1118.0 | 324 | 50% |
| 10 | zoroark190 | 1116.1 | 429 | 54% |
| 11 | TEAM NAME | 1112.1 | 11 | 27% |
| 12 | BluezLee | 1110.1 | 6 | 17% |
| 13 | XP3RiX | 1107.0 | 0 | n/a |
| 14 | MtN | 1104.5 | 0 | n/a |
| 15 | The Debauchery Tea Party | 1104.4 | 863 | 57% |
| 16 | pokeka_ryo | 1102.4 | 110 | 62% |
| 17 | Ajishio | 1097.0 | 233 | 37% |
| 18 | Kohenyan | 1090.3 | 29 | 24% |
| 19 | ykuroka | 1084.2 | 157 | 49% |
| 20 | Yufeng | 1082.4 | 0 | n/a |

## Coverage

- Games considered (post recency filter): 5153
- Games matched to a top-N team: 3924
- Training rows written: 239232
- Date range of matched games: 2026-07-02 to 2026-07-02

## Archetype breakdown

- meta_grimmsnarl: 2309
- other: 1178
- meta_archaludon: 987
- meta_grimmsnarl_tonakaiiii: 846

## Unmapped team names

- MtN (no game in the scanned dataset names this team)
- XP3RiX (no game in the scanned dataset names this team)
- Yufeng (no game in the scanned dataset names this team)
- 渡邊征央 (no game in the scanned dataset names this team)

## Losses

| team | losses | dominant loss bucket | most common opponent |
|---|---|---|---|
| The Debauchery Tea Party | 369 | endgame_misplay | tonakaiiii |
| kazuki0123 | 369 | bad_determinization | tonakaiiii |
| tonakaiiii | 357 | bad_determinization | The Debauchery Tea Party |
| Yushin Ito | 258 | early_collapse | kazuki0123 |
| zoroark190 | 199 | bad_determinization | tonakaiiii |
| Akira-Ninth | 180 | bad_determinization | The Debauchery Tea Party |
| aidy | 168 | deckout | Yushin Ito |
| yamy893 | 161 | deck_matchup | The Debauchery Tea Party |
| Ajishio | 146 | deckout | Yushin Ito |
| btk15049 | 119 | slow_search | kazuki0123 |
| ykuroka | 80 | deck_matchup | Yushin Ito |
| pokeka_ryo | 42 | early_collapse | Michael Krager |
| Kohenyan | 22 | bad_determinization | kazuki0123 |
| TEAM NAME | 8 | bad_determinization | kazuki0123 |
| chamboabi | 8 | deck_matchup | aidy |
| BluezLee | 5 | early_collapse | kazuki0123 |

## Staleness

- newest matched game is 0 day(s) old (as of 2026-07-03)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

