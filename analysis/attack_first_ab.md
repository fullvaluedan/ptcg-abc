# PTCG_ATTACK_FIRST offline gauntlet (U93 step 2, no ladder slot)

Prep step for the LOOP_BRIEF's U93 step 2 gate: before the attack-before-attach sequencing
lever (`agents/heuristics.py`'s `_resolve_attack_first`, gated behind `PTCG_ATTACK_FIRST`,
default off) can spend a ladder slot it must clear the same two-gate discipline as the L1
ability lever (analysis/ability_ab.md): a must-not-regress offline weak-bot gauntlet, and a
bracket-ring A/B (analysis/attack_first_ring_check.md) agreeing in direction.

## Build

`tools/build_submission.py --agent agents/agent_heuristic.py --deck decks/trolley.csv --extra
agents/heuristics.py --extra agents/card_effects.py --env PTCG_ATTACK_FIRST=1 --out
submission_trolley_attack_first.tar.gz`

Baked lever flags: `{'PTCG_ATTACK_FIRST': '1'}`. Linux engine lib present. Grader
exec-without-`__file__` load verified green (`tests/test_grader_submission.py
[heuristic-trolley-attack_first]`, added this iteration alongside the existing
heuristic-trolley-ability case; both the in-process build test and the
extracted-tarball `env.run` case cover this build, closing the exact gap the L1
ERROR (ref 54281824) exposed).

## Gauntlet (must-not-regress check)

`deck:trolley` (the shipped agent+deck combo) vs the standard 8-deck opponent pool
(`deck:meta_archaludon deck:meta_grimmsnarl deck:meta_grimmsnarl_tonakaiiii deck:aggro
deck:control deck:ultraball deck:trolley deck:trolley_thick`), 200 games/arm via
`tools/run_ab.py --flag PTCG_ATTACK_FIRST` (which fans out through
`tools.parallel_gauntlet.run_parallel_gauntlet`, raw counts in `analysis/attack_first_ab.json`):

| arm | wins | losses | win rate |
| --- | --- | --- | --- |
| off (PTCG_ATTACK_FIRST=0, shipped default) | 143 | 57 | 71.5% |
| on (PTCG_ATTACK_FIRST=1) | 154 | 46 | 77.0% |

diff_pp (on minus off) = +5.5. No regression; attack-first is directionally better offline,
consistent with U91's mined finding that the shipped pilot over-attaches relative to both
winners and losers in the top-player corpus. 0 invalid moves in either arm. Gate: PASS
(clears run_ab.py's own +4.0pp bar and the plan's "must not regress" bar).

## Reproduce

```
python -m tools.run_ab deck:trolley deck:meta_archaludon deck:meta_grimmsnarl \
    deck:meta_grimmsnarl_tonakaiiii deck:aggro deck:control deck:ultraball deck:trolley \
    deck:trolley_thick -n 200 --flag PTCG_ATTACK_FIRST -o analysis/attack_first_ab.json
```

## Status

NOT submitted this iteration: both ladder slots are occupied (the trolley king copy and the
in-flight L1 ability A/B, settle-by 2026-07-08, neither eligible to settle yet). This build is
now fully staged (tarball built, grader-verified via both the in-process and extracted-tarball
paths, offline gauntlet clean, bracket-ring A/B clean at +10.0pp
(analysis/attack_first_ring_check.md), pre-registered) so it can submit the instant a slot
frees, per the plan's "prep even while slots are full" instruction.
