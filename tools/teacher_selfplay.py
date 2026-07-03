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
"""
from __future__ import annotations

import argparse
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


def _default_teacher():
    return ring_calibrate._search_trolley_agent()


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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-n", "--matches", type=int, default=20)
    ap.add_argument("--out", default=None, help="JSONL path (default data/training/teacher_labels_<ts>.jsonl)")
    args = ap.parse_args(argv)
    stats = run_teacher_selfplay(n_matches=args.matches, out_path=args.out)
    print(f"teacher vs ring over {stats['matches']} matches")
    print(f"  win rate: {stats['win_rate']:.1%}  W/D/L: {stats['wins']}/{stats['draws']}/{stats['losses']}")
    print(f"  decisions logged: {stats['decisions_logged']}")
    print(f"  log: {stats['log_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
