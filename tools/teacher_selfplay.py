"""Teacher self-play label harvester (plan U83, teacher-student distill, prep step).

OFFLINE ONLY. Never bundled into a submission. Runs a "teacher" agent (default:
the full determinized-search stack on the trolley deck, the same
`search+trolley` build the L5 ring already calibrated at tau 0.857,
`tools.ring_calibrate._search_trolley_agent`) against opponents (default: that
same calibrated ring, `tools.ring_calibrate.ring_names`) and logs every
scorable MAIN decision the teacher makes, win or lose, to a JSONL file via
`analysis.teacher_labels.TeacherLogger`.

This module only produces the labels. The teacher never ships; only a later
CEM run's distilled weights would, through the normal offline-filter and
ladder-A/B gates (see `analysis/teacher_labels.py`'s docstring for why this
label source exists: it targets the "materially larger expert-move sample"
re-open condition `analysis/cem_run_prio_pooled.md` named after the PRIO
genome's second consecutive non-WIN CEM candidate). Wiring these labels into
`tools/cem_tune.py` as a fitness channel is a separate, later step.

A single process harvesting the real search+trolley teacher is slow (the
full determinized-search stack, by design, since a teacher is only useful if
it is stronger than what it is distilling into): a 200-match run takes on the
order of an hour serially. `run_teacher_selfplay_parallel` splits the match
count across worker OS processes (default up to 20, this machine's core
count, matching plan L7's "20-core parallel gauntlet"), each running the
existing sequential `main()` CLI as a subprocess against its own shard file.
Subprocesses rather than a `multiprocessing.Pool` deliberately: the native
engine is a per-process singleton, and shelling out to fresh interpreters
sidesteps ever having to make a teacher factory or fitness callable
picklable. Every shard lands in the same directory, and
`analysis.teacher_labels.load_records` already reads a directory as every
`*.jsonl` member and stamps each record's source file name, so the shards
need no merge step; a caller just points at the directory.
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

from analysis import teacher_labels  # noqa: E402
from ptcg_agent.engine import run_match  # noqa: E402
from tools import opponents  # noqa: E402
from tools import ring_calibrate  # noqa: E402

DEFAULT_LOG_DIR = _ROOT / "data" / "training"
MAX_DEFAULT_WORKERS = 20


def _default_teacher():
    return ring_calibrate._search_trolley_agent()


def resolve_teacher_factory(name):
    """A zero-arg agent factory named by `name`, for the CLI and worker subprocesses.

    "search_trolley" (the CLI default) resolves to the real teacher
    (`_default_teacher`). Any other name is looked up lazily via
    `tools.opponents.get`, so a fast opponent like "baseline" can stand in as
    a fake teacher in tests without a lambda (subprocess args must be plain
    strings anyway, so this is also how `--teacher` reaches a worker).
    """
    if name == "search_trolley":
        return _default_teacher
    return lambda: opponents.get(name)


def _split_counts(n_matches, workers):
    """Split `n_matches` into `workers` near-equal, non-negative chunks."""
    base, rem = divmod(n_matches, workers)
    return [base + (1 if i < rem else 0) for i in range(workers)]


def run_teacher_selfplay(opponent_names=None, n_matches=20, out_path=None,
                          teacher_factory=None):
    """Play the teacher against `opponent_names`, logging its own decisions.

    `opponent_names` defaults to the calibrated L5 ring
    (`ring_calibrate.ring_names()`, tau 0.857); `teacher_factory` defaults to
    the real `search+trolley` build and is injectable so a fast fake teacher
    can drive a quick test without paying the real search cost. Alternates who
    plays first like `tools.gauntlet`, and only the TEACHER's decisions are
    logged (the opponent seat is always a different agent). Raises if no
    opponent is available, since a ring of zero opponents cannot generate
    labels.
    """
    opponent_names = opponent_names if opponent_names is not None else ring_calibrate.ring_names()
    if not opponent_names:
        raise RuntimeError("no opponents available; build the clone ring first")
    teacher_factory = teacher_factory or _default_teacher
    out_path = Path(out_path) if out_path else DEFAULT_LOG_DIR / f"teacher_labels_{int(time.time())}.jsonl"
    logger = teacher_labels.TeacherLogger(out_path)
    wins = draws = losses = 0
    decisions = 0
    try:
        for i in range(n_matches):
            teacher_fn = teacher_factory()
            opp_fn = opponents.get(opponent_names[i % len(opponent_names)])
            swap_first = (i % 2 == 1)
            teacher_seat = 1 if swap_first else 0
            rows = []
            wrapped_teacher = logger.wrap(teacher_fn, i, teacher_seat, rows)
            res = run_match(wrapped_teacher, opp_fn, swap_first=swap_first)
            logger.flush_game(rows)
            decisions += len(rows)
            r = res["reward_a"]
            if r == 1:
                wins += 1
            elif r == -1:
                losses += 1
            else:
                draws += 1
    finally:
        logger.close()
    n = wins + draws + losses
    return {
        "matches": n,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": wins / n if n else 0.0,
        "decisions_logged": decisions,
        "log_path": str(out_path),
    }


def run_teacher_selfplay_parallel(n_matches, workers=None, opponent_names=None,
                                   teacher="search_trolley", out_dir=None, run_tag=None,
                                   python_exe=None):
    """Split `n_matches` across worker subprocesses, each a normal CLI run.

    Each worker writes its own `<run_tag>_w<i>.jsonl` shard (plus a matching
    `.stats.json`) under `out_dir` and is launched via `python tools/
    teacher_selfplay.py ...` (not `multiprocessing`, see module docstring).
    `workers` defaults to `min(MAX_DEFAULT_WORKERS, os.cpu_count())`, capped at
    `n_matches` so no worker is asked to play zero games. Raises if any worker
    subprocess exits non-zero. The returned dict adds `shard_paths`, `out_dir`,
    and `workers` on top of the same keys `run_teacher_selfplay` returns
    (`decisions_logged` in place of a single `log_path`, since the labels now
    live in several files); pass `out_dir` straight to
    `analysis.teacher_labels.load_records`, which already reads a whole
    directory of shards.
    """
    if n_matches <= 0:
        raise ValueError("n_matches must be positive")
    workers = workers if workers else min(MAX_DEFAULT_WORKERS, os.cpu_count() or 1)
    workers = max(1, min(workers, n_matches))
    out_dir = Path(out_dir) if out_dir else DEFAULT_LOG_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    run_tag = run_tag or f"teacher_parallel_{int(time.time())}"
    python_exe = python_exe or sys.executable
    script = str(_ROOT / "tools" / "teacher_selfplay.py")

    counts = [c for c in _split_counts(n_matches, workers) if c > 0]
    shard_paths, stats_paths, procs = [], [], []
    for i, count in enumerate(counts):
        shard = out_dir / f"{run_tag}_w{i}.jsonl"
        stats_path = out_dir / f"{run_tag}_w{i}.stats.json"
        cmd = [python_exe, script, "-n", str(count), "--out", str(shard),
               "--teacher", teacher, "--stats-out", str(stats_path)]
        if opponent_names:
            cmd += ["--opponents", ",".join(opponent_names)]
        procs.append(subprocess.Popen(cmd, cwd=str(_ROOT)))
        shard_paths.append(shard)
        stats_paths.append(stats_path)

    for cmd_i, p in enumerate(procs):
        rc = p.wait()
        if rc != 0:
            raise RuntimeError(f"teacher_selfplay worker {cmd_i} exited with code {rc}")

    wins = draws = losses = decisions = 0
    for stats_path in stats_paths:
        with open(stats_path, encoding="utf-8") as fh:
            s = json.load(fh)
        wins += s["wins"]
        draws += s["draws"]
        losses += s["losses"]
        decisions += s["decisions_logged"]
    n = wins + draws + losses
    return {
        "matches": n,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": wins / n if n else 0.0,
        "decisions_logged": decisions,
        "out_dir": str(out_dir),
        "shard_paths": [str(p) for p in shard_paths],
        "workers": len(procs),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-n", "--matches", type=int, default=20)
    ap.add_argument("--out", default=None, help="JSONL path (default data/training/teacher_labels_<ts>.jsonl)")
    ap.add_argument("--teacher", default="search_trolley",
                     help="teacher factory name: search_trolley (default, the real "
                          "search+trolley build) or any tools.opponents name (e.g. "
                          "baseline, for fast tests/smoke runs)")
    ap.add_argument("--opponents", default=None,
                     help="comma-separated opponent names (default: the calibrated L5 ring)")
    ap.add_argument("--stats-out", default=None, help="also write the stats dict as JSON to this path")
    ap.add_argument("--workers", type=int, default=1,
                     help="parallel worker subprocesses (default 1 = sequential in-process run; "
                          ">1 splits --matches across that many `python tools/teacher_selfplay.py` "
                          "subprocesses instead, ignoring --out in favor of --out-dir shards)")
    ap.add_argument("--out-dir", default=None,
                     help="shard directory for --workers > 1 (default data/training/)")
    ap.add_argument("--run-tag", default=None,
                     help="shard file name prefix for --workers > 1 (default teacher_parallel_<ts>)")
    args = ap.parse_args(argv)
    opponent_names = args.opponents.split(",") if args.opponents else None

    if args.workers > 1:
        stats = run_teacher_selfplay_parallel(
            n_matches=args.matches, workers=args.workers, opponent_names=opponent_names,
            teacher=args.teacher, out_dir=args.out_dir, run_tag=args.run_tag,
        )
        print(f"teacher vs ring over {stats['matches']} matches ({stats['workers']} workers)")
        print(f"  win rate: {stats['win_rate']:.1%}  W/D/L: {stats['wins']}/{stats['draws']}/{stats['losses']}")
        print(f"  decisions logged: {stats['decisions_logged']}")
        print(f"  shards in: {stats['out_dir']}")
    else:
        teacher_factory = resolve_teacher_factory(args.teacher)
        stats = run_teacher_selfplay(opponent_names=opponent_names, n_matches=args.matches,
                                      out_path=args.out, teacher_factory=teacher_factory)
        print(f"teacher vs ring over {stats['matches']} matches")
        print(f"  win rate: {stats['win_rate']:.1%}  W/D/L: {stats['wins']}/{stats['draws']}/{stats['losses']}")
        print(f"  decisions logged: {stats['decisions_logged']}")
        print(f"  log: {stats['log_path']}")

    if args.stats_out:
        with open(args.stats_out, "w", encoding="utf-8") as fh:
            json.dump(stats, fh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
