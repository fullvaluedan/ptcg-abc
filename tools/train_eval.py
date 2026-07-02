"""Train and export the learned state evaluator (plan U4).

Reads a states_*.csv produced by tools/gauntlet.py --log-states, splits by
GAME (not row) into an 80/20 train/test set so no game straddles the split,
and fits a standardized logistic regression over ptcg_agent.features'
FEATURE_NAMES. The full model must beat a single-feature baseline (prize_diff
alone) on test-set AUC, or the run fails: that is the bar the plan sets for
"the learned features are worth having".

Exports search/eval_model.json (feature_names, mean, std, coef, intercept)
for search/learned_eval.py, a pure-Python scorer with no sklearn dependency,
to load at match time. scikit-learn itself is a dev-only dependency
(requirements-dev.txt); nothing here ships in the submission bundle.

Dev tool only; never shipped.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ptcg_agent.features import FEATURE_NAMES  # noqa: E402

import numpy as np  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import accuracy_score, roc_auc_score  # noqa: E402

DEFAULT_MODEL_PATH = _ROOT / "search" / "eval_model.json"
BASELINE_FEATURE = "prize_diff"


def load_rows(csv_path):
    """(game_ids, X, y) parallel arrays from a states CSV (tools/gauntlet.py --log-states)."""
    with open(csv_path, newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        game_idx = header.index("game_id")
        label_idx = header.index("label")
        feature_idx = [header.index(name) for name in FEATURE_NAMES]
        game_ids, X, y = [], [], []
        for row in reader:
            game_ids.append(row[game_idx])
            X.append([float(row[i]) for i in feature_idx])
            y.append(int(row[label_idx]))
    return np.array(game_ids), np.array(X, dtype=float), np.array(y, dtype=int)


def game_split(game_ids, test_frac=0.2, seed=0):
    """Boolean (train_mask, test_mask) over rows, split by unique game id.

    Every row from one game lands on the same side, so the model can never see
    a held-out game's states during training (row-level splitting would leak:
    near-duplicate states from the same game would appear on both sides).
    """
    unique_games = sorted(set(game_ids.tolist()))
    rng = np.random.RandomState(seed)
    shuffled = rng.permutation(unique_games)
    n_test_games = max(1, int(round(len(shuffled) * test_frac)))
    test_games = set(shuffled[:n_test_games].tolist())
    test_mask = np.array([g in test_games for g in game_ids])
    return ~test_mask, test_mask


def fit_standardized(X_train, y_train):
    """Standardize by train-set mean/std and fit a logistic regression."""
    mean = X_train.mean(axis=0)
    std = X_train.std(axis=0)
    std = np.where(std == 0, 1.0, std)
    model = LogisticRegression(max_iter=1000)
    model.fit((X_train - mean) / std, y_train)
    return model, mean, std


def evaluate(model, mean, std, X, y):
    proba = model.predict_proba((X - mean) / std)[:, 1]
    preds = (proba >= 0.5).astype(int)
    return {"auc": roc_auc_score(y, proba), "accuracy": accuracy_score(y, preds)}


def export_model(model, mean, std, path):
    payload = {
        "feature_names": list(FEATURE_NAMES),
        "mean": mean.tolist(),
        "std": std.tolist(),
        "coef": model.coef_[0].tolist(),
        "intercept": float(model.intercept_[0]),
    }
    Path(path).write_text(json.dumps(payload, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path", help="states_*.csv from tools/gauntlet.py --log-states")
    ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=str(DEFAULT_MODEL_PATH))
    args = ap.parse_args()

    game_ids, X, y = load_rows(args.csv_path)
    train_mask, test_mask = game_split(game_ids, args.test_frac, args.seed)
    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]

    model, mean, std = fit_standardized(X_train, y_train)
    metrics = evaluate(model, mean, std, X_test, y_test)

    baseline_idx = [FEATURE_NAMES.index(BASELINE_FEATURE)]
    baseline_model, baseline_mean, baseline_std = fit_standardized(
        X_train[:, baseline_idx], y_train
    )
    baseline_metrics = evaluate(
        baseline_model, baseline_mean, baseline_std, X_test[:, baseline_idx], y_test
    )

    print(f"games: {len(set(game_ids.tolist()))}  train rows: {len(X_train)}  test rows: {len(X_test)}")
    print(f"full model  AUC={metrics['auc']:.4f}  accuracy={metrics['accuracy']:.4f}")
    print(f"baseline ({BASELINE_FEATURE} only)  AUC={baseline_metrics['auc']:.4f}")

    if metrics["auc"] <= baseline_metrics["auc"]:
        sys.exit(
            f"FAIL: full model AUC {metrics['auc']:.4f} does not beat the "
            f"{BASELINE_FEATURE}-only baseline {baseline_metrics['auc']:.4f}"
        )

    export_model(model, mean, std, args.out)
    print(f"exported {args.out}")


if __name__ == "__main__":
    main()
