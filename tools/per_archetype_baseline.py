"""Per-archetype expert-agreement baselines on the frozen md5 split (plan U32).

The global top-1 agreement (0.212, analysis/move_ranking_diverges_ability_gap.md)
is a single pooled number over every expert decision; it is NOT transferable to a
per-family gate, because a build that helps a Grimmsnarl mirror can hurt an
Archaludon matchup while the pooled number barely moves. Every later aware-pilot
A/B (U34 ability, U38 attribution, U40 ranker) is scored per archetype family, so
each family needs its OWN heuristic-pilot baseline on the SAME held-out episodes
those A/Bs use.

This tool recomputes that: for every episode it resolves the winning-seat cohort
(analysis/expert_cohort), classifies the seat's deck into a family against the real
archetype signatures, keeps only the test-bucket episodes (analysis/replay_trace's
canonical md5 split), runs the deployed heuristic pilot over that seat's scorable
MAIN decisions, and aggregates top-1 agreement per family. The committed artifact
is analysis/per_archetype_baselines.json (aggregate counts and rates per family, no
raw episodes); the machine dump also lands isolated under data/derived/. Dev tool
only; never shipped. Reads the competition dataset, never redistributes it.
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

from analysis import replay_trace  # noqa: E402
from analysis.expert_cohort import (  # noqa: E402
    classify_family,
    cohort_seat,
    seat_decklists,
)
from analysis.move_ranking_validator import agreement, load_replays  # noqa: E402
from tools.expert_census import build_signatures  # noqa: E402
from tools.isolation import derived_path  # noqa: E402


def baseline_by_family(
    source, signatures, pilot_choose, threshold=0.35, split="test", limit=None
) -> dict:
    """Aggregate the heuristic pilot's per-family top-1 agreement over `source`.

    Only episodes whose canonical md5 split matches `split` are scored ("all"
    disables the filter). Each kept episode contributes its winning seat's decisions
    to that seat's family bucket. A draw, an unreadable opener, or a family that
    stays "other" all still classify; only a missing cohort seat drops an episode.
    Returns {split, threshold, episodes, skipped, by_family:{fam:{episodes,n,agree,
    agreement}}, overall:{...}}. Pure over the inputs, never raises.
    """
    by_family = {}
    episodes = 0
    skipped = 0
    for replay, label in load_replays(source, limit=limit):
        if split in ("train", "test") and replay_trace.split_of(label) != split:
            continue
        seat = cohort_seat(replay)
        if seat is None:
            skipped += 1
            continue
        decks = seat_decklists(replay)
        family = (
            classify_family(decks[seat], signatures, threshold)
            if decks is not None
            else "other"
        )
        res = agreement(replay, pilot_choose, seat)
        episodes += 1
        row = by_family.setdefault(family, {"episodes": 0, "n": 0, "agree": 0})
        row["episodes"] += 1
        row["n"] += res["n"]
        row["agree"] += res["agree"]
    for row in by_family.values():
        row["agreement"] = (row["agree"] / row["n"]) if row["n"] else None
    total_n = sum(r["n"] for r in by_family.values())
    total_agree = sum(r["agree"] for r in by_family.values())
    return {
        "split": split,
        "threshold": threshold,
        "episodes": episodes,
        "skipped": skipped,
        "by_family": by_family,
        "overall": {
            "n": total_n,
            "agree": total_agree,
            "agreement": (total_agree / total_n) if total_n else None,
        },
    }


def _default_pilot():
    """The deployed heuristic pilot's choose(), imported lazily (pulls in cg)."""
    from agents.heuristics import choose

    return choose


def _print_summary(report) -> None:
    ov = report["overall"]
    agr = ov["agreement"]
    print(
        f"split={report['split']} threshold={report['threshold']} "
        f"episodes={report['episodes']} (skipped {report['skipped']})"
    )
    print(
        f"overall: {ov['agree']}/{ov['n']} "
        + (f"({agr:.3f})" if agr is not None else "(n/a)")
    )
    print("\nper archetype family (episodes, decisions, agreement):")
    fams = sorted(report["by_family"], key=lambda f: -report["by_family"][f]["n"])
    for fam in fams:
        row = report["by_family"][fam]
        r = row["agreement"]
        rstr = f"{r:.3f}" if r is not None else "n/a"
        print(
            f"  {fam:<28} ep={row['episodes']:<5} n={row['n']:<6} "
            f"agree={row['agree']:<6} ({rstr})"
        )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", help="a .zip of episode JSONs or a dir of *.json")
    ap.add_argument("--decks-dir", default=None, help="extra archetype .csv dir")
    ap.add_argument("--threshold", type=float, default=0.35)
    ap.add_argument(
        "--split",
        choices=("all", "train", "test"),
        default="test",
        help="which md5 bucket to score (default: the held-out test bucket)",
    )
    ap.add_argument("--limit", type=int, default=None, help="cap episodes read")
    ap.add_argument(
        "--commit",
        default=None,
        help="also write the aggregate JSON to this committed path "
        "(e.g. analysis/per_archetype_baselines.json)",
    )
    ap.add_argument(
        "--out",
        default="per_archetype_baselines.json",
        help="machine JSON filename under data/derived/census/ (isolated)",
    )
    args = ap.parse_args(argv)

    signatures = build_signatures(args.decks_dir)
    report = baseline_by_family(
        args.source,
        signatures,
        _default_pilot(),
        threshold=args.threshold,
        split=args.split,
        limit=args.limit,
    )
    _print_summary(report)

    out = derived_path("census", args.out)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nbaseline written (isolated): {out}")
    if args.commit:
        Path(args.commit).write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
        )
        print(f"baseline committed: {args.commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
