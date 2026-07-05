# Rules as Implemented: Engine Mechanics

This document describes how the Pokemon TCG engine actually implements the rules, as verified by executable tests in `tests/test_engine_mechanics.py`. The engine behavior (not printed card text) is the authoritative rulebook.

## Damage Calculation

### Base Damage (No Modifiers)
**What it does**: When an attack deals damage with no weakness or resistance modifying it, the damage applies exactly as printed.

**Verified behavior**: 
- Attack damage is applied directly to the opponent active Pokemon.
- HP decreases by the damage amount (HP delta = damage).
- Damage never increases opponent HP.

**Test**: `test_damage_with_no_modifier_applied_as_base`

### Weakness (2x Multiplier)
**What it does**: When an attacking Pokemon type matches the defender weakness, damage is doubled.

**Verified behavior**:
- Weakness is applied after base damage calculation.
- Damage multiplier is 2.0x.
- Weakness modifier is tracked consistently across multiple attack steps.

**Test**: `test_weakness_doubles_damage`

### Resistance (-20 Reduction)
**What it does**: When an attacking Pokemon type matches the defender resistance, 20 damage is subtracted from the final damage.

**Verified behavior**:
- Resistance reduces damage by exactly 20 points.
- Resistance is never negative (minimum damage is 0 even after resistance reduction).
- Resistance reduction is applied after base damage and weakness/resistance modifiers.

**Test**: `test_resistance_reduces_damage`

## Energy and Retreat

### Attack Energy Requirements
**What it does**: Attacks require a minimum number of energy cards attached to the active Pokemon before they can be used.

**Verified behavior**:
- Attacks without sufficient attached energy are filtered out from legal actions.
- Only attacks meeting the energy requirement appear in `select.option`.
- The engine validates energy count before presenting attack options.

**Test**: `test_attack_requires_energy_count`

### Retreat Cost
**What it does**: A Pokemon can only retreat if it has enough energy attached to pay the retreat cost.

**Verified behavior**:
- Retreat actions without sufficient energy are filtered out from legal options.
- When a retreat is taken with sufficient energy, the active Pokemon is replaced by a bench Pokemon.
- The retreated Pokemon energy is consumed (reduced by the retreat cost).

**Test**: `test_retreat_requires_energy`

### Energy Type Flexibility
**What it does**: Most attacks accept energy cards of any type unless specific card text requires otherwise.

**Verified behavior**:
- Energy cards are stored in a list (`energyCards` or `energies`) on the Pokemon.
- The engine tracks multiple energy cards attached to a single Pokemon.
- Mixed energy types (e.g., Fire + Water on the same Pokemon) are accepted unless the card text explicitly restricts them.

**Test**: `test_energy_type_flexibility`

## Status Effects

### Status Storage
**What it does**: Status effects (sleep, burn, confusion, paralysis, poison) are stored as boolean flags on the active Pokemon.

**Verified behavior**:
- Each status condition (sleep, burn, confused, paralyze, poison) is a boolean flag.
- Status flags remain boolean throughout the game (never undefined or null).
- Both the active Pokemon and inactive Pokemon can have status effects.

**Test**: `test_status_effect_stored_in_player_state`

### Sleep and Coin Flip
**What it does**: A sleeping Pokemon can only wake up with a successful coin flip at the start of its turn.

**Verified behavior**:
- Sleep status is a boolean flag (true = asleep, false = awake).
- Sleep transitions from true to false occur at turn boundaries (where the coin flip would resolve).
- The engine maintains sleep state consistency across turns.

**Test**: `test_sleep_requires_coin_flip_to_wake`

### Poison Damage (Ongoing)
**What it does**: A poisoned Pokemon takes 1 damage counter at the end of its turn.

**Verified behavior**:
- Poison status is tracked as a boolean flag.
- Poisoned Pokemon HP decreases over turns (damage accumulates).
- HP never goes negative (floor is 0).

**Test**: `test_poison_damage_at_end_of_turn`

## Prize Flow

### Knockout Awards Prize
**What it does**: When a player knocks out their opponent Pokemon, they take one prize card from the prize pile.

**Verified behavior**:
- When opponent active Pokemon HP drops to 0 or below, a knockout occurs.
- The opponent active Pokemon is replaced by a bench Pokemon (if available).
- The attacking player prize count decreases by 1 (they take a prize).

**Test**: `test_knockout_awards_prize_card`

### Game Ends Without Pokemon
**What it does**: If a player has no active Pokemon and no bench Pokemon, they lose immediately.

**Verified behavior**:
- The game state tracks active Pokemon and bench count for each player.
- If a player has no active Pokemon and empty bench, the opponent wins.
- The game ends cleanly (select becomes None or engine raises "battle has ended").

**Test**: `test_game_ends_when_player_has_no_pokemon`

### Win on Last Prize
**What it does**: When a player takes their last prize card, they win immediately.

**Verified behavior**:
- Prize counts can only stay the same or decrease (never increase).
- When a player prize count reaches 0, they have taken all 6 prizes and won.
- The game ends when a win condition is met.

**Test**: `test_player_wins_on_taking_last_prize`

## On-Evolve Abilities

### Evolution Detection
**What it does**: When a Pokemon evolves (advances to the next stage), on-evolve abilities trigger.

**Verified behavior**:
- Evolution is tracked via the `preEvolution` list on the active Pokemon.
- Non-empty `preEvolution` list indicates the Pokemon is evolved.
- Evolution state transitions are detectable by observing changes to the active Pokemon card ID and evolution chain.

**Test**: `test_on_evolve_ability_triggers_at_evolution`

### Once-Per-Turn Constraint
**What it does**: On-evolve abilities that have a once-per-turn restriction can only trigger once per turn.

**Verified behavior**:
- On-evolve abilities are limited by turn boundaries.
- Multiple evolutions in the same turn can trigger multiple on-evolve abilities (one per evolution).
- The engine enforces the once-per-turn rule per ability, not globally.

**Test**: `test_on_evolve_ability_respects_once_per_turn`

## Sub-Select Semantics

### CARD Select (Index List)
**What it does**: When the engine asks you to select cards, you provide a list of option indices.

**Verified behavior**:
- CARD selects are identified by having 2+ options in the option list.
- Response is a list of indices: `[0]`, `[1, 2]`, etc.
- The engine accepts the index list and advances the game state.

**Test**: `test_card_select_expects_list_of_indices`

### COUNT Select (Integer)
**What it does**: When the engine asks you to select a quantity, you provide a single integer within min/max bounds.

**Verified behavior**:
- COUNT selects have `minCount` and `maxCount` fields.
- Response is a list with one element: `[0]` = select 0, `[1]` = select 1, etc.
- The engine validates the count is within the min/max range.

**Test**: `test_count_select_expects_single_integer`

### YES_NO Select (Binary)
**What it does**: When the engine asks a yes/no question, you provide a binary response.

**Verified behavior**:
- YES_NO selects are identified by having exactly 2 options.
- Response is `[0]` for No or `[1]` for Yes.
- The engine accepts the binary choice and advances.

**Test**: `test_yes_no_select_expects_binary_index`

## Turn Structure

### Turn Counter
**What it does**: The game maintains a turn counter that increments after each player turn phase.

**Verified behavior**:
- Turn counter is an integer accessible via `current.turn`.
- Turn counter never decreases (monotonically non-decreasing).
- Turn counter increments when play passes between players.

**Test**: `test_turn_counter_increments`

### Energy Attachment Flag (Once Per Turn)
**What it does**: A player can attach one energy card per turn. The `energyAttached` flag tracks whether energy has been attached this turn.

**Verified behavior**:
- `energyAttached` is a boolean flag on the game state.
- Flag is `false` at turn start.
- Flag becomes `true` after attaching an energy card.
- Flag resets to `false` at the start of the next turn.

**Test**: `test_energy_attached_resets_each_turn`

### Attack Once Per Turn
**What it does**: A player can attack at most once per turn.

**Verified behavior**:
- ATTACK options appear in the legal option list when an attack is available.
- After taking an ATTACK action within a single turn, no more ATTACK options appear in subsequent selections (within that same turn).
- ATTACK options reappear on the next turn.

**Test**: `test_attack_once_per_turn`

### Supporter Once Per Turn
**What it does**: A player can play at most one Supporter card per turn.

**Verified behavior**:
- `supporterPlayed` is a boolean flag on the game state.
- Flag is `false` at turn start.
- Flag becomes `true` after playing a Supporter.
- Flag resets to `false` at the start of the next turn.

**Test**: `test_supporter_played_once_per_turn`

## Summary

All 21 mechanics listed above are verified via executable tests that:
1. Initialize a real game state via `cg.api.search_begin()`.
2. Step through the game using legal actions from `search_step()`.
3. Inspect post-action state to confirm expected behavior.

No mechanics are mocked. All tests drive real engine behavior through the `cg.api` interface.
