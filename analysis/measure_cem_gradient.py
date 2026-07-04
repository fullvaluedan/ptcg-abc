"""Measure the CEM genome's leverage over the pilot's expert-move agreement.

OFFLINE ONLY. Diagnostic for plan U6. The CEM optimizer (tools/cem_tune.py)
scores a candidate weight vector by two offline filters: the pool win rate (U4)
and the held-out expert-move agreement (U5). For CEM to climb, at least one of
those signals must MOVE as the genome (tools/weight_space.PARAM_SPACE) changes.
This harness measures exactly that leverage on the agreement channel: for each of
the 11 genome dims it holds every other knob at its shipped default, sets that one
dim to its low bound then its high bound, and reports the top-1 agreement each
build scores against the held-out expert decisions. A dim whose low-vs-high
agreement delta is ~0 is INERT: CEM cannot use it to climb the agreement signal.

Why a dim can be inert. The seven search/eval.py shaping weights tune the offline
TEACHER's leaf value; they never enter the shipped pilot's choose(), so they
cannot move the pilot's move agreement at all (a structural zero, not noise). The
four pilot knobs are narrow thresholds (bench width, retreat HP ratio, two deckout
counts) that only fire in a small slice of MAIN decisions, while the dominant
driver of the pilot's choices, the fixed category priority order
(lethal -> rare-candy -> evolve -> play -> attach -> ability -> retreat -> attack
-> end in agents/heuristics.choose), is NOT part of the genome. So the measured
agreement gradient is expected to be near-flat, which is the point this diagnostic
pins down (see analysis/cem_signal_flat.md).

Ship-faithful. Each build is scored in a FRESH subprocess with the candidate's
PTCG_W_* env set, the same clean-runtime contract the grader and cem_tune use, so
a knob read at import can never leak across builds. Reads the competition replay
dataset but never redistributes it (the sample dir stays gitignored).

Teacher-labels mode (condition (c), LOOP_BRIEF L7/U83). The genome now carries the
18-dim PRIO_* ordering (this file's own 2026-07-01 run found ATTACH/ATTACK moved
agreement on a 40-episode real-replay sample), but three later CEM sweeps over
that exact genome (`analysis/cem_run_prio.md`, `_pooled.md`, `_teacher.md`) all
BLOCKED on held-out transfer. Their one remaining named re-open condition is "a
genome region with a measured non-flat held-out gradient" on the SAME held-out
'test' split those sweeps blocked against, not the small real-replay sample. The
`--teacher-labels`/`--split` CLI flags (and `teacher_labels=`/`split=` sweep()
kwargs) point this same per-dim probe at `analysis.teacher_labels`'s corpus
instead of `move_ranking_validator`'s real replays, so that check can be made
directly instead of inferred from a full CEM run's aggregate fitness.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools import weight_space as ws  # noqa: E402


def _score_env(env_overrides, replays, teams, limit, python):
    """Top-1 agreement of a single env-baked pilot build, via a fresh subprocess.

    Spawns the validator's own module in a child whose environment carries the
    PTCG_W_* overrides, so the pilot reads them at import exactly like a baked
    build. Returns (agreement, n_decisions); a missing/None agreement maps to
    (None, n). The child prints one JSON line so parsing stays trivial.
    """
    env = dict(os.environ)
    env.update(env_overrides)
    code = (
        "import json,sys;"
        "sys.path[:0]=['.','src'];"
        "from analysis import move_ranking_validator as m;"
        "from agents.heuristics import choose;"
        "teams=%r;"
        "r=m.score_replays(list(m.load_replays(%r,limit=%r)),choose,teams);"
        "print(json.dumps({'a':r['agreement'],'n':r['n']}))"
        % (list(teams), replays, limit)
    )
    out = subprocess.run(
        [python, "-c", code],
        env=env,
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip().splitlines()[-1]
    data = json.loads(out)
    return data["a"], data["n"]


def _score_env_teacher(env_overrides, teacher_labels, split, limit, python):
    """Same contract as `_score_env`, scored against the U83 teacher corpus.

    Mirrors `tools.cem_tune._internal_evaluate`'s teacher-labels branch (split
    filter via `analysis.teacher_labels.split_of`, agreement via
    `analysis.teacher_labels.agreement`) so this diagnostic can probe the exact
    held-out 'test' split the CEM held-out gate (`tools/cem_held_out_gate.py`)
    blocks candidates on, instead of only the small real-ladder replay sample.
    """
    env = dict(os.environ)
    env.update(env_overrides)
    code = (
        "import json,sys;"
        "sys.path[:0]=['.','src'];"
        "from analysis import teacher_labels as tl;"
        "from agents.heuristics import choose;"
        "records=list(tl.load_records(%r,limit=%r));"
        "split=%r;"
        "records=[r for r in records if tl.split_of(r)==split] "
        "if split in ('train','test') else records;"
        "r=tl.agreement(records, choose);"
        "print(json.dumps({'a':r['agreement'],'n':r['n']}))"
        % (teacher_labels, limit, split)
    )
    out = subprocess.run(
        [python, "-c", code],
        env=env,
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip().splitlines()[-1]
    data = json.loads(out)
    return data["a"], data["n"]


def sweep(replays=None, teams=None, limit=200, python=None, score=None,
          teacher_labels=None, split=None):
    """Per-dim agreement at (low, default, high), one row per genome dim.

    Holds every other knob at its shipped default and moves the one dim to each
    bound, so each row isolates that dim's leverage over the expert-move agreement.
    Returns {"baseline": {...}, "rows": [ {dim, low, high, agr_low, agr_high,
    delta}, ... ]}. `delta` is abs(agr_high - agr_low); a dim with delta ~0 is
    inert on this signal. `score(env_overrides) -> (agreement, n)` defaults to a
    real subprocess scorer and is injectable so a test can drive the orchestration
    without the engine or the dataset. Pure over the parent environment.

    Two label sources: `replays` (real-ladder expert episodes, via
    `move_ranking_validator`, the original U6 diagnostic) or `teacher_labels` (the
    U83 self-play corpus, via `analysis.teacher_labels`, optionally restricted to
    one `split`). `teacher_labels` takes priority when both are given and `score`
    is not overridden.
    """
    python = python or sys.executable
    if score is None:
        if teacher_labels is not None:
            def score(env_overrides):
                return _score_env_teacher(
                    env_overrides, teacher_labels, split, limit, python
                )
        else:
            from analysis.move_ranking_validator import DEFAULT_EXPERT_TEAMS

            resolved_teams = teams or list(DEFAULT_EXPERT_TEAMS)

            def score(env_overrides):
                return _score_env(env_overrides, replays, resolved_teams, limit, python)
    base_agr, base_n = score({})
    rows = []
    for key, default, low, high, cast in ws.PARAM_SPACE:
        lo_env = {} if cast(low) == cast(default) else {key: str(cast(low))}
        hi_env = {} if cast(high) == cast(default) else {key: str(cast(high))}
        agr_lo, _ = score(lo_env)
        agr_hi, _ = score(hi_env)
        delta = (
            abs(agr_hi - agr_lo)
            if agr_lo is not None and agr_hi is not None
            else None
        )
        rows.append(
            {
                "dim": key,
                "low": cast(low),
                "high": cast(high),
                "agr_low": agr_lo,
                "agr_high": agr_hi,
                "delta": delta,
            }
        )
    return {
        "baseline": {"agreement": base_agr, "n": base_n},
        "rows": rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "replays",
        nargs="?",
        default=None,
        help="a .zip of episode JSONs or a directory of *.json expert replays",
    )
    ap.add_argument("--teams", nargs="+", default=None)
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument(
        "--teacher-labels",
        dest="teacher_labels",
        default=None,
        help="a U83 teacher self-play .jsonl file or dir, instead of real replays",
    )
    ap.add_argument(
        "--split",
        default=None,
        choices=["train", "test"],
        help="restrict to one held-out split (teacher-labels mode only)",
    )
    ap.add_argument("--out", default=None, help="write the full result JSON here")
    args = ap.parse_args(argv)

    if not args.replays and not args.teacher_labels:
        ap.error("either a replays source or --teacher-labels is required")

    result = sweep(
        args.replays,
        teams=args.teams,
        limit=args.limit,
        teacher_labels=args.teacher_labels,
        split=args.split,
    )
    base = result["baseline"]
    b = base["agreement"]
    print(
        f"baseline agreement: {b:.4f} (n={base['n']})"
        if b is not None
        else "baseline agreement: n/a"
    )
    print("\nper-dim leverage on expert-move agreement (others at default):")
    print(f"  {'dim':<32} {'low->agr':>12} {'high->agr':>12} {'delta':>8}")
    for r in sorted(result["rows"], key=lambda x: -(x["delta"] or 0.0)):
        al = f"{r['agr_low']:.4f}" if r["agr_low"] is not None else "n/a"
        ah = f"{r['agr_high']:.4f}" if r["agr_high"] is not None else "n/a"
        d = f"{r['delta']:.4f}" if r["delta"] is not None else "n/a"
        print(f"  {r['dim']:<32} {al:>12} {ah:>12} {d:>8}")
    moved = [r for r in result["rows"] if (r["delta"] or 0.0) > 0.0]
    print(
        f"\n{len(moved)}/{len(result['rows'])} dims move agreement at all; "
        f"max delta = {max((r['delta'] or 0.0) for r in result['rows']):.4f}"
    )
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nfull result written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
