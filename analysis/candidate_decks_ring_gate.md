# Deck Candidate Scoring Through Bracket Ring (2026-07-05)

## Objective
Score 6 newly deduped deck candidates (from tools/select_new_deck_candidates.py) through the calibrated bracket ring (tau 0.857, analysis/ring_calibration.md) against trolley baseline to identify promotion-eligible candidates for TRACK L ladder A/B testing.

## Setup
- **Ring composition**: 9 opponents (bracket_1..6 + clones of top-rated builds)
- **Baseline**: trolley (historical calibration reference point)
- **Promotion gate**: +0.10 win-rate delta over baseline (default margin from tools/score_candidate_decks.py, half the discordant gap from the passing calibration run)
- **Sample per build**: 20 matches (DEFAULT_MATCHES)

## Results

### Summary
Only 1 of 6 candidates cleared the gate. The remainder scored below baseline by 10-60 percentage points.

| Candidate | Win Rate | Wins/n | Delta vs Trolley | Verdict |
|-----------|----------|--------|------------------|---------|
| trolley (baseline) | 0.900 | 18/20 | — | — |
| candidate_yushin_ito | 1.000 | 20/20 | +0.100 | **PROMOTE** |
| candidate_btk15049 | 0.800 | 16/20 | -0.100 | no promote |
| candidate_windecks | 0.750 | 15/20 | -0.150 | no promote |
| candidate_nasuo445 | 0.650 | 13/20 | -0.250 | no promote |
| candidate_easonyanyan | 0.550 | 11/20 | -0.350 | no promote |
| candidate_zoroark190 | 0.300 | 6/20 | -0.600 | no promote |

### Promoted Candidate: candidate_yushin_ito
- **Source**: top-player deck mining, deduped against known candidates via signature matching (U39 step 1)
- **Performance**: 20/20 against ring (perfect record)
- **Key observation**: This is a small-sample result (n=20). Ring variance is non-negligible at this scale; a 0.900 baseline can drift ±~0.12 on same-build replays under ring-composition and match-count noise (historical: ring calibration itself used larger samples to establish tau >= 0.7). A follow-up ring run with n=40 or n=60 is prudent before ladder submission to confirm this is not a luck artifact.

### Non-Promoted Candidates (Technical Notes)
All remaining candidates scored below the baseline:
- **btk15049, windecks**: modest underperformance (-10-15 pp). These are on the margin of distinguishability from noise.
- **nasuo445, easonyanyan**: clearer gap (-25-35 pp). Unlikely to flip on a rerun.
- **zoroark190**: substantial underperformance (-60 pp). Discard.

The diversity of deltas (from -10 to -60) suggests the candidates do carry real structure (not uniform noise), though small-sample variance remains the largest uncertainty at n=20 per build.

## Next Steps (TRACK L pre-registration)
1. **Confirmation run**: Rescore candidate_yushin_ito with n=40 or n=60 in isolation against the same ring to verify the 1.0 is not a statistical outlier. If it sustains >0.85, proceed.
2. **Deck legality audit**: Verify the 60-card list against current Pokemon TCG rules (no suspensions, no duplicates beyond 4-per-name, energy types valid).
3. **Pre-register for ladder A/B**: Build heuristic+candidate_yushin_ito, grader-verify (tests/test_grader_submission.py), and pre-register per state/current.md discipline (M=60, settle-by date). Do NOT submit until confirmation run passes.

## Measurement Notes
All results from a single run (tools/score_candidate_decks.py, 2026-07-05, ring_names() via ring_calibrate.py). Ring is the DECISION GATE (per L9 NOISE RECALIBRATION); ladder A/B is only to confirm and serialize the finding, not to dispute ring outcomes. See analysis/ring_calibration.md for ring validation (tau=0.857, 6/6 settled builds covered).
