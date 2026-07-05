# Rules As Implemented

**The engine's actual behavior is the real rulebook.** This document explains how the Pokemon TCG AI Battle Challenge engine interprets the game rules, based on probing the `cg.api` forward model.

This is distinct from the printed card text or the official Pokemon TCG rulebook. When the engine's behavior differs from the card text, **the engine's behavior is what matters for our agent**.

## Damage Calculation

### Base Mechanic

- An attack specifies base damage (e.g., 40, 60, 120).
- The engine calculates final damage as: **base damage, then apply weakness/resistance**.

### Weakness

- Most Pokemon have a weakness type (e.g., a Water Pokemon has weakness x2 to Lightning).
- When an attack deals damage to a Pokemon with weakness, the **final damage is multiplied** by the weakness factor (typically 2x).
- Example: A 40-base-damage Lightning attack against a Water Pokemon with weakness 2x deals 80 damage total.

### Resistance

- Some Pokemon have resistance (e.g., a Fire Pokemon might have -20 resistance to Grass).
- When an attack deals damage to a Pokemon with resistance, the **final damage is reduced** by the resistance amount.
- Example: A 40-base-damage Grass attack against a Fire Pokemon with -20 resistance deals 20 damage (40 - 20).
- If resistance makes final damage negative or zero, the Pokemon takes 0 damage (the engine doesn't apply healing).

### Damage Counters

- Damage is stored as individual 10-HP counters on the Pokemon.
- A Pokemon with 60 HP has 6 damage counters maximum; 40 damage applied = 4 counters placed.
- The observation includes the damage count in the Pokemon's state.

## Energy and Retreat Costs

### Attack Energy Requirements

- Each attack has a cost: a count of energy (e.g., 2 energy) and optionally a type constraint (e.g., 2x Fire).
- The engine only offers an attack as a legal MAIN option if the Active Pokemon has enough energy **attached** to satisfy the cost.
- Attachment rules:
  - Basic energy (Grass, Fire, Water, Lightning, Psychic, Fighting, Darkness, Metal) and Rainbow energy typically count as "any 1 energy".
  - Special energy might have specific typing or restrictions.
  - If an attack requires "2x Fire energy", only Fire (or Rainbow, if it counts as Fire) satisfy that requirement.

### Energy Attachment per Turn

- Each turn, the player can attach up to 1 energy to a Pokemon (the "manual energy attachment").
- The state includes `energyAttached` (boolean): if True, no more manual attachments are allowed this turn.
- Some card effects allow attaching additional energy beyond the 1-per-turn limit (e.g., Lugia VSTAR's ability).

### Retreat Cost

- Each Pokemon has a retreat cost (e.g., 1, 2, 3 energy).
- To retreat, the player must discard that many energy from the Active Pokemon.
- The engine only offers RETREAT as a legal MAIN option if the Active Pokemon has at least that much energy attached.
- Retreat cost is separate from attack energy cost; both must be satisfied from the same energy pool.

## Status Effects

Status effects are boolean flags on the Active Pokemon in the observation's `state.players[index]`:
- `poisoned`: Poison (regular or badly poisoned both set this flag).
- `burned`: Burn.
- `asleep`: Sleep.
- `paralyzed`: Paralyze.
- `confused`: Confuse.

### Poison

- Regular poison: 1 damage counter placed on the Active Pokemon at the end of the turn.
- Badly poisoned: 2 damage counters placed at the end of the turn.
- Both are represented by the same `poisoned` boolean flag in the observation.
- A Pokemon can be cured of poison by card effects (typically healing or switch effects).

### Burn

- 1 damage counter placed on the Active Pokemon at the end of the turn.
- Represented by the `burned` flag.

### Sleep

- At the start of the turn, the engine may offer a coin-flip choice: "Would you like to wake up?"
- If the player chooses Yes and the flip is heads, the Pokemon wakes up (flag is cleared).
- If the flip is tails or the player chooses No, the Pokemon remains asleep.
- While asleep, the player's main options are limited: typically only SWITCH and RETREAT are available (if they have energy for retreat).

### Paralyze

- Similar to Sleep: at the start of the turn, a coin-flip choice is offered.
- If the flip is heads, the Pokemon is cured of paralyze.
- If the flip is tails, it remains paralyzed.
- While paralyzed, the player's main options may be limited (exact rules unclear; empirically, it seems to block or restrict ATTACK/ABILITY).

### Confuse

- If the Active Pokemon uses an attack while confused, a coin flip determines if the attack hits.
- If it doesn't hit, the attack is canceled and the defending Pokemon takes 1 damage counter instead (reflected in the damage/outcome logs).
- Represented by the `confused` flag.

## Prizes and Knockout

### Prize Pile

- Each player starts with 6 prize cards (face-down).
- The prize pile is a stack; the top card is the most recent prize (last added).
- Observation includes `state.players[index].prizeCount` and `state.players[index].prize` (array of cards, None if face-down).

### Knockout

- When a Pokemon reaches 0 HP (or is Knocked Out by an effect), it is removed from play.
  - Active Pokemon: the opponent (player who knocked it out) takes a prize card.
  - Bench Pokemon: only taken as a prize if it was a result of an attack on Active (e.g., an area damage attack).
- The player who owns the knocked-out Pokemon selects a bench Pokemon to become the new Active.
- If the bench is empty, the game ends and the opponent wins.

### Prize Taking

- When a prize card is taken, it moves from the prize pile to the player's hand.
- Observation shows the prize pile decreasing by 1 and the hand size increasing by 1.
- Prize cards are **not** identified to the opponent; the card itself is face-down in the logs but face-up in your own observation.

### Winning Condition

- A player wins immediately if:
  1. They take their 6th (last) prize card, **and**
  2. They still have at least one Pokemon in play (Active or Bench) after taking the prize.
- If both conditions are met, the game ends and that player is declared the winner (state.result = winning_player_index).

## On-Evolve Abilities

### When an On-Evolve Ability Triggers

- When a Pokemon evolves (via the EVOLVE main option), any abilities on that Pokemon with an on-evolve trigger activate **immediately after evolution**.
- The engine resolves the ability effect in the logs or via a new SelectData request (e.g., "Which card would you like to search for?").
- Some on-evolve abilities are mandatory (no choice); others are optional (Yes/No choice).

### Once-Per-Turn Constraint

- An ability with a once-per-turn restriction can only be used once per turn, even if multiple Pokemon have the same ability.
- The engine tracks this via the state or logs; a second activation of the same ability on the same turn is not offered as a legal option.
- If a Pokemon with an already-used ability evolves, that evolved form's ability is also considered "used for the turn" (abilities on the same Pokemon inherit the status).

### Ability Activation

- Not all abilities activate automatically; some require the player to choose "Yes" or "No" to activate.
- The SelectData will indicate the ability activation choice.

## Sub-Select Semantics

The game's selection model has several layers:

### MainOption (SelectType.MAIN)

When a decision is required, the observation provides `select` with:
- `type`: The selection type (MAIN, CARD, COUNT, YES_NO, etc.).
- `minCount` and `maxCount`: How many options must/can be selected.
- `option`: An array of legal options (OptionType enum values).

### CARD Selection (SelectType.CARD)

When the player must select one or more **cards**, the response is a **list of indices into the option array**.
- Example: "Select a card to discard" => response [0] selects the first card in the option array.
- Multiple cards: "Select up to 3 cards" => response [0, 1, 2] selects the first three.
- Duplicate indices are not allowed (each card can be selected once).

### COUNT Selection (SelectType.COUNT)

When the player must enter a **number**, the response is a **list with one integer**.
- Example: "How many cards to draw?" => response [3] draws 3 cards.
- The engine validates the count is between minCount and maxCount.
- Responses outside the valid range are rejected.

### YES_NO Selection (SelectType.YES_NO)

When the player chooses between Yes and No:
- Response [1] = Yes.
- Response [0] = No.
- An empty response [] may also be valid for optional questions (unclear; empirical testing needed).

### Option Types

Each element in the `option` array has a `type` (OptionType enum):

| Type | Meaning | Additional Fields |
| --- | --- | --- |
| PLAY | Play a card from hand | index (hand position) |
| ATTACH | Attach energy/tool to Pokemon | area, index (card to attach), inPlayArea, inPlayIndex (target) |
| EVOLVE | Evolve a Pokemon | area, index (evolution card), inPlayArea, inPlayIndex (base Pokemon) |
| ABILITY | Use a Pokemon ability | area, index (Pokemon location) |
| DISCARD | Discard a card in play | area, index (card to discard) |
| RETREAT | Retreat the Active Pokemon | (no sub-selection needed; just select RETREAT and pick bench Pokemon next) |
| ATTACK | Use an attack | attackId (attack identifier) |
| END | End your turn | (terminal; no sub-selection) |
| CARD | Select any card | area, index, playerIndex |
| ENERGY | Select energy attached to a Pokemon | area, index (Pokemon), energyIndex |
| NUMBER | Select a count | (responds with integer) |
| YES / NO | Select Yes or No | (respond [1] or [0]) |

## Turn Structure

### Turn Order

- Turns are numbered: 1 = starting player's first turn, 2 = second player's first turn, 3 = starting player's second turn, etc.
- The `state.turn` field reflects the current turn number.
- The `state.firstPlayer` indicates who went first (0 or 1); it's -1 before the first-player choice is made.

### Turn Phases

Each turn follows this order:

1. **Draw Phase**: Automatically draw 1 card from deck (no choice).
2. **Play Phase**: Take zero or more PLAY, ATTACH, EVOLVE, ABILITY, DISCARD actions.
3. **Attack Phase**: Take at most one ATTACK action.
4. **Retreat Phase**: Optionally take one RETREAT action (after attack or in place of attack).
5. **End Phase**: Take the END action to end the turn.

### Action Constraints

- **PLAY** (Trainer cards):
  - Unlimited per turn, BUT:
    - Supporters: 1 per turn (enforced by `supporterPlayed` flag).
    - Stadiums: 1 per turn (enforced by `stadiumPlayed` flag).
    - Items: unlimited.
- **ATTACH** (Energy):
  - 1 energy per turn (enforced by `energyAttached` flag).
  - Some abilities allow attaching additional energy; this overrides the 1-per-turn limit.
- **EVOLVE** (Pokemon evolution):
  - Unlimited per turn (a Pokemon can only evolve once per turn, but multiple Pokemon can evolve in one turn).
- **ABILITY**:
  - Unlimited activations, but each ability has:
    - A once-per-turn restriction (if the text says "once per turn").
    - Source Pokemon restrictions (abilities can't be used if the Pokemon is asleep or paralyzed).
- **ATTACK**:
  - 1 per turn (enforced by the game; a second ATTACK option is not offered).
- **RETREAT**:
  - 1 per turn (enforced by the game; a second RETREAT option is not offered after the first).

### State Flags

- `turnActionCount`: Increments with each "major" action (unclear exactly what counts; empirically, PLAY, ATTACH, EVOLVE, ABILITY, ATTACK, RETREAT increment this).
- `supporterPlayed`: Set to True after a Supporter is played; reset to False at the start of the next turn.
- `stadiumPlayed`: Set to True after a Stadium is played; reset to False at the start of the next turn.
- `energyAttached`: Set to True after manual energy attachment; reset to False at the start of the next turn.
- `retreated`: Set to True after a RETREAT action; reset to False at the start of the next turn.

## Game Start: First Player Choice and Mulligan

### Is First?

At the very start of the game, before any cards are drawn, the engine offers a choice: "Would you like to go first?"
- Response [1] = Yes, I want to go first.
- Response [0] = No, I want to go second.
- The engine then determines the actual first player and begins the game.

### Mulligan

After the first player's turn 1 begins, that player is offered a mulligan: "Would you like to redraw?"
- If the player's opening hand contains no Basic Pokemon, they may choose to mulligan (redraw all cards and reshuffle).
- Response [1] = Yes, redraw. Response [0] = No, keep this hand.
- A mulligan can be chained (multiple redraws in a row if the opening hand keeps having no Basic Pokemon).

## Known Gaps and Future Work

The following mechanics are **not yet documented** (stubs in tests/test_engine_mechanics.py):

- Exact interaction of confuse with attacks (does the flip prevent the attack or just cause recoil?).
- Paralyze exact interaction (does it prevent all actions or just specific ones?).
- Special energy typing and restrictions.
- On-deck searchers and hand-size limits.
- Discarding energy vs. other effects (e.g., are there any priority rules?).
- Bench size limits and behavior when bench is full.
- Devolve mechanics (unclear if the engine supports them).
- Coin-flip probability (assumed 50/50; not empirically verified).
- Damage rounding and edge cases (fractional damage, overflow).

These are candidates for future empirical probing as the agent's requirements expand.
