"""Sanity-check a state-outcome or move-ordering training CSV (plans U3, U8a).

Reads a CSV produced by tools/gauntlet.py --log-states (columns: game_id, seat,
turn, FEATURE_NAMES..., label) and reports the checks the plan requires before
training: class balance between 35 and 65 percent labelled wins, no NaNs or
unparseable values anywhere, and the observed min/max of every feature column.
Exits non-zero if class balance or the no-NaN check fails, so a bad dataset
generation run is caught before tools/train_eval.py (U4) wastes time on it.

Also reads the move-ordering schema (tools/gauntlet.py --log-moves or
tools/replays_to_rows.py --log-moves, columns: game_id, seat, decision_id,
n_options, option_index, is_chosen, imitation FEATURE_NAMES..., source),
detected by the presence of a decision_id column: checks is_chosen's raw class
balance against the naturally-imbalanced expected rate (~1/n_options averaged
over decisions, not 50/50), and that every (game_id, decision_id) group has
exactly one option row per its own n_options and at most one is_chosen=1 row,
so a logging bug (a truncated or duplicated decision) is caught before
tools/train_move_prior.py (U8b) trains on it.

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


def move_report(path) -> dict:
    """Class balance and decision-group integrity for a move-ordering CSV (U8a).

    Groups rows by (game_id, decision_id): each group must contain exactly
    n_options rows (no truncated or duplicated decision) and at most one
    is_chosen=1 row (a chosen index that failed to resolve at capture time
    leaves a group with zero, which is valid; more than one is a logging bug).
    class_balance is is_chosen's raw mean; expected_balance is the number of
    decision groups over the number of rows, i.e. mean(1/n_options) weighted by
    group size, the natural (not 50/50) rate a correct capture produces.
    """
    header, rows = load(path)
    n_rows = len(rows)
    n_games = len({row[0] for row in rows}) if rows else 0
    game_idx = header.index("game_id")
    decision_idx = header.index("decision_id")
    n_opt_idx = header.index("n_options")
    is_chosen_idx = header.index("is_chosen")

    groups = {}
    for row in rows:
        groups.setdefault((row[game_idx], row[decision_idx]), []).append(row)

    bad_group_size = 0
    multi_chosen = 0
    n_chosen = 0
    for grp in groups.values():
        try:
            n_opt = int(grp[0][n_opt_idx])
        except ValueError:
            bad_group_size += 1
            continue
        if len(grp) != n_opt:
            bad_group_size += 1
        chosen_count = sum(1 for r in grp if r[is_chosen_idx] == "1")
        if chosen_count > 1:
            multi_chosen += 1
        n_chosen += chosen_count

    n_decisions = len(groups)
    class_balance = n_chosen / n_rows if n_rows else 0.0
    expected_balance = n_decisions / n_rows if n_rows else 0.0
    return {
        "path": str(path),
        "n_rows": n_rows,
        "n_games": n_games,
        "n_decisions": n_decisions,
        "class_balance": round(class_balance, 4),
        "expected_balance": round(expected_balance, 4),
        "bad_group_size": bad_group_size,
        "group_size_ok": bad_group_size == 0,
        "multi_chosen_groups": multi_chosen,
        "multi_chosen_ok": multi_chosen == 0,
        "ok": bad_group_size == 0 and multi_chosen == 0,
    }


def _format_move(result: dict) -> str:
    return "\n".join([
        f"move dataset report: {result['path']}",
        f"  rows: {result['n_rows']}  games: {result['n_games']}  decisions: {result['n_decisions']}",
        f"  is_chosen rate: {result['class_balance']:.1%} (expected ~{result['expected_balance']:.1%} "
        f"from mean 1/n_options)",
        f"  decision group sizes match n_options: {'OK' if result['group_size_ok'] else 'FAIL'} "
        f"({result['bad_group_size']} bad groups)",
        f"  at most one chosen option per decision: {'OK' if result['multi_chosen_ok'] else 'FAIL'} "
        f"({result['multi_chosen_groups']} groups with >1 chosen)",
    ])


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
    ap.add_argument("csv_path", help="path to a states_*.csv or move_rows_*.csv training file")
    args = ap.parse_args()
    header, _rows = load(args.csv_path)
    if "decision_id" in header:
        result = move_report(args.csv_path)
        print(_format_move(result))
        if not result["ok"]:
            sys.exit(1)
    else:
        result = report(args.csv_path)
        print(_format(result))
        if not (result["balance_ok"] and result["nan_ok"]):
            sys.exit(1)


if __name__ == "__main__":
    main()
