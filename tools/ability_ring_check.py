"""U74: re-gate the staged PTCG_ABILITY lever through the calibrated clone ring.

The plan (docs/plans/2026-07-03-002-feat-top-player-clone-ring-plan.md, U74) is
immediate payoff once the ring passes calibration (U81, tau 0.857): score the
staged ability-on vs ability-off builds against the ring and record whether the
ring's verdict agrees with the pending ladder A/B (heuristic+trolley-ability vs
heuristic+trolley, settle-by 2026-07-08, state/current.md) once it settles. Ring
results never veto an already-pre-registered ladder A/B; they only gate FUTURE
candidates and, here, produce a free predictiveness data point.

_ABILITY (agents/heuristics.py) is a module-level constant read once at import
time from PTCG_ABILITY, so toggling the environment variable after import has no
effect. Reproduced in-process the same way tools/ring_calibrate.py's own
_no_benchguard_trolley_agent patches THIN_BENCH: monkeypatch the module constant
around each call and restore it afterward.
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


def _ability_trolley_agent(ability_on):
    """heuristic+trolley with _ABILITY forced on or off, deck fixed to trolley."""
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


BUILD_FACTORIES = {
    "heuristic+trolley-ability-off": lambda: _ability_trolley_agent(False),
    "heuristic+trolley-ability-on": lambda: _ability_trolley_agent(True),
}


def run_check(n_matches=DEFAULT_MATCHES, opponent_names=None) -> dict:
    """Ring win-rate stats for the ability-off and ability-on builds.

    Returns run_ring's shape (build name -> {win_rate, wins, draws, losses, n})
    plus a "diff_pp" key (on minus off, percentage points) for convenience.
    """
    results = rc.run_ring(
        n_matches=n_matches, builds=BUILD_FACTORIES, opponent_names=opponent_names,
    )
    off = results["heuristic+trolley-ability-off"]["win_rate"]
    on = results["heuristic+trolley-ability-on"]["win_rate"]
    results["diff_pp"] = (on - off) * 100.0
    return results


def _main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", "--matches", type=int, default=DEFAULT_MATCHES)
    args = parser.parse_args(argv)

    results = run_check(n_matches=args.matches)
    for name in ("heuristic+trolley-ability-off", "heuristic+trolley-ability-on"):
        r = results[name]
        print(f"{name}: {r['win_rate']:.3f} ({r['wins']}/{r['n']})")
    print(f"diff_pp (on minus off) = {results['diff_pp']:+.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
