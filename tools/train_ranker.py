"""Train and export the outcome-labeled per-option policy ranker.

Reads an outcome_rows_*.csv (tools/build_outcome_dataset.py, the chosen-option
outcome model; the exact formulation and rationale are documented in
analysis/ranker_outcome_model.md), splits by GAME (not row, reusing
tools.train_eval.game_split so the same no-leakage discipline applies here)
into an 80/20 train/test set, and fits BOTH a standardized logistic regression
and a small one-hidden-layer (64 unit) MLP over agents/imitation_features.
FEATURE_NAMES. Reports held-out AUC for both against two baselines:

  1. predict-by-option-order (first-legal): a single-feature logistic
     regression on opt_is_first alone, mirroring tools/train_eval.py's
     BASELINE_FEATURE pattern (there: prize_diff; here: the position signal
     U71 found already correlates with what strong players pick).
  2. the existing eval_model.json state-level heuristic
     (search/learned_eval.predict_win_probability), captured per-decision at
     dataset-build time as the state_eval_p column: scored directly (no fit)
     against the identical held-out rows. This is the same value for every
     option within one decision (a function of board state, not option
     identity), so it cannot rank options against each other -- it is
     reported to show how much the per-option features add over reading the
     board alone, the "if comparable" baseline the plan calls for.

Exports whichever of LR/MLP has the higher held-out AUC to search/
ranker_model.json (search/learned_ranker.py's load format) for match-time use
under agents/heuristics.py's PTCG_RANKER flag.

Dev tool only; never shipped. scikit-learn is a dev-only dependency
(requirements-dev.txt); nothing here ships in the submission bundle.
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

from agents.imitation_features import FEATURE_NAMES, feature_version  # noqa: E402
from tools.train_eval import game_split  # noqa: E402

import numpy as np  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402
from sklearn.neural_network import MLPClassifier  # noqa: E402

DEFAULT_MODEL_PATH = _ROOT / "search" / "ranker_model.json"
BASELINE_FEATURE = "opt_is_first"
HIDDEN_UNITS = 64


def load_rows(csv_path):
    """(game_ids, X, y, state_eval_p) parallel arrays from an outcome_rows_*.csv.

    X is read by FEATURE_NAMES column name (never by position), so a schema
    with extra bookkeeping columns (game_id, seat, decision_id, n_options,
    option_index, is_chosen, state_eval_p, source) never desyncs the feature
    matrix. is_chosen is deliberately NOT read into X: every row in this
    dataset already is the chosen option (analysis/ranker_outcome_model.md),
    so the column is constant and carries no signal.
    """
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        game_idx = header.index("game_id")
        outcome_idx = header.index("outcome")
        feature_idx = [header.index(name) for name in FEATURE_NAMES]
        state_eval_idx = header.index("state_eval_p") if "state_eval_p" in header else None
        game_ids, X, y, state_eval = [], [], [], []
        for row in reader:
            game_ids.append(row[game_idx])
            X.append([float(row[i]) for i in feature_idx])
            y.append(int(row[outcome_idx]))
            state_eval.append(float(row[state_eval_idx]) if state_eval_idx is not None else float("nan"))
    return (np.array(game_ids), np.array(X, dtype=float), np.array(y, dtype=int),
            np.array(state_eval, dtype=float))


def fit_standardized_logreg(X_train, y_train):
    mean = X_train.mean(axis=0)
    std = X_train.std(axis=0)
    std = np.where(std == 0, 1.0, std)
    model = LogisticRegression(max_iter=1000)
    model.fit((X_train - mean) / std, y_train)
    return model, mean, std


def fit_standardized_mlp(X_train, y_train, seed=0, hidden_units=HIDDEN_UNITS):
    mean = X_train.mean(axis=0)
    std = X_train.std(axis=0)
    std = np.where(std == 0, 1.0, std)
    model = MLPClassifier(
        hidden_layer_sizes=(hidden_units,), activation="relu", max_iter=500,
        random_state=seed, early_stopping=True,
    )
    model.fit((X_train - mean) / std, y_train)
    return model, mean, std


def auc_of(model, mean, std, X, y):
    proba = model.predict_proba((X - mean) / std)[:, 1]
    return roc_auc_score(y, proba)


def export_logreg(model, mean, std, path):
    payload = {
        "model_type": "logreg",
        "feature_names": list(FEATURE_NAMES),
        "feature_version": list(feature_version()),
        "mean": mean.tolist(),
        "std": std.tolist(),
        "coef": model.coef_[0].tolist(),
        "intercept": float(model.intercept_[0]),
    }
    Path(path).write_text(json.dumps(payload, indent=2) + "\n")


def export_mlp(model, mean, std, path):
    """Export an sklearn MLPClassifier(hidden_layer_sizes=(N,)) binary model.

    coefs_ = [W0 (n_features, n_hidden), W1 (n_hidden, 1)];
    intercepts_ = [b0 (n_hidden,), b1 (1,)]. w1/b1 are flattened to a plain
    list/scalar (the output layer has exactly one unit for binary
    classification) so search/learned_ranker.py's pure-Python forward pass
    never needs a nested-list dot product for the output layer.
    """
    w0, w1 = model.coefs_
    b0, b1 = model.intercepts_
    payload = {
        "model_type": "mlp",
        "feature_names": list(FEATURE_NAMES),
        "feature_version": list(feature_version()),
        "mean": mean.tolist(),
        "std": std.tolist(),
        "hidden_activation": "relu",
        "w0": w0.tolist(),
        "b0": b0.tolist(),
        "w1": [row[0] for row in w1.tolist()],
        "b1": float(b1[0]),
    }
    Path(path).write_text(json.dumps(payload, indent=2) + "\n")


def train(csv_path, test_frac=0.2, seed=0, hidden_units=HIDDEN_UNITS):
    game_ids, X, y, state_eval = load_rows(csv_path)
    train_mask, test_mask = game_split(game_ids, test_frac, seed)
    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]

    lr_model, lr_mean, lr_std = fit_standardized_logreg(X_train, y_train)
    lr_auc = auc_of(lr_model, lr_mean, lr_std, X_test, y_test)

    mlp_model, mlp_mean, mlp_std = fit_standardized_mlp(X_train, y_train, seed=seed,
                                                          hidden_units=hidden_units)
    mlp_auc = auc_of(mlp_model, mlp_mean, mlp_std, X_test, y_test)

    baseline_idx = [FEATURE_NAMES.index(BASELINE_FEATURE)]
    base_model, base_mean, base_std = fit_standardized_logreg(X_train[:, baseline_idx], y_train)
    baseline_auc = auc_of(base_model, base_mean, base_std, X_test[:, baseline_idx], y_test)

    state_eval_test = state_eval[test_mask]
    have_state_eval = not np.isnan(state_eval_test).any()
    state_eval_auc = float(roc_auc_score(y_test, state_eval_test)) if have_state_eval else None

    return {
        "n_games": len(set(game_ids.tolist())),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "lr_model": lr_model, "lr_mean": lr_mean, "lr_std": lr_std, "lr_auc": float(lr_auc),
        "mlp_model": mlp_model, "mlp_mean": mlp_mean, "mlp_std": mlp_std, "mlp_auc": float(mlp_auc),
        "baseline_auc": float(baseline_auc),
        "state_eval_auc": state_eval_auc,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path")
    ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--hidden-units", type=int, default=HIDDEN_UNITS)
    ap.add_argument("--out", default=str(DEFAULT_MODEL_PATH))
    args = ap.parse_args()

    result = train(args.csv_path, args.test_frac, args.seed, args.hidden_units)

    print(f"games: {result['n_games']}  train rows: {result['n_train']}  "
          f"test rows: {result['n_test']}")
    print(f"LogisticRegression  AUC={result['lr_auc']:.4f}")
    print(f"MLP({args.hidden_units})  AUC={result['mlp_auc']:.4f}")
    print(f"baseline (first-legal, {BASELINE_FEATURE} only)  AUC={result['baseline_auc']:.4f}")
    if result["state_eval_auc"] is not None:
        print(f"baseline (eval_model.json state prize-diff heuristic)  "
              f"AUC={result['state_eval_auc']:.4f}")

    if result["lr_auc"] >= result["mlp_auc"]:
        export_logreg(result["lr_model"], result["lr_mean"], result["lr_std"], args.out)
        print(f"exported LogisticRegression (higher held-out AUC) to {args.out}")
    else:
        export_mlp(result["mlp_model"], result["mlp_mean"], result["mlp_std"], args.out)
        print(f"exported MLP({args.hidden_units}) (higher held-out AUC) to {args.out}")


if __name__ == "__main__":
    main()
