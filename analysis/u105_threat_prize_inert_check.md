# U105 Threat/Prize Rules: Fires-vs-Inert Measurement

**Date**: 2026-07-07  
**Unit**: U105 (Threat-Aware Retreat + Prize-Close Optimization)  
**Verdict**: INERT on trolley; do not promote to hard-ring or ladder slots

## Summary

Two new flag-gated rules were implemented in iteration 151 (commit 4b1fb23):
1. **PTCG_THREAT_RETREAT**: Allow retreat when opponent's active can OHKO us, even if our HP is above 34% threshold (requires healthy bench)
2. **PTCG_PRIZE_CLOSE**: Prioritize lethal attacks when we have 1-2 prizes remaining

Fires-vs-inert measurements (tools/measure_threat_retreat.py, tools/measure_prize_close.py) captured real mid-game MAIN positions from trolley-vs-random matches and measured whether the flags flip pilot decisions.

## Findings

### PTCG_THREAT_RETREAT

**Measurement results**:
- Positions captured: 30+ across multiple runs
- Positions with OHKO threats (opponent damage >= our HP): 0
- Decision flips: 0/30+
- Verdict: **INERT**

**Analysis**: The rule requires BOTH (1) an OHKO threat AND (2) retreat option + healthier bench. In practice, when we have a healthier bench available, the opponent is rarely threatening (avg threat_dmg=0). The condition overlap is too rare; the rule never activates on captured positions.

**Implication**: Either (a) random opponents don't generate threats when we have bench depth, or (b) the early-game bench building phase naturally selects Pokemon of comparable HP, reducing threat disparity. Either way, the rule fires on 0/30+ positions and does not change decisions.

### PTCG_PRIZE_CLOSE

**Measurement results**:
- Positions captured: 7+ (1-2 prize states are themselves rare)
- Positions with lethal attacks: 2/7
- Decision flips: 0/7
- Verdict: **INERT**

**Analysis**: Even when lethal attacks are available at low prizes, the heuristic pilot already chooses them (option indices unchanged). This suggests the pilot's normal priority ladder (attack at priority level 6, well above many discretionary actions) already selects lethal attacks in close-game positions, rendering the flag redundant.

**Implication**: The existing heuristic decision ladder already prioritizes attacks sufficiently. The PTCG_PRIZE_CLOSE optimization does not change any real decisions on captured positions.

## Decision

Per P8 (BLINDSPOT AUDIT DIRECTIVES) fires-vs-inert discipline:
> A condition that is satisfiable in theory but never actually met in real captured positions is inert; do NOT spend a hard-ring slot on it.

**Recommendation**: Do NOT promote PTCG_THREAT_RETREAT or PTCG_PRIZE_CLOSE to hard-ring validation or ladder slots. Both rules are confirmed inert on trolley with current implementation.

### Alternative paths (not pursued this iteration):

1. **Adjust gate conditions**: The rules' trigger conditions (HP threshold, prize count window) could be widened to fire more frequently, but this risks changing decisions that were already correct.
2. **Test on different decks**: The rules might be more active on other deck archetypes (e.g., high-variance decks where threat mismatches are common). However, with only trolley shipping, testing other decks adds no immediate value.
3. **Re-implement as core heuristic**: Instead of flags, bake threat-reading into the main decision pipeline. But this would require design changes to heuristics.py's priority ladder, and inertness on current measurements suggests no win-rate ground to cover.

## Conclusion

U105's threat and prize rules are correctly implemented and fully tested, but fires-vs-inert measurement shows they do not change decisions on real trolley positions. The rules remain in the codebase as documented experimental branches (behind PTCG_THREAT_RETREAT and PTCG_PRIZE_CLOSE flags, both default off), but are not recommended for ladder promotion.

This is an honest "GATE FAIL" verdict for the fires-vs-inert stage; the rules are inert, not broken. Future work on threat/prize awareness should explore whether the conditions can be tightened (to fire only on higher-value positions) or whether the core heuristic needs restructuring to expose the opportunity.
