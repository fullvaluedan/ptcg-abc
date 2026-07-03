# U93 step 2: gating the staged PTCG_ATTACK_FIRST lever through the calibrated clone ring

Plan: LOOP_BRIEF.md's U93 step 2 (attack-before-attach sequencing, built and confirmed LIVE in
U93 step 1, analysis/attack_first_flip_check.md). Per the calibrated ring's own re-gate
pattern (U74, analysis/ability_ring_check.md), score the staged attack_first-on vs
attack_first-off builds against the U81 bracket-band ring (tau 0.857,
analysis/ring_calibration.md) and require BOTH a >=+5pp ring margin AND directional agreement
with the offline weak-bot gauntlet (analysis/attack_first_ab.md) before this lever earns a
pre-registered ladder slot.

## Method

`tools/attack_first_ring_check.py`: heuristic + trolley deck, `_ATTACK_FIRST`
(agents/heuristics.py) forced on or off in-process (module constant is read once at import, so
the env var toggle used for the real submission build has no effect after import; monkeypatched
the same way `tools/ability_ring_check.py` patches `_ABILITY`), round-robin against every
`clone:<family>` opponent currently on disk (`tools.opponents.clone_family_names()`: the U81
bracket-band ring, bracket_1..6 plus meta_archaludon/meta_grimmsnarl/meta_grimmsnarl_tonakaiiii,
9 families), 20 games/arm.

## Result

| arm | wins | n | win rate |
| --- | --- | --- | --- |
| attack_first off | 15 | 20 | 75.0% |
| attack_first on | 17 | 20 | 85.0% |

diff_pp (on minus off) = +10.0. Gate (>= +5.0pp): PASS.

## Reproduce

```
python tools/attack_first_ring_check.py -n 20
```

## Reading

The ring's directional call (on beats off) agrees with the offline weak-bot gauntlet's
directional call (+5.5pp, analysis/attack_first_ab.md, off 71.5% vs on 77.0%, 200 games/arm).
Both offline signals point the same way as U91's mined finding (winners attach-before-attack
LESS than losers) and U93 step 1's confirmed-live flip check. As with the ability lever's ring
check, the ring's margin (+10.0pp at n=20/arm) is larger than the gauntlet's (+5.5pp at
n=200/arm); at this sample size that is consistent with either a genuinely bigger edge against
the bracket-band field specifically, or small-n noise on top of a real but smaller effect. This
is not a claim that the ring predicts the ladder's exact margin, only its direction, and both
gates (ring margin AND gauntlet-direction agreement) are satisfied per the U93 step 2 rule.

## Verdict

PASS on both required conditions (gauntlet must-not-regress + directional ring agreement at
>=+5pp). This unlocks a pre-registered ladder A/B for `heuristic+trolley-attack_first` per the
plan's gate; it does not itself move the ladder. Staged and pre-registered this iteration
(state/current.md); will submit the instant a ladder slot frees, per TRACK L priority.
