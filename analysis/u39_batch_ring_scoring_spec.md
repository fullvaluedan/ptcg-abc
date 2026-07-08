# U39 Batch Ring-Scoring Specification

## Status
- Deduplication: COMPLETE (analysis/mined_candidates_dedup_report.md)
- Legality Validation: COMPLETE (analysis/candidate_validation_report.md)
- Ring Scoring: PENDING (requires kaggle_environments, batch compute job)

## Task
Score 5 new candidate decks through the calibrated bracket ring (tau 0.857, from analysis/ring_calibration.md).
Candidates were mined from 800+ rated teams (analysis/top_rated_mining.md) and deduped against existing decks/.

## Candidates (by play count)
1. **candidate_third_ptcg_club** — 19 plays (HIGHEST PRIORITY)
2. candidate_kashiwashira — 8 plays
3. candidate_zoroark190 — 7 plays
4. candidate_変化の書ゾロアーク — 6 plays
5. candidate_bluezlee (variant 2) — 1 play

## Scoring Command
```bash
cd C:\Users\danom\ptcg-abc
.\.venv\Scripts\python.exe tools\score_candidate_decks.py \
  -n 40 \
  --margin 0.10 \
  --out analysis\u39_candidates_ring_scores.json
```

## Scoring Parameters
- **Matches per deck**: 40 (higher confidence than default 20)
- **Promotion threshold**: +0.10 ring win-rate delta over trolley FRESH reading (this run's trolley)
- **Context**: The calibrated bracket ring already has deck-judging authority (it was calibrated on 6 builds including 2 deck-changed meta copies). This run scores every candidate simultaneously with a fresh trolley reading in the same ring composition, preventing match-count drift contamination.

## Expected Outcome
- Comparison table: candidate win rates vs trolley fresh reading
- Promotion eligibility: any candidate clearing trolley by > +0.10 gets pre-registered for TRACK L ladder A/B
- Gate**: ring evidence only (not ladder reads per L9 noise recalibration); if a candidate clears this gate, it ships immediately without offline gauntlet repeat

## Prerequisites
- kaggle_environments must be installed in .venv
- decks/*.csv must be current (all 55 existing candidates + 5 new candidates readable)
- ring_calibration.md must document the tau 0.857 ring's build list (already done, 2026-07-02)

## Dependencies
- tools/ring_calibrate.py (run_ring function)
- tools/score_candidate_decks.py (main orchestrator)
- decks/*.csv (all candidate CSV files)
- analysis/ring_calibration.md (ring metadata)

## Output Files
- analysis/u39_candidates_ring_scores.json (structured results)
- analysis/u39_candidates_ring_scores.md (human-readable summary, if tool generates)

## Loop Status
This job is scheduled for batch compute (ptcgcompute) per P5 MODEL NOTE (compute-heavy work belongs in plain Python via tmux, never inside loop). Loop environment lacks kaggle_environments, so scoring cannot run here. Once batch job completes, loop can consume results and pre-register winners.

## Next Steps (after batch completes)
1. Read u39_candidates_ring_scores.json
2. Identify promotion-eligible candidates (win_rate_delta > +0.10 vs trolley)
3. Add pre-registrations to state/current.md for top 1-2 candidates
4. Submit top candidate to ladder (M=240, N=30, settle-by 2026-07-25 typical)
