# Ring Scoring Job Specification: Top 5 Mined Candidates (2026-07-07)

## Overview
This job specification defines the parallel ring-scoring campaign for the 5 top mined candidates that passed legality validation. Execute via `ptcgcompute` pattern (plain Python via tmux) on a multi-core machine.

## Candidates to Score

| Rank | Candidate | Play Count | Target |
|---|---|---|---|
| 1 | candidate_third_ptcg_club | 19 | trolley baseline 0.85 |
| 2 | candidate_disgruntled.coffee | 18 | trolley baseline 0.85 |
| 3 | candidate_xp3rix | 12 | trolley baseline 0.85 |
| 4 | candidate_kenkoooo | 11 | trolley baseline 0.85 |
| 5 | candidate_chamboabi | 10 | trolley baseline 0.85 |

## Scoring Methodology

**Tool**: `python tools/ring_calibrate.py`  
**Ring**: Calibrated bracket ring (tau 0.857, analysis/ring_calibration.md)  
**Opponents**: 6-deck mix (bracket_1..6) from ~450–750 ladder rating band  
**Sample Size**: n=40 per arm (matches prior U104 protocol)  
**Pilot**: Heuristic agent (agents/agent_heuristic.py) vs standard heuristic on trolley

## Command Template

```bash
# Example: score candidate_third_ptcg_club
python tools/ring_calibrate.py \
  --seed 0 \
  --pilot agents/agent_heuristic.py \
  --deck decks/candidate_third_ptcg_club.csv \
  --opponents tools.ring_calibrate.ring_names() \
  --ring-matches 40 \
  --output-json analysis/ring_score_third_ptcg_club.json
```

Repeat for each candidate with unique `--deck`, `--seed`, and `--output-json`.

## Execution Strategy

1. **Parallel Execution**: Run all 5 candidates in parallel (20-core machine, 4 cores per candidate)
2. **Baseline Reference**: Include a trolley-baseline control run (seed 0) for same-run delta comparison
3. **Output Destination**: All `*.json` artifacts to `analysis/ring_score_*.json`
4. **Postprocessing**: After all runs complete, generate `analysis/ring_scoring_results_summary.md`

## Pass Criteria (from brief P2)

> "Only a candidate that clears trolley's ring win rate by a material margin is pre-registered for a TRACK L ladder A/B."

**Decision Rule**:
- **PASS**: candidate win rate >= (trolley win rate + 0.10) at same run (delta >= +10pp)
- **FAIL**: candidate win rate < (trolley win rate + 0.10)

Per U104 precedent, any candidate that passes this gate is immediately pre-registered in `state/current.md` and becomes ladder-eligible.

## Expected Timeline

- **Job Duration**: ~4–6 hours (5 candidates × 40 rings, 20-core parallel)
- **Completion Target**: 2026-07-08 (1 day turnaround for results)
- **Next Action**: If PASS on any candidate → pre-register in state/current.md; if FAIL on all → note in findings, continue U107/U102

## Reference

- U39 deduplication: `analysis/mined_candidates_dedup_report.md`
- Legality validation: `analysis/top_mined_candidates_legality_audit.md`
- Ring calibration: `analysis/ring_calibration.md` (tau 0.857)
- Prior precedent: `analysis/candidate_decks_ring_gate.md` (U104 protocol)
- Ring operator docs: `tools/ring_calibrate.py --help`

---

**Created**: 2026-07-07  
**Status**: Ready for ptcgcompute execution  
**Executor**: Plain Python via tmux (external to main loop)
