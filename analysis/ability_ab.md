# PTCG_ABILITY offline gauntlet (L1 prep, no ladder slot)

Prep step for the RESUME STATE's L1 ladder lever: the pilot agrees with top players on
0/554 real ABILITY decisions with the flag off (analysis/move_ranking_diverges_ability_gap.md).
A loop-safe once-per-turn ability guard already exists (agents/heuristics.py's
`_is_once_per_turn_ability`, gated behind `_ABILITY = os.environ.get("PTCG_ABILITY", "0") != "0"`,
default off). Before this spends a ladder slot it must clear a must-not-regress offline gauntlet
and carry a complete pre-registration, per the plan's L1 action.

## Build

`tools/build_submission.py --agent agents/agent_heuristic.py --deck decks/trolley.csv --extra
agents/heuristics.py --extra agents/card_effects.py --env PTCG_ABILITY=1 --out
submission_trolley_ability.tar.gz`

Baked lever flags: `{'PTCG_ABILITY': '1'}`. Linux engine lib present. Grader
exec-without-`__file__` load verified green (`tests/test_grader_submission.py
[heuristic-trolley-ability]`, added this iteration alongside the existing
heuristic/heuristic-trolley/heuristic-trolley_thick/search/search-trolley cases).

**2026-07-03 correction:** the command above originally omitted `--extra
agents/card_effects.py`. Since U33 (2e18145), `agents/heuristics.py` imports
`card_effects` unconditionally at module load, so a tarball missing it fails to
import under the grader's exec-without-`__file__` path and the whole submission
is marked ERROR (the same failure class as the original `__file__` bug this
test suite exists to catch). The test file's own `_HEUR_EXTRAS` list
(`tests/test_grader_submission.py`) already included both files and built its
own in-memory tarball via `bs.build()` directly, so the local grader-emulation
test passed even though the real uploaded tarball, built by hand-running this
now-corrected command, did not carry `card_effects.py` and ERRORed for real on
the ladder (ref 54281824). Lesson: a test that re-derives its own tarball
in-process does not catch a stale/hand-typed CLI invocation used for the real
submission; keep the two in sync, or have the real build shell out to the same
extras list the test uses.

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

**2026-07-03 update:** submitted (ref 54281824) once L2 freed a slot -- but built from the stale
CLI command above (missing `--extra agents/card_effects.py`), so it ERRORed on the grader and
never played a single episode (see the correction under Build). Root-caused and rebuilt correctly
this iteration; verified both via the grader-emulation test and a direct extracted-tarball
`env.run` (reward=1, status=DONE, 25 steps, real gameplay). Resubmitted as ref 54282097; a
king-copy cleanup resubmission (ref 54282104) followed immediately to evict the dead ERRORed ref
54281824 from the tracked latest-2 scoring window (analysis/final_scoring_semantics.md). Fresh
pre-registration: direction up, M=60, N=30, settle-by 2026-07-08 (the earlier settle clock never
validly started, since the ERRORed build could not play episodes). Both resubmissions read
COMPLETE on the first board check: king copy 691.5, ability build 536.7 (both first readings, not
settled). The new regression test `tests/test_grader_submission.py::test_extras_cover_flat_layout_
imports` also caught the SAME missing-extras bug class already present in `_SEARCH_EXTRAS` for the
(non-shipped) search agent (features.py, imitation_features.py, learned_eval.py, move_prior.py all
missing); fixed alongside this unit since it was already found by the new test.
