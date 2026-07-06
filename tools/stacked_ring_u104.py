"""U104: Stacked ring run - measure three arms factorized by lever combination.

Three arms measured in one ring run (same-run deltas, no cross-run confounds):
  Arm 1: trolley+ability (shadow-king baseline)
  Arm 2: yushin+ability (ability on yushin, same config as arm 1)
  Arm 3: yushin+ability+attack_first (adds attack_first to arm 2)

Decision gate per plan U104: arm 3 beats arm 1 by more than +0.10 same-run delta.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ptcg_agent.engine import run_match  # noqa: E402
from tools import opponents, ring_calibrate  # noqa: E402

DEFAULT_MATCHES = 40


def _make_agent_factory(deck_name, ability_on, attack_first_on):
    """Factory returning an agent that pilots deck_name with the specified lever settings.

    Wraps the deck opponent with flag patching at call time, so each arm's
    games see its own ability and attack_first settings.
    """
    def factory():
        from agents import heuristics as H

        base_agent = opponents.get(f"deck:{deck_name}")

        def agent(obs):
            orig_ability = H._ABILITY
            orig_attack_first = H._ATTACK_FIRST
            H._ABILITY = ability_on
            H._ATTACK_FIRST = attack_first_on
            try:
                return base_agent(obs)
            finally:
                H._ABILITY = orig_ability
                H._ATTACK_FIRST = orig_attack_first

        return agent

    return factory


def _ring_win_rate(agent_fn, opponent_names, n_matches):
    """(win_rate, wins, draws, losses, n) for agent_fn round-robin over opponent_names."""
    if not opponent_names or n_matches <= 0:
        return 0.0, 0, 0, 0, 0
    wins = draws = losses = 0
    for i in range(n_matches):
        opp_fn = opponents.get(opponent_names[i % len(opponent_names)])
        res = run_match(agent_fn, opp_fn, swap_first=(i % 2 == 1))
        r = res["reward_a"]
        if r == 1:
            wins += 1
        elif r == -1:
            losses += 1
        else:
            draws += 1
    n = wins + draws + losses
    return (wins / n if n else 0.0), wins, draws, losses, n


def run_stacked_ring(n_matches=DEFAULT_MATCHES) -> dict:
    """Run the three arms and return {arm_name: {win_rate, wins, draws, losses, n}}."""
    opponent_names = ring_calibrate.ring_names()
    if not opponent_names:
        raise RuntimeError(
            "no clone: opponents available; run tools/bracket_decks.py or check decks/"
        )

    # Three arm definitions
    arms = {
        "arm1_trolley_ability": _make_agent_factory("trolley", ability_on=True, attack_first_on=False),
        "arm2_yushin_ability": _make_agent_factory("candidate_yushin_ito", ability_on=True, attack_first_on=False),
        "arm3_yushin_ability_attack_first": _make_agent_factory(
            "candidate_yushin_ito", ability_on=True, attack_first_on=True
        ),
    }

    results = {}
    for arm_name, factory in arms.items():
        agent_fn = factory()
        win_rate, wins, draws, losses, n = _ring_win_rate(agent_fn, opponent_names, n_matches)
        results[arm_name] = {
            "win_rate": win_rate,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "n": n,
        }
        print(f"{arm_name}: {win_rate:.3f} ({wins}-{draws}-{losses}, n={n})")

    return results


def _main(argv=None):
    ap = argparse.ArgumentParser(description="U104 stacked ring run")
    ap.add_argument("-n", "--matches", type=int, default=DEFAULT_MATCHES,
                     help="games per arm (default %(default)s)")
    args = ap.parse_args(argv)

    print(f"Running U104 stacked ring (n={args.matches} per arm)...")
    results = run_stacked_ring(n_matches=args.matches)

    print("\n" + "=" * 60)
    print("Results:")
    print(json.dumps(results, indent=2))

    # Gate check
    arm1_wr = results["arm1_trolley_ability"]["win_rate"]
    arm3_wr = results["arm3_yushin_ability_attack_first"]["win_rate"]
    delta = arm3_wr - arm1_wr
    gate_threshold = 0.10

    print("\n" + "=" * 60)
    print(f"Arm 1 (trolley+ability):              {arm1_wr:.3f}")
    print(f"Arm 3 (yushin+ability+attack_first): {arm3_wr:.3f}")
    print(f"Delta (arm3 - arm1):                 {delta:+.3f}")
    print(f"Gate threshold (>+{gate_threshold:.2f}):          {'PASS' if delta > gate_threshold else 'FAIL'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
