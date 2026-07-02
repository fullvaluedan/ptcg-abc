"""Ladder replay -> training rows converter (plan U3b).

Reads every replay JSON under data/replays/ (as saved by tools/harvest_replays.py,
U3a) and turns each decision state into a training row, mirroring the
state-outcome logging tools/gauntlet.py does for gauntlet games (plan U1): one row
per seat per decision, features from ptcg_agent.features.extract_features,
labelled with that seat's final result. Draws and games whose outcome cannot be
determined are dropped entirely (neither seat contributes rows). Malformed replay
files are skipped rather than aborting the whole batch.

Output columns mirror the gauntlet CSV (game_id, seat, turn, FEATURE_NAMES...,
label) plus a trailing source column tagged "ladder", so tools/train_eval.py (U4)
can concatenate both sources by column name.

GATE: if the resulting class balance falls outside 30-70 percent, the majority
label is downsampled to a 50/50 split with a fixed seed, so a lopsided batch of
episodes never trains a systematically biased evaluator.

Dev tool only; never shipped. Ladder replay JSON is gitignored competition data,
never committed or redistributed.
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.replay_trace import episode_id_of  # noqa: E402
from ptcg_agent.features import FEATURE_NAMES, extract_features  # noqa: E402
from tools.scout import load_replay  # noqa: E402

DEFAULT_SRC_DIR = _ROOT / "data" / "replays"
DEFAULT_OUT_DIR = _ROOT / "data" / "training"
SOURCE = "ladder"
BALANCE_LO = 0.30
BALANCE_HI = 0.70
DOWNSAMPLE_SEED = 0


def _seat_labels(replay):
    """{0: 1/0, 1: 1/0} final result per seat, or None for a draw/undetermined game.

    Mirrors the rewards comparison analysis.loss_classifier.parse_replay uses for
    outcome, generalized to both seats at once instead of one our_index at a time.
    """
    if not isinstance(replay, dict):
        return None
    steps = replay.get("steps") or []
    rewards = replay.get("rewards")
    if not rewards and steps:
        last = steps[-1]
        if isinstance(last, (list, tuple)) and len(last) == 2 and all(isinstance(e, dict) for e in last):
            rewards = [last[0].get("reward"), last[1].get("reward")]
    if not rewards or len(rewards) != 2 or rewards[0] is None or rewards[1] is None:
        return None
    if rewards[0] == rewards[1]:
        return None
    return {0: 1 if rewards[0] > rewards[1] else 0, 1: 1 if rewards[1] > rewards[0] else 0}


def rows_from_replay(replay, game_id: str) -> list:
    """One row per seat per decision state in `replay`, or [] for a draw/error.

    Walks every step the same way analysis.loss_classifier.parse_replay does
    (ACTIVE entries with a real select and current state, the deck handshake
    skipped), extracts that seat's own feature vector, and labels it with the
    seat's final result from _seat_labels.
    """
    labels = _seat_labels(replay)
    if labels is None:
        return []
    rows = []
    for step in replay.get("steps") or []:
        if not isinstance(step, (list, tuple)):
            continue
        for p, entry in enumerate(step):
            if not isinstance(entry, dict) or entry.get("status") != "ACTIVE":
                continue
            obs = entry.get("observation") or {}
            sel = obs.get("select")
            current = obs.get("current")
            if sel is None or current is None:
                continue  # deck handshake
            seat = current.get("yourIndex", p)
            if seat not in (0, 1):
                continue
            feats = extract_features(current, seat)
            rows.append([game_id, seat, current.get("turn", 0), *feats, labels[seat]])
    return rows


def convert_dir(src_dir=None) -> list:
    """Rows from every replay JSON in src_dir. Malformed files are skipped."""
    src_dir = Path(src_dir) if src_dir else DEFAULT_SRC_DIR
    rows = []
    for path in sorted(Path(src_dir).glob("*.json")):
        try:
            replay = load_replay(path)
        except (OSError, ValueError):
            continue
        try:
            rows.extend(rows_from_replay(replay, episode_id_of(path.name)))
        except (AttributeError, TypeError, KeyError):
            continue
    return rows


def _class_balance(rows) -> float:
    if not rows:
        return 0.0
    wins = sum(1 for row in rows if row[-1] == 1)
    return wins / len(rows)


def downsample_to_balance(rows, lo: float = BALANCE_LO, hi: float = BALANCE_HI,
                           seed: int = DOWNSAMPLE_SEED) -> list:
    """Trim the majority label to match the minority count when balance is bad.

    Only fires when the raw class balance (label==1 fraction) falls outside
    [lo, hi]; otherwise rows pass through unchanged. Deterministic (fixed seed)
    so a re-run on the same rows drops the same ones.
    """
    if not rows:
        return rows
    balance = _class_balance(rows)
    if lo <= balance <= hi:
        return rows
    majority = 1 if balance > hi else 0
    keep, majority_rows = [], []
    for row in rows:
        (majority_rows if row[-1] == majority else keep).append(row)
    rng = random.Random(seed)
    rng.shuffle(majority_rows)
    keep.extend(majority_rows[: len(keep)])  # match the minority count, a 50/50 split
    return keep


def write_csv(rows, out_path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["game_id", "seat", "turn", *FEATURE_NAMES, "label", "source"])
        for row in rows:
            writer.writerow([*row, SOURCE])
    return out_path


def main():
    ap = argparse.ArgumentParser(description="convert downloaded ladder replays into training rows")
    ap.add_argument("--dir", default=str(DEFAULT_SRC_DIR),
                     help="directory of replay JSON files (default data/replays)")
    ap.add_argument("--out", default=None,
                     help="output CSV path (default data/training/ladder_rows_<timestamp>.csv)")
    args = ap.parse_args()

    rows = convert_dir(args.dir)
    before = _class_balance(rows)
    rows = downsample_to_balance(rows)
    after = _class_balance(rows)

    out_path = Path(args.out) if args.out else DEFAULT_OUT_DIR / f"ladder_rows_{int(time.time())}.csv"
    write_csv(rows, out_path)
    print(f"wrote {len(rows)} rows to {out_path} (class balance {before:.1%} -> {after:.1%})")


if __name__ == "__main__":
    main()
