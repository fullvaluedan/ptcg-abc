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

Exports agents/clone_weights/<family>.json per qualifying family (same
payload shape as search/move_prior.json: feature_names, feature_version,
mean, std, coef, intercept) for agents/clone_policy.py to load at decision
time. scikit-learn is dev-only; nothing here ships in the submission bundle
(clone bots never ship).

Dev tool only; never shipped.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402

from agents.imitation_features import N_FEATURES  # noqa: E402
from tools.clone_dataset import iter_groups, load_npz  # noqa: E402
from tools.train_eval import fit_standardized  # noqa: E402
from tools.train_move_prior import export_model  # noqa: E402

DEFAULT_WEIGHTS_DIR = _ROOT / "agents" / "clone_weights"
DEFAULT_REPORT_PATH = _ROOT / "analysis" / "clone_quality.md"
QUALIFY_MARGIN = 0.15
MIN_TEST_GROUPS = 20


def load_pooled_groups(npz_paths) -> list:
    """All ranking groups from one or more clone_dataset npz files, concatenated."""
    groups = []
    for path in npz_paths:
        groups.extend(iter_groups(load_npz(path)))
    return groups


def families_present(groups) -> list:
    """Sorted distinct family names across `groups`."""
    return sorted({g["family"] for g in groups})


def rows_for_family(groups, family, split=None) -> tuple:
    """(X, y, group_id) rows flattened from every group of `family` (optionally one split).

    y is 1 for the option the top team actually played, 0 for every sibling
    option in that decision; group_id ties rows back to the decision they
    came from so top1_accuracy / first_legal_baseline can regroup them.
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


def train_family(groups, family) -> dict | None:
    """Fitted model + held-out read for one family, or None if untrainable.

    None when the family has zero train or zero held-out rows (too little
    data to fit or to judge, rather than reporting a meaningless 0.0).
    """
    X_train, y_train, _ = rows_for_family(groups, family, split="train")
    X_test, y_test, gid_test = rows_for_family(groups, family, split="test")
    if len(X_train) == 0 or len(X_test) == 0:
        return None
    model, mean, std = fit_standardized(X_train, y_train)
    scores = model.predict_proba((X_test - mean) / std)[:, 1]
    accuracy, n_scored = top1_accuracy(scores, y_test, gid_test)
    baseline = first_legal_baseline(y_test, gid_test)
    return {
        "model": model, "mean": mean, "std": std,
        "accuracy": accuracy, "baseline": baseline, "n_scored": n_scored,
        "n_train": len(X_train), "n_test": len(X_test),
    }


def qualifies(result: dict, margin: float, min_test_groups: int) -> bool:
    return result is not None and (result["accuracy"] - result["baseline"]) >= margin \
        and result["n_scored"] >= min_test_groups


def write_report(results: dict, margin: float, min_test_groups: int, path) -> Path:
    lines = [
        "# Clone policy training (plan U71)",
        "",
        "tools/train_clone.py fits one standardized logistic regression per",
        "archetype family over agents/imitation_features's per-option feature",
        "vector, target is the option the top team actually played, held out by",
        "EPISODE (the split tools/clone_dataset.py already assigned).",
        "",
        "## Gate",
        "",
        "A family qualifies as a ring opponent only if its held-out top-1",
        "accuracy beats the FIRST-LEGAL baseline (always picking option 0) by",
        f"at least {margin:.0%}, with at least {min_test_groups} scored held-out",
        "decisions (below that the read is too noisy to trust either way).",
        "",
        "| family | train rows | test rows | decisions scored | accuracy | "
        "first-legal baseline | margin | qualified |",
        "|---|---|---|---|---|---|---|---|",
    ]
    qualified = []
    for family in sorted(results):
        r = results[family]
        if r is None:
            lines.append(f"| {family} | - | - | - | - | - | - | NO (no train or test rows) |")
            continue
        passed = qualifies(r, margin, min_test_groups)
        if passed:
            qualified.append(family)
        margin_val = r["accuracy"] - r["baseline"]
        lines.append(
            f"| {family} | {r['n_train']} | {r['n_test']} | {r['n_scored']} | "
            f"{r['accuracy']:.4f} | {r['baseline']:.4f} | {margin_val:+.4f} | "
            f"{'YES' if passed else 'NO'} |"
        )
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
    args = ap.parse_args(argv)

    groups = load_pooled_groups(args.npz_paths)
    families = families_present(groups)
    results = {family: train_family(groups, family) for family in families}

    out_dir = Path(args.out_dir)
    exported = []
    for family in families:
        r = results[family]
        if r is None:
            print(f"{family}: no train/test rows, skipped")
            continue
        margin_val = r["accuracy"] - r["baseline"]
        if qualifies(r, args.margin, args.min_test_groups):
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / _safe_family_filename(family)
            export_model(r["model"], r["mean"], r["std"], out_path)
            exported.append(family)
            print(f"{family}: accuracy {r['accuracy']:.4f} baseline {r['baseline']:.4f} "
                  f"margin {margin_val:+.4f} n_scored {r['n_scored']} -> exported {out_path}")
        else:
            print(f"{family}: accuracy {r['accuracy']:.4f} baseline {r['baseline']:.4f} "
                  f"margin {margin_val:+.4f} n_scored {r['n_scored']} -> NOT exported (below gate)")

    write_report(results, args.margin, args.min_test_groups, args.report)
    print(f"wrote {args.report}")
    print(f"exported {len(exported)}/{len(families)} families: {exported}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
