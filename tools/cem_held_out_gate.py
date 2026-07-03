"""Held-out KTD1/KTD4 gate for a CEM candidate (plan U83, LOOP_BRIEF L7 step c).

Every CEM candidate so far (U35 pool-only, the pooled predecessor recorded in
`analysis/cem_run_prio_pooled.md`) was gated by hand: run the default vector
and the tuned vector separately against the held-out 'test' split, diff the
agreement, and write the WIN/BLOCKED verdict into a fresh markdown file each
time. This module is that same comparison as reusable code, so the next
candidate (the U83 teacher-corpus distill run, or any later one) gets the
same honest check without a fresh hand computation.

Per KTD1/KTD4 as actually applied in `cem_run_prio_pooled.md` ("block, never
promote on a non-positive read"): a candidate may spend a ladder slot only on
a STRICTLY POSITIVE held-out agreement delta (tuned - default) on the clean
'test' split. A delta of exactly zero is not evidence of a real generalizing
improvement, so it BLOCKS, same as a negative delta.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools import weight_space as ws  # noqa: E402
from tools.cem_tune import evaluate_raw  # noqa: E402

WIN = "WIN"
BLOCKED = "BLOCKED"


def held_out_spec(source, is_teacher=True, limit=None, teams=None):
    """Build an `_internal_evaluate` spec scored only on the held-out 'test' split."""
    spec = {"split": "test", "limit": limit, "teams": teams}
    if is_teacher:
        spec["teacher_labels"] = source
    else:
        spec["replays"] = source
    return spec


def gate(tuned_vector, source, is_teacher=True, limit=None, teams=None,
         python=None, runner=None):
    """Compare `tuned_vector` against the default vector on the held-out split.

    Returns {default_agreement, tuned_agreement, delta, verdict}. Either
    agreement may be None if the evaluator could not score it (empty source,
    no scorable decisions in the split); the gate then BLOCKS, since a missing
    baseline or candidate reading is never evidence of an improvement.
    """
    spec = held_out_spec(source, is_teacher=is_teacher, limit=limit, teams=teams)
    default_data = evaluate_raw(
        list(ws.defaults()), spec, python=python, runner=runner
    )
    tuned_data = evaluate_raw(tuned_vector, spec, python=python, runner=runner)
    default_agreement = default_data.get("agreement")
    tuned_agreement = tuned_data.get("agreement")

    if default_agreement is None or tuned_agreement is None:
        delta = None
        verdict = BLOCKED
    else:
        delta = tuned_agreement - default_agreement
        verdict = WIN if delta > 0 else BLOCKED

    return {
        "default_agreement": default_agreement,
        "tuned_agreement": tuned_agreement,
        "delta": delta,
        "verdict": verdict,
    }


def gate_from_cem_result(result_path, source, is_teacher=True, limit=None,
                          teams=None, python=None, runner=None):
    """Load a `tools/cem_tune.py --out` result JSON and gate its best vector."""
    result = json.loads(Path(result_path).read_text(encoding="utf-8"))
    tuned_vector = result["best"]["vector"]
    return gate(
        tuned_vector,
        source,
        is_teacher=is_teacher,
        limit=limit,
        teams=teams,
        python=python,
        runner=runner,
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--result", required=True, help="a tools/cem_tune.py --out JSON file")
    ap.add_argument("--teacher-labels", dest="teacher_labels", default=None,
                     help="a .jsonl file or dir from tools/teacher_selfplay.py")
    ap.add_argument("--replays", default=None,
                     help="a .zip or dir of episode JSONs; overrides --teacher-labels")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--teams", nargs="+", default=None)
    args = ap.parse_args(argv)

    if args.replays:
        source, is_teacher = args.replays, False
    elif args.teacher_labels:
        source, is_teacher = args.teacher_labels, True
    else:
        ap.error("one of --replays or --teacher-labels is required")

    verdict = gate_from_cem_result(
        args.result, source, is_teacher=is_teacher, limit=args.limit, teams=args.teams
    )
    print(json.dumps(verdict, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
