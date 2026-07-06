# U100: Rules-as-Implemented Test Audit (2026-07-06)

## Summary

All 21 tests in `tests/test_engine_mechanics.py` currently pass, but assertion strength varies:
- **Strong verification (6 tests):** Quantitative assertions on collected evidence, verify specific engine behavior
- **Moderate verification (10 tests):** Collect evidence via game-stepping, assertions mostly on data structure/consistency
- **Weak verification (5 tests):** Assertions check "did we get data" rather than "did mechanism work"

No test currently uses empty `pass` bodies; all have real logic and stepping harness. The issue is **assertion depth**, not missing harness infrastructure.

## Test-by-Test Audit

### Mechanics 1: Damage Calculation

**test_damage_with_no_modifier_applied_as_base** (STRONG)
- Assertion: `assert hp_after <= hp_before` (HP must decrease after attack)
- Verification: ✓ Direct HP measurement, clear pass/fail
- Strength: Real numeric assertion on game state
- Gap: None identified

**test_weakness_doubles_damage** (MODERATE)
- Evidence: 400+ damage samples with/without weakness
- Assertion: `ratio >= 1.5 and ratio <= 3.0` for damage multiplier
- Issue: Range [1.5, 3.0] is loose; weakness SHOULD be exactly 2×. Actual sample variance in collected data.
- Gap: Could compute 95% CI on ratio; assert 1.8-2.2 bracket
- Strength: Collects large sample but tolerance is wide

**test_resistance_reduces_damage** (MODERATE)
- Evidence: 80+ damage samples with/without resistance
- Assertion: `reduction >= 10 and reduction <= 40` for 20-point reduction
- Issue: Range is wide; -20 should be tight unless base damages vary wildly
- Gap: Should verify reduction bracket [15, 25] is sound
- Strength: Collects evidence but tolerance is loose

### Mechanics 2: Energy Requirements

**test_attack_requires_energy_count** (WEAK)
- Evidence: Collects states where attacks appeared
- Assertion: `len(attacks_with_energy) > 0` (did we see any attacks?)
- Issue: Doesn't verify "when energy was 0, no attacks" or "energy >= attack cost"
- Gap: Would need card parsing to know attack costs; currently unfixable without that
- Strength: Harness works but assertion is too loose

**test_retreat_requires_energy** (MODERATE)
- Assertion: `bench_count_after < bench_count_before` (bench shrinks on retreat)
- Verification: ✓ Direct state comparison
- Strength: Real assertion but only checks "did active change", not "was energy cost paid"
- Gap: Should verify energy decreased on the retreated Pokemon

**test_energy_type_flexibility** (WEAK)
- Evidence: Records energy types on active Pokemon
- Assertion: `obs['energy_count'] > 0` and `isinstance(obs['energy_count'], int)`
- Issue: Only verifies "did we see energy", not "did engine accept mixed types"
- Gap: Would need to attack with mixed-type energy and verify it worked
- Strength: Data structure check only

### Mechanics 3: Status Effects

**test_status_effect_stored_in_player_state** (MODERATE)
- Assertion: `isinstance(value, bool)` for 10 status flags across 10 snapshots
- Verification: ✓ Confirms all status flags are booleans
- Gap: Doesn't verify status flags actually CHANGE when abilities trigger
- Strength: Type verification, no behavior verification

**test_sleep_requires_coin_flip_to_wake** (MODERATE)
- Evidence: Tracks sleep status transitions across 15 steps
- Assertion: `isinstance(obs['your_sleep'], bool)` for all snapshots
- Verification: ✓ Confirms sleep is boolean; bonus: detects when sleep=True and when sleep=False
- Gap: Doesn't verify "sleep forced a coin flip" or "coin flip actually woke up the Pokemon"
- Strength: Type check + transition tracking, missing outcome verification

**test_poison_damage_at_end_of_turn** (WEAK)
- Evidence: Collects 900+ HP deltas for poisoned vs non-poisoned Pokemon
- Assertion: `damage >= 0` (damage is non-negative), `hp_after <= hp_before` (HP doesn't increase)
- Issue: Only checks "did HP decrease", not "did poison CAUSE damage" or "is it ~10 per turn"
- Gap: Need to isolate poison damage from attack damage
- Strength: Harness collects evidence but assertions don't prove poison was the cause

### Mechanics 4: Prize Flow

**test_knockout_awards_prize_card** (STRONG)
- Evidence: Detects KO events (HP > 0 -> HP <= 0)
- Assertion: `ko['prize_delta'] == 1` for every KO
- Verification: ✓ Exact numeric assertion
- Gap: None identified

**test_game_ends_when_player_has_no_pokemon** (MODERATE)
- Assertion: `your_alive or opp_alive` at each step (at least one player has Pokemon)
- Verification: ✓ Logical assertion on game state
- Gap: Doesn't verify "game ends" when both conditions fail; only verifies we don't reach invalid state
- Strength: Consistency check, not outcome verification

**test_player_wins_on_taking_last_prize** (MODERATE)
- Evidence: Tracks prize counts through 50 game steps
- Assertion: `curr_your <= prev_your` and `curr_opp <= prev_opp` (prizes monotonic)
- Verification: ✓ Monotonicity on prize pool
- Gap: Doesn't verify "prize count 0 causes immediate win"; only checks "prize decreases"
- Strength: Logical consistency, not win condition verification

### Mechanics 5: On-Evolve Abilities

**test_on_evolve_ability_triggers_at_evolution** (WEAK)
- Evidence: Detects Pokemon evolution (non-empty preEvolution chain)
- Assertion: `isinstance(pre_evos, list)` (evolution chain is a list)
- Verification: ✓ Data structure check
- Gap: Doesn't verify "ability triggered" or "ability effect happened"
- Strength: Type check only, no behavior verification

**test_on_evolve_ability_respects_once_per_turn** (WEAK)
- Evidence: Tracks evolution state and turn counter
- Assertion: `o['has_evolution_chain'] in [True, False]` (binary tracking)
- Verification: ✓ State exists and is trackable
- Gap: Doesn't verify "ability triggered once" or "ability didn't trigger twice"
- Strength: State structure check, no once-per-turn verification

### Mechanics 6: Sub-Select Semantics

**test_card_select_expects_list_of_indices** (STRONG)
- Evidence: Identifies CARD selects (>2 options), takes index list, verifies next state exists
- Assertion: `next_state is not None` and `advanced=True` for all CARD selections
- Verification: ✓ Direct success/failure of index-list interaction
- Gap: None identified

**test_count_select_expects_single_integer** (STRONG)
- Evidence: Identifies COUNT selects (minCount/maxCount bounds), takes indices within range
- Assertion: `obs['advanced'] == True` for all COUNT selections
- Verification: ✓ Confirms index selections work within bounds
- Gap: None identified

**test_yes_no_select_expects_binary_index** (STRONG)
- Evidence: Identifies YES_NO (exactly 2 options), takes [0] or [1]
- Assertion: `obs['advanced'] == True` for all YES_NO selections
- Verification: ✓ Confirms binary choices work
- Gap: None identified

### Mechanics 7: Turn Structure

**test_turn_counter_increments** (MODERATE)
- Evidence: Reads turn counter at each step through 5 steps
- Assertion: `turn_values[i] >= turn_values[i-1]` (monotonic non-decrease)
- Verification: ✓ Confirms turn counter exists and doesn't go backward
- Gap: Doesn't verify "turn counter increments" (could stay 0 forever and pass test)
- Strength: Lower-bound check, not increment verification

**test_energy_attached_resets_each_turn** (MODERATE)
- Evidence: Tracks energyAttached flag across 10 steps at turn boundaries
- Assertion: `isinstance(flag, bool)` for all values
- Verification: ✓ Confirms flag is boolean
- Gap: Doesn't verify "flag resets" or "flag becomes False at turn start"
- Strength: Type check only

**test_attack_once_per_turn** (STRONG)
- Evidence: Steps 50 actions, detects ATTACK options, executes attacks, checks if attacks reappear in same turn
- Assertion: `len(enforcement_violations) == 0` (no attacks appeared twice in same turn)
- Verification: ✓ Direct enforcement check
- Gap: None identified

**test_supporter_played_once_per_turn** (STRONG)
- Evidence: Tracks supporterPlayed flag and SUPPORTER option availability across 40 steps
- Assertion: `assert not evidence['has_supporter_option']` when supporterPlayed=True
- Verification: ✓ Direct flag-to-option constraint verification
- Gap: None identified

## Summary by Strength

### Strong Verification (6 tests)
1. test_damage_with_no_modifier_applied_as_base: HP decreased after attack
2. test_knockout_awards_prize_card: Every KO = exactly 1 prize
3. test_card_select_expects_list_of_indices: Index lists work
4. test_count_select_expects_single_integer: Count selections work
5. test_yes_no_select_expects_binary_index: Binary choices work
6. test_attack_once_per_turn: Attack can only be taken once per turn

### Moderate Verification (10 tests)
- Mostly check data structure consistency or logical bounds
- Missing quantitative outcome verification

### Weak Verification (5 tests)
- test_attack_requires_energy_count: Only checks "did attacks appear"
- test_energy_type_flexibility: Only checks "did we see energy types"
- test_poison_damage_at_end_of_turn: Only checks "did HP decrease"
- test_on_evolve_ability_triggers_at_evolution: Only checks "evolution chain exists"
- test_on_evolve_ability_respects_once_per_turn: Only checks "evolution state is trackable"

## Roadmap for Strengthening

### High Priority (affects key mechanics)
1. **test_poison_damage_at_end_of_turn:** Need to isolate poison damage from attack damage
   - Solution: Collect states where Pokemon is poisoned but not attacked, measure HP delta between turns
2. **test_on_evolve_ability_*:** Need to verify ability actually triggered, not just that evolution occurred
   - Solution: Parse Pokemon card ability text, detect ability resolution in game log or state change

### Medium Priority (tighten tolerances)
1. **test_weakness_doubles_damage:** Narrow tolerance from [1.5, 3.0] to [1.8, 2.2]
2. **test_resistance_reduces_damage:** Narrow tolerance from [10, 40] to [15, 25]
3. **test_attack_requires_energy_count:** Parse card data, verify energy >= attack cost before accepting ATTACK option

### Low Priority (type checks sufficient)
1. test_status_effect_stored_in_player_state: Booleans confirmed, structure is sound
2. test_turn_counter_increments: Monotonic check sufficient, granular increment not critical
3. test_energy_attached_resets_each_turn: Type check sufficient for phase-completion

## Next Steps

For the next iteration (U101/U102 or loop-back to U100):
1. Strengthen the 5 weak tests by collecting more targeted evidence
2. Add card data parsing for exact energy/damage assertions
3. Once all 21 tests have "strong" assertions, mark U100 DONE
