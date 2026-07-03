"""U93 step 2: gate the staged PTCG_ATTACK_FIRST lever through the calibrated clone ring.

Mirrors tools/ability_ring_check.py exactly (same U74 pattern, now reused for a
second lever): score the flag-off vs flag-on trolley builds against the
calibrated bracket-band ring (tau 0.857, analysis/ring_calibration.md) and
require BOTH a >=+5pp ring margin AND directional agreement with the offline
weak-bot gauntlet (analysis/attack_first_ab.md) before this lever earns a
pre-registered ladder slot, per LOOP_BRIEF.md's U93 step 2 gate. A ring PASS
here only unlocks a ladder A/B; it does not itself move the ladder.

_ATTACK_FIRST (agents/heuristics.py) is a module-level constant read once at
import time from PTCG_ATTACK_FIRST, so toggling the environment variable after
import has no effect. Reproduced in-process the same way ability_ring_check.py
patches _ABILITY: monkeypatch the module constant around each call and restore
it afterward.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools import opponents  # noqa: E402
from tools import ring_calibrate as rc  # noqa: E402

DEFAULT_MATCHES = 20
GATE_MARGIN_PP = 5.0


def _attack_first_trolley_agent(flag_on):
    """heuristic+trolley with _ATTACK_FIRST forced on or off, deck fixed to trolley."""
    from agents import heuristics as H

    inner = opponents.get("deck:trolley")

    def agent(obs):
        orig = H._ATTACK_FIRST
        H._ATTACK_FIRST = flag_on
        try:
            return inner(obs)
        finally:
            H._ATTACK_FIRST = orig

    return agent


BUILD_FACTORIES = {
    "heuristic+trolley-attack_first-off": lambda: _attack_first_trolley_agent(False),
    "heuristic+trolley-attack_first-on": lambda: _attack_first_trolley_agent(True),
}


def run_check(n_matches=DEFAULT_MATCHES, opponent_names=None) -> dict:
    """Ring win-rate stats for the attack_first-off and attack_first-on builds.

    Returns run_ring's shape (build name -> {win_rate, wins, draws, losses, n})
    plus a "diff_pp" key (on minus off, percentage points) for convenience.
    """
    results = rc.run_ring(
        n_matches=n_matches, builds=BUILD_FACTORIES, opponent_names=opponent_names,
    )
    off = results["heuristic+trolley-attack_first-off"]["win_rate"]
    on = results["heuristic+trolley-attack_first-on"]["win_rate"]
    results["diff_pp"] = (on - off) * 100.0
    return results


def _main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", "--matches", type=int, default=DEFAULT_MATCHES)
    args = parser.parse_args(argv)

    results = run_check(n_matches=args.matches)
    for name in ("heuristic+trolley-attack_first-off", "heuristic+trolley-attack_first-on"):
        r = results[name]
        print(f"{name}: {r['win_rate']:.3f} ({r['wins']}/{r['n']})")
    print(f"diff_pp (on minus off) = {results['diff_pp']:+.1f}")
    print(f"gate: diff_pp >= {GATE_MARGIN_PP:+.1f} -> "
          f"{'PASS' if results['diff_pp'] >= GATE_MARGIN_PP else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
