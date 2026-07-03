"""A/B search/timebudget.py's confidence-based allocation (plan U12).

search/timebudget.py's confidence_multiplier scales a decision's soft cap by
how uncertain the learned evaluator (search/learned_eval.py) is about the root
position: more bank for an undecided position, less for an already-decided
one. This is gated by PTCG_CONFIDENCE_BUDGET (default on since the gate below
passed), read once at
agents/agent_search.py's import time, so each arm is its own subprocess with
the flag baked into its env, mirroring tools/eval_blend_sweep.py's pattern.

GATE (plan U12): keep only if win rate does not drop AND average bank spend
does not increase, at least 400 games total. tools/gauntlet.py's run_gauntlet
reports avg_bank_spend_s / max_bank_spend_s for agents.agent_search (added
alongside this unit); tools/parallel_gauntlet.py merges them across shards.

Dev tool only; never shipped.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.parallel_gauntlet import run_parallel_gauntlet  # noqa: E402

DEFAULT_OPPONENTS = (
    "deck:meta_archaludon",
    "deck:meta_grimmsnarl",
    "deck:meta_grimmsnarl_tonakaiiii",
    "deck:aggro",
    "deck:control",
    "deck:ultraball",
    "deck:trolley",
    "deck:trolley_thick",
)
DEFAULT_N = 200


def _run_arm(agent, opponent_names, n, flag_on, python_exe, jobs=None) -> dict:
    env = os.environ.copy()
    env["PTCG_CONFIDENCE_BUDGET"] = "1" if flag_on else "0"
    result = run_parallel_gauntlet(agent, opponent_names, n, jobs=jobs, python_exe=python_exe, env=env)
    if result["shard_errors"]:
        raise RuntimeError(f"arm subprocess failed (PTCG_CONFIDENCE_BUDGET={flag_on}): {result['shard_errors']}")
    return result


def run_ab(agent, opponent_names, n, python_exe=None, log=None, jobs=None) -> dict:
    """Run the off/on arms, n matches each, and decide the gate.

    Returns {"off": {...}, "on": {...}, "win_rate_kept": bool,
    "bank_spend_kept": bool, "gate_passed": bool}.
    """
    python_exe = python_exe or sys.executable
    log = log or print
    off = _run_arm(agent, opponent_names, n, False, python_exe, jobs=jobs)
    log(f"off: win rate {off['win_rate']:.1%} over {off['matches']} matches, "
        f"avg bank spend {off.get('avg_bank_spend_s', 0.0):.2f}s")
    on = _run_arm(agent, opponent_names, n, True, python_exe, jobs=jobs)
    log(f"on:  win rate {on['win_rate']:.1%} over {on['matches']} matches, "
        f"avg bank spend {on.get('avg_bank_spend_s', 0.0):.2f}s")

    win_rate_kept = on["win_rate"] >= off["win_rate"]
    bank_spend_kept = on.get("avg_bank_spend_s", 0.0) <= off.get("avg_bank_spend_s", 0.0)
    return {
        "agent": agent,
        "opponents": opponent_names,
        "matches_per_arm": n,
        "off": off,
        "on": on,
        "win_rate_kept": win_rate_kept,
        "bank_spend_kept": bank_spend_kept,
        "gate_passed": win_rate_kept and bank_spend_kept,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--agent", default="search", help="agent under test")
    ap.add_argument("--opponents", nargs="+", default=list(DEFAULT_OPPONENTS))
    ap.add_argument("-n", "--matches", type=int, default=DEFAULT_N, help="matches per arm")
    ap.add_argument("-o", "--out", help="write the JSON result to this path")
    ap.add_argument("--jobs", type=int, default=None,
                     help="worker subprocesses per arm (default: min(cores-2, 16))")
    args = ap.parse_args()
    result = run_ab(args.agent, args.opponents, args.matches, jobs=args.jobs)
    print(json.dumps(result, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2))
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
