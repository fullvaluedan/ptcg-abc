"""Aggregate progress across a teacher self-play label harvest (plan U83 prep).

Prior iterations checked harvest progress by hand (`wc -l`, eyeballing file
mtimes). That does not answer the question `analysis/cem_run_prio_pooled.md`'s
re-open condition (a) actually asks: how many DISTINCT GAMES has the corpus
seen (records are per-decision, and one game contributes many decisions), and
how does that split across train/test once `analysis.teacher_labels.split_of`
buckets it. This module answers that directly from whatever `.jsonl` shards
already exist under a directory, whether they came from the sequential CLI
path or `run_teacher_selfplay_parallel`'s shards; `load_records` already reads
a directory as every member file and stamps `_source`, so no merge step or
knowledge of run tags is needed here.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from analysis import teacher_labels  # noqa: E402

DEFAULT_LOG_DIR = _ROOT / "data" / "training"


def scan(source, limit=None):
    """Aggregate stats for every teacher-label record under `source`.

    `source` is a `.jsonl` file or a directory of them (same contract as
    `teacher_labels.load_records`). Returns a dict with total record and game
    counts, the train/test game split (by `teacher_labels.split_of`, which
    splits on the whole game so a game's decisions never straddle both), and a
    per-source-file record count for spotting a stalled or empty shard.
    """
    games = set()
    train_games = set()
    test_games = set()
    per_source = {}
    n_records = 0
    for rec in teacher_labels.load_records(source, limit=limit):
        n_records += 1
        key = teacher_labels.match_key(rec)
        games.add(key)
        if teacher_labels.split_of(rec) == "test":
            test_games.add(key)
        else:
            train_games.add(key)
        src = rec.get("_source", "")
        per_source[src] = per_source.get(src, 0) + 1
    return {
        "records": n_records,
        "games": len(games),
        "train_games": len(train_games),
        "test_games": len(test_games),
        "per_source": per_source,
    }


def format_report(stats) -> str:
    lines = [
        f"records: {stats['records']}",
        f"games: {stats['games']} (train {stats['train_games']}, test {stats['test_games']})",
        f"shards: {len(stats['per_source'])}",
    ]
    for name in sorted(stats["per_source"]):
        lines.append(f"  {name}: {stats['per_source'][name]} records")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", nargs="?", default=str(DEFAULT_LOG_DIR),
                     help="a .jsonl file or a directory of them (default data/training/)")
    ap.add_argument("--limit", type=int, default=None, help="cap records scanned")
    args = ap.parse_args(argv)
    stats = scan(args.source, limit=args.limit)
    print(format_report(stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
