# Top-player leaderboard tracker

Plan U3c (addendum v2). Tracks the live top-N leaderboard teams and pulls
their newest games from the published episode dataset into a weighted
training corpus (source=top_player).

Recency window: --days 14 (games older than the dataset's own newest
game minus this window are dropped before matching).

## Teams covered

| rank | team | rating | corpus games | corpus win rate |
|---|---|---|---|---|
| 1 | The Debauchery Tea Party | 1241.0 | 159 | 60% |
| 2 | tonakaiiii | 1225.5 | 145 | 68% |
| 3 | S4nkurero | 1214.9 | 246 | 60% |
| 4 | zoroark190 | 1185.7 | 112 | 55% |
| 5 | kazuki0123 | 1185.0 | 246 | 66% |
| 6 | ShumpeiNomura | 1178.8 | 150 | 60% |
| 7 | Yushin Ito | 1161.4 | 201 | 50% |
| 8 | Dick Jessen William | 1154.9 | 72 | 56% |
| 9 | btk15049 | 1147.1 | 6 | 17% |
| 10 | Michael Krager | 1141.7 | 107 | 60% |
| 11 | やる気元気ミワハルキ | 1133.9 | 0 | n/a |
| 12 | aidy | 1129.0 | 208 | 50% |
| 13 | THIRD PTCG Club | 1126.6 | 296 | 63% |
| 14 | Akira-Ninth | 1113.9 | 97 | 48% |
| 15 | YIN | 1113.4 | 0 | n/a |
| 16 | Ajishio | 1111.3 | 82 | 61% |
| 17 | Moegi | 1109.9 | 147 | 60% |
| 18 | Bata09 | 1095.5 | 0 | n/a |
| 19 | kashiwashira | 1095.4 | 121 | 54% |
| 20 | ezreal77 | 1095.2 | 6 | 50% |

## Coverage

- Games considered (post recency filter): 5734
- Games matched to a top-N team: 2041
- Training rows written: 173663
- Date range of matched games: 2026-06-30 to 2026-06-30

## Archetype breakdown

- meta_grimmsnarl: 1227
- meta_archaludon: 617
- other: 412
- meta_grimmsnarl_tonakaiiii: 145

## Unmapped team names

- Bata09 (no game in the scanned dataset names this team)
- YIN (no game in the scanned dataset names this team)
- やる気元気ミワハルキ (no game in the scanned dataset names this team)

## Staleness

- newest matched game is 1 day(s) old (as of 2026-07-02)

## Weekly refresh

Intended to run every Monday 09:00 Taipei time via a Hermes scheduled
task. Hermes registration is not reachable from this repo/tool, so run
manually (or wire it into whatever scheduler is available) with:

    python tools/top_player_tracker.py --refresh

