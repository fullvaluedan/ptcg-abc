# Legality Audit: Top 5 Mined Candidates (2026-07-07)

## Summary
**Status: ALL LEGAL**

The top 5 newly mined candidates pass all legality checks and are eligible for ring scoring and ladder testing.

## Candidates Validated

| Rank | Team | Play Count | Candidate Name | Status |
|---|---|---|---|---|
| 1 | THIRD PTCG Club | 19 | candidate_third_ptcg_club | LEGAL ✓ |
| 2 | disgruntled.coffee | 18 | candidate_disgruntled.coffee | LEGAL ✓ |
| 3 | XP3RiX | 12 | candidate_xp3rix | LEGAL ✓ |
| 4 | kenkoooo | 11 | candidate_kenkoooo | LEGAL ✓ |
| 5 | chamboabi | 10 | candidate_chamboabi | LEGAL ✓ |

## Validation Details

All candidates were validated using `tools/deck_validate.py` against:
- Deck size: 60 cards (required)
- Copy limit: Max 4 copies per non-energy card (basic energy exempt)
- ACE SPEC limit: At most 1 ACE SPEC per deck
- Engine validation: Official `cg.game.battle_start` compatibility check

All 5 decks passed every check.

## Deck Composition Summary

Each deck consists of 60 cards with valid PTCG composition:
- Mix of Pokemon, Trainer, and Energy cards
- Comply with all legality restrictions
- Ready for pilot testing through the calibrated bracket ring

## Next Steps

1. **Ring Scoring** (compute-heavy, external ptcgcompute job):
   - Score each candidate via `python tools/ring_calibrate.py` (heuristic pilot, n=40/arm)
   - Compare each win rate vs trolley's calibrated ring baseline (0.85)
   - Only candidates clearing trolley's rate by a material margin advance to ladder pre-registration

2. **Pre-registration** (upon ring gate success):
   - Add candidate to `state/current.md` under "Candidates awaiting a ladder slot"
   - Follow the pattern from `candidate_yushin_ito` row (ring-gated, noise model M, settle-by date)

3. **Tarball & Grader** (upon pre-registration):
   - Build: `python tools/build_submission.py agents/agent_heuristic.py decks/candidate_<name>.csv --out submission-<name>.tar.gz`
   - Grader test: `python -m pytest tests/test_grader_submission.py::test_grader_heuristic_<name> -v`

## Reference

- U39 deduplication: `analysis/mined_candidates_dedup_report.md`
- Legality precedent: `analysis/candidate_yushin_ito_legality_audit.md`
- Ring calibration: `analysis/ring_calibration.md` (tau 0.857, bracket opponents)
- Ring gate standard: `analysis/candidate_decks_ring_gate.md` (requires +0.100 delta over trolley baseline)

---

**Execution Date**: 2026-07-07  
**Tool**: `python tools/deck_validate.py`  
**Candidates Ready**: 5/5  
**Next Blocker**: Ring scoring job (external ptcgcompute)
