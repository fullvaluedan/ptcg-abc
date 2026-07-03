"""Sweep search/eval.py's PTCG_EVAL_BLEND weight in the gauntlet (plan U11).

U5 settled PTCG_LEARNED_EVAL as an on/off switch between the hand-tuned
board_value and the learned evaluator; the A/B showed learned barely ahead
(+0.75pp, analysis/learned_eval_ab.md), short of the 4pp bar needed to flip
the default. This generalizes that switch into a continuous weight
(search/eval.py's _EVAL_BLEND / PTCG_EVAL_BLEND) and asks whether some
in-between blend beats BOTH pure endpoints, which an on/off A/B could never
see by construction.

Each weight in WEIGHTS runs as its own tools.parallel_gauntlet.run_parallel_gauntlet
arm with PTCG_EVAL_BLEND baked into worker subprocess env, mirroring
tools/run_ab.py's _run_arm. Checkpointed per weight (data/training/ by
default) so a run that gets cut off mid-sweep resumes instead of restarting,
the same lesson tools/run_ab.py's run_ab_resumable already learned the hard
way (a background gauntlet run here does not survive past the end of the
invoking turn).

Dev tool only; never shipped.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import os  # noqa: E402

from tools.parallel_gauntlet import run_parallel_gauntlet  # noqa: E402

WEIGHTS = (0.0, 0.25, 0.5, 0.75, 1.0)
DEFAULT_N = 200


def _run_weight(agent, opponent_names, n, weight, python_exe, jobs=None) -> dict:
    env = os.environ.copy()
    env["PTCG_EVAL_BLEND"] = str(weight)
    result = run_parallel_gauntlet(agent, opponent_names, n, jobs=jobs, python_exe=python_exe, env=env)
    if result["shard_errors"]:
        raise RuntimeError(f"arm subprocess failed (PTCG_EVAL_BLEND={weight}): {result['shard_errors']}")
    return result


def load_checkpoint(checkpoint_path) -> dict:
    path = Path(checkpoint_path)
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_checkpoint(checkpoint_path, state) -> None:
    Path(checkpoint_path).write_text(json.dumps(state, indent=2))


def run_sweep(agent, opponent_names, n, weights=WEIGHTS, python_exe=None, log=None,
              jobs=None, checkpoint_path=None) -> dict:
    """Run one gauntlet arm per weight in `weights`, n matches each.

    Resumable: if checkpoint_path is given and already has a result for a
    weight (keyed by its str()), that arm is skipped and the cached result
    reused instead of re-running the games. Returns
    {"weights": [{"weight": w, **result}, ...], "best": {...}, "endpoints_beaten": bool}.
    """
    python_exe = python_exe or sys.executable
    log = log or print
    state = load_checkpoint(checkpoint_path) if checkpoint_path else {}
    rows = []
    for w in weights:
        key = str(w)
        if key in state:
            log(f"weight {w}: cached ({state[key]['win_rate']:.1%} over {state[key]['matches']} matches)")
            rows.append({"weight": w, **state[key]})
            continue
        t0 = time.time()
        result = _run_weight(agent, opponent_names, n, w, python_exe, jobs=jobs)
        elapsed = time.time() - t0
        state[key] = result
        if checkpoint_path:
            save_checkpoint(checkpoint_path, state)
        log(f"weight {w}: win rate {result['win_rate']:.1%} over {result['matches']} matches, {elapsed:.0f}s")
        rows.append({"weight": w, **result})

    best = max(rows, key=lambda r: r["win_rate"])
    off_endpoint = next(r for r in rows if r["weight"] == min(weights))
    on_endpoint = next(r for r in rows if r["weight"] == max(weights))
    endpoints_beaten = (
        best["weight"] not in (off_endpoint["weight"], on_endpoint["weight"])
        and best["win_rate"] > off_endpoint["win_rate"]
        and best["win_rate"] > on_endpoint["win_rate"]
    )
    return {
        "agent": agent,
        "opponents": opponent_names,
        "matches_per_weight": n,
        "weights": rows,
        "best": best,
        "off_endpoint": off_endpoint,
        "on_endpoint": on_endpoint,
        "endpoints_beaten": endpoints_beaten,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("agent", help="agent under test (e.g. search)")
    ap.add_argument("opponents", nargs="+", help="opponent names (e.g. deck:aggro deck:control)")
    ap.add_argument("-n", "--matches", type=int, default=DEFAULT_N, help="matches per weight")
    ap.add_argument("--weights", type=float, nargs="+", default=list(WEIGHTS))
    ap.add_argument("-o", "--out", help="write the JSON result to this path")
    ap.add_argument("--checkpoint", help="resumable mode: cache each weight's result here")
    ap.add_argument("--jobs", type=int, default=None,
                     help="worker subprocesses per weight (default: min(cores-2, 16))")
    args = ap.parse_args()
    result = run_sweep(
        args.agent, args.opponents, args.matches, weights=args.weights,
        jobs=args.jobs, checkpoint_path=args.checkpoint,
    )
    print(json.dumps(result, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2))
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
