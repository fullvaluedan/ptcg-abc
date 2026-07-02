"""Full expert-cohort census over the episode dataset (plan U25).

Replaces the 3-episode / 116-decision sample read with a full count over the
5734-game dataset. The expert cohort is the winning seat of every decided
episode (analysis/expert_cohort resolves the 3/116-vs-40/1427 fork); this tool
classifies each cohort seat's deck into an archetype family and counts, per
family, expert-anchored episodes, MAIN decisions, and ranking groups. The
target family's ranking-group count picks the pre-committed training tier that
sizes the whole imitation stack (U40/U41).

Output is competition-derived (mined from episodes the license forbids
redistributing), so the machine-readable census JSON is written THROUGH the
shared isolation helper into data/derived/census/ (gitignored). The committed
artifact is the human verdict analysis/expert_census.md, authored from this
tool's summary; it carries counts, not raw episodes.

Dev tool only; never shipped.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis import expert_cohort  # noqa: E402
from analysis.move_ranking_validator import load_replays  # noqa: E402
from tools.isolation import derived_path  # noqa: E402


def build_signatures(decks_dir=None) -> dict:
    """Family-name -> distinctive-card-id frozenset, from analysis/archetype.

    Uses the builtin field archetypes (the harvested meta pillars) plus, when a
    decks directory is given, any .csv decklists there. Building a signature
    needs the card index (to drop basic energy), which pulls in cg lazily, so
    this is only reachable on a real dataset run, not at import. Kept here rather
    than in expert_cohort so that module stays cg-free and unit-testable.
    """
    from analysis import archetype

    if decks_dir:
        archetype.load_decks_dir(decks_dir)
    return {a.name: a.signature for a in archetype._archetypes()}


def run_census(source, signatures, threshold, limit=None) -> dict:
    """Aggregate the cohort census over every episode in `source`.

    `source` is the dataset zip or a directory of episode JSONs; each replay is
    reduced to its cohort row and folded into per-family and total counts.
    """
    rows = (
        expert_cohort.census_episode(replay, signatures, threshold)
        for replay, _label in load_replays(source, limit=limit)
    )
    return expert_cohort.aggregate(rows)


def _print_summary(report, threshold, target) -> None:
    print(f"expert cohort = winning seat; family threshold cover >= {threshold}")
    print(
        f"episodes: {report['episodes']} scored, {report['skipped']} skipped "
        f"(draws / malformed)"
    )
    print(f"total ranking groups: {report['ranking_groups']}")
    print(f"total MAIN decisions: {report['main_decisions']}")
    print("\nper archetype family (episodes, MAIN decisions, ranking groups, tier):")
    fams = sorted(
        report["by_family"],
        key=lambda f: -report["by_family"][f]["ranking_groups"],
    )
    for fam in fams:
        row = report["by_family"][fam]
        tier = expert_cohort.tier_for(row["ranking_groups"])
        mark = " <-- target" if fam == target else ""
        print(
            f"  {fam:<28} ep={row['episodes']:<5} "
            f"main={row['main_decisions']:<7} groups={row['ranking_groups']:<7} "
            f"{tier}{mark}"
        )
    top_teams = sorted(report["teams"].items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    if top_teams:
        print("\ntop winning-seat handles:")
        for name, n in top_teams:
            print(f"  {name:<28} {n}")


def _resolve_target(report, target) -> str:
    """The family whose tier is the headline: the requested one, else the largest.

    If --target names a family the census produced, its tier sizes the pipeline;
    otherwise the family with the most ranking groups is the de facto target
    (the widest-adoption pillar we would clone first).
    """
    if target and target in report["by_family"]:
        return target
    if not report["by_family"]:
        return "other"
    return max(
        report["by_family"],
        key=lambda f: report["by_family"][f]["ranking_groups"],
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "source",
        help="a .zip of episode JSONs or a directory of *.json replays",
    )
    ap.add_argument(
        "--decks-dir",
        default=None,
        help="optional directory of extra archetype .csv decklists to classify against",
    )
    ap.add_argument(
        "--threshold",
        type=float,
        default=0.35,
        help="minimum signature coverage to assign a deck to a family (else other)",
    )
    ap.add_argument(
        "--target",
        default=None,
        help="target family for the headline tier (default: the largest family)",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        help="cap episodes read (default: the whole dataset)",
    )
    ap.add_argument(
        "--out",
        default="expert_census.json",
        help="census JSON filename under data/derived/census/ (isolated)",
    )
    args = ap.parse_args(argv)

    signatures = build_signatures(args.decks_dir)
    report = run_census(args.source, signatures, args.threshold, limit=args.limit)
    target = _resolve_target(report, args.target)
    report["target_family"] = target
    report["target_tier"] = expert_cohort.tier_for(
        report["by_family"].get(target, {}).get("ranking_groups", 0)
    )
    report["threshold"] = args.threshold

    _print_summary(report, args.threshold, target)
    print(f"\ntarget family: {target} -> tier {report['target_tier']}")

    out = derived_path("census", args.out)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"census written (isolated): {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
