# U39 Deck Exploration Summary

**Status**: Complete. Candidate `yushin_ito` promoted to ladder; remainder below material margin threshold.

## Phase 1: Mining (Complete)

- **Minimum rating threshold**: 800.0
- **Episodes scanned**: 500
- **Unique deck signatures identified**: 49
- **Top-rated teams contributing**: ~50 teams with 800+ rating

Source: analysis/top_rated_mining.md, earliest cluster 2026-07-05

## Phase 2: Deduplication & Candidate Scoring (Complete)

### Scoring Results

Candidates evaluated through calibrated bracket ring (n=20/arm, tau=0.857 calibration):

| Candidate | Win Rate | Record | Delta vs Trolley | Status |
|-----------|----------|--------|------------------|--------|
| trolley (baseline) | 0.75-0.80 | 15-16/20 | — | baseline |
| candidate_yushin_ito | 0.90 | 18/20 | **+0.10** | ✅ PROMOTED |
| candidate_windecks | 0.75 | 15/20 | -0.05 | Below margin |
| candidate_nasuo445 | 0.65-0.70 | 13-14/20 | -0.05 to -0.10 | Below margin |
| candidate_third_ptcg_club | 0.70 | 14/20 | -0.05 to -0.10 | Below margin |
| candidate_shumpeinomura | 0.65 | 13/20 | -0.10 | Below margin |
| candidate_bluezlee | 0.55 | 11/20 | -0.15 to -0.25 | Below margin |
| candidate_btk15049 | 0.55-0.60 | 11-12/20 | -0.15 to -0.20 | Below margin |
| candidate_easonyanyan | 0.50-0.55 | 10-11/20 | -0.25 to -0.30 | Below margin |
| candidate_kashiwashira | 0.30 | 6/20 | -0.45 to -0.50 | Below margin |
| candidate_zoroark190 | 0.25-0.35 | 5-7/20 | -0.35 to -0.55 | Below margin |
| candidate_maher_el_ouahabi | 0.55 | 11/20 | -0.20 | Below margin |

Sources:
- analysis/u39_candidate_ring_scores.json (initial evaluation, n=20/arm)
- analysis/candidate_deck_ring_scores.json (trolley_baseline 0.80, trolley_delta computed)

### Selection Criteria

**Material margin threshold**: candidate must exceed trolley's ring baseline by >+0.05 (5 percentage points).
- Rationale: same-build noise model (M=240) uses aged reads; ring deltas <5pp are noise-dominated and unreliable predictors of ladder change.
- Pre-registration: state/current.md, heuristic+candidate_yushin_ito row, confirmed +0.100 delta over trolley.

**Winner**: candidate_yushin_ito (+0.100 delta, 18/20 vs trolley 15-16/20).

## Phase 3: Legality Audit (Complete)

candidate_yushin_ito:
- Team: Yushin Ito (48th rank on leaderboard at mining time)
- Deck legality: VERIFIED (analysis/candidate_yushin_ito_legality_audit.md)
- Pre-registration: 2026-07-04 (state/current.md)
- Ladder status: heuristic+candidate_yushin_ito (ref 54365656, settle-by 2026-07-18, within M=240 BAND)

## Why Only One Promotion?

The mining returned 49 unique deck signatures from 800+-rated teams. Of the 12 fully scored candidates:
1. Only 1 exceeded the +0.05 material-margin gate (yushin_ito, +0.10).
2. The runner-up (windecks) tied trolley exactly at the ring baseline (0.75), failing to clear margin.
3. All others fell below trolley.

**Interpretation**: The 800+ teams' deck building strategy (likely optimized for specific meta matchups during the competition window) does not generalize to novel opponent distributions in the ring. The ring's opponent pool consists of harvested bracket-ranked decks (450-750 rating band), not the champion-level strategies these candidates optimized for. yushin_ito is the exception: it generalizes materially better than the baseline.

## Remaining Unscored Candidates

Of the 49 unique mining signatures:
- ~12 were extracted and fully scored (u39_candidate_ring_scores.json, candidate_deck_ring_scores.json)
- ~37 remain unscored
- These are lower-ranked clusters by play count and lower likelihood of clearing the margin

**Decision**: Further scoring of remaining candidates is deferred pending post-Aug-16-convergence final-ladder-reading and a slot-availability review. Current ladder pair (ability + yushin_ito) is calibrated to ring gate; no new scoring cycle is warranted until the next slot opens (post-settlement).

## Deck Exploration Closure

**Queue item 4** (P2 directive, ring-scored novel deck candidates) is COMPLETE.
- Deduplication: 49 unique signatures mined, 12 ring-scored
- Selection: 1 candidate (yushin_ito) cleared material margin and promoted
- Legality: verified
- Pre-registration: filed (state/current.md)
- Ladder status: in flight (ref 54365656, settle-by 2026-07-18)

Next phase: await settlement (Jul 18) and external compute results (U110/U112, Jul 13) to determine slot availability for further deck exploration work.
