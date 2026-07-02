"""Process-parallel gauntlet runner (plan U60).

tools/gauntlet.py runs matches sequentially because the native engine is a per
process singleton; one process only ever uses one of this machine's cores.
This module gets the other cores back by chunking the requested match count
into N shards and running each shard's tools.gauntlet.run_gauntlet in its own
subprocess (mirroring tools/cem_tune.py's subprocess_fitness and
tools/run_ab.py's _run_arm), then merging the results here in the parent.

Seed honesty: the bundled cabt engine (kaggle_environments' compiled cg.dll /
libcg.so) exposes no seed hook at all, so match-to-match diversity comes from
its own internal entropy regardless of anything this module does. The
per-shard seed this module sets is Python-level only (random.seed in the
worker), which controls any Python-side randomness (e.g. the random_agent
opponent's random.sample calls) for reproducibility; it is not a claim that
the underlying engine itself is seeded.

Each worker logs to its own temp state CSV (the _StateLogger in gauntlet.py
owns one file handle per process, so shards cannot share a file). On merge,
every row's game_id is rewritten to "shard<k>:<original_id>" before writing
the combined CSV, which is what makes shard-local game_ids (each shard's own
0..n-1 range) globally unique after the merge -- required because two shards
otherwise produce colliding ids for their own game 0, game 1, and so on.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.gauntlet import _wilson  # noqa: E402

DEFAULT_LOG_DIR = _ROOT / "data" / "training"


def default_jobs() -> int:
    """min(cores - 2, 16), floored at 1, leaving headroom for the autoloop."""
    cores = os.cpu_count() or 1
    return max(1, min(cores - 2, 16))


def _chunk_matches(n_matches, jobs):
    """Split n_matches into up to `jobs` near-equal positive shard sizes."""
    jobs = max(1, min(jobs, n_matches)) if n_matches > 0 else 0
    if jobs == 0:
        return []
    base, rem = divmod(n_matches, jobs)
    sizes = [base + (1 if i < rem else 0) for i in range(jobs)]
    return [s for s in sizes if s > 0]


def _run_shard(shard_idx, agent, opponent_names, n, seed, log_path, python_exe):
    """Run one shard's matches in a subprocess; return (stats_dict, error_str).

    Exactly one of the two is None. log_path=None means state logging is off
    for this run; otherwise the worker writes its rows there (KTD2: one file
    handle per process).
    """
    log_states = log_path is not None
    log_path_expr = repr(str(log_path)) if log_states else "None"
    code = (
        "import json, random, sys; "
        f"sys.path.insert(0, {str(_ROOT)!r}); sys.path.insert(0, {str(_ROOT / 'src')!r}); "
        f"random.seed({seed!r}); "
        "from tools.gauntlet import run_gauntlet; "
        f"s = run_gauntlet({agent!r}, {opponent_names!r}, {n!r}, "
        f"log_states={log_states!r}, log_path={log_path_expr}); "
        "print(json.dumps(s))"
    )
    proc = subprocess.run(
        [python_exe, "-c", code], cwd=str(_ROOT), capture_output=True, text=True
    )
    if proc.returncode != 0:
        tail = proc.stderr.strip().splitlines()
        detail = tail[-1] if tail else f"exit code {proc.returncode}"
        return None, f"shard {shard_idx}: {detail}"
    lines = proc.stdout.strip().splitlines()
    if not lines:
        return None, f"shard {shard_idx}: no output"
    try:
        return json.loads(lines[-1]), None
    except ValueError as exc:
        return None, f"shard {shard_idx}: unparseable output ({exc})"


def _merge_logs(shard_results, out_path):
    """Concatenate shard state CSVs into out_path, namespacing and deduping game_id.

    Dedup is by GAME (all rows sharing one namespaced game_id), not by row: a
    game legitimately contributes many rows (one per seat per decision), and
    only a re-merged duplicate shard file should ever collide. Rows for a
    given game are contiguous within one shard file (gauntlet.py's
    _StateLogger flushes one game at a time), so a seen-game boundary check
    while scanning is sufficient. Returns (out_path, row_count). Missing or
    empty shard files are skipped rather than raising, since a shard that
    logged no rows is not an error.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    seen_games = set()
    row_count = 0
    with open(out_path, "w", newline="") as out_fh:
        writer = None
        for shard_idx, stats in shard_results:
            log_path = stats.get("log_path")
            if not log_path or not Path(log_path).exists():
                continue
            with open(log_path, newline="") as fh:
                rows = list(csv.reader(fh))
            if not rows:
                continue
            if writer is None:
                writer = csv.writer(out_fh)
                writer.writerow(rows[0])
            current_gid, current_allowed = None, True
            for row in rows[1:]:
                if not row:
                    continue
                gid = f"shard{shard_idx}:{row[0]}"
                if gid != current_gid:
                    current_gid = gid
                    current_allowed = gid not in seen_games
                    if current_allowed:
                        seen_games.add(gid)
                if not current_allowed:
                    continue
                writer.writerow([gid, *row[1:]])
                row_count += 1
    return out_path, row_count


def _aggregate_stats(agent, opponent_names, requested_n, shard_results, errors, jobs):
    stats_list = [s for _, s in shard_results]
    completed = sum(s["matches"] for s in stats_list)
    wins = sum(s["wins"] for s in stats_list)
    draws = sum(s["draws"] for s in stats_list)
    losses = sum(s["losses"] for s in stats_list)
    decisions = sum(s["decisions"] for s in stats_list)
    invalid = sum(s["invalid_moves"] for s in stats_list)
    time_ms = sum(s["avg_decision_ms"] * s["decisions"] for s in stats_list)
    lo, hi = _wilson(wins, completed)
    return {
        "agent": agent,
        "opponents": opponent_names,
        "jobs": jobs,
        "requested_matches": requested_n,
        "matches": completed,
        "shortfall": requested_n - completed,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": wins / completed if completed else 0.0,
        "win_rate_ci95": (round(lo, 3), round(hi, 3)),
        "avg_decision_ms": round(time_ms / decisions, 3) if decisions else 0.0,
        "max_decision_ms": max((s["max_decision_ms"] for s in stats_list), default=0.0),
        "decisions": decisions,
        "invalid_moves": invalid,
        "invalid_rate": round(invalid / decisions, 6) if decisions else 0.0,
        "shard_errors": errors,
    }


def run_parallel_gauntlet(
    agent, opponent_names, n_matches, jobs=None, log_states=False,
    log_path=None, seed=0, python_exe=None,
):
    """Run n_matches split across up to `jobs` worker subprocesses; merge results.

    A worker that exits nonzero (or emits unparseable output) is recorded in
    the returned stats' "shard_errors" and simply excluded from the merge; the
    run still reports the survivors' aggregate plus the resulting shortfall,
    rather than raising. jobs defaults to default_jobs(). Each shard gets its
    own base seed (seed + shard_idx) and, if log_states, its own temp CSV
    later merged with shard-namespaced game_ids (module docstring, KTD2).
    """
    jobs = jobs or default_jobs()
    sizes = _chunk_matches(n_matches, jobs)
    python_exe = python_exe or sys.executable

    tmp_dir = Path(tempfile.mkdtemp(prefix="parallel_gauntlet_")) if log_states else None
    try:
        shard_log_paths = (
            [tmp_dir / f"states_shard{i}_{int(time.time())}.csv" for i in range(len(sizes))]
            if log_states else [None] * len(sizes)
        )
        shard_results = []
        errors = []
        with ThreadPoolExecutor(max_workers=max(1, len(sizes))) as ex:
            futures = [
                ex.submit(
                    _run_shard, i, agent, opponent_names, n, seed + i,
                    shard_log_paths[i], python_exe,
                )
                for i, n in enumerate(sizes)
            ]
            for i, fut in enumerate(futures):
                stats, err = fut.result()
                if err is not None:
                    errors.append(err)
                else:
                    shard_results.append((i, stats))

        result = _aggregate_stats(agent, opponent_names, n_matches, shard_results, errors, len(sizes))
        if log_states:
            out_path = Path(log_path) if log_path else DEFAULT_LOG_DIR / f"states_{int(time.time())}.csv"
            merged_path, row_count = _merge_logs(shard_results, out_path)
            result["log_path"] = str(merged_path)
            result["log_rows"] = row_count
        return result
    finally:
        if tmp_dir is not None:
            for p in shard_log_paths:
                if p is not None:
                    try:
                        p.unlink()
                    except OSError:
                        pass
            try:
                tmp_dir.rmdir()
            except OSError:
                pass


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("agent", help="agent under test (e.g. baseline)")
    ap.add_argument("opponents", nargs="+", help="opponent names (e.g. random first)")
    ap.add_argument("-n", "--matches", type=int, default=100)
    ap.add_argument("--jobs", type=int, default=None, help="worker subprocesses (default: min(cores-2, 16))")
    ap.add_argument("--seed", type=int, default=0, help="base seed; shard i uses seed + i")
    ap.add_argument("--log-states", action="store_true",
                     help="log one feature row per decision state per seat to "
                          "data/training/ (also enabled by PTCG_LOG_STATES=1)")
    ap.add_argument("-o", "--out", help="write the JSON result to this path")
    args = ap.parse_args()
    log_states = args.log_states or os.environ.get("PTCG_LOG_STATES") == "1"
    t0 = time.time()
    s = run_parallel_gauntlet(
        args.agent, args.opponents, args.matches, jobs=args.jobs,
        log_states=log_states, seed=args.seed,
    )
    elapsed = time.time() - t0
    ci = s["win_rate_ci95"]
    print(f"{s['agent']} vs {s['opponents']} over {s['matches']}/{s['requested_matches']} matches, {s['jobs']} jobs, {elapsed:.1f}s")
    print(f"  win rate: {s['win_rate']:.1%}  (95% CI {ci[0]:.1%} to {ci[1]:.1%})")
    print(f"  W/D/L: {s['wins']}/{s['draws']}/{s['losses']}")
    print(f"  decision time: avg {s['avg_decision_ms']} ms, max {s['max_decision_ms']} ms over {s['decisions']} decisions")
    print(f"  invalid moves: {s['invalid_moves']} ({s['invalid_rate']:.4%})")
    if s["shard_errors"]:
        print(f"  shard errors ({len(s['shard_errors'])}): {s['shard_errors']}")
    if log_states:
        print(f"  logged {s['log_rows']} states to: {s['log_path']}")
    if args.out:
        Path(args.out).write_text(json.dumps(s, indent=2))
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
