"""Isolate PTCG_ABILITY's one-sided effect from the shared-process confound.

LOOP_BRIEF.md L1/L9 flag an unresolved caveat on the shipped ability lever
(heuristic+trolley-ability, currently shadow-king): PTCG_ABILITY is read from a
single process-global (agents.heuristics._ABILITY), and every deck:<name>
opponent in the gauntlet pool is piloted by the SAME heuristics module in the
SAME process (tools/opponents.py's _deck_opponent calls heuristics.choose
directly). The offline gauntlet A/B (analysis/ability_ab.md, +4.0pp) and the
bracket-ring check (analysis/ability_ring_check.md, +20.0pp) both baked
PTCG_ABILITY into the whole subprocess env, so the "on" arm actually gave BOTH
seats the ability lever, not just the pilot under test. This script isolates
it: before each seat's decision, it flips heuristics._ABILITY to that seat's
assigned value, so one arm is genuinely "our pilot has the lever, the opponent
does not" (the claim the ladder lever actually needs).

Three arms over the same 8-deck pool ability_ab.md used:
  off/off   - both seats off (the shipped default; matches the "off" row)
  on/on     - both seats on (mirrors the confounded env-var-baked A/B exactly)
  on/off    - ISOLATED: only our pilot has the lever, opponent does not

If on/off's diff_pp collapses toward zero (or goes negative) relative to
on/on's, the previously-recorded +4.0pp / +20.0pp were largely a mirror-match
symmetric effect, not a one-sided edge for us, and the shadow-king promotion
should be treated as unconfirmed pending a real asymmetric gate. If on/off
still clears a meaningful positive diff_pp, the lever survives deconfounding.

Dev/measurement tool only; never shipped, touches no shipped code path. The
_ABILITY flag is toggled on the imported module attribute (read fresh in
heuristics.choose() on every call, per agents/heuristics.py:1215), and reset to
the shipped default (False) when the run completes. The native engine is a
per-process singleton, so all matches here run sequentially in one process
(mirrors tools/gauntlet.py's run_gauntlet, not the sharded parallel runner).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agents import heuristics as h  # noqa: E402
from ptcg_agent.engine import run_match  # noqa: E402
from tools import opponents  # noqa: E402
from tools.gauntlet import _wilson  # noqa: E402

DEFAULT_POOL = (
    "deck:meta_archaludon",
    "deck:meta_grimmsnarl",
    "deck:meta_grimmsnarl_tonakaiiii",
    "deck:aggro",
    "deck:control",
    "deck:ultraball",
    "deck:trolley",
    "deck:trolley_thick",
)


def _seat_wrap(fn, ability_on):
    """Wrap an opponent callable so it always plays with a fixed ability setting.

    heuristics.choose() reads the module-global _ABILITY fresh on every call
    (not a value captured at import time), so setting the attribute right
    before invoking this seat's callable is enough to pin its ability behavior
    independent of whatever the other seat's wrapper set most recently.
    """

    def wrapped(obs):
        h._ABILITY = ability_on
        return fn(obs)

    return wrapped


def run_arm(pilot_ability, opponent_ability, pool=DEFAULT_POOL, n_matches=200, seed=0):
    """Play n_matches of deck:trolley (piloted by 'heuristic') vs the pool.

    pilot_ability / opponent_ability are independent booleans, so on/off arms
    that the env-var-baked gauntlet in analysis/ability_ab.md could never
    produce (it can only set PTCG_ABILITY once per whole subprocess) are
    reachable here.
    """
    random.seed(seed)
    pilot_fn = opponents.get("heuristic")
    wins = draws = losses = 0
    try:
        for i in range(n_matches):
            opp_fn = opponents.get(pool[i % len(pool)])
            wrapped_a = _seat_wrap(pilot_fn, pilot_ability)
            wrapped_b = _seat_wrap(opp_fn, opponent_ability)
            res = run_match(wrapped_a, wrapped_b, swap_first=(i % 2 == 1))
            if res["reward_a"] == 1:
                wins += 1
            elif res["reward_a"] == -1:
                losses += 1
            else:
                draws += 1
    finally:
        h._ABILITY = False  # restore the shipped default no matter how this exits
    n = wins + draws + losses
    lo, hi = _wilson(wins, n)
    return {
        "pilot_ability": pilot_ability,
        "opponent_ability": opponent_ability,
        "matches": n,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": wins / n if n else 0.0,
        "wilson_lo": lo,
        "wilson_hi": hi,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-n", "--matches", type=int, default=200, help="matches per arm")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    off_off = run_arm(False, False, n_matches=args.matches, seed=args.seed)
    on_on = run_arm(True, True, n_matches=args.matches, seed=args.seed)
    on_off = run_arm(True, False, n_matches=args.matches, seed=args.seed)

    result = {
        "off_off": off_off,
        "on_on": on_on,
        "on_off_isolated": on_off,
        "diff_pp_on_on_vs_off_off": round((on_on["win_rate"] - off_off["win_rate"]) * 100, 1),
        "diff_pp_on_off_vs_off_off": round((on_off["win_rate"] - off_off["win_rate"]) * 100, 1),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
