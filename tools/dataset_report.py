"""Sanity-check a state-outcome training CSV (plan U3).

Reads a CSV produced by tools/gauntlet.py --log-states (columns: game_id, seat,
turn, FEATURE_NAMES..., label) and reports the checks the plan requires before
training: class balance between 35 and 65 percent labelled wins, no NaNs or
unparseable values anywhere, and the observed min/max of every feature column.
Exits non-zero if class balance or the no-NaN check fails, so a bad dataset
generation run is caught before tools/train_eval.py (U4) wastes time on it.

Dev tool only; never shipped.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ptcg_agent.features import FEATURE_NAMES  # noqa: E402

BALANCE_LO = 0.35
BALANCE_HI = 0.65


def load(path) -> tuple:
    """(header, data rows) from the CSV at path, rows as raw string lists."""
    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    return rows[0], rows[1:]


def report(path) -> dict:
    """Class balance, NaN count, and per-feature min/max for the CSV at path."""
    header, rows = load(path)
    n_rows = len(rows)
    n_games = len({row[0] for row in rows}) if rows else 0
    label_idx = header.index("label")
    feature_idx = [header.index(name) for name in FEATURE_NAMES]

    n_nan = 0
    bounds = {name: [math.inf, -math.inf] for name in FEATURE_NAMES}
    wins = 0
    for row in rows:
        if row[label_idx] == "1":
            wins += 1
        for name, idx in zip(FEATURE_NAMES, feature_idx):
            try:
                value = float(row[idx])
            except ValueError:
                n_nan += 1
                continue
            if math.isnan(value):
                n_nan += 1
                continue
            lo_hi = bounds[name]
            lo_hi[0] = min(lo_hi[0], value)
            lo_hi[1] = max(lo_hi[1], value)

    class_balance = wins / n_rows if n_rows else 0.0
    return {
        "path": str(path),
        "n_rows": n_rows,
        "n_games": n_games,
        "class_balance": round(class_balance, 4),
        "balance_ok": BALANCE_LO <= class_balance <= BALANCE_HI,
        "n_nan": n_nan,
        "nan_ok": n_nan == 0,
        "feature_stats": {
            name: (round(lo, 4), round(hi, 4)) if hi >= lo else (0.0, 0.0)
            for name, (lo, hi) in bounds.items()
        },
    }


def _format(result: dict) -> str:
    lines = [
        f"dataset report: {result['path']}",
        f"  rows: {result['n_rows']}  games: {result['n_games']}",
        f"  class balance (label=1 fraction): {result['class_balance']:.1%} "
        f"({'OK' if result['balance_ok'] else 'FAIL, want 35-65%'})",
        f"  NaN/unparseable values: {result['n_nan']} ({'OK' if result['nan_ok'] else 'FAIL'})",
        "  feature min/max:",
    ]
    for name in FEATURE_NAMES:
        lo, hi = result["feature_stats"][name]
        lines.append(f"    {name:24s} [{lo}, {hi}]")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path", help="path to a states_*.csv from tools/gauntlet.py --log-states")
    args = ap.parse_args()
    result = report(args.csv_path)
    print(_format(result))
    if not (result["balance_ok"] and result["nan_ok"]):
        sys.exit(1)


if __name__ == "__main__":
    main()
