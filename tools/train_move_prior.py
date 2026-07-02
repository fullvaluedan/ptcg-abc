"""Train and export the move-ordering model (plan U8b).

Reads move_rows_*.csv file(s) produced by tools/gauntlet.py --log-moves or
tools/replays_to_rows.py --log-moves (one row per candidate MAIN option per
decision, is_chosen 0/1), pools them, splits by GAME (never by row, same
leakage guard as U4's tools/train_eval.py, reused here via game_split), and
fits a standardized logistic regression over agents.imitation_features's
FEATURE_NAMES with is_chosen as the target. This is the plan's own "logistic
regression ... simple ranking score" simplification, not a true listwise
ranker (U41's abandoned pairwise-ranker training code is not revived here).

GATE: held-out top-1 accuracy (does the model's highest-scoring option within
a decision group match the actual is_chosen row) must beat the random
baseline (mean 1/n_options over the same held-out decisions) by at least
GATE_MARGIN. A below-margin result is a valid negative result, same posture
as U65's sweep: recorded in analysis/move_prior_train.md, and the model is
NOT exported (U8c must not wire an unproven model into search).

Exports search/move_prior.json (feature_names, feature_version, mean, std,
coef, intercept) for search/move_prior.py (U8c), a pure-Python scorer with no
sklearn dependency, to load at match time. feature_version is stored as a
list (JSON has no tuple type); U8c compares it against
tuple(imitation_features.feature_version()). scikit-learn itself is a
dev-only dependency; nothing here ships in the submission bundle.

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

from agents.imitation_features import FEATURE_NAMES, feature_version  # noqa: E402
from tools.train_eval import fit_standardized, game_split  # noqa: E402

import numpy as np  # noqa: E402

DEFAULT_MODEL_PATH = _ROOT / "search" / "move_prior.json"
DEFAULT_REPORT_PATH = _ROOT / "analysis" / "move_prior_train.md"
GATE_MARGIN = 0.05


def load_rows(csv_path, tag_prefix=None):
    """(game_ids, group_keys, X, y) from a move_rows CSV (plan U8a schema).

    group_keys is "<tagged game_id>:<decision_id>", unique per decision, so
    top1_accuracy/random_baseline can regroup option rows back into the
    decision they came from after a row-level train/test mask is applied.
    """
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        game_idx = header.index("game_id")
        decision_idx = header.index("decision_id")
        chosen_idx = header.index("is_chosen")
        feature_idx = [header.index(name) for name in FEATURE_NAMES]
        game_ids, group_keys, X, y = [], [], [], []
        for row in reader:
            gid = f"{tag_prefix}:{row[game_idx]}" if tag_prefix else row[game_idx]
            game_ids.append(gid)
            group_keys.append(f"{gid}:{row[decision_idx]}")
            X.append([float(row[i]) for i in feature_idx])
            y.append(int(row[chosen_idx]))
    return np.array(game_ids), np.array(group_keys), np.array(X, dtype=float), np.array(y, dtype=int)


def load_pooled(csv_paths):
    """Load and concatenate one or more move-rows CSVs.

    Each file's game_ids are tagged with that file's own stem before
    concatenation (e.g. "move_rows_123:0"), so two files that happen to reuse
    the same small integer game ids (two separate gauntlet runs) or the same
    replay episode id can never collide once pooled.
    """
    parts = [load_rows(p, tag_prefix=Path(p).stem) for p in csv_paths]
    game_ids = np.concatenate([p[0] for p in parts])
    group_keys = np.concatenate([p[1] for p in parts])
    X = np.concatenate([p[2] for p in parts], axis=0)
    y = np.concatenate([p[3] for p in parts], axis=0)
    return game_ids, group_keys, X, y


def _scored_groups(group_keys, y):
    """{group_key: [row indices]} restricted to groups with exactly one is_chosen=1 row.

    A group with zero (an unresolved chosen index at capture time) or more
    than one (a logging bug tools/dataset_report.py's move_report already
    flags) chosen rows carries no usable top-1 signal, so both top1_accuracy
    and random_baseline exclude it from numerator and denominator alike.
    """
    groups = {}
    for i, key in enumerate(group_keys):
        groups.setdefault(key, []).append(i)
    return {key: idxs for key, idxs in groups.items() if sum(1 for i in idxs if y[i] == 1) == 1}


def top1_accuracy(scores, y, group_keys):
    """(accuracy, n_scored): fraction of well-formed decision groups whose
    highest-scoring option is the one actually chosen.
    """
    scored = _scored_groups(group_keys, y)
    if not scored:
        return 0.0, 0
    correct = 0
    for idxs in scored.values():
        chosen = next(i for i in idxs if y[i] == 1)
        best = max(idxs, key=lambda i: scores[i])
        if best == chosen:
            correct += 1
    return correct / len(scored), len(scored)


def random_baseline(group_keys, y):
    """mean(1/n_options) over the same decision groups top1_accuracy scores:
    the expected top-1 accuracy of picking an option uniformly at random.
    """
    scored = _scored_groups(group_keys, y)
    if not scored:
        return 0.0
    return sum(1.0 / len(idxs) for idxs in scored.values()) / len(scored)


def export_model(model, mean, std, path):
    payload = {
        "feature_names": list(FEATURE_NAMES),
        "feature_version": list(feature_version()),
        "mean": mean.tolist(),
        "std": std.tolist(),
        "coef": model.coef_[0].tolist(),
        "intercept": float(model.intercept_[0]),
    }
    Path(path).write_text(json.dumps(payload, indent=2) + "\n")


def write_report(n_train_games, n_test_games, n_train, n_test, n_scored,
                  accuracy, baseline, margin, passed, path):
    lines = [
        "# Move-ordering model training (plan U8b)",
        "",
        "tools/train_move_prior.py fits a standardized logistic regression over",
        "agents/imitation_features's per-option feature vector, target is_chosen,",
        "pooled across every candidate option row from the training CSVs, split",
        "by GAME (never by row) into train/held-out sets.",
        "",
        "## Setup",
        "",
        f"- Train games: {n_train_games}  train rows: {n_train}",
        f"- Held-out games: {n_test_games}  held-out rows: {n_test}",
        f"- Held-out decisions scored (exactly one is_chosen row): {n_scored}",
        "",
        "## Gate",
        "",
        "Held-out top-1 accuracy (does the model's highest-scoring option within",
        "a decision match the one actually chosen) must beat the random baseline",
        f"(mean 1/n_options over the same decisions) by at least {margin:.0%}.",
        "",
        f"- top-1 accuracy: {accuracy:.4f}",
        f"- random baseline: {baseline:.4f}",
        f"- margin: {accuracy - baseline:+.4f} (need >= {margin:.4f})",
        "",
        f"Verdict: **{'PASS' if passed else 'FAIL'}**.",
        "",
    ]
    if passed:
        lines += [
            "The model is exported to search/move_prior.json for U8c to wire",
            "behind a flag.",
            "",
        ]
    else:
        lines += [
            "This is a valid negative result (same posture as U65's sweep): the",
            "model is NOT exported, and U8c does not proceed on an unproven model.",
            "",
        ]
    Path(path).write_text("\n".join(lines))
    return Path(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_paths", nargs="+",
                     help="move_rows_*.csv path(s) from tools/gauntlet.py --log-moves or "
                          "tools/replays_to_rows.py --log-moves; multiple are pooled together")
    ap.add_argument("--test-frac", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=str(DEFAULT_MODEL_PATH))
    ap.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    ap.add_argument("--margin", type=float, default=GATE_MARGIN)
    args = ap.parse_args()

    game_ids, group_keys, X, y = load_pooled(args.csv_paths)
    train_mask, test_mask = game_split(game_ids, args.test_frac, args.seed)
    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]
    group_keys_test = group_keys[test_mask]

    model, mean, std = fit_standardized(X_train, y_train)
    scores = model.predict_proba((X_test - mean) / std)[:, 1]
    accuracy, n_scored = top1_accuracy(scores, y_test, group_keys_test)
    baseline = random_baseline(group_keys_test, y_test)
    passed = (accuracy - baseline) >= args.margin

    n_train_games = len(set(game_ids[train_mask].tolist()))
    n_test_games = len(set(game_ids[test_mask].tolist()))
    print(f"games: train {n_train_games}  test {n_test_games}")
    print(f"rows: train {len(X_train)}  test {len(X_test)}  decisions scored {n_scored}")
    print(f"top-1 accuracy {accuracy:.4f}  baseline {baseline:.4f}  margin {accuracy - baseline:+.4f}")

    write_report(n_train_games, n_test_games, len(X_train), len(X_test), n_scored,
                 accuracy, baseline, args.margin, passed, args.report)
    print(f"wrote {args.report}")

    if not passed:
        sys.exit(
            f"FAIL: held-out top-1 accuracy {accuracy:.4f} does not beat baseline "
            f"{baseline:.4f} by the required margin {args.margin:.4f}"
        )

    export_model(model, mean, std, args.out)
    print(f"exported {args.out}")


if __name__ == "__main__":
    main()
