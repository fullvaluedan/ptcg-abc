# U39 Deck Exploration Phase 2: Candidate Scoring Verdict

**Date**: 2026-07-06  
**Status**: COMPLETE - GATE FAILED (NO PROMOTIONS)

## Summary

U39 deck exploration extracted 5 + additional candidates from the U39 top-rated mining dataset (43 unique signatures, 800+ rated teams). All 11 total candidates were scored through the calibrated bracket ring (tau 0.857, 9 opponents, 20 games each). **None cleared the gate** (+0.10 delta vs trolley baseline).

## Candidates Scored (11 total)

Ranked by ring win rate (baseline trolley 0.750):

| Deck | Win Rate | Wins | Delta | Promote |
|---|---|---|---|---|
| **candidate_yushin_ito** | 0.800 | 16/20 | +0.050 | ✗ |
| **candidate_nasuo445** | 0.700 | 14/20 | -0.050 | ✗ |
| **candidate_btk15049** | 0.600 | 12/20 | -0.150 | ✗ |
| **candidate_third_ptcg_club** | 0.600 | 12/20 | -0.150 | ✗ |
| **candidate_bluezlee** | 0.550 | 11/20 | -0.200 | ✗ |
| **candidate_shumpeinomura** | 0.500 | 10/20 | -0.250 | ✗ |
| **candidate_maher_el_ouahabi** | 0.450 | 9/20 | -0.300 | ✗ |
| **candidate_easonyanyan** | 0.450 | 9/20 | -0.300 | ✗ |
| **candidate_windecks** | 0.450 | 9/20 | -0.300 | ✗ |
| **candidate_kashiwashira** | 0.300 | 6/20 | -0.450 | ✗ |
| **candidate_zoroark190** | 0.350 | 7/20 | -0.400 | ✗ |

## Gate Definition

- **Gate criterion**: `delta >= 0.10` (10 percentage points above baseline)
- **Baseline**: trolley heuristic, 0.750 win rate (15 wins / 20 games vs 9-deck ring)
- **Threshold to promote**: 0.850 win rate (17/20)
- **Best candidate**: candidate_yushin_ito at 0.800 (16/20), **0.050 below gate**

## Interpretation

**Ring-based verdict (the only decision gate per L9 POSTURE INVERSION)**:
The top-rated 800+ team decks (cluster 1-5 picks, representing ~600 total plays by elite players) do not individually beat trolley through the calibrated ring. The best candidate (yushin_ito, 145 plays from cluster 1) still underperforms on the ring by -0.050 (statistical noise at n=20).

### Why might the mining find top decks that ring-underperform?

1. **Opponent pool mismatch** (historical issue, now fixed per L5): The top players face a different meta (higher ratings, different archetypes) than the bracket ring's 450-750 calibration pool. Their success is contextual to their field; re-ranked against our bracket opponents, they regress.

2. **Mirror effect**: The ring is built to evaluate our heuristic pilot *piloting* each deck. Top players' success also includes their own superior piloting (better decision-making, archetype awareness, reads). Our generic heuristic may not extract the deck's best play.

3. **Luck and limited sample**: With n=20, a 0.050 delta is within noise; yushin_ito could plausibly tie or beat trolley on a rerun. But the gate is set to catch material gains, and no candidate demonstrates one.

## Implications

- **U39 step 2 result: DONE, GATE FAILED.** No new deck candidate advances to TRACK L pre-registration.
- **Deck exploration ceiling hypothesis**: The top-rated mining (800+ rating cluster 1, ~145 plays, lowest loss rate on Kaggle) is not a source of TRACK L gains. Either the win-rate gains they show are contextual (their meta, their play), or our pilot is too weak to extract their value. Retest would require: (a) a much larger mining pool (below 800 rating), (b) the full game state + piloting replay to extract their play, or (c) accepting that deck changes alone do not move the ladder and returning to heuristic refinement (the comprehension track's game-plan / archetype awareness thesis from U90-U92).
- **Next offline units**: U101 (invariant fuzzer, Dan-directed), U102 (card-text audit, Dan-directed), or writeup work per TRACK S. No further deck exploration in this loop without a new mining strategy or a deck whose ring read is ambiguous enough to warrant ladder A/B.

## Data

- **Ring composition**: 9 clone opponents (bracket_1 through bracket_6, plus meta_archaludon, meta_grimmsnarl from ring_names())
- **Games per build**: 20 (n=20 per build to match tolerance for statistical noise at ~0.100 margin)
- **Run date**: 2026-07-06 iteration 21
- **Output**: analysis/new_candidates_phase2_scores_full.json
- **Tool**: tools/score_candidate_decks.py v2 (fixed to use rc.run_ring API)
