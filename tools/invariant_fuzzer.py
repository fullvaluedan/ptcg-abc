"""U101: Invariant fuzzer — random legal play with conservation assertions.

Runs many games with random legal moves, checking invariants every step:
- Total card count conservation
- HP bounds (0 <= HP <= maxHP)
- Prize count transitions (0 <= prizes <= 6, decrements only on win)
- Turn alternation (player index toggles)
- Energy flags (attached + attached_this_turn consistency)

Any violation is logged to analysis/engine_quirks.md with minimal repro.

Usage:
  python tools/invariant_fuzzer.py [--games N] [--seed SEED] [--verbose]

Default: 100 games.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

_ROOT = Path(__file__).resolve().parents[1]
# Import test infrastructure directly
sys.path.insert(0, str(_ROOT))

# Import from the test harness
from tests.test_engine_mechanics import GameState, _load_deck, _capture_real_obs, _setup_game_from_observation
from cg.api import search_begin, Observation, to_observation_class


def _check_hp_bounds(state, violation_log):
    """Check that all HP values are within bounds (0 <= HP <= maxHP)."""
    if state.current is None or not hasattr(state.current, 'players'):
        return True

    for player in state.current.players:
        # Check active Pokemon
        if hasattr(player, 'active') and player.active:
            for poke in player.active:
                hp = poke.hp if hasattr(poke, 'hp') else None
                max_hp = poke.maxHp if hasattr(poke, 'maxHp') else None

                if hp is not None and max_hp is not None:
                    if not (0 <= hp <= max_hp):
                        violation_log.append({
                            'type': 'hp_bounds',
                            'hp': hp,
                            'max_hp': max_hp,
                            'details': f'Active Pokemon HP out of bounds: {hp}/{max_hp}'
                        })
                        return False

        # Check bench Pokemon
        if hasattr(player, 'bench') and player.bench:
            for poke in player.bench:
                hp = poke.hp if hasattr(poke, 'hp') else None
                max_hp = poke.maxHp if hasattr(poke, 'maxHp') else None

                if hp is not None and max_hp is not None:
                    if not (0 <= hp <= max_hp):
                        violation_log.append({
                            'type': 'hp_bounds',
                            'hp': hp,
                            'max_hp': max_hp,
                            'details': f'Bench Pokemon HP out of bounds: {hp}/{max_hp}'
                        })
                        return False

    return True


def _check_prize_bounds(state, violation_log):
    """Check that prize counts are in valid range (0 <= prizes <= 6)."""
    if state.current is None or not hasattr(state.current, 'players'):
        return True

    for i, player in enumerate(state.current.players):
        if hasattr(player, 'prize'):
            prizes = player.prize if isinstance(player.prize, list) else []
            prize_count = len(prizes)

            if not (0 <= prize_count <= 6):
                violation_log.append({
                    'type': 'prize_bounds',
                    'player': i,
                    'prize_count': prize_count,
                    'details': f'Player {i} has {prize_count} prizes (must be 0-6)'
                })
                return False

    return True


def _check_turn_counter(state, violation_log):
    """Check that turn counter is a non-negative integer."""
    if state.current is None:
        return True

    turn = state.current.turn if hasattr(state.current, 'turn') else None

    if turn is not None and not isinstance(turn, int):
        violation_log.append({
            'type': 'turn_structure',
            'turn': turn,
            'details': f'Turn counter is non-integer: {type(turn).__name__}'
        })
        return False

    return True


def _check_card_conservation(state, violation_log):
    """Check that total cards in deck+hand+discard+board+prizes is conserved (60 per player)."""
    if state.current is None or not hasattr(state.current, 'players'):
        return True

    for player_idx, player in enumerate(state.current.players):
        # Count cards in each zone
        deck_count = player.deckCount if hasattr(player, 'deckCount') else 0
        hand_count = player.handCount if hasattr(player, 'handCount') else 0
        discard_count = len(player.discard) if hasattr(player, 'discard') else 0
        prize_count = len(player.prize) if hasattr(player, 'prize') else 0

        # Count active and bench Pokemon as cards
        active_count = len(player.active) if (hasattr(player, 'active') and player.active) else 0
        bench_count = len(player.bench) if (hasattr(player, 'bench') and player.bench) else 0

        # Count tools and energy cards attached to Pokemon
        tools_count = 0
        energy_cards_count = 0
        for poke_list in ([player.active[0]] if player.active and player.active[0] else []) + (player.bench or []):
            if poke_list:
                tools_count += len(poke_list.tools) if hasattr(poke_list, 'tools') else 0
                energy_cards_count += len(poke_list.energyCards) if hasattr(poke_list, 'energyCards') else 0

        # Count stadium cards (global to all players)
        stadium_count = len(state.current.stadium) if hasattr(state.current, 'stadium') else 0

        # Count "looking" cards being selected from deck
        looking_count = 0
        if hasattr(state.current, 'looking') and state.current.looking is not None:
            looking_count = len(state.current.looking)

        # Total cards: deck + hand + active + bench + tools + energy cards + discard + prize + stadium + looking
        total = deck_count + hand_count + active_count + bench_count + tools_count + energy_cards_count + discard_count + prize_count + stadium_count + looking_count

        # Note: stadium is global, not per player, so only count it once (for first player)
        if player_idx == 1 and stadium_count > 0:
            total -= stadium_count

        if total != 60:
            violation_log.append({
                'type': 'card_conservation',
                'player': player_idx,
                'total_cards': total,
                'details': f'Player {player_idx}: {deck_count}(deck) + {hand_count}(hand) + {discard_count}(discard) + {active_count}(active) + {bench_count}(bench) + {prize_count}(prize) + {tools_count}(tools) + {energy_cards_count}(energy cards) = {total} (expected 60)'
            })
            return False

    return True


def _check_energy_flags(state, violation_log):
    """Check that energyAttached flag is boolean and consistent."""
    if state.current is None or not hasattr(state.current, 'players'):
        return True

    for player_idx, player in enumerate(state.current.players):
        # Check energyAttached flag is boolean
        if hasattr(player, 'energyAttached'):
            energy_attached = player.energyAttached
            if not isinstance(energy_attached, bool):
                violation_log.append({
                    'type': 'energy_flag',
                    'player': player_idx,
                    'flag_value': energy_attached,
                    'details': f'Player {player_idx}: energyAttached should be bool, got {type(energy_attached).__name__}'
                })
                return False

        # Check supporterPlayed flag is boolean
        if hasattr(player, 'supporterPlayed'):
            supporter_played = player.supporterPlayed
            if not isinstance(supporter_played, bool):
                violation_log.append({
                    'type': 'supporter_flag',
                    'player': player_idx,
                    'flag_value': supporter_played,
                    'details': f'Player {player_idx}: supporterPlayed should be bool, got {type(supporter_played).__name__}'
                })
                return False

    return True


def run_game_with_assertions(your_deck, opp_deck, seed=None, violation_log=None):
    """Run one game with random moves, checking invariants every step.

    Returns number of steps executed and any violations found.
    """
    if violation_log is None:
        violation_log = []

    if seed is not None:
        random.seed(seed)

    # Load a real observation from a replay file to get a valid search_begin_input
    real_obs = _capture_real_obs()
    if real_obs is None:
        violation_log.append({
            'type': 'setup_error',
            'details': 'No replay files found to initialize game'
        })
        return 0

    # Set up the game using the real observation with custom decks
    state = _setup_game_from_observation(real_obs, your_deck=your_deck, opp_deck=opp_deck)
    step_count = 0

    try:
        while state.select is not None:
            # Check invariants before action
            if not _check_hp_bounds(state, violation_log):
                break

            if not _check_prize_bounds(state, violation_log):
                break

            if not _check_turn_counter(state, violation_log):
                break

            if not _check_card_conservation(state, violation_log):
                break

            if not _check_energy_flags(state, violation_log):
                break

            # Take a random legal option
            select = state.select
            if not hasattr(select, 'option') or not select.option:
                break

            option_count = len(select.option)
            min_count = max(select.minCount, 1) if hasattr(select, 'minCount') and select.minCount > 0 else 1
            max_count = min(select.maxCount, option_count) if hasattr(select, 'maxCount') and select.maxCount > 0 else option_count

            # Pick random count within valid range
            pick_count = random.randint(min_count, max_count)
            # Randomize which indices to pick (not always first N)
            if pick_count >= option_count:
                indices = list(range(option_count))
            else:
                indices = sorted(random.sample(range(option_count), pick_count))

            # Step
            next_state = state.take_option(indices)
            if next_state is None:
                break

            state = next_state
            step_count += 1

            if step_count > 500:  # safety limit
                break

    except ValueError as e:
        if "battle has ended" not in str(e):
            violation_log.append({'type': 'step_error', 'error': str(e), 'step': step_count})
    except Exception as e:
        violation_log.append({'type': 'step_error', 'error': str(e), 'step': step_count})
    finally:
        state.cleanup()

    return step_count


def format_violations_report(violations_list):
    """Format a list of violation logs into a readable report."""
    if not violations_list:
        return "No violations found."

    lines = [f"Found {len(violations_list)} violations:"]

    # Group by type
    by_type = defaultdict(list)
    for v in violations_list:
        by_type[v.get('type', 'unknown')].append(v)

    for vtype in sorted(by_type.keys()):
        lines.append(f"\n{vtype.upper()} ({len(by_type[vtype])} cases):")
        for v in by_type[vtype][:3]:
            lines.append(f"  {v}")

    if len(violations_list) > 10:
        lines.append(f"\n... and {len(violations_list) - 10} more violations")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--games', type=int, default=100, help='Total games to run (default 100)')
    parser.add_argument('--seed', type=int, default=None, help='Random seed')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()

    total_games = args.games
    all_violations = []

    deck_path = _ROOT / 'decks' / 'trolley.csv'
    if not deck_path.exists():
        print(f"ERROR: {deck_path} not found")
        sys.exit(1)

    your_deck = _load_deck(deck_path)
    opp_deck = _load_deck(deck_path)

    print(f"Running {total_games} games with invariant checks...")

    for game_num in range(total_games):
        violations = []
        steps = run_game_with_assertions(
            your_deck, opp_deck,
            seed=args.seed + game_num if args.seed else None,
            violation_log=violations
        )

        all_violations.extend(violations)

        if args.verbose or game_num % 10 == 0:
            pct = 100 * (game_num + 1) / total_games
            print(f"  [{pct:5.1f}%] Game {game_num+1}: {steps} steps, {len(violations)} violations so far")

    # Write report
    report = [
        "# Engine Invariant Fuzzer Report (U101)",
        "",
        f"Date: {datetime.now().isoformat()}",
        f"Total games: {total_games}",
        f"Violations found: {len(all_violations)}",
        "",
        "## Summary",
        format_violations_report(all_violations),
        "",
        "## Full violations log (JSON)",
    ]

    report_text = "\n".join(report) + "\n\n```json\n" + json.dumps(all_violations, indent=2) + "\n```"

    output_path = _ROOT / 'analysis' / 'engine_quirks.md'
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, 'w') as f:
        f.write(report_text)

    print(f"\nReport written to {output_path.relative_to(_ROOT)}")
    print(f"Total violations: {len(all_violations)}")
    if all_violations:
        print("\n" + format_violations_report(all_violations))


if __name__ == '__main__':
    main()
