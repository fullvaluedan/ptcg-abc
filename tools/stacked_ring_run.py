"""U104 stacked ring run: factorized three-arm measurement of ring-positive levers.

Measures three arms in a single run:
1. heuristic+trolley with ability (baseline)
2. heuristic+yushin with ability
3. heuristic+yushin with ability+attack_first

All against the calibrated bracket-band ring (tau 0.857, analysis/ring_calibration.md).
Computes diff_pp (arm 3 minus arm 1) and reports PASS if diff_pp > +10pp (0.10 delta).

A PASS promotes arm 3 (yushin+ability+attack_first) to P3 lock-the-strongest-pair
selection, not an immediate ladder slot. The run doubles as a yushin ability/attack_first
tiebreak given recent contested readings.
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

from tools import opponents  # noqa: E402
from tools import ring_calibrate as rc  # noqa: E402

DEFAULT_MATCHES = 40
GATE_MARGIN_PP = 10.0


def _trolley_ability_agent(ability_on):
    """heuristic+trolley with ability flag, deck fixed to trolley."""
    from agents import heuristics as H

    inner = opponents.get("deck:trolley")

    def agent(obs):
        orig = H._ABILITY
        H._ABILITY = ability_on
        try:
            return inner(obs)
        finally:
            H._ABILITY = orig

    return agent


def _yushin_ability_agent(ability_on, attack_first_on=False):
    """heuristic+yushin with ability and/or attack_first flags, deck fixed to yushin."""
    from agents import heuristics as H

    inner = opponents.get("deck:candidate_yushin_ito")

    def agent(obs):
        orig_ability = H._ABILITY
        orig_attack_first = H._ATTACK_FIRST
        H._ABILITY = ability_on
        H._ATTACK_FIRST = attack_first_on
        try:
            return inner(obs)
        finally:
            H._ABILITY = orig_ability
            H._ATTACK_FIRST = orig_attack_first

    return agent


BUILD_FACTORIES = {
    "arm1-trolley+ability": lambda: _trolley_ability_agent(True),
    "arm2-yushin+ability": lambda: _yushin_ability_agent(True, False),
    "arm3-yushin+ability+attack_first": lambda: _yushin_ability_agent(True, True),
}


def run_check(n_matches=DEFAULT_MATCHES, opponent_names=None) -> dict:
    """Ring win-rate stats for all three arms.

    Returns run_ring's shape (build name -> {win_rate, wins, draws, losses, n})
    plus a "diff_pp" key (arm 3 minus arm 1, percentage points) for gate.
    """
    results = rc.run_ring(
        n_matches=n_matches, builds=BUILD_FACTORIES, opponent_names=opponent_names,
    )
    arm1 = results["arm1-trolley+ability"]["win_rate"]
    arm3 = results["arm3-yushin+ability+attack_first"]["win_rate"]
    results["diff_pp"] = (arm3 - arm1) * 100.0
    return results


def _main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", "--matches", type=int, default=DEFAULT_MATCHES,
                        help="games per arm (default %(default)s)")
    parser.add_argument("--json", action="store_true",
                        help="output JSON results instead of human-readable")
    args = parser.parse_args(argv)

    results = run_check(n_matches=args.matches)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        for name in ("arm1-trolley+ability", "arm2-yushin+ability",
                     "arm3-yushin+ability+attack_first"):
            r = results[name]
            print(f"{name}: {r['win_rate']:.3f} ({r['wins']}/{r['n']})")
        print()
        print(f"diff_pp (arm3 minus arm1) = {results['diff_pp']:+.1f}")
        gate_status = "PASS" if results['diff_pp'] > GATE_MARGIN_PP else "FAIL"
        print(f"gate: diff_pp > +{GATE_MARGIN_PP:.1f} -> {gate_status}")

    return 0 if results['diff_pp'] > GATE_MARGIN_PP else 1


if __name__ == "__main__":
    raise SystemExit(_main())
