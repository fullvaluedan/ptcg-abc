"""Gauntlet A/B harness: same agent, opponents, and N, learned eval off vs on.

search/eval.py reads PTCG_LEARNED_EVAL once at import time (a module-level
constant), so flipping the env var mid-process would not change an
already-imported agent's behavior. Each arm therefore runs in its own
subprocess with the flag baked into that subprocess's environment, and
tools/gauntlet.py itself stays unmodified. Used for the U5 gate and any later
U6 retraining A/B (plan docs/plans/2026-07-02-002-feat-learned-evaluator-plan.md).

Dev tool only; never shipped.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

GATE_MARGIN_PP = 4.0


def _run_arm(agent, opponent_names, n, learned_eval, python_exe) -> dict:
    """Run one gauntlet arm as a fresh subprocess with the flag baked into its env."""
    env = os.environ.copy()
    env["PTCG_LEARNED_EVAL"] = "1" if learned_eval else "0"
    code = (
        "import json, sys; "
        f"sys.path.insert(0, {str(_ROOT)!r}); sys.path.insert(0, {str(_ROOT / 'src')!r}); "
        "from tools.gauntlet import run_gauntlet; "
        f"print(json.dumps(run_gauntlet({agent!r}, {opponent_names!r}, {n!r})))"
    )
    proc = subprocess.run(
        [python_exe, "-c", code], cwd=str(_ROOT), env=env, capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise RuntimeError(f"arm subprocess failed (learned_eval={learned_eval}):\n{proc.stderr}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def run_ab(agent, opponent_names, n, python_exe=None, log=None) -> dict:
    """Run the off arm then the on arm, n matches each, and diff their win rates.

    log, if given, is called with a one-line progress string after each arm
    (a plain print by default), so a long run started in the background still
    leaves a trace of progress.
    """
    python_exe = python_exe or sys.executable
    log = log or print
    results = {}
    for label, flag in (("off", False), ("on", True)):
        t0 = time.time()
        results[label] = _run_arm(agent, opponent_names, n, flag, python_exe)
        elapsed = time.time() - t0
        log(
            f"arm {label} (PTCG_LEARNED_EVAL={'1' if flag else '0'}): "
            f"win rate {results[label]['win_rate']:.1%} over {results[label]['matches']} matches, "
            f"{elapsed:.0f}s"
        )
    diff_pp = round((results["on"]["win_rate"] - results["off"]["win_rate"]) * 100, 2)
    verdict = "flip default on" if diff_pp > GATE_MARGIN_PP else "keep default off"
    return {
        "agent": agent,
        "opponents": opponent_names,
        "matches_per_arm": n,
        "off": results["off"],
        "on": results["on"],
        "diff_pp": diff_pp,
        "gate_margin_pp": GATE_MARGIN_PP,
        "verdict": verdict,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("agent", help="agent under test (e.g. search)")
    ap.add_argument("opponents", nargs="+", help="opponent names (e.g. deck:aggro deck:control)")
    ap.add_argument("-n", "--matches", type=int, default=400, help="matches per arm")
    ap.add_argument("-o", "--out", help="write the JSON result to this path")
    args = ap.parse_args()
    result = run_ab(args.agent, args.opponents, args.matches)
    print(json.dumps(result, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2))
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
