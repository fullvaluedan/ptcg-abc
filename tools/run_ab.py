"""Gauntlet A/B harness: same agent, opponents, and N, one env flag off vs on.

The flagged modules (search/eval.py's PTCG_LEARNED_EVAL, search/rollout.py's
PTCG_MOVE_PRIOR, ...) read their env flag once at import time (a module-level
constant), so flipping the env var mid-process would not change an
already-imported agent's behavior. Each arm therefore runs as one or more
subprocesses with the flag baked into their environment, and tools/gauntlet.py
itself stays unmodified. flag_name defaults to PTCG_LEARNED_EVAL (the U5 gate
and any later U6 retraining A/B, plan
docs/plans/2026-07-02-002-feat-learned-evaluator-plan.md); pass a different
flag_name (e.g. PTCG_MOVE_PRIOR for the U8c gate) to A/B a different lever with
the same harness.

Each arm fans out across worker subprocesses via
tools.parallel_gauntlet.run_parallel_gauntlet (plan U60) instead of running
n matches sequentially in one subprocess, so a 400-games-per-arm A/B settles
in minutes instead of tens of minutes on this machine's many idle cores.
jobs=1 reproduces the old fully-sequential behavior (e.g. for tests that want
one predictable subprocess call per arm).

Dev tool only; never shipped.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.parallel_gauntlet import run_parallel_gauntlet  # noqa: E402

GATE_MARGIN_PP = 4.0


def _run_arm(agent, opponent_names, n, flag_on, python_exe, jobs=None,
             flag_name="PTCG_LEARNED_EVAL") -> dict:
    """Run one gauntlet arm across `jobs` worker subprocesses with the flag baked into their env."""
    env = os.environ.copy()
    env[flag_name] = "1" if flag_on else "0"
    result = run_parallel_gauntlet(
        agent, opponent_names, n, jobs=jobs, python_exe=python_exe, env=env,
    )
    if result["shard_errors"]:
        raise RuntimeError(
            f"arm subprocess failed ({flag_name}={flag_on}): {result['shard_errors']}"
        )
    return result


def run_ab(agent, opponent_names, n, python_exe=None, log=None, jobs=None,
           flag_name="PTCG_LEARNED_EVAL") -> dict:
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
        results[label] = _run_arm(agent, opponent_names, n, flag, python_exe, jobs=jobs,
                                   flag_name=flag_name)
        elapsed = time.time() - t0
        log(
            f"arm {label} ({flag_name}={'1' if flag else '0'}): "
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


def _empty_arm() -> dict:
    return {"wins": 0, "draws": 0, "losses": 0, "matches": 0}


def _accumulate(total, batch) -> dict:
    for key in ("wins", "draws", "losses", "matches"):
        total[key] += batch[key]
    return total


def load_checkpoint(checkpoint_path) -> dict:
    """Load {"off": {...}, "on": {...}} counts, or a fresh zeroed state if absent."""
    path = Path(checkpoint_path)
    if path.exists():
        data = json.loads(path.read_text())
        return {"off": data.get("off") or _empty_arm(), "on": data.get("on") or _empty_arm()}
    return {"off": _empty_arm(), "on": _empty_arm()}


def save_checkpoint(checkpoint_path, state) -> None:
    Path(checkpoint_path).write_text(json.dumps(state, indent=2))


def run_ab_resumable(
    agent, opponent_names, n, checkpoint_path, batch_size=40,
    python_exe=None, log=None, time_budget_s=None, jobs=None,
    flag_name="PTCG_LEARNED_EVAL",
) -> dict:
    """Run the A/B in small batches, checkpointing counts to checkpoint_path after each.

    A background gauntlet run in this environment does not survive past the
    end of the invoking turn (observed directly: a prior long-running A/B
    died mid-arm with only partial progress). This makes each call resumable
    instead: it picks up wherever checkpoint_path left off, runs batches
    until either both arms reach n matches or time_budget_s elapses, and
    checkpoints after every batch so no more than one batch of progress can
    ever be lost. Returns {"done": False, "off": ..., "on": ...} if the time
    budget cut the run short, or the full run_ab-shaped result (with
    diff_pp/verdict, "done": True) once both arms reach n matches.
    """
    python_exe = python_exe or sys.executable
    log = log or print
    state = load_checkpoint(checkpoint_path)
    start = time.time()
    for label, flag in (("off", False), ("on", True)):
        while state[label]["matches"] < n:
            if time_budget_s is not None and time.time() - start > time_budget_s:
                save_checkpoint(checkpoint_path, state)
                log(
                    f"time budget reached, checkpointed at "
                    f"off={state['off']['matches']}/{n} on={state['on']['matches']}/{n}"
                )
                return {"done": False, **state}
            batch_n = min(batch_size, n - state[label]["matches"])
            batch = _run_arm(agent, opponent_names, batch_n, flag, python_exe, jobs=jobs,
                              flag_name=flag_name)
            state[label] = _accumulate(state[label], batch)
            save_checkpoint(checkpoint_path, state)
            wr = state[label]["wins"] / state[label]["matches"]
            log(f"arm {label}: +{batch_n} -> {state[label]['matches']}/{n} (cum win rate {wr:.1%})")
    off, on = state["off"], state["on"]
    off_wr = off["wins"] / off["matches"] if off["matches"] else 0.0
    on_wr = on["wins"] / on["matches"] if on["matches"] else 0.0
    diff_pp = round((on_wr - off_wr) * 100, 2)
    verdict = "flip default on" if diff_pp > GATE_MARGIN_PP else "keep default off"
    return {
        "agent": agent,
        "opponents": opponent_names,
        "matches_per_arm": n,
        "off": {**off, "win_rate": off_wr},
        "on": {**on, "win_rate": on_wr},
        "diff_pp": diff_pp,
        "gate_margin_pp": GATE_MARGIN_PP,
        "verdict": verdict,
        "done": True,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("agent", help="agent under test (e.g. search)")
    ap.add_argument("opponents", nargs="+", help="opponent names (e.g. deck:aggro deck:control)")
    ap.add_argument("-n", "--matches", type=int, default=400, help="matches per arm")
    ap.add_argument("-o", "--out", help="write the JSON result to this path")
    ap.add_argument(
        "--checkpoint",
        help="resumable mode: run in batches, checkpointing counts to this path across calls",
    )
    ap.add_argument("--batch-size", type=int, default=40, help="games per batch in resumable mode")
    ap.add_argument("--time-budget", type=float, help="seconds; stop and checkpoint once exceeded")
    ap.add_argument(
        "--jobs", type=int, default=None,
        help="worker subprocesses per arm, fanned out via parallel_gauntlet (default: min(cores-2, 16))",
    )
    ap.add_argument(
        "--flag", default="PTCG_LEARNED_EVAL",
        help="env flag to A/B off vs on (default: PTCG_LEARNED_EVAL; e.g. PTCG_MOVE_PRIOR)",
    )
    args = ap.parse_args()
    if args.checkpoint:
        result = run_ab_resumable(
            args.agent, args.opponents, args.matches, args.checkpoint,
            batch_size=args.batch_size, time_budget_s=args.time_budget, jobs=args.jobs,
            flag_name=args.flag,
        )
    else:
        result = run_ab(args.agent, args.opponents, args.matches, jobs=args.jobs, flag_name=args.flag)
    print(json.dumps(result, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2))
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
