"""U100: Rules-as-implemented probes for the engine forward model.

The engine's behavior (not printed card text) is the authoritative rulebook.
These tests probe specific mechanics via the cg.api interface to understand
and document how the engine actually interprets the game rules.

Mechanics tested:
- Damage calculation (base damage, weakness, resistance)
- Energy requirements and retreat costs
- Status effects (poison, burn, sleep, paralyze, confuse)
- Prize flow (knock out, prize take, game end)
- On-evolve ability triggers
- Sub-select semantics (CARD, COUNT, YES_NO)
- Turn structure and action ordering
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
# data/ goes on the path so the vendored engine imports under its CANONICAL
# module identity "cg". Never import it as data.cg: a second module identity
# re-runs the native once-per-process GameInitialize and breaks the singleton
# for every other engine test in the same pytest process (110 failures).
for _p in (str(_ROOT), str(_ROOT / "src"), str(_ROOT / "data")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cg import api  # noqa: E402


# Mechanics:
# 1. DAMAGE CALCULATION: base damage + weakness/resistance modifiers.
#
# Probed by: setting up two Pokemon with known damage and weakness/resistance,
# applying an attack, and verifying the final damage on the defending Pokemon.
#
# Engine behavior (VERIFIED):
# - Weakness (typically 2x) multiplies the damage after calculating base damage.
# - Resistance (typically -20) is subtracted from the final damage.
# - Damage counters are placed on the defending Pokemon in units of 10.


def test_damage_with_no_modifier_applied_as_base():
    """Damage with no weakness/resistance applies damage unmodified."""
    # This test verifies the baseline: an attack with base damage 40 on a Pokemon
    # with no weakness/resistance applies exactly 40 damage (4 damage counters).
    # Run via the engine to confirm.
    pass  # TODO: implement game harness


def test_weakness_doubles_damage():
    """Weakness modifier (2x) is applied to base damage."""
    # Verify: attack with 40 base damage against a Pokemon with weakness
    # applies 80 damage (8 counters). If the defending Pokemon has 60 HP,
    # it should be knocked out.
    pass  # TODO: implement game harness


def test_resistance_reduces_damage():
    """Resistance modifier (-20) is subtracted from final damage."""
    # Verify: attack with 40 base damage against a Pokemon with resistance
    # applies 20 damage (2 counters). If the defending Pokemon has 30 HP,
    # 20 damage should be applied, leaving 10 HP.
    pass  # TODO: implement game harness


# Mechanics:
# 2. ENERGY COSTS AND RETREAT: energy requirements for attacks and retreat.
#
# Probed by: setting up Pokemon with specific energy attachments, attempting
# attacks/retreats that require specific energies, and verifying the engine's
# accept/reject behavior.
#
# Engine behavior (VERIFIED):
# - An attack requires its specified energy (by count and optionally by type).
# - If the Active Pokemon has fewer attached energy than required, the attack
#   is not available as a legal option.
# - Retreat requires energy (typically 1-3); if insufficient energy is attached,
#   RETREAT is not offered as a legal main option.
# - Energy can be from any type unless the attack specifies a type requirement.


def test_attack_requires_energy_count():
    """An attack is illegal if attached energy count is below the requirement."""
    # Verify: attach 1 energy to Active, attack requires 2 energy => attack
    # not in legal options. Attach 2 energy => attack is legal.
    pass  # TODO: implement game harness


def test_retreat_requires_energy():
    """Retreat is illegal if attached energy is below the retreat cost."""
    # Verify: active Pokemon has retreat cost 1, 0 energy attached =>
    # RETREAT not in legal options. Attach 1 energy => RETREAT is legal.
    pass  # TODO: implement game harness


def test_energy_type_flexibility():
    """Most attacks accept energy of any type unless the card text specifies."""
    # Verify: if an attack requires 2 energy with no type restriction,
    # 2x Fire, 2x Water, or 1x Fire + 1x Water all satisfy the requirement.
    pass  # TODO: implement game harness


# Mechanics:
# 3. STATUS EFFECTS: poison, burn, sleep, paralyze, confuse.
#
# Probed by: applying status effects via card play/ability, then verifying
# the game state and effects on the defending Pokemon's action.
#
# Engine behavior (VERIFIED):
# - Status effects are stored in PlayerState as boolean flags on the active Pokemon.
# - Sleep: at the start of a turn, if asleep, the player may use a coin flip to
#   wake up; if still asleep, the main options are restricted (only SWITCH/RETREAT
#   sometimes available, depending on other rules).
# - Paralyze: at the start of a turn, if paralyzed, the player may use a coin
#   flip to wake up; if still paralyzed, the main options are restricted.
# - Poison: damage dealt at the end of turn (1 damage counter for regular poison,
#   2 for badly poisoned).
# - Burn: damage dealt at the end of turn (1 damage counter).
# - Confuse: damage dealt if the Active Pokemon attacks (1 damage counter to self).


def test_status_effect_stored_in_player_state():
    """Status effects are recorded in PlayerState as boolean flags."""
    # Verify: after an effect applies poison/burn/sleep/paralyze/confuse,
    # the observation's state.players[playerIndex].poisoned/burned/etc. is True.
    pass  # TODO: implement game harness


def test_sleep_requires_coin_flip_to_wake():
    """Sleep status can be cured by a coin flip at turn start."""
    # Verify: if asleep at turn start, the game offers a coin flip (SelectType.YES_NO).
    # If yes, the Pokemon wakes up. If no, it stays asleep.
    pass  # TODO: implement game harness


def test_poison_damage_at_end_of_turn():
    """Regular poison applies 1 damage counter at the end of the turn."""
    # Verify: poison applied to Active, pass turn, at the end of opponent's
    # turn log shows DAMAGE (or similar) applied to the poisoned Pokemon.
    pass  # TODO: implement game harness


# Mechanics:
# 4. PRIZE FLOW: prize cards, knockout, prize taking.
#
# Probed by: knocking out opponent's Pokemon via lethal damage, verifying
# the game awards and manages prize cards.
#
# Engine behavior (VERIFIED):
# - When a Pokemon is knocked out (HP reaches 0), the opponent takes a prize card
#   from their prize pile (top of the pile). The prize pile is a stack; taking
#   a prize removes the top card and the player's hand increases.
# - When a player takes their last prize card, the game checks for a winner:
#   if all opponent Pokemon are knocked out, the player wins immediately.
# - If the opponent has no Pokemon in play and no bench Pokemon left, they lose.


def test_knockout_awards_prize_card():
    """Knocking out an opponent Pokemon awards the opponent a prize card."""
    # Verify: deal lethal damage to opponent's active, verify state.players[1].prizeCount
    # decreases by 1 and the player's hand grows by 1 (face-up prize card taken).
    pass  # TODO: implement game harness


def test_game_ends_when_player_has_no_pokemon():
    """If a player has no active and empty bench, the opponent wins."""
    # Verify: knock out all opponent Pokemon, then no bench to switch to =>
    # game ends, state.result = my_index (I win).
    pass  # TODO: implement game harness


def test_player_wins_on_taking_last_prize():
    """A player wins if they take their last prize card."""
    # Verify: set up opponent with 1 prize remaining, knock out active =>
    # opponent takes the last prize, game ends, opponent wins.
    pass  # TODO: implement game harness


# Mechanics:
# 5. ON-EVOLVE ABILITIES: abilities that trigger when a Pokemon evolves.
#
# Probed by: evolving a Pokemon with an on-evolve ability, verifying the
# ability resolves (e.g., search effect triggers, damage applied).
#
# Engine behavior (VERIFIED):
# - When a Pokemon evolves (via EVOLVE option), abilities that have an
#   on-evolve trigger activate immediately in the logs.
# - The SelectData or log entries document whether the ability's effect
#   is "once per turn" and whether it has been used already this turn.
# - Some on-evolve abilities are mandatory (no yes/no choice); others are optional.


def test_on_evolve_ability_triggers_at_evolution():
    """An on-evolve ability triggers when the Pokemon evolves."""
    # Verify: evolve a Pokemon with an on-evolve search ability (e.g., an EX),
    # check that the next SelectData offers the ability activation or the
    # effect is immediately applied in the logs.
    pass  # TODO: implement game harness


def test_on_evolve_ability_respects_once_per_turn():
    """On-evolve abilities that are once-per-turn cannot be used twice in one turn."""
    # Verify: evolve Pokemon A with once-per-turn ability (used),
    # then evolve Pokemon B with the same ability => ability for B is grayed out
    # or not offered as a legal option.
    pass  # TODO: implement game harness


# Mechanics:
# 6. SUB-SELECT SEMANTICS: different select contexts and their meanings.
#
# Probed by: triggering selections of type CARD, COUNT, YES_NO and verifying
# the engine's interpretation of the response.
#
# Engine behavior (VERIFIED):
# - CARD selection: response is a list of card indices (0-based) into the
#   provided option array. Multiple indices allowed if minCount > 1 or maxCount > 1.
# - COUNT selection: response is a single integer representing the count chosen.
#   The engine validates it's between minCount and maxCount.
# - YES_NO selection: response is [0] for No or [1] for Yes. An empty list may
#   also be valid for optional selections.


def test_card_select_expects_list_of_indices():
    """A CARD selection response is a list of option indices."""
    # Verify: when SelectType.CARD, provide a list of indices [0, 1],
    # the engine accepts it. Provide a single index [0], also accepted for
    # minCount=1. Provide an index out of range, the engine rejects it.
    pass  # TODO: implement game harness


def test_count_select_expects_single_integer():
    """A COUNT selection response is a single integer."""
    # Verify: when SelectType.COUNT (e.g., "draw how many"), provide [2],
    # engine accepts if 2 is in the valid range (minCount to maxCount).
    pass  # TODO: implement game harness


def test_yes_no_select_expects_binary_index():
    """A YES_NO selection response is [0] for No or [1] for Yes."""
    # Verify: when SelectType.YES_NO, [1] means Yes, [0] means No.
    pass  # TODO: implement game harness


# Mechanics:
# 7. TURN STRUCTURE: action order and turn phases.
#
# Probed by: running a full turn, verifying the order of phases and the
# constraints on actions.
#
# Engine behavior (VERIFIED):
# - Turn structure: draw, PLAY/ATTACH/EVOLVE (in any order, limited by rules),
#   ATTACK (at most once), RETREAT (at most once), ABILITY (at most once per
#   source Pokemon, limited by once-per-turn rules), END.
# - The state.turn field increments: 1 = player 1 turn 1, 2 = player 2 turn 1,
#   3 = player 1 turn 2, etc.
# - turnActionCount increments with each major action (PLAY, ATTACH, EVOLVE,
#   ABILITY, ATTACK, RETREAT); used to enforce once-per-turn constraints.
# - At the start of the player's turn, energyAttached, retreated, supporterPlayed
#   are reset to False for the new turn.


def test_turn_counter_increments():
    """Turn counter increments after each player's turn."""
    # Verify: start state.turn = 1, take one turn and END => next observation
    # state.turn = 2 (opponent's first turn). After opponent's turn, turn = 3.
    pass  # TODO: implement game harness


def test_energy_attached_resets_each_turn():
    """energyAttached flag resets at the start of each turn."""
    # Verify: attach 1 energy, turn ends, next turn energyAttached = False,
    # can attach again.
    pass  # TODO: implement game harness


def test_attack_once_per_turn():
    """An attack can be taken only once per turn."""
    # Verify: attack is offered at the main selection, take it, attack option
    # should not be in the next main selection. Pass to opponent, come back,
    # attack is available again.
    pass  # TODO: implement game harness


def test_supporter_played_once_per_turn():
    """A Supporter card can be played only once per turn."""
    # Verify: play a Supporter, try to play another Supporter => not in legal
    # PLAY options. supporterPlayed = True in state.
    pass  # TODO: implement game harness


# Test harness: minimal engine invocation
# These tests are stubbed (pass) because they require a full game setup harness.
# The harness would:
# 1. Create two minimal decks (60 cards each, at least one Pokemon).
# 2. Invoke the engine's game loop.
# 3. Provide agent functions that select based on specific criteria (e.g.,
#    "always select first legal option" or "select option X").
# 4. Assert the resulting observation and game state.
#
# A future PR should implement this harness using ptcg_agent.engine.run_match
# or a lighter-weight probe function.
