# PTCG_ABILITY offline gauntlet (L1 prep, no ladder slot)

Prep step for the RESUME STATE's L1 ladder lever: the pilot agrees with top players on
0/554 real ABILITY decisions with the flag off (analysis/move_ranking_diverges_ability_gap.md).
A loop-safe once-per-turn ability guard already exists (agents/heuristics.py's
`_is_once_per_turn_ability`, gated behind `_ABILITY = os.environ.get("PTCG_ABILITY", "0") != "0"`,
default off). Before this spends a ladder slot it must clear a must-not-regress offline gauntlet
and carry a complete pre-registration, per the plan's L1 action.

## Build

`tools/build_submission.py --agent agents/agent_heuristic.py --deck decks/trolley.csv --extra
agents/heuristics.py --env PTCG_ABILITY=1 --out submission_trolley_ability.tar.gz`

Baked lever flags: `{'PTCG_ABILITY': '1'}`. Linux engine lib present. Grader
exec-without-`__file__` load verified green (`tests/test_grader_submission.py
[heuristic-trolley-ability]`, added this iteration alongside the existing
heuristic/heuristic-trolley/heuristic-trolley_thick/search/search-trolley cases).

## Gauntlet (must-not-regress check)

`deck:trolley` (the shipped agent+deck combo) vs the standard 8-deck opponent pool
(`deck:meta_archaludon deck:meta_grimmsnarl deck:meta_grimmsnarl_tonakaiiii deck:aggro
deck:control deck:ultraball deck:trolley deck:trolley_thick`), 200 games/arm via
`tools.parallel_gauntlet.run_parallel_gauntlet` with `PTCG_ABILITY` baked into each shard's
env (raw counts in `analysis/ability_ab.json`):

| arm | wins | losses | win rate |
| --- | --- | --- | --- |
| off (PTCG_ABILITY=0, shipped default) | 135 | 65 | 67.5% |
| on (PTCG_ABILITY=1) | 143 | 57 | 71.5% |

diff_pp (on minus off) = +4.0. No regression; ability-on is directionally better offline,
consistent with the ability lever closing a real 0/554 blind spot rather than introducing risk.
0 invalid moves in either arm. Gate: PASS, clears the "must not regress" bar for L1.

## Ladder pre-registration

Registered via `tools/loop_state.py prereg` against the trolley king (state/current.md), direction
up, M=60 (v1 noise model), N=30, settle-by 2026-07-08 (a placeholder 6 days out; the real settle
clock starts once this build actually spends a slot, which requires L2 to free one first per the
RESUME STATE priority order). Build name: `heuristic+trolley-ability`.

## Status

NOT submitted this iteration: both ladder slots are occupied (slot 1 the trolley king, slot 2 the
in-flight trolley_thick A/B, <24h old, not yet eligible to settle). This build is now fully
staged (tarball built, grader-verified, offline gauntlet clean, pre-registered) so it can submit
the instant L2 frees a slot, per the plan's "prep L1 even while slots are full" instruction.
