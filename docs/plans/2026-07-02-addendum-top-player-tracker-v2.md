---
title: "feat: top-player leaderboard tracker v2 (addendum to combined plan v2)"
date: 2026-07-02
type: feat
status: ready
depth: standard
origin: addendum to 2026-07-02-combined-learned-eval-plan-v2.md, insert as U3c after U3b
target_repo: ptcg-abc
---

# U3c: top-player leaderboard tracker

## Why

Current expert data is either a stale bulk snapshot or whoever we randomly played. This unit tracks the LIVE top-N leaderboard teams, pulls their newest games specifically, and feeds them into training with extra weight. Refreshable weekly.

## Hard constraints (inherited)

- No em dashes anywhere.
- data/training/ and data/replays/ stay gitignored.
- Kaggle token stays at ~/.kaggle/access_token, never in code or logs.
- Dev-only script, no new runtime dependency in the submission.

## Steps

1. New file: tools/top_player_tracker.py
   a. Fetch current leaderboard (reuse the Kaggle API client/auth pattern from deck_harvest.py). Capture team name AND rating.
   b. NAME-TO-ID MAP: episode datasets key games by submission ID, not team name. Build a mapping from team name to submission ID(s) using the leaderboard/submission metadata available through the same API surface deck_harvest.py uses. If a name cannot be mapped, log it in the report and skip it. Filtering happens by ID, never by name string match inside episodes.
   c. Take top-N teams (flag --top-n, default 20).
   d. Load the newest published episode dataset (reuse deck_harvest.py's loader).
   e. RECENCY: flag --days (default 14). Keep only games newer than that cutoff. Old games reflect old bot versions.
   f. Filter games to those where a mapped top-N submission ID appears as a seat.
   g. Run existing deck_harvest extraction and expert_cohort extraction on the filtered subset only.
   h. Output: data/training/top_player_corpus_<date>.csv with source=top_player, same row schema as expert_cohort output plus a team column, and analysis/top_player_report.md.

2. Report contents (analysis/top_player_report.md):
   - Teams covered with current rating and each team's win rate within the corpus (identifies who to imitate hardest).
   - Game count, date range, archetype breakdown.
   - Unmapped team names, if any.
   - STALENESS line: age of newest game in the corpus. If older than 7 days, print a refresh warning.

3. Flag --refresh: re-fetch leaderboard and episodes, append new rows, DEDUPE by game_id both within the file and against ladder rows (a game must not appear under both source=ladder and source=top_player; top_player wins the tie).

4. Training weight hook: tools/train_eval.py gains --source-weights, default top_player=2.0 and all others 1.0, applied as sample weights during fit. Document the chosen weights in analysis/ladder_data_ab.md alongside the existing AUC comparison.

5. Weekly refresh: register a Hermes scheduled task to run tools/top_player_tracker.py --refresh every Monday 09:00 Taipei time. If Hermes registration is not reachable from this repo, write the exact command line into analysis/top_player_report.md under a "weekly refresh" heading for manual scheduling.

6. Tests:
   - Mock leaderboard with 3 fake teams (with ratings), mock name-to-ID map with 1 unmappable name.
   - Mock episode dataset with 6 games: 2 matching and recent, 1 matching but older than --days, 3 non-matching.
   - Assert: only the 2 recent matching games in output, unmappable name listed in report, dedupe removes a planted duplicate game_id, report contains ratings and win rates.

7. Commit: feat(training): top-player leaderboard tracker

## Definition of done

- tools/top_player_tracker.py runs standalone, produces corpus CSV and report with ratings, win rates, and staleness line.
- Dedupe against ladder rows verified by test.
- train_eval.py accepts --source-weights.
- Weekly refresh registered with Hermes or documented for manual scheduling.
- Tests pass.
