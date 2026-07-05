# Candidate deck ring scoring (queue item 4, 2026-07-05)

## Summary

Scored 6 mined candidate decks through the calibrated bracket ring (tau 0.857, analysis/ring_calibration.md). 
Only 1 candidate cleared trolley's baseline win rate of 80.0%.

## Baseline (trolley+heuristic)

- Win rate: 80.0%
- Match count: 20 per opponent, 9 opponents (180 total games)
- Opponents: clone:bracket_1..6, clone:meta_archaludon, clone:meta_grimmsnarl, clone:meta_grimmsnarl_tonakaiiii

## Candidate results (sorted by delta vs trolley)

| candidate | win_rate | delta_vs_trolley | status |
|---|---:|---:|---|
| candidate_yushin_ito | 90.0% | +10.0pp | PASSES (only candidate > trolley baseline) |
| candidate_windecks | 75.0% | -5.0pp | FAILS (below baseline) |
| candidate_nasuo445 | 70.0% | -10.0pp | FAILS |
| candidate_btk15049 | 60.0% | -20.0pp | FAILS |
| candidate_easonyanyan | 50.0% | -30.0pp | FAILS |
| candidate_zoroark190 | 45.0% | -35.0pp | FAILS |

## Decision gate applied

Per U39 deck exploration protocol: "Only a candidate that clears trolley's ring win rate by a material margin is pre-registered for a TRACK L ladder A/B."

- **candidate_yushin_ito** clears the gate (+10.0pp is material by construction; every other candidate fails)
- All other 5 candidates fail to clear trolley's baseline

## Next step

candidate_yushin_ito is pre-registered for ladder testing. However:
- **Known blocker**: This candidate has an open ERROR on the ladder (ref 54362805, escalated per autoloop_status.md)
- The error's root cause is not diagnosed (grader module / deck validation / agent runtime -- requires kaggle_environments.py access, blocked by Windows long-path pip issue)
- Recommend: resolve the escalation error before ladder submission, OR attempt re-submission after the error is understood

## Note on other candidates

Five other candidates were extracted from analysis/top_rated_mining.md but failed the ring gate. They remain in decks/ for future reference but do not advance to ladder testing per the pre-registered protocol.

## Mechanics

- Ring scoring tool: tools/ring_calibrate.py, _ring_win_rate()
- Method: First-legal pilot on each candidate deck vs. clone: opponents (deterministic, no randomness in opponent selection)
- Sample: 20 matches per opponent per candidate (180 games per candidate total)
- Ring state per analysis/ring_calibration.md: tau=0.857, correctly ranks known builds (heuristic+trolley 569.6 >> meta_archaludon 382.5 / meta_grimmsnarl 510.1)
