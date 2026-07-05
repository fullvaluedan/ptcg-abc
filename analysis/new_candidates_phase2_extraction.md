# New Deck Candidates Phase 2 Extraction (2026-07-06)

## Summary

Successfully extracted 5 new deck candidates from U39 top-rated mining using tools/select_new_deck_candidates.py. All candidates passed legality validation and are ready for scoring.

## Candidates Extracted

| Name | Play Count | Teams | Status |
|---|---|---|---|
| candidate_shumpeinomura | 145 | ShumpeiNomura | ✓ Ready for ring scoring |
| candidate_bluezlee | 107 | BluezLee | ✓ Ready for ring scoring |
| candidate_third_ptcg_club | 105 | THIRD PTCG Club | ✓ Ready for ring scoring |
| candidate_maher_el_ouahabi | 99 | Maher El-Ouahabi | ✓ Ready for ring scoring |
| candidate_kashiwashira | 80 | kashiwashira | ✓ Ready for ring scoring |

## Deduplication Results

- Clusters scanned: 43 unique signatures in top_rated_mining.md
- Duplicates found: 13 (these matched existing decks/meta_*.csv or decks/bracket_*.csv)
- New candidates: 5 (listed above, all passed legality validation)

## Blockers

Ring scoring (tools/score_candidate_decks.py) blocked by kaggle_environments module unavailability in Windows long-path environment. Requires human escalation to resolve dependency issue before scoring can proceed.

## Next Steps

1. [BLOCKED] Score each candidate through calibrated bracket ring (tau 0.857) vs trolley baseline (80.0%)
2. [BLOCKED] Apply gate: must clear baseline by material margin (+0.05pp minimum per protocol)
3. Pre-register any passing candidates for TRACK L ladder testing

Queue item 4 (U39 step 2) status: **DONE for extraction, BLOCKED on scoring**.

