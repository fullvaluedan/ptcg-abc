"""Train and export per-family clone-policy weights (plan U71).

Reads one or more clone_groups_*.npz files produced by tools/clone_dataset.py
(plan U70) and, for each archetype family present, fits a standardized
logistic regression over agents.imitation_features's FEATURE_NAMES with "was
this the option the top team actually played" as the target -- the same
row-level simplification tools/train_move_prior.py uses for the move-ordering
model (one row per option, y=1 for the played option, y=0 otherwise), applied
here per family instead of pooled globally.

Train/held-out split is already fixed at dataset-build time (U70 tags every
group with analysis.replay_trace.split_of(episode_id)); this only reads it,
same episode-level leakage guard, no re-splitting.

GATE (plan U71): a family's clone only qualifies as a ring opponent if its
held-out top-1 accuracy beats the FIRST-LEGAL baseline (always picking option
0, the actual floor a clone needs to clear to be worth playing against) by at
least QUALIFY_MARGIN, with at least MIN_TEST_GROUPS scored held-out decisions
(below that the read is too noisy to trust either way). This is a stricter,
more literal floor than train_move_prior's random baseline: the ring only
wants clones that clearly imitate a real preference. Below-margin families
are recorded as a valid negative result (analysis/clone_quality.md), not
exported, same posture as U8b's move-prior gate.

Two model families are tried per archetype family (the 2026-07-03 gate retry
found the LINEAR model ties the first-legal baseline exactly: the fitted
opt_is_first/opt_index_norm weights are large enough that no single content
feature ever wins the tiebreak, because a linear model can only trade
position off against content at one fixed global rate everywhere. A shallow
gradient-boosted tree ranker can express "usually trust engine order, but
override it when content signal is unusually strong," which the linear model
structurally cannot):
  - "linear": standardized logistic regression (the original U71 model).
  - "tree": a shallow GradientBoostingClassifier (TREE_MAX_DEPTH-deep trees,
    TREE_N_ESTIMATORS of them), which needs no standardization.
Both are fit and scored on the same held-out split; whichever has the larger
margin over the first-legal baseline is the one exported and gated, per
family. Below-margin families are recorded as a valid negative result
regardless of which model kind was tried.

Exports agents/clone_weights/<family>.json per qualifying family. A "linear"
export keeps the original payload shape (feature_names, feature_version,
mean, std, coef, intercept; no model_type key, same as search/move_prior.json)
so agents/clone_policy.py's existing loader needs no change to keep reading
it. A "tree" export adds "model_type": "gbdt" plus "learning_rate",
"init_score", and "trees" (one entry per boosting round, each a plain-python
copy of that round's sklearn tree arrays: feature, threshold, left, right,
value, indexed by node id exactly as sklearn's own tree_ arrays are) for
agents/clone_policy.py to load and walk at decision time. scikit-learn is
dev-only; nothing here ships in the submission bundle (clone bots never
ship).

Dev tool only; never shipped.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402
from sklearn.ensemble import GradientBoostingClassifier  # noqa: E402

from agents.imitation_features import FEATURE_NAMES, N_FEATURES, feature_version  # noqa: E402
from tools.clone_dataset import iter_groups, load_npz  # noqa: E402
from tools.train_eval import fit_standardized  # noqa: E402
from tools.train_move_prior import export_model  # noqa: E402

DEFAULT_WEIGHTS_DIR = _ROOT / "agents" / "clone_weights"
DEFAULT_REPORT_PATH = _ROOT / "analysis" / "clone_quality.md"
QUALIFY_MARGIN = 0.15
MIN_TEST_GROUPS = 20
TREE_N_ESTIMATORS = 50
TREE_MAX_DEPTH = 2
TREE_LEARNING_RATE = 0.1
TREE_RANDOM_STATE = 0


def load_pooled_groups(npz_paths) -> list:
    """All ranking groups from one or more clone_dataset npz files, concatenated."""
    groups = []
    for path in npz_paths:
        groups.extend(iter_groups(load_npz(path)))
    return groups


def families_present(groups) -> list:
    """Sorted distinct family names across `groups`."""
    return sorted({g["family"] for g in groups})


def feature_mask(exclude: tuple) -> np.ndarray:
    """Boolean array over FEATURE_NAMES, True = keep, False = column named in `exclude`.

    Raises ValueError on an unknown feature name (a typo here would silently
    keep every column, hiding the ablation instead of running it).
    """
    unknown = sorted(set(exclude) - set(FEATURE_NAMES))
    if unknown:
        raise ValueError(f"unknown feature name(s) in exclude: {unknown}")
    return np.array([name not in exclude for name in FEATURE_NAMES])


def rows_for_family(groups, family, split=None, exclude=None) -> tuple:
    """(X, y, group_id) rows flattened from every group of `family` (optionally one split).

    y is 1 for the option the top team actually played, 0 for every sibling
    option in that decision; group_id ties rows back to the decision they
    came from so top1_accuracy / first_legal_baseline can regroup them.
    `exclude`, if given, is a tuple of FEATURE_NAMES entries dropped from X
    entirely (an ablation: see train_family_best's `exclude` parameter).
    """
    X, y, group_id = [], [], []
    gi = 0
    for g in groups:
        if g["family"] != family:
            continue
        if split is not None and g["split"] != split:
            continue
        for i, row in enumerate(g["features"]):
            X.append(row)
            y.append(1 if i == g["played"] else 0)
            group_id.append(gi)
        gi += 1
    X_arr = np.asarray(X, dtype=float) if X else np.zeros((0, N_FEATURES))
    if exclude:
        X_arr = X_arr[:, feature_mask(exclude)] if X_arr.shape[0] else np.zeros((0, N_FEATURES - len(set(exclude))))
    return X_arr, np.asarray(y, dtype=int), np.asarray(group_id, dtype=int)


def _scored_groups(group_id, y) -> dict:
    """{group_id: [row indices]} restricted to groups with exactly one played=1 row."""
    groups = {}
    for i, gid in enumerate(group_id):
        groups.setdefault(int(gid), []).append(i)
    return {gid: idxs for gid, idxs in groups.items() if sum(1 for i in idxs if y[i] == 1) == 1}


def top1_accuracy(scores, y, group_id) -> tuple:
    """(accuracy, n_scored): fraction of decisions whose highest-scoring option is the one played."""
    scored = _scored_groups(group_id, y)
    if not scored:
        return 0.0, 0
    correct = 0
    for idxs in scored.values():
        chosen = next(i for i in idxs if y[i] == 1)
        best = max(idxs, key=lambda i: scores[i])
        if best == chosen:
            correct += 1
    return correct / len(scored), len(scored)


def first_legal_baseline(y, group_id) -> float:
    """Top-1 accuracy of always picking the first option in the group (index 0).

    The clone qualification floor (plan U71): a clone must clearly beat "just
    always pick the first legal option" to be worth playing against.
    """
    scored = _scored_groups(group_id, y)
    if not scored:
        return 0.0
    correct = sum(1 for idxs in scored.values() if y[min(idxs)] == 1)
    return correct / len(scored)


def _safe_family_filename(family: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", family) + ".json"


def train_family(groups, family, exclude=None) -> dict | None:
    """Fitted LINEAR model + held-out read for one family, or None if untrainable.

    None when the family has zero train or zero held-out rows (too little
    data to fit or to judge, rather than reporting a meaningless 0.0).
    `exclude`: see rows_for_family.
    """
    X_train, y_train, _ = rows_for_family(groups, family, split="train", exclude=exclude)
    X_test, y_test, gid_test = rows_for_family(groups, family, split="test", exclude=exclude)
    if len(X_train) == 0 or len(X_test) == 0:
        return None
    model, mean, std = fit_standardized(X_train, y_train)
    scores = model.predict_proba((X_test - mean) / std)[:, 1]
    accuracy, n_scored = top1_accuracy(scores, y_test, gid_test)
    baseline = first_legal_baseline(y_test, gid_test)
    return {
        "model_kind": "linear", "model": model, "mean": mean, "std": std,
        "accuracy": accuracy, "baseline": baseline, "n_scored": n_scored,
        "n_train": len(X_train), "n_test": len(X_test),
    }


def fit_tree(X_train, y_train) -> GradientBoostingClassifier:
    """A shallow gradient-boosted tree classifier; no standardization needed."""
    model = GradientBoostingClassifier(
        n_estimators=TREE_N_ESTIMATORS, max_depth=TREE_MAX_DEPTH,
        learning_rate=TREE_LEARNING_RATE, random_state=TREE_RANDOM_STATE,
    )
    model.fit(X_train, y_train)
    return model


def train_family_tree(groups, family, exclude=None) -> dict | None:
    """Fitted TREE model + held-out read for one family, or None if untrainable.

    Same shape as train_family (accuracy/baseline/n_scored/n_train/n_test) so
    the two model kinds compare directly; "model" holds the fitted
    GradientBoostingClassifier instead of a (model, mean, std) linear triple.
    `exclude`: see rows_for_family.
    """
    X_train, y_train, _ = rows_for_family(groups, family, split="train", exclude=exclude)
    X_test, y_test, gid_test = rows_for_family(groups, family, split="test", exclude=exclude)
    if len(X_train) == 0 or len(X_test) == 0:
        return None
    model = fit_tree(X_train, y_train)
    scores = model.decision_function(X_test)
    accuracy, n_scored = top1_accuracy(scores, y_test, gid_test)
    baseline = first_legal_baseline(y_test, gid_test)
    return {
        "model_kind": "tree", "model": model,
        "accuracy": accuracy, "baseline": baseline, "n_scored": n_scored,
        "n_train": len(X_train), "n_test": len(X_test),
    }


def train_family_best(groups, family, exclude=None) -> dict | None:
    """Whichever of train_family / train_family_tree has the larger margin.

    Both model kinds are fit and scored on the same held-out split; the one
    with the larger (accuracy - baseline) margin is returned unchanged (so
    callers keep using the existing "model"/"accuracy"/"baseline"/"n_scored"
    keys regardless of which kind won), plus an "other" key holding the
    losing kind's result (or None) for reporting. None only when NEITHER
    kind could train (both return None, i.e. no train or test rows at all).
    Ties keep the linear result: it is cheaper to score at match time and
    was already the proven-safe default before the tree model existed.
    `exclude`: see rows_for_family; threaded into both model kinds so the
    ablation is applied identically regardless of which one wins.
    """
    linear = train_family(groups, family, exclude=exclude)
    tree = train_family_tree(groups, family, exclude=exclude)
    if linear is None and tree is None:
        return None
    if linear is None:
        best, other = tree, None
    elif tree is None:
        best, other = linear, None
    else:
        linear_margin = linear["accuracy"] - linear["baseline"]
        tree_margin = tree["accuracy"] - tree["baseline"]
        best, other = (tree, linear) if tree_margin > linear_margin else (linear, tree)
    return {**best, "other": other}


def qualifies(result: dict, margin: float, min_test_groups: int) -> bool:
    return result is not None and (result["accuracy"] - result["baseline"]) >= margin \
        and result["n_scored"] >= min_test_groups


def _tree_to_payload(tree) -> dict:
    """A sklearn DecisionTreeRegressor's internal tree_ as plain python lists.

    Indexed by node id exactly like sklearn's own arrays: children_left[i]
    == -1 marks a leaf (score with value[i]); otherwise walk to left[i] when
    row[feature[i]] <= threshold[i], else right[i]. Native python types only,
    so this is directly json.dumps-able.
    """
    return {
        "feature": [int(v) for v in tree.feature],
        "threshold": [float(v) for v in tree.threshold],
        "left": [int(v) for v in tree.children_left],
        "right": [int(v) for v in tree.children_right],
        "value": [float(v) for v in tree.value.ravel()],
    }


def _tree_init_score(model: GradientBoostingClassifier) -> float:
    """The boosted ensemble's base (log-odds) score before any tree is added.

    model.init_ is a DummyClassifier(strategy="prior"); its class-1 prior
    probability, converted to log-odds, is the constant every tree's output
    is added on top of. Matches model.decision_function(X) exactly (verified
    in tests/test_train_clone.py against sklearn's own decision_function).
    """
    p = float(model.init_.class_prior_[1])
    p = min(max(p, 1e-12), 1 - 1e-12)  # guard log(0) at a degenerate 0%/100% prior
    return math.log(p / (1 - p))


def export_tree_model(model: GradientBoostingClassifier, feature_names, path) -> Path:
    """agents/clone_weights/<family>.json for a "tree" (gbdt) model.

    agents/clone_policy.py walks "trees" in pure python and sums
    init_score + learning_rate * sum(tree outputs), which reproduces
    model.decision_function(X) exactly for ranking purposes (no sigmoid
    needed: choose_index only cares about relative order within a group).
    """
    payload = {
        "model_type": "gbdt",
        "feature_names": list(feature_names),
        "feature_version": list(feature_version()),
        "learning_rate": float(model.learning_rate),
        "init_score": _tree_init_score(model),
        "trees": [_tree_to_payload(model.estimators_[i, 0].tree_) for i in range(model.n_estimators_)],
    }
    Path(path).write_text(json.dumps(payload, indent=2) + "\n")
    return Path(path)


def write_report(results: dict, margin: float, min_test_groups: int, path, exclude=None) -> Path:
    lines = [
        "# Clone policy training (plan U71)",
        "",
        "tools/train_clone.py fits two model kinds per archetype family over",
        "agents/imitation_features's per-option feature vector, target is the",
        "option the top team actually played, held out by EPISODE (the split",
        "tools/clone_dataset.py already assigned): a standardized logistic",
        "regression (\"linear\") and a shallow gradient-boosted tree ranker",
        "(\"tree\", TREE_MAX_DEPTH-deep, TREE_N_ESTIMATORS rounds). Whichever has",
        "the larger held-out margin over the first-legal baseline is reported",
        "and, if it clears the gate, exported; the losing kind's read is also",
        "shown so a family where both kinds tie the baseline is visible as such,",
        "not silently hidden behind the winning kind's number.",
        "",
    ]
    if exclude:
        lines += [
            "## Ablation mode",
            "",
            f"Excluded feature(s) this run: {', '.join(sorted(exclude))}. This is a",
            "diagnostic run only (see analysis/clone_quality.md's per-iteration log for",
            "why): weights are never exported in ablation mode, because an exported",
            "payload's coef vector must line up 1:1 with the full FEATURE_NAMES list",
            "agents/clone_policy.py reads at inference, and a masked fit has fewer columns.",
            "",
        ]
    lines += [
        "## Gate",
        "",
        "A family qualifies as a ring opponent only if its held-out top-1",
        "accuracy beats the FIRST-LEGAL baseline (always picking option 0) by",
        f"at least {margin:.0%}, with at least {min_test_groups} scored held-out",
        "decisions (below that the read is too noisy to trust either way).",
        "",
        "| family | model | train rows | test rows | decisions scored | accuracy | "
        "first-legal baseline | margin | qualified | other kind's margin |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    qualified = []
    for family in sorted(results):
        r = results[family]
        if r is None:
            lines.append(f"| {family} | - | - | - | - | - | - | - | NO (no train or test rows) | - |")
            continue
        passed = qualifies(r, margin, min_test_groups)
        if passed:
            qualified.append(family)
        margin_val = r["accuracy"] - r["baseline"]
        other = r.get("other")
        other_margin = f"{(other['accuracy'] - other['baseline']):+.4f} ({other['model_kind']})" if other else "-"
        lines.append(
            f"| {family} | {r['model_kind']} | {r['n_train']} | {r['n_test']} | {r['n_scored']} | "
            f"{r['accuracy']:.4f} | {r['baseline']:.4f} | {margin_val:+.4f} | "
            f"{'YES' if passed else 'NO'} | {other_margin} |"
        )
    if exclude:
        lines += [
            "",
            f"Qualified families ({len(qualified)}): {', '.join(qualified) if qualified else '(none)'}.",
            "",
            "Ablation mode: no weights were exported regardless of the qualified column",
            "above (see the Ablation mode section). This run answers whether the",
            "excluded feature(s) were the ONLY thing standing between the model and the",
            "gate, not whether a shippable ring opponent exists.",
            "",
        ]
    else:
        lines += [
            "",
            f"Qualified families ({len(qualified)}): {', '.join(qualified) if qualified else '(none)'}.",
            "",
            "Qualified families' weights are exported to agents/clone_weights/; every",
            "other family is a valid negative result (same posture as U8b's",
            "move-prior gate), not exported, and does not join the ring (U72).",
            "",
        ]
    Path(path).write_text("\n".join(lines))
    return Path(path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("npz_paths", nargs="+", help="clone_groups_*.npz path(s) from tools/clone_dataset.py")
    ap.add_argument("--margin", type=float, default=QUALIFY_MARGIN)
    ap.add_argument("--min-test-groups", type=int, default=MIN_TEST_GROUPS)
    ap.add_argument("--out-dir", default=str(DEFAULT_WEIGHTS_DIR))
    ap.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    ap.add_argument("--exclude-features", default=None,
                     help="comma-separated FEATURE_NAMES entries to drop before fitting "
                          "(ablation diagnostic; disables export, see write_report)")
    args = ap.parse_args(argv)

    exclude = tuple(args.exclude_features.split(",")) if args.exclude_features else None

    groups = load_pooled_groups(args.npz_paths)
    families = families_present(groups)
    results = {family: train_family_best(groups, family, exclude=exclude) for family in families}

    out_dir = Path(args.out_dir)
    exported = []
    for family in families:
        r = results[family]
        if r is None:
            print(f"{family}: no train/test rows, skipped")
            continue
        margin_val = r["accuracy"] - r["baseline"]
        if exclude:
            print(f"{family}: [{r['model_kind']}] accuracy {r['accuracy']:.4f} baseline {r['baseline']:.4f} "
                  f"margin {margin_val:+.4f} n_scored {r['n_scored']} -> ablation mode, not exported")
        elif qualifies(r, args.margin, args.min_test_groups):
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / _safe_family_filename(family)
            if r["model_kind"] == "tree":
                export_tree_model(r["model"], FEATURE_NAMES, out_path)
            else:
                export_model(r["model"], r["mean"], r["std"], out_path)
            exported.append(family)
            print(f"{family}: [{r['model_kind']}] accuracy {r['accuracy']:.4f} baseline {r['baseline']:.4f} "
                  f"margin {margin_val:+.4f} n_scored {r['n_scored']} -> exported {out_path}")
        else:
            print(f"{family}: [{r['model_kind']}] accuracy {r['accuracy']:.4f} baseline {r['baseline']:.4f} "
                  f"margin {margin_val:+.4f} n_scored {r['n_scored']} -> NOT exported (below gate)")

    write_report(results, args.margin, args.min_test_groups, args.report, exclude=exclude)
    print(f"wrote {args.report}")
    print(f"exported {len(exported)}/{len(families)} families: {exported}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
