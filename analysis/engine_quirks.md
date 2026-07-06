# Engine Invariant Fuzzer Report (U101)

**Status**: Tool implemented, game harness initialization needs investigation.

**Date**: 2026-07-06

**Finding**: The invariant fuzzer tool (`tools/invariant_fuzzer.py`) is structurally complete with all five required invariant checks built (HP bounds, prize bounds, turn counter, card conservation, energy flags). However, the game initialization path (`_setup_fresh_game`) inherited from the test harness is raising an error when called outside the pytest context, suggesting the harness has a dependency on test-time setup that is not self-contained.

## Invariant checks implemented

1. **HP bounds**: 0 <= HP <= maxHP for all active and bench Pokemon
2. **Prize bounds**: 0 <= prize_count <= 6, no decrements except via knockout resolution
3. **Turn counter**: Non-negative integer, increments once per full turn cycle
4. **Card conservation**: Total cards across deck/hand/discard/bench/active/prizes conserved
5. **Energy flags**: attached + attached_this_turn consistency checks

## Diagnosis

The test harness at `tests/test_engine_mechanics.py::_setup_fresh_game` uses `to_observation_class()` to construct an Observation object from a minimal dict skeleton. When called from `tools/invariant_fuzzer.py`, this fails with:

```
AttributeError: 'int' object has no attribute 'items'
```

This occurs in `cg.utils.to_dataclass()`, which tries to recursively convert the minimal obs dict into the Observation dataclass, but fails when it encounters the prize list's integer card IDs (which it tries to treat as dicts).

The same `_setup_fresh_game` function passes in pytest (confirmed: `pytest tests/test_engine_mechanics.py::test_damage_with_no_modifier_applied_as_base PASSED`), suggesting pytest does some initialization that makes the harness work. The error is not in the tool logic but in the shared game-setup infrastructure.

## Next steps

1. Investigate what pytest or conftest.py sets up that enables to_observation_class() to work
2. Either port that setup into the tool, or rewrite game initialization directly via search_begin without the to_observation_class intermediate
3. Run the fuzzer on 50-100 games and log any violations found

## No violations found yet

The tool is ready to run once the initialization path is unblocked. No quirks in the engine have been discovered at this stage because no games have executed successfully.
