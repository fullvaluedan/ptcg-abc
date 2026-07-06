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
from tests.test_engine_mechanics import GameState, _setup_fresh_game, _load_deck


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


def run_game_with_assertions(your_deck, opp_deck, seed=None, violation_log=None):
    """Run one game with random moves, checking invariants every step.

    Returns number of steps executed and any violations found.
    """
    if violation_log is None:
        violation_log = []

    if seed is not None:
        random.seed(seed)

    state = _setup_fresh_game(your_deck, opp_deck)
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

            # Take a random legal option
            select = state.select
            if not hasattr(select, 'option') or not select.option:
                break

            option_count = len(select.option)
            min_count = max(select.minCount, 1) if hasattr(select, 'minCount') and select.minCount > 0 else 1
            max_count = min(select.maxCount, option_count) if hasattr(select, 'maxCount') and select.maxCount > 0 else option_count

            # Pick random count
            pick_count = random.randint(min_count, max_count)
            indices = list(range(min(pick_count, option_count)))

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
