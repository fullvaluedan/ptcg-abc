"""Mastery-scored archetype target selector (plan U36).

Picks the target family the deck-aware pilot should master. The expert census
(U25) counts only the WINNING seat, so its "target family" is really the widest
ADOPTED pillar: a measure of popularity, not skill. A deck that is merely common
racks up raw wins by volume even at a mediocre win rate. This selector folds in
the LOSING appearances the census drops (it classifies BOTH seats of every
decided episode) and scores each family by

    MASTERY = expert_wins * expert_win_rate

so a popular-but-mediocre pillar cannot win the target slot on adoption alone.
The selector is free to disagree with the Grimmsnarl census prior; its verdict
is a separate, mastery-weighted signal, not a re-derivation of the census.

Output is competition-derived (mined from episodes the license forbids
redistributing), so the machine-readable targets JSON is written THROUGH the
shared isolation helper into data/derived/targets/ (gitignored). The committed
artifact is the human verdict analysis/archetype_select.md, authored from this
tool's summary; it carries per-family counts, never raw episodes.

Pure and cg-free at import: family classification takes injected archetype
signatures (main() wires in the real ones from analysis/archetype via
expert_census.build_signatures), so the scoring primitives unit-test without the
card engine. Reuses analysis/expert_cohort so the selector reads the winner, the
opener decklists, and the family the exact same way the census does.

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

from analysis import expert_cohort as ec  # noqa: E402
from analysis.move_ranking_validator import load_replays  # noqa: E402
from tools.expert_census import build_signatures  # noqa: E402
from tools.isolation import derived_path  # noqa: E402

# A family with fewer than this many games has too noisy a win rate to name a
# target; it is still reported for coverage but cannot win the target slot.
MIN_GAMES = 50

# "other" is the below-threshold grab-bag, not a real archetype, so it is
# reported but never selected as the target.
OTHER = "other"


def mastery_rows(replay, signatures, threshold: float = 0.35):
    """Both seats' (family, won) contribution for one decided episode, or None.

    Unlike census_episode (which credits only the winning seat), this classifies
    BOTH seats and marks which one won, so a family's LOSING appearances are
    counted and a real win rate can be computed. A draw, a missing reward, or an
    unreadable opener drops the episode (returns None) so a batch over thousands
    of games never credits an ambiguous seat. Pure, never raises.
    """
    seat = ec.winner_seat(replay)
    if seat is None:
        return None
    decks = ec.seat_decklists(replay)
    if decks is None:
        return None
    names = ec.team_names(replay)
    rows = []
    for s in (0, 1):
        rows.append(
            {
                "family": ec.classify_family(decks[s], signatures, threshold),
                "won": s == seat,
                "team": names[s] if names is not None else None,
            }
        )
    return rows


def aggregate(episode_rows) -> dict:
    """Fold mastery_rows results into per-family games/wins, skipping None.

    `episode_rows` is an iterable of mastery_rows results (each a two-seat list or
    None); None entries (draws / malformed) are counted as skipped so the report
    states its own coverage. Per family it sums games (appearances) and wins.
    Pure, never raises.
    """
    by_family = {}
    episodes = 0
    skipped = 0
    for rows in episode_rows:
        if rows is None:
            skipped += 1
            continue
        episodes += 1
        for row in rows:
            fam = by_family.setdefault(row["family"], {"games": 0, "wins": 0})
            fam["games"] += 1
            if row["won"]:
                fam["wins"] += 1
    return {"episodes": episodes, "skipped": skipped, "by_family": by_family}


def win_rate(stats: dict) -> float:
    """Expert win rate for a family: wins / games (0.0 when it never appeared)."""
    games = stats.get("games", 0)
    return stats.get("wins", 0) / games if games else 0.0


def mastery_score(stats: dict) -> float:
    """Mastery = expert wins * expert win rate.

    Raw wins are a popularity artifact: a widely played deck accumulates wins by
    volume even at a coin-flip win rate. Multiplying by win rate rewards a deck
    that actually converts its games, so a common-but-mediocre pillar cannot top
    the ranking on adoption alone. Pure.
    """
    return stats.get("wins", 0) * win_rate(stats)


def rank_families(report: dict, min_games: int = MIN_GAMES) -> list:
    """Every family with games, wins, win_rate, mastery, and eligibility.

    Sorted by mastery descending, then name ascending for a deterministic tie
    break. "other" and families under `min_games` are marked ineligible: reported
    for coverage, never selectable as the target.
    """
    out = []
    for name, stats in report["by_family"].items():
        out.append(
            {
                "family": name,
                "games": stats["games"],
                "wins": stats["wins"],
                "win_rate": win_rate(stats),
                "mastery": mastery_score(stats),
                "eligible": name != OTHER and stats["games"] >= min_games,
            }
        )
    out.sort(key=lambda r: (-r["mastery"], r["family"]))
    return out


def select_target(ranking: list):
    """The highest-mastery eligible family in a rank_families ranking, or None.

    The ranking is already sorted by mastery, so the first eligible entry is the
    target; None when no family clears the eligibility bar (min games, not
    "other").
    """
    for row in ranking:
        if row["eligible"]:
            return row["family"]
    return None


def run_select(source, signatures, threshold, limit=None) -> dict:
    """Aggregate the two-seat mastery census over every episode in `source`."""
    rows = (
        mastery_rows(replay, signatures, threshold)
        for replay, _label in load_replays(source, limit=limit)
    )
    return aggregate(rows)


def _print_summary(report, ranking, target, min_games) -> None:
    print(
        f"mastery = wins * win_rate; eligible if family != other and "
        f"games >= {min_games}"
    )
    print(
        f"episodes: {report['episodes']} scored, {report['skipped']} skipped "
        f"(draws / malformed)"
    )
    print("\nper archetype family (games, wins, win_rate, mastery, eligible):")
    for row in ranking:
        mark = " <-- target" if row["family"] == target else ""
        elig = "yes" if row["eligible"] else "no "
        print(
            f"  {row['family']:<28} games={row['games']:<6} "
            f"wins={row['wins']:<6} wr={row['win_rate']:.3f} "
            f"mastery={row['mastery']:.2f} elig={elig}{mark}"
        )
    print(f"\ntarget family (mastery): {target}")


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
        "--min-games",
        type=int,
        default=MIN_GAMES,
        help="minimum family appearances to be eligible as the target",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        help="cap episodes read (default: the whole dataset)",
    )
    ap.add_argument(
        "--out",
        default="targets.json",
        help="targets JSON filename under data/derived/targets/ (isolated)",
    )
    args = ap.parse_args(argv)

    signatures = build_signatures(args.decks_dir)
    report = run_select(args.source, signatures, args.threshold, limit=args.limit)
    ranking = rank_families(report, min_games=args.min_games)
    target = select_target(ranking)

    _print_summary(report, ranking, target, args.min_games)

    payload = {
        "episodes": report["episodes"],
        "skipped": report["skipped"],
        "threshold": args.threshold,
        "min_games": args.min_games,
        "ranking": ranking,
        "target_family": target,
    }
    out = derived_path("targets", args.out)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"targets written (isolated): {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
