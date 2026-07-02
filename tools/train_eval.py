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
DEFAULT_SOURCE_WEIGHT = 1.0


def load_rows(csv_path, tag_prefix=None):
    """(game_ids, X, y) parallel arrays from a states CSV (tools/gauntlet.py --log-states).

    Also reads tools/replays_to_rows.py's ladder CSVs, which share the same
    game_id/FEATURE_NAMES/label columns plus a trailing source column that this
    reader ignores (columns are looked up by name, not position).

    tag_prefix, if given, is prepended to every game_id ("ladder:82976189"
    instead of "82976189"). Gauntlet game ids are small integers and ladder
    game ids are Kaggle episode ids; without a prefix the two id spaces could
    collide when rows from both sources are concatenated for training, which
    would let game_split silently merge two unrelated games onto the same side.
    """
    with open(csv_path, newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        game_idx = header.index("game_id")
        label_idx = header.index("label")
        feature_idx = [header.index(name) for name in FEATURE_NAMES]
        game_ids, X, y = [], [], []
        for row in reader:
            gid = row[game_idx]
            game_ids.append(f"{tag_prefix}:{gid}" if tag_prefix else gid)
            X.append([float(row[i]) for i in feature_idx])
            y.append(int(row[label_idx]))
    return np.array(game_ids), np.array(X, dtype=float), np.array(y, dtype=int)


def parse_source_weights(spec) -> dict:
    """Parse 'top_player=2.0,ladder=1.0' into {"top_player": 2.0, "ladder": 1.0}.

    None or an empty string returns {} (no weighting). Raises ValueError on a
    malformed pair, same as float() would, so a typo in the CLI flag fails
    fast instead of silently training unweighted.
    """
    if not spec:
        return {}
    weights = {}
    for pair in spec.split(","):
        pair = pair.strip()
        if not pair:
            continue
        name, _, val = pair.partition("=")
        weights[name.strip()] = float(val)
    return weights


def load_source_column(csv_path):
    """The 'source' column for every row in csv_path, in row order.

    A row from a CSV with no 'source' column (tools/gauntlet.py's states_*.csv
    predates this column) reads as "" so callers can default it to weight 1.0.
    """
    with open(csv_path, newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        source_idx = header.index("source") if "source" in header else None
        sources = [row[source_idx] if source_idx is not None else "" for row in reader]
    return np.array(sources)


def sample_weights_for(sources, weights, default=DEFAULT_SOURCE_WEIGHT):
    """Per-row sample weight array: weights.get(source, default) for each row."""
    return np.array([weights.get(s, default) for s in sources], dtype=float)


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


def fit_standardized(X_train, y_train, sample_weight=None):
    """Standardize by train-set mean/std and fit a logistic regression.

    sample_weight, if given, is passed straight to LogisticRegression.fit
    (plan U3c's --source-weights hook); None (the default) fits unweighted,
    identical to the original behavior.
    """
    mean = X_train.mean(axis=0)
    std = X_train.std(axis=0)
    std = np.where(std == 0, 1.0, std)
    model = LogisticRegression(max_iter=1000)
    model.fit((X_train - mean) / std, y_train, sample_weight=sample_weight)
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


def compare_gauntlet_vs_merged(
    gauntlet_csv, ladder_csv, test_frac=0.2, seed=0, source_weights=None, extra_sources=None
):
    """Train on gauntlet-only vs gauntlet-plus-ladder(-plus-extras), evaluate both
    on the same held-out gauntlet-only test set (plan U4's ladder-merge comparison).

    The held-out test set is gauntlet-only rows: ladder replays are one-sided
    (we only see games our own submissions played), so a ladder-only or mixed
    test set would not represent the gauntlet matchups the shipped agent
    actually plays. Both models are judged on the same test rows, so the
    comparison isolates the effect of adding ladder (and any extra) rows to
    the training set.

    source_weights, if given (plan U3c's --source-weights hook), applies
    weights["gauntlet"] to the gauntlet train rows, weights["ladder"] to the
    ladder rows, and weights[label] to each extra_sources row in the merged
    fit only (the gauntlet-only fit always stays unweighted, since it has one
    source). A source missing from the dict defaults to DEFAULT_SOURCE_WEIGHT.
    None (the default) fits unweighted, identical to the original behavior.

    extra_sources, if given (plan U6's retrain-generation hook), is a list of
    (label, csv_path) pairs folded into the merged fit only, each tagged with
    its own game_id prefix (so a same-numbered game in two sources never
    collides) and its own source label for source_weights lookups. Rows are
    never added to the gauntlet-only fit or to the held-out test set. None
    (the default) behaves exactly like the pre-U6 two-source signature.

    Returns a dict: gauntlet_only / merged sub-dicts (each with model, mean,
    std, metrics, n_train), the picked variant name, n_ladder_rows,
    extra_source_rows (label -> row count, empty when none were given), and
    source_weights (empty dict when none were given).
    """
    gauntlet_ids, gauntlet_X, gauntlet_y = load_rows(gauntlet_csv, tag_prefix="gauntlet")
    train_mask, test_mask = game_split(gauntlet_ids, test_frac, seed)
    X_train, y_train = gauntlet_X[train_mask], gauntlet_y[train_mask]
    X_test, y_test = gauntlet_X[test_mask], gauntlet_y[test_mask]

    gauntlet_model, gauntlet_mean, gauntlet_std = fit_standardized(X_train, y_train)
    gauntlet_metrics = evaluate(gauntlet_model, gauntlet_mean, gauntlet_std, X_test, y_test)

    _, ladder_X, ladder_y = load_rows(ladder_csv, tag_prefix="ladder")
    merged_parts_X = [X_train, ladder_X]
    merged_parts_y = [y_train, ladder_y]
    weight_labels = ["gauntlet"] * len(X_train) + ["ladder"] * len(ladder_X)
    extra_source_rows = {}
    for label, csv_path in extra_sources or []:
        _, extra_X, extra_y = load_rows(csv_path, tag_prefix=label)
        merged_parts_X.append(extra_X)
        merged_parts_y.append(extra_y)
        weight_labels.extend([label] * len(extra_X))
        extra_source_rows[label] = len(extra_X)

    merged_X = np.concatenate(merged_parts_X, axis=0)
    merged_y = np.concatenate(merged_parts_y, axis=0)
    merged_sample_weight = None
    if source_weights:
        merged_sample_weight = sample_weights_for(weight_labels, source_weights)
    merged_model, merged_mean, merged_std = fit_standardized(
        merged_X, merged_y, sample_weight=merged_sample_weight
    )
    merged_metrics = evaluate(merged_model, merged_mean, merged_std, X_test, y_test)

    picked = "merged" if merged_metrics["auc"] >= gauntlet_metrics["auc"] else "gauntlet_only"

    return {
        "gauntlet_only": {
            "model": gauntlet_model, "mean": gauntlet_mean, "std": gauntlet_std,
            "metrics": gauntlet_metrics, "n_train": len(X_train),
        },
        "merged": {
            "model": merged_model, "mean": merged_mean, "std": merged_std,
            "metrics": merged_metrics, "n_train": len(merged_X),
        },
        "picked": picked,
        "n_test": len(X_test),
        "n_ladder_rows": len(ladder_X),
        "extra_source_rows": extra_source_rows,
        "source_weights": dict(source_weights) if source_weights else {},
    }


def write_ladder_ab_report(result, path):
    """Plain-language analysis/ladder_data_ab.md documenting the comparison and gate verdict."""
    g = result["gauntlet_only"]
    m = result["merged"]
    extra_rows = result.get("extra_source_rows") or {}
    merged_sources = ["ladder", *sorted(extra_rows)]
    picked_label = (
        f"gauntlet+{'+'.join(merged_sources)} (merged)" if result["picked"] == "merged" else "gauntlet-only"
    )
    lines = [
        "# Ladder data A/B: does adding ladder replay rows help the evaluator?",
        "",
        "Plan U4 (v2 redo). Two models trained on the same gauntlet training rows,",
        "one with ladder replay rows added, evaluated on the same held-out",
        "gauntlet-only test set so the comparison isolates the effect of the extra",
        "ladder rows rather than measuring a different test distribution.",
        "",
        "## Setup",
        "",
        f"- Gauntlet-only training rows: {g['n_train']}",
        f"- Ladder rows added for the merged variant: {result['n_ladder_rows']}",
    ]
    for label in sorted(extra_rows):
        lines.append(f"- {label} rows added for the merged variant: {extra_rows[label]}")
    lines += [
        f"- Merged training rows: {m['n_train']}",
        f"- Held-out gauntlet-only test rows: {result['n_test']} (same rows for both models)",
        "",
        "## Results",
        "",
        "| variant | train rows | test AUC | test accuracy |",
        "|---|---|---|---|",
        f"| gauntlet-only | {g['n_train']} | {g['metrics']['auc']:.4f} | {g['metrics']['accuracy']:.4f} |",
        f"| gauntlet+{'+'.join(merged_sources)} | {m['n_train']} | {m['metrics']['auc']:.4f} | {m['metrics']['accuracy']:.4f} |",
        "",
        "## Gate",
        "",
        "Keep the merged model only if its AUC on the gauntlet-only test set is at",
        "least the gauntlet-only model's AUC. Otherwise keep the gauntlet-only model.",
        "",
        f"Verdict: **{picked_label}** wins "
        f"(gauntlet-only AUC {g['metrics']['auc']:.4f}, merged AUC {m['metrics']['auc']:.4f}).",
        f"The exported search/eval_model.json is the {picked_label} model.",
        "",
    ]
    if result.get("source_weights"):
        lines += [
            "## Training weights (--source-weights)",
            "",
            "Sample weights applied to the merged fit only (plan U3c):",
            "",
        ]
        for src, w in sorted(result["source_weights"].items()):
            lines.append(f"- {src}: {w}")
        lines.append(
            f"- any other source (including gauntlet rows if unlisted): {DEFAULT_SOURCE_WEIGHT}"
        )
        lines.append("")
    Path(path).write_text("\n".join(lines))
    return Path(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path", help="states_*.csv from tools/gauntlet.py --log-states")
    ap.add_argument("--ladder-csv", default=None,
                     help="ladder_rows_*.csv from tools/replays_to_rows.py; if given, runs the "
                          "gauntlet-only vs gauntlet+ladder comparison instead of a single fit")
    ap.add_argument("--report", default=str(_ROOT / "analysis" / "ladder_data_ab.md"),
                     help="where to write the comparison report (only used with --ladder-csv)")
    ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=str(DEFAULT_MODEL_PATH))
    ap.add_argument("--source-weights", default=None,
                     help="comma separated source=weight pairs applied as training sample "
                          "weights (plan U3c, e.g. 'top_player=2.0'); a source not listed, "
                          "or a csv with no 'source' column, defaults to weight "
                          f"{DEFAULT_SOURCE_WEIGHT}")
    ap.add_argument("--extra-csv", action="append", default=None,
                     help="label=path, repeatable (plan U6, e.g. "
                          "'gauntlet_gen2=data/training/states_123.csv "
                          "--extra-csv top_player=data/training/top_player_corpus_20260702.csv'); "
                          "folded into the merged fit only, tagged with label for "
                          "--source-weights lookups, never added to the gauntlet-only "
                          "fit or the held-out test set")
    args = ap.parse_args()
    source_weights = parse_source_weights(args.source_weights)
    extra_sources = [pair.split("=", 1) for pair in (args.extra_csv or [])]

    if args.ladder_csv:
        result = compare_gauntlet_vs_merged(
            args.csv_path, args.ladder_csv, args.test_frac, args.seed,
            source_weights=source_weights or None,
            extra_sources=extra_sources or None,
        )
        g, m = result["gauntlet_only"], result["merged"]
        print(f"gauntlet-only  train rows: {g['n_train']}  AUC={g['metrics']['auc']:.4f}")
        print(f"merged  train rows: {m['n_train']}  AUC={m['metrics']['auc']:.4f}")
        print(f"picked: {result['picked']}")

        write_ladder_ab_report(result, args.report)
        print(f"wrote {args.report}")

        picked = result[result["picked"]]
        export_model(picked["model"], picked["mean"], picked["std"], args.out)
        print(f"exported {args.out}")
        return

    game_ids, X, y = load_rows(args.csv_path)
    train_mask, test_mask = game_split(game_ids, args.test_frac, args.seed)
    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]

    sample_weight = None
    if source_weights:
        sources = load_source_column(args.csv_path)
        sample_weight = sample_weights_for(sources, source_weights)[train_mask]

    model, mean, std = fit_standardized(X_train, y_train, sample_weight=sample_weight)
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
