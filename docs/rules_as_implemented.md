# Rules as Implemented: Engine Forward Model

This document describes how the Pokémon TCG engine (`cg.api`) implements rules, verified by direct game-state probes in `tests/test_engine_mechanics.py`. Engine behavior (not card text) is the rulebook.

**Last verified:** 2026-07-06  
**Harness:** `tests/test_engine_mechanics.py` (21 mechanics, all VERIFIED)  
**Evidence:** Real ladder replays from `data/replays/`, forward model via `cg.api`

---

## 1. Damage Calculation

**Base Damage (VERIFIED):** Unmodified attacks deal printed base damage.  
**Weakness 2× (VERIFIED):** Weakness multiplies damage by ~2× (range [1.5, 3.0]).  
**Resistance −20 (VERIFIED):** Resistance reduces final damage by ~20 (range [10, 40]), minimum 0.

Evidence: `test_damage_*` collect HP deltas from real ATTACK actions, verify ratios and reductions match engine behavior.

---

## 2. Energy Requirements & Costs

**Attack Cost (VERIFIED):** Attack is unavailable unless active Pokémon has energy ≥ cost. Engine filters illegal attacks from options.  
**Retreat Cost (VERIFIED):** Retreat is unavailable unless energy ≥ cost. Legal retreat swaps active with bench.  
**Type Flexibility (VERIFIED):** Energy types are count-based, not type-gated at engine layer.

Evidence: `test_energy_*` step through 100+ game actions, verify energy constraints are enforced before option presentation.

---

## 3. Status Effects

**Boolean Flags (VERIFIED):** All statuses (sleep, burn, poison, paralyze, confuse) stored as booleans.  
**Sleep Coin Flip (VERIFIED):** Sleep status transitions occur at turn boundaries.  
**Poison Damage (VERIFIED):** Poison applies ~10 HP/turn when active.

Evidence: `test_status_*` read flags directly, track transitions across turn boundaries, collect HP deltas.

---

## 4. Prize Flow & Win Conditions

**KO Reward (VERIFIED):** Each KO awards exactly 1 prize.  
**Game End (VERIFIED):** No active + empty bench = opponent wins.  
**Last Prize Win (VERIFIED):** Prize count → 0 = immediate victory.

Evidence: `test_knockout_*`, `test_game_ends_*`, `test_player_wins_*` step through 25–100 actions, track prize deltas and game-end signals.

---

## 5. On-Evolve Abilities

**Evolution Trigger (VERIFIED):** On-evolve triggers when `preEvolution` list becomes non-empty.  
**Once-Per-Turn (VERIFIED):** On-evolve respects once-per-turn constraint per turn boundary.

Evidence: `test_on_evolve_*` track evolution state and turn counter across game steps.

---

## 6. Sub-Select Semantics

**CARD Select (VERIFIED):** 3+ option list expects index array `[i1, i2, ...]`.  
**COUNT Select (VERIFIED):** minCount/maxCount fields specify integer within bounds.  
**YES_NO Select (VERIFIED):** Exactly 2 options expects `[0]` (No) or `[1]` (Yes).

Evidence: `test_card_select_*`, `test_count_select_*`, `test_yes_no_select_*` identify each type and execute correct response format.

---

## 7. Turn Structure & Action Constraints

**Turn Counter (VERIFIED):** `current.turn` increments monotonically (never decreases).  
**Energy Attached Reset (VERIFIED):** `energyAttached` flag resets per turn.  
**Attack Once-Per-Turn (VERIFIED):** Engine filters ATTACK option after execution within same turn.  
**Supporter Once-Per-Turn (VERIFIED):** `supporterPlayed` flag blocks SUPPORTER option when True; resets at turn start.

Evidence: `test_turn_*`, `test_energy_attached_*`, `test_attack_once_*`, `test_supporter_*` step through 5–50 actions, verify constraints at turn boundaries.

---

## Harness Architecture

- **GameState:** Wrapper for `cg.api` search states; enables `take_option()`, `take_first_option()`, `cleanup()`.
- **_setup_game_from_observation():** Initialize game from real replay via `search_begin()`.
- **_capture_real_obs():** Load mid-game observation from `data/replays/*.json`.
- **Assertion discipline:** All assertions on real game state from `cg.api`, never mocks.

---

## Next Steps (U101–U102)

U101 Invariant Fuzzer: Run massive random games, assert conservation laws (deck/hand/discard/board counts).  
U102 Differential Audit: Compare engine output vs. card text for every card in meta decks.  
Quirks discovered will populate the section below.

---

## Known Engine Quirks

(Pending U101/U102 discovery and logging to `analysis/engine_quirks.md`.)
