# U39 Deck Candidate Ring Scoring (2026-07-07)

## Methodology
Scored 11 candidate decks against the calibrated bracket ring (9 clones: bracket_1..6 + meta_archaludon + meta_grimmsnarl + meta_grimmsnarl_tonakaiiii), n=20 games/build, single fresh run.

Baseline: heuristic+trolley, 0.75 (15/20)
Promotion gate: delta >= +0.10 (half the discordant margin that existed in the passing ring calibration run)

## Results

| Candidate | Win Rate | Record | Delta | Verdict |
| --- | --- | --- | --- | --- |
| yushin_ito | 0.900 | 18/20 | +0.150 | **PROMOTE** |
| windecks | 0.750 | 15/20 | 0.000 | no promote |
| third_ptcg_club | 0.700 | 14/20 | -0.050 | no promote |
| shumpeinomura | 0.650 | 13/20 | -0.100 | no promote |
| nasuo445 | 0.650 | 13/20 | -0.100 | no promote |
| bluezlee | 0.550 | 11/20 | -0.200 | no promote |
| btk15049 | 0.550 | 11/20 | -0.200 | no promote |
| easonyanyan | 0.550 | 11/20 | -0.200 | no promote |
| maher_el_ouahabi | 0.550 | 11/20 | -0.200 | no promote |
| kashiwashira | 0.300 | 6/20 | -0.450 | no promote |
| zoroark190 | 0.250 | 5/20 | -0.500 | no promote |

## Key Findings

1. **Candidate_yushin_ito clears the promotion gate** with a +0.15 delta (18/20 vs 15/20). This is the only new candidate to beat trolley by a material margin.

2. **Windecks ties trolley** but does not cross the +0.10 threshold (0.00 delta exactly). With n=20 noise band around same-build readings (~52.0 ppn), a 0.00 delta is indistinguishable from trolley and does not merit a ladder slot.

3. **Majority of candidates perform below trolley** (8 of 11 show negative deltas). The cohort does not represent a hidden tier of top decks; mining by play count does not identify decks that beat trolley in isolation.

4. **Candidate_yushin_ito's performance aligns with team rank**: Yushin Ito is the #2 player on the current leaderboard (Ars Noveau #1, Yushin Ito #2 as of 2026-07-07 leaderboard), so a deck that beats trolley by +0.15 on the ring is consistent with a top-tier player.

## Pre-Registration

Candidate_yushin_ito (heuristic+trolley+yushin_ito):
- Hypothesis: The yushin_ito deck, piloted by our heuristic, beats the trolley deck.
- Offline gate: ring win rate 0.90 vs trolley 0.75, diff +0.15 (clears +0.10 threshold).
- Next: pre-register for a ladder slot once a slot becomes available (board currently frozen at 2 scored slots).

## Recommendation

Monitor the board for an available ladder slot. When M=60 noise margin allows (currently blocked by board freeze), submit heuristic+trolley-yushin_ito as per standard pre-registration protocol (settle-by date, N=30).
