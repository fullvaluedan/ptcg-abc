"""U92 step 0: pairwise-RankNet kill test on the clone dataset (plan U92).

Three straight attempts to clone a top-player MAIN decision (tools/train_clone.py:
a standardized logistic regression, then a shallow gradient-boosted tree, then
both again after a within-category local-rank feature fix) all converged on the
identical collapse: the fitted model's top-1 pick equals the FIRST-LEGAL option
in 100% of held-out decisions, exactly tying the first-legal baseline rather than
beating it (analysis/clone_quality.md). The U90 comprehension-track autopsy named
the likely root cause as an INSTRUMENT DEFECT, not unlearnable structure: all
three attempts optimized a per-row, pointwise log-loss, whose zero-risk optimum
is provably "always predict the baseline row" whenever the baseline already
achieves non-trivial accuracy (which first-legal does here, 33-45% depending on
family) -- the objective has no incentive to ever risk a different pick.

This is the cheap, single-variable kill test the U92 plan calls for before
building a full groupwise-ranking retrain (tools/train_clone2.py, not yet
written): change ONLY the training objective (pointwise log-loss -> pairwise
logistic RankNet, analysis.unit_zero_spike.PairwiseLinearRanker, plan U26) while
holding the feature set, the dataset, and the train/test split completely fixed,
and see whether that alone breaks the collapse. A RankNet loss is fit over
chosen-vs-every-sibling-option difference vectors within a decision, so its
zero-risk optimum is not "copy the baseline row" the same way a per-row
classifier's is -- if position still dominates under this different objective,
that is strong evidence the collapse is a genuine property of the data (position
carries essentially all the discriminating signal), not an artifact of the
objective tools/train_clone.py happened to use, and closes the objective-change
hypothesis before any further build effort.

Verdict rule: PASS (worth building train_clone2.py) if the ranker beats the
first-legal baseline by a positive, non-noise margin (>= KILL_TEST_MARGIN) on at
least one family with >= MIN_TEST_GROUPS scored held-out decisions. Otherwise
FAIL -- record it as a fourth converging negative result and close the
"wrong objective" hypothesis too.

Dev tool only; never shipped. Reads clone_groups_*.npz (gitignored, plan U70).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.unit_zero_spike import PairwiseLinearRanker  # noqa: E402
from tools.train_clone import families_present, load_pooled_groups  # noqa: E402

DEFAULT_REPORT_PATH = _ROOT / "analysis" / "rank_clone_killtest.md"
KILL_TEST_MARGIN = 0.03
MIN_TEST_GROUPS = 20


def family_groups(groups, family: str, split: str) -> list:
    """[(X, played_idx), ...] for `family`'s groups in `split`, PairwiseLinearRanker's own shape."""
    return [(g["features"], g["played"]) for g in groups if g["family"] == family and g["split"] == split]


def _scored(groups: list) -> list:
    """`groups` restricted to those with an in-range played index (well-formed decisions)."""
    return [(X, chosen) for X, chosen in groups if 0 <= chosen < len(X)]


def first_legal_accuracy(groups: list) -> float:
    """Top-1 accuracy of always picking option 0, over the scored subset of `groups`."""
    scored = _scored(groups)
    if not scored:
        return 0.0
    return sum(1 for _, chosen in scored if chosen == 0) / len(scored)


def rank_accuracy(ranker: PairwiseLinearRanker, groups: list) -> float:
    """Held-out top-1 accuracy of `ranker`, over the scored subset of `groups`."""
    scored = _scored(groups)
    if not scored:
        return 0.0
    return sum(1 for X, chosen in scored if ranker.top1(X) == chosen) / len(scored)


def run_family(groups: list, family: str) -> dict | None:
    """RankNet vs first-legal read for one family, or None if untrainable (no train or test rows)."""
    train = family_groups(groups, family, "train")
    test = family_groups(groups, family, "test")
    if not train or not test:
        return None
    ranker = PairwiseLinearRanker().fit(train)
    accuracy = rank_accuracy(ranker, test)
    baseline = first_legal_accuracy(test)
    return {
        "family": family,
        "n_train": len(train),
        "n_test": len(test),
        "n_scored": len(_scored(test)),
        "accuracy": accuracy,
        "baseline": baseline,
        "margin": accuracy - baseline,
    }


def passes(result: dict, margin: float, min_test_groups: int) -> bool:
    return result is not None and result["margin"] >= margin and result["n_scored"] >= min_test_groups


def write_report(results: dict, margin: float, min_test_groups: int, path) -> Path:
    lines = [
        "# U92 step 0: pairwise-RankNet kill test on the clone dataset",
        "",
        "tools/rank_clone_killtest.py fits analysis.unit_zero_spike's",
        "PairwiseLinearRanker (RankNet, plan U26) per archetype family on the",
        "same clone_groups_*.npz dataset and train/test split tools/train_clone.py",
        "already gated (analysis/clone_quality.md), changing ONLY the training",
        "objective (pairwise ranking instead of per-row log-loss) to test whether",
        "the objective, not the data, was the reason every prior attempt collapsed",
        "to exactly the first-legal baseline.",
        "",
        "## Verdict rule",
        "",
        f"PASS (worth building tools/train_clone2.py) if the ranker beats the",
        f"first-legal baseline by at least {margin:+.2f} on some family with at",
        f"least {min_test_groups} scored held-out decisions. Otherwise FAIL: a",
        "fourth converging negative result, closing the objective-change",
        "hypothesis alongside the three tools/train_clone.py attempts.",
        "",
        "| family | train groups | test groups | decisions scored | ranker accuracy | "
        "first-legal baseline | margin | verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]
    any_pass = False
    for family in sorted(results):
        r = results[family]
        if r is None:
            lines.append(f"| {family} | - | - | - | - | - | - | NO (no train or test rows) |")
            continue
        ok = passes(r, margin, min_test_groups)
        any_pass = any_pass or ok
        lines.append(
            f"| {family} | {r['n_train']} | {r['n_test']} | {r['n_scored']} | "
            f"{r['accuracy']:.4f} | {r['baseline']:.4f} | {r['margin']:+.4f} | "
            f"{'PASS' if ok else 'FAIL'} |"
        )
    lines += [
        "",
        f"Overall: {'PASS' if any_pass else 'FAIL'} "
        f"({'at least one family cleared the margin' if any_pass else 'no family cleared the margin'}).",
        "",
    ]
    Path(path).write_text("\n".join(lines))
    return Path(path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("npz_paths", nargs="+", help="clone_groups_*.npz path(s) from tools/clone_dataset.py")
    ap.add_argument("--margin", type=float, default=KILL_TEST_MARGIN)
    ap.add_argument("--min-test-groups", type=int, default=MIN_TEST_GROUPS)
    ap.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    args = ap.parse_args(argv)

    groups = load_pooled_groups(args.npz_paths)
    families = families_present(groups)
    results = {family: run_family(groups, family) for family in families}

    any_pass = False
    for family in families:
        r = results[family]
        if r is None:
            print(f"{family}: no train/test rows, skipped")
            continue
        ok = passes(r, args.margin, args.min_test_groups)
        any_pass = any_pass or ok
        print(
            f"{family}: ranker {r['accuracy']:.4f} baseline {r['baseline']:.4f} "
            f"margin {r['margin']:+.4f} n_scored {r['n_scored']} -> {'PASS' if ok else 'FAIL'}"
        )

    write_report(results, args.margin, args.min_test_groups, args.report)
    print(f"wrote {args.report}")
    print(f"VERDICT: {'PASS' if any_pass else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
