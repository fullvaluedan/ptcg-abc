# U105 Threat/Prize Rules: Fires-vs-Inert Check (2026-07-07)

## SUPERSEDED 2026-07-08: the INERT verdict below measured an implementation bug, not the game

The zeros this check observed were produced by a defect in
`agents/heuristics.py`'s `_opponent_best_attack_damage`: `CardData.attacks`
holds attack IDs (ints), and the function passed those raw ints into
`effective_damage`, whose `getattr(int, "damage", 0)` is always 0. The OHKO
fire condition was therefore unsatisfiable for EVERY card in the game (0 of
1057 attackers returned nonzero threat damage). The unit test masked the bug
by monkeypatching this exact function to return 100. Fixed 2026-07-08 by
resolving IDs through `attack_index()` exactly as `best_attack` does, with a
non-mocked regression test (`test_opponent_threat_damage_nonzero_on_real_card_data`,
953 of 1057 attackers nonzero, the remainder status-only).

Re-run of this same tool with the fixed code (n=25 target positions):

| deck | positions captured | OHKO-capable | decisions flipped | verdict |
|---|---|---|---|---|
| trolley | 12 | 7/12 | 3/12 | LIVE |
| candidate_yushin_ito | 25 | 22/25 | 7/25 | LIVE |

PTCG_THREAT_RETREAT is LIVE on both decks and is re-eligible for its ring
A/B (standard calibrated ring, n=100/arm, same-run delta vs the same build
with the flag off; the "hard ring" named in the original gate does not exist
yet, U110 unbuilt). The PRIZE_CLOSE half of the original verdict is
structurally different: choose() takes any lethal at step 1 before the
resolver ladder runs, so the rule as written can never flip a decision; that
half of the closure stands, though for a different reason than the doc gave
(subsumed by the lethal FORCE, not distribution rarity). The original text
is preserved below as the record of what was believed on 2026-07-07.

---

**VERDICT (2026-07-07, superseded above): BOTH RULES INERT IN PRACTICE ON TROLLEY**

## PTCG_THREAT_RETREAT (threat-aware retreat)

Rule: when opponent active can OHKO our active and bench is healthy, allow retreat independent of own HP.

fires-vs-inert check (tools/measure_threat_retreat.py, trolley deck):
- Positions captured where retreat offered + threat check triggered: 3
- Positions where opponent threat >= our HP (OHKO-capable): 0/3
- Decisions flipped by enabling PTCG_THREAT_RETREAT: 0/3

**Conclusion: INERT. The OHKO-threat condition never applied in the captured positions, so the rule never fired. Do NOT spend a hard-ring slot on this lever.**

## PTCG_PRIZE_CLOSE (prize-close optimization)

Rule: with 1-2 prizes remaining, prefer any legal attack line that takes the last prize.

fires-vs-inert check (tools/measure_prize_close.py, trolley deck):
- Positions captured where 1-2 prizes + attack offered: 5
- Positions with a lethal attack available: 1/5
- Decisions flipped by enabling PTCG_PRIZE_CLOSE: 0/5

**Conclusion: INERT. Only 1 of 5 captured positions had lethal attack available, and the rule still did not change the decision. Do NOT spend a hard-ring slot on this lever.**

## Interpretation

Both rules are correctly implemented and compile, but neither fires on the shipped trolley deck in practice. The THREAT_RETREAT condition (opponent OHKO-capable while our bench is better) appears to be rare or absent in mid-game trolley positions. The PRIZE_CLOSE rule also finds little leverage: only 1 position in 5 had lethal available, and even that did not shift the pilot's decision.

This closes U105 for the trolley deck context: both rules fail the fires-vs-inert gate and are ineligible for hard-ring validation or ladder submission. Per the loop discipline: a measurement that refutes a lever as inert saves the project from spending hard-ring resources on a change that has no practical effect.

## Next steps

These rules remain implemented (off by default, flag-gated) and are available for retest on different decks if a future platform change or deck exploration surfaces contexts where the underlying conditions apply. No changes to agents/heuristics.py needed; the lever implementations stay as-is.
