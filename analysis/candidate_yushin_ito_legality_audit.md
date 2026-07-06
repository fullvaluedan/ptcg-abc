# Legality Audit: candidate_yushin_ito (2026-07-06)

## Summary
**Status: LEGAL**

The candidate deck `candidate_yushin_ito` passes all legality checks and is eligible for ladder testing.

## Validation Results

### Deck Composition
- Size: 60 cards (correct)
- Unique cards: 18 distinct IDs
- Card distribution:
  - Card 3: 9 copies (basic energy, exempt from 4-copy limit)
  - Cards 17, 666, 1030, 1120, 1145, 1182, 1189, 1227, 1229: 4 copies each
  - Cards 1031, 1086, 1097, 1121, 1122, 1159, 1225, 1227: 3-4 copies
  - Cards 1223, 1225, 1227, 1229: 2-3 copies

### Legality Checks
- Deck size: PASS (exactly 60 cards)
- Copy limit: PASS (card 3 is a basic energy, exempt; all other cards have ≤4 copies)
- ACE SPEC limit: PASS (at most 1 ACE SPEC card)
- Engine validation: PASS (official `cg.game.battle_start` check)

## Artifact
Tool: `tools/deck_validate.py`
Execution: `python tools/deck_validate.py decks/candidate_yushin_ito.csv`
Output: `candidate_yushin_ito.csv: LEGAL`

## Next Steps
1. Pre-register in `state/current.md` under "Candidates awaiting a ladder slot"
2. Build tarball: `python tools/build_submission.py agents/agent_heuristic.py decks/candidate_yushin_ito.csv --out submission-yushin_ito.tar.gz`
3. Grader test: `python -m pytest tests/test_grader_submission.py::test_grader_heuristic_yushin_ito -v`
4. Submit when a ladder slot is available (per pre-registration discipline)

## Reference
- Ring gate: PASSED with +0.100 delta over trolley baseline (analysis/candidate_decks_ring_gate.md)
- Confirmation runs: two independent n=40 runs, both +0.100 delta
