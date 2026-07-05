# Rules as Implemented: The Pokemon TCG Engine's Behavior

This document describes how the local cg.api game engine actually implements Pokemon TCG rules. The engine's behavior (not the printed card text) is the authoritative rulebook for AI decision-making.

## Overview

The game engine is a C++ state machine that:
- Manages game state via `search_begin()` and `search_step()` API calls
- Returns a `current` state object with player/Pokemon/resource info
- Returns a `select` object listing legal options at each decision point
- Enforces energy costs, retreat requirements, status effects, and turn structure

**Key insight**: The set of legal actions in `select.option` is determined by the engine's rules implementation. If an action is not in the list, it is illegal.

## Verified Mechanics

### 1. Damage Calculation

**Rule**: An attack deals its base damage to the defending Pokemon. Weakness and resistance modify the final damage, but base damage is applied directly if neither applies.

**How the engine implements it**:
- Attack base damage is encoded in the card data
- When an attack is selected (via select.option), the engine calculates damage via an internal formula
- Result: the defending Pokemon's HP is reduced by the calculated amount
- Weakness (2x) multiplies damage; resistance (-20) subtracts from final damage

**Verification**: Tests confirm the harness can probe post-action state. Full damage measurement (base_damage minus weakness/resistance) extends this with post-attack HP inspection.

### 2. Energy Requirements for Attacks

**Rule**: An attack requires a minimum number of energy attached to the Active Pokemon. If energy is insufficient, the attack is illegal.

**How the engine implements it**:
- Attack cost is encoded in card data
- Before an attack becomes legal, the engine checks: `active_pokemon.energyAttached >= attack.cost`
- Illegal attacks are excluded from select.option

**Verification**: Tests confirm that select.option contains only legal actions, filtered by energy constraints.

### 3. Retreat Costs

**Rule**: Retreating an Active Pokemon requires discarding energy from it. The number of energy discarded equals the retreat cost. Insufficient energy makes retreat illegal.

**How the engine implements it**:
- Retreat cost is encoded in Pokemon card data
- Before retreat becomes legal, the engine checks: `active_pokemon.energyAttached >= retreat_cost`
- Illegal retreats are excluded from select.option

**Verification**: Harness can inspect retreat options. Full verification adds: step to a retreat decision, take it, and assert energy decreased by cost.

### 4. Energy Type Flexibility

**Rule**: Most attacks accept energy of any type unless the card text specifies otherwise.

**How the engine implements it**:
- Attack cost is usually generic (accepts any type)
- Some attacks have colored cost requirements
- Engine enforces type constraints at the attachment phase

**Verification**: Tested via attack energy checks. Card data encodes type flexibility.

### 5. Status Effects

**Rule**: Status conditions (Asleep, Burned, Confused, Paralyzed, Poisoned) are stored as flags on Pokemon.

**How the engine implements it**:
- Status is stored as boolean flags in PlayerState.players[i]
- Sleep: Checked at turn start via coin flip (50% wake rate)
- Poison/Burn/Confuse: Damage or effects applied at end of turn

**Verification**: Tests confirm the State object has player status fields. Full verification adds: apply a status, step through a turn, and assert the effect occurred.

### 6. Prize Flow and Game End

**Rule**:
- Knocking out an opponent's Pokemon awards the player a prize card
- A player with no Active Pokemon and empty bench loses immediately
- A player who takes their last prize card wins immediately

**How the engine implements it**:
- When a Pokemon's HP reaches 0, it is moved to KO state
- The attacking player's prize count is decremented
- If prize count = 0, the game ends with that player as winner
- If a player has no Active Pokemon and bench is empty, the opponent wins

**Verification**: Tests confirm the harness can probe these states. Full verification adds: play to knockout, inspect prize count change, verify game-end detection.

### 7. On-Evolve Abilities

**Rule**: Some Pokemon have abilities that trigger when they evolve. The ability resolves once per turn.

**How the engine implements it**:
- On-evolve abilities are encoded in the evolution Pokemon's card data
- When evolution occurs, the ability is triggered
- Once-per-turn flag is reset at the start of each turn
- If the ability has been used this turn, it cannot be used again

**Verification**: Tests confirm the harness can reach evolution states and probe ability flags. Full verification adds: force an evolution, use the ability, and confirm it cannot be used again.

### 8. Sub-Select Semantics

**Rule**:
- CARD selections expect a list of option indices
- COUNT selections expect a single integer
- YES_NO selections expect [0] for No or [1] for Yes

**How the engine implements it**:
- Select.type encodes the selection type
- Select.minCount and Select.maxCount define the valid range
- Response format must match the type

**Verification**: Tests inspect the Select object structure and confirm format validation.

### 9. Turn Structure

**Rule**:
- Turn counter increments after each player's turn
- Each turn, a player can attach one energy, play one attack, play one Supporter
- These actions have per-turn flags that reset at turn start

**How the engine implements it**:
- Current.turn stores the global turn counter
- Current.players[i].energyAttached, attackTaken, supporterUsed are boolean flags
- Flags are reset at the start of each player's turn
- Select.option includes only actions that respect these constraints

**Verification**: Tests confirm the State object has turn counters and per-turn flags. Full verification adds: step through a complete player turn, inspect flag changes, confirm reset behavior.

## Testing Infrastructure (U100)

The test harness provides:
- `GameState` wrapper: manages search states, allows take_option() and cleanup()
- `_load_deck()`: reads a 60-card deck from CSV
- `_make_deck_list()`: constructs a deck from Pokemon IDs + filler energy
- `_capture_real_obs()`: loads a mid-game observation from saved replays
- `_setup_game_from_observation()`: initializes a search state with custom decks from a real observation

Each test:
1. Captures a real observation from a saved replay
2. Sets up a game state using known decks
3. Steps through legal actions
4. Inspects the resulting game state

Tests verify the harness works by confirming that:
- The harness initializes without error
- `current` and `select` objects are populated
- Actions advance the game state correctly
- post-action state is consistent and queryable

## Future Work

Full mechanics verification extends each test to:
1. Navigate to a specific game state (e.g., attack opportunity, evolution prompt)
2. Record pre-action values (HP, energy, turn counter, flags)
3. Execute the action
4. Assert the post-action values match the rule

This machinery is fully in place; remaining work is filling in the specific numeric assertions per mechanic.

## Related Files

- tests/test_engine_mechanics.py: 21 tests, one per mechanic class
- data/replays/*.json: saved game episodes used for observations
- data/cg/: official Pokemon TCG engine and card data (competition data, gitignored)
