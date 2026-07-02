"""Train and export the early-turn archetype classifier (plan U9b).

Reads archetype_rows_*.csv produced by tools/replays_to_archetype_rows.py
(one row per replay: game_id, label, analysis.early_archetype_features's
FEATURE_NAMES, source), splits by GAME (never by row, same leakage guard as
U4/U8b's game_split) into an 80/20 train/held-out set, and fits a
standardized one-vs-rest logistic regression over the collapsed label set
from U9a with the silver archetype label as the target.

GATE: held-out top-1 accuracy (predicted label matches the silver label for
that held-out game) must beat the majority-class baseline (always predict the
label most common in the TRAINING games) by at least GATE_MARGIN, averaged
over DEFAULT_SEEDS' several independent train/held-out splits rather than one
arbitrary split. n=140 games total (2026-07-03 ladder replay pool) is small
enough that a single 28-game held-out split can flip PASS/FAIL on a 1-2 game
swing (checked by hand: seed 0 alone passes at +0.0714 margin, but 4 of the
next 5 seeds fail), so a bare single-split percentage would be misleading;
analysis/archetype_prior_train.md reports the per-seed table plus the mean
margin the gate actually decides on. A below-margin result is a valid
negative result, same posture as U8b/U65's sweep: the model is NOT exported,
and U9c does not wire an unproven model into search.

Exports analysis/archetype_prior.json (feature_names, feature_version, labels
in classes_ order, mean, std, coef, intercept) for U9c's pure-Python scorer to
load at match time. scikit-learn is a dev-only dependency; nothing here ships
in the submission bundle.

Dev tool only; never shipped.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.early_archetype_features import FEATURE_NAMES, feature_version  # noqa: E402
from tools.train_eval import game_split  # noqa: E402

import numpy as np  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.multiclass import OneVsRestClassifier  # noqa: E402

DEFAULT_MODEL_PATH = _ROOT / "analysis" / "archetype_prior.json"
DEFAULT_REPORT_PATH = _ROOT / "analysis" / "archetype_prior_train.md"
GATE_MARGIN = 0.05
DEFAULT_SEEDS = (0, 1, 2, 3, 4)


def load_rows(csv_path, tag_prefix=None):
    """(game_ids, X, y) from an archetype_rows CSV (plan U9a schema).

    y holds the raw label strings (not integer-encoded): OneVsRestClassifier
    handles string class labels directly, and keeping them as strings all the
    way through avoids a separate encode/decode step that could drift from
    the label spelling stored in the exported JSON.
    """
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        game_idx = header.index("game_id")
        label_idx = header.index("label")
        feature_idx = [header.index(name) for name in FEATURE_NAMES]
        game_ids, X, y = [], [], []
        for row in reader:
            gid = f"{tag_prefix}:{row[game_idx]}" if tag_prefix else row[game_idx]
            game_ids.append(gid)
            X.append([float(row[i]) for i in feature_idx])
            y.append(row[label_idx])
    return np.array(game_ids), np.array(X, dtype=float), np.array(y)


def fit_standardized_multiclass(X_train, y_train):
    """Standardize by train-set mean/std and fit a one-vs-rest logistic regression.

    Plan U9b calls for one-vs-rest explicitly (sklearn's LogisticRegression
    itself dropped its multi_class= parameter; OneVsRestClassifier gives the
    same "one binary classifier per label" shape and keeps the exported
    coef/intercept a simple per-label linear score, easy to reproduce in a
    pure-Python scorer, same posture as tools/train_move_prior.py's binary fit).
    """
    mean = X_train.mean(axis=0)
    std = X_train.std(axis=0)
    std = np.where(std == 0, 1.0, std)
    model = OneVsRestClassifier(LogisticRegression(max_iter=1000))
    model.fit((X_train - mean) / std, y_train)
    return model, mean, std


def majority_baseline(y_train, y_test):
    """(accuracy, majority_label) of always predicting y_train's most common label.

    (0.0, None) when either side is empty (no scorable held-out gate result).
    """
    if len(y_train) == 0 or len(y_test) == 0:
        return 0.0, None
    majority_label = Counter(y_train.tolist()).most_common(1)[0][0]
    accuracy = float(np.mean(y_test == majority_label))
    return accuracy, majority_label


def evaluate_seed(game_ids, X, y, test_frac, seed):
    """One train/held-out split's result: a dict with accuracy, baseline,
    baseline_label, correct/total counts, game counts, and the fitted
    (model, mean, std) for this seed's train side.
    """
    train_mask, test_mask = game_split(game_ids, test_frac, seed)
    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]

    model, mean, std = fit_standardized_multiclass(X_train, y_train)
    preds = model.predict((X_test - mean) / std)
    total = len(y_test)
    correct = int(np.sum(preds == y_test)) if total else 0
    accuracy = correct / total if total else 0.0
    baseline, baseline_label = majority_baseline(y_train, y_test)

    return {
        "seed": seed,
        "accuracy": accuracy,
        "baseline": baseline,
        "baseline_label": baseline_label,
        "correct": correct,
        "total": total,
        "n_train_games": len(set(game_ids[train_mask].tolist())),
        "n_test_games": len(set(game_ids[test_mask].tolist())),
        "n_train_rows": int(train_mask.sum()),
        "n_test_rows": int(test_mask.sum()),
        "model": model,
        "mean": mean,
        "std": std,
    }


def multi_seed_gate(game_ids, X, y, seeds=DEFAULT_SEEDS, test_frac=0.2, margin=GATE_MARGIN):
    """Per-seed results plus the gate's actual verdict: mean accuracy minus
    mean baseline across every seed's independent split, not one lucky split.
    """
    results = [evaluate_seed(game_ids, X, y, test_frac, seed) for seed in seeds]
    mean_accuracy = sum(r["accuracy"] for r in results) / len(results)
    mean_baseline = sum(r["baseline"] for r in results) / len(results)
    passed = (mean_accuracy - mean_baseline) >= margin
    return results, mean_accuracy, mean_baseline, passed


def export_model(model, mean, std, path):
    labels = list(model.classes_)
    if len(model.estimators_) == 1 and len(labels) == 2:
        # sklearn's OneVsRestClassifier collapses an exactly-2-class problem
        # to a single estimator for classes_[1] (fitting classes_[0] too
        # would be redundant). classes_[0]'s score is that estimator's exact
        # negation in log-odds space (sigmoid(-z) == 1 - sigmoid(z)), so this
        # reconstructs the missing row rather than silently losing a label.
        estimator = model.estimators_[0]
        coef = [(-estimator.coef_[0]).tolist(), estimator.coef_[0].tolist()]
        intercept = [float(-estimator.intercept_[0]), float(estimator.intercept_[0])]
    else:
        coef = [estimator.coef_[0].tolist() for estimator in model.estimators_]
        intercept = [float(estimator.intercept_[0]) for estimator in model.estimators_]
    payload = {
        "feature_names": list(FEATURE_NAMES),
        "feature_version": feature_version(),
        "labels": labels,
        "mean": mean.tolist(),
        "std": std.tolist(),
        "coef": coef,
        "intercept": intercept,
    }
    Path(path).write_text(json.dumps(payload, indent=2) + "\n")


def write_report(label_counts, results, mean_accuracy, mean_baseline, margin, passed, path):
    lines = [
        "# Early-turn archetype classifier training (plan U9b)",
        "",
        "tools/train_archetype.py fits a standardized one-vs-rest logistic",
        "regression over analysis/early_archetype_features's early-turn vector,",
        "target is the collapsed archetype label from U9a's silver-label rows,",
        "split by GAME (never by row) into train/held-out sets.",
        "",
        "## Setup",
        "",
        "Label counts (all rows, before any train/test split):",
        "",
    ]
    for label, n in sorted(label_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"- {label}: {n}")
    lines += [
        "",
        "n=140 total games (2026-07-03 ladder replay pool) is small enough that",
        "one 28-game held-out split can flip PASS/FAIL on a 1-2 game swing, so",
        "the gate is decided on the MEAN margin across several independent",
        "splits (DEFAULT_SEEDS), not a single arbitrary seed. Per-seed detail:",
        "",
        "| seed | train games | held-out games | accuracy | baseline | margin |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['seed']} | {r['n_train_games']} | {r['n_test_games']} | "
            f"{r['accuracy']:.4f} ({r['correct']}/{r['total']}) | "
            f"{r['baseline']:.4f} ('{r['baseline_label']}') | "
            f"{r['accuracy'] - r['baseline']:+.4f} |"
        )
    lines += [
        "",
        "## Gate",
        "",
        "Mean held-out top-1 accuracy across every seed's split must beat the",
        "mean majority-class baseline (always predict the label most common in",
        f"that seed's TRAINING games) by at least {margin:.0%}.",
        "",
        f"- mean held-out top-1 accuracy: {mean_accuracy:.4f}",
        f"- mean majority-class baseline: {mean_baseline:.4f}",
        f"- mean margin: {mean_accuracy - mean_baseline:+.4f} (need >= {margin:.4f})",
        "",
        f"Verdict: **{'PASS' if passed else 'FAIL'}**.",
        "",
    ]
    if passed:
        lines += [
            "The model (fit on DEFAULT_SEEDS[0]'s train split) is exported to",
            "analysis/archetype_prior.json for U9c to wire behind a flag.",
            "",
        ]
    else:
        n_seed_pass = sum(1 for r in results if r["accuracy"] - r["baseline"] >= margin)
        lines += [
            "This is a valid negative result (same posture as U8b/U65): only "
            f"{n_seed_pass}/{len(results)} individual seeds clear the margin on their",
            "own, so any one of them would have been a cherry-picked,",
            "non-generalizing PASS. The model is NOT exported, and U9c does not",
            "wire an unproven model into search.",
            "",
        ]
    Path(path).write_text("\n".join(lines))
    return Path(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path", help="archetype_rows_*.csv from tools/replays_to_archetype_rows.py")
    ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS))
    ap.add_argument("--out", default=str(DEFAULT_MODEL_PATH))
    ap.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    ap.add_argument("--margin", type=float, default=GATE_MARGIN)
    args = ap.parse_args()

    game_ids, X, y = load_rows(args.csv_path)
    results, mean_accuracy, mean_baseline, passed = multi_seed_gate(
        game_ids, X, y, seeds=args.seeds, test_frac=args.test_frac, margin=args.margin
    )
    label_counts = dict(Counter(y.tolist()))

    for r in results:
        print(f"seed {r['seed']}: games train {r['n_train_games']} test {r['n_test_games']}  "
              f"top-1 accuracy {r['accuracy']:.4f} ({r['correct']}/{r['total']})  "
              f"baseline {r['baseline']:.4f} ('{r['baseline_label']}')  "
              f"margin {r['accuracy'] - r['baseline']:+.4f}")
    print(f"mean top-1 accuracy {mean_accuracy:.4f}  mean baseline {mean_baseline:.4f}  "
          f"mean margin {mean_accuracy - mean_baseline:+.4f}")

    write_report(label_counts, results, mean_accuracy, mean_baseline, args.margin, passed, args.report)
    print(f"wrote {args.report}")

    if not passed:
        sys.exit(
            f"FAIL: mean held-out top-1 accuracy {mean_accuracy:.4f} does not beat mean "
            f"baseline {mean_baseline:.4f} by the required margin {args.margin:.4f}"
        )

    first = results[0]
    export_model(first["model"], first["mean"], first["std"], args.out)
    print(f"exported {args.out}")


if __name__ == "__main__":
    main()
