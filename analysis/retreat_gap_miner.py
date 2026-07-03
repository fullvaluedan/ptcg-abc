"""Retreat-gap conditional miner (plan U82, LOOP_BRIEF L6 "retreat timing").

The move-ranking breakdown named RETREAT the pilot's worst category by a wide
margin: 2/202 (1.0%) exact-target agreement with the top players
(analysis/move_ranking_diverges_ability_gap.md). Unlike the ABILITY gap (a total
capability hole) or the ATTACH gap (already root-caused in
analysis/energy_seq_refuted_by_expert_moves.md as ordering, not mistargeting),
RETREAT's low number could come from two very different causes that need
different fixes:

  1. Ordering: `should_retreat` (agents/heuristics.py) already agrees a retreat
     is warranted on the real state, but a higher-priority develop category
     (EVOLVE/PLAY/ATTACH/ABILITY) produced the pilot's actual pick first. This is
     a single-decision artifact, not a real disagreement (over a full turn the
     pilot still retreats once development is done).
  2. Threshold miss: `should_retreat`'s own HP-ratio rule (RETREAT_HP_RATIO,
     default 0.34) says False on the real state, so the pilot never even
     considers retreating. This is the genuine gap: real conditions under which
     top players retreat that the shipped rule does not model.

This module runs the shipped pilot AND the shipped `should_retreat` rule
directly (with lethal_available forced False, isolating the pure HP-ratio
verdict from whatever else preempted it) on every real expert RETREAT decision,
and buckets each one so the two causes are told apart before any lever is built.
Pure over the raw replay dicts and the injected pilot; reads the competition
dataset but never redistributes it (replay files stay gitignored).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.move_ranking_validator import (  # noqa: E402
    DEFAULT_EXPERT_TEAMS,
    _option_category,
    load_replays,
)
from analysis.replay_trace import iter_expert_decisions, team_seat  # noqa: E402


def _active_and_bench(obs):
    """(my_active, bench) for the deciding seat's own board, or (None, []).

    Mirrors agents.heuristics.choose's own player-record extraction so this miner
    reads exactly the state the shipped rule would have seen. Pure, defensive:
    any missing piece yields (None, []).
    """
    from agents.heuristics import _active

    state = obs.get("current") or {}
    yi = state.get("yourIndex", 0)
    players = state.get("players") or []
    if not (0 <= yi < len(players)):
        return None, []
    me = players[yi]
    if not isinstance(me, dict):
        return None, []
    return _active(me), (me.get("bench") or [])


def _hp_ratio(mon):
    """A Pokemon's hp/maxHp in [0, 1], or None when unknown. Pure, never raises."""
    if not mon:
        return None
    hp = mon.get("hp", 0)
    mx = mon.get("maxHp") or hp
    if not mx:
        return None
    return hp / mx


def retreat_gap_rows(replays, expert_teams, pilot_choose=None):
    """One row per real expert RETREAT decision, classifying the pilot's miss.

    For every scorable expert MAIN decision whose PLAYED option is category
    RETREAT, runs the pilot (agents.heuristics.choose by default, or an injected
    `pilot_choose` for tests) on the same observation and buckets the result:

      "agree"          -- the pilot's chosen index equals the expert's.
      "preempted"      -- should_retreat already agrees a retreat is warranted on
                          the real state, but the pilot picked a different
                          category (a higher-priority develop step ran first).
      "threshold_miss" -- should_retreat says False on the real state, so the
                          pilot never considered retreating at all.

    Each row also carries the active's hp ratio and the best bench hp ratio at
    decision time, so a caller can profile the threshold_miss bucket's actual HP
    distribution. Pure over the inputs, never raises (a per-decision failure,
    e.g. a pilot exception, is treated as pilot_idx=None rather than aborting).
    """
    from agents.heuristics import should_retreat

    if pilot_choose is None:
        from agents.heuristics import choose as pilot_choose

    rows = []
    for replay, label in replays:
        seat = team_seat(replay, expert_teams)
        if seat is None:
            continue
        for obs, played in iter_expert_decisions(replay, seat):
            sel = obs.get("select") or {}
            if _option_category(sel, played) != "RETREAT":
                continue
            try:
                choice = pilot_choose(obs)
            except Exception:
                choice = None
            pilot_idx = (
                choice[0]
                if isinstance(choice, (list, tuple))
                and len(choice) == 1
                and isinstance(choice[0], int)
                and not isinstance(choice[0], bool)
                else None
            )
            pilot_cat = (
                _option_category(sel, pilot_idx) if pilot_idx is not None else "NONE"
            )
            my_active, bench = _active_and_bench(obs)
            rule_says_retreat = bool(
                my_active is not None and should_retreat(my_active, bench, False)
            )
            if pilot_idx == played:
                bucket = "agree"
            elif rule_says_retreat:
                bucket = "preempted"
            else:
                bucket = "threshold_miss"
            bench_ratios = [r for r in (_hp_ratio(b) for b in bench if b) if r is not None]
            rows.append(
                {
                    "episode": label,
                    "bucket": bucket,
                    "pilot_category": pilot_cat,
                    "active_hp_ratio": _hp_ratio(my_active),
                    "bench_best_hp_ratio": max(bench_ratios) if bench_ratios else None,
                }
            )
    return rows


def summarize(rows) -> dict:
    """Bucket counts plus the threshold_miss active-hp-ratio distribution.

    Splits the threshold_miss active_hp_ratio values into 0.1-wide bins (floored,
    top bin absorbs exactly 1.0) so a caller can see WHAT health level top
    players retreat at that the shipped RETREAT_HP_RATIO threshold does not
    reach, without a stats dependency. Pure.
    """
    counts = {"agree": 0, "preempted": 0, "threshold_miss": 0}
    bins = {}
    for row in rows:
        counts[row["bucket"]] = counts.get(row["bucket"], 0) + 1
        if row["bucket"] == "threshold_miss" and row["active_hp_ratio"] is not None:
            b = min(int(row["active_hp_ratio"] * 10) / 10, 0.9)
            bins[b] = bins.get(b, 0) + 1
    return {"n": len(rows), "counts": counts, "threshold_miss_hp_ratio_bins": bins}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "source", help="a .zip of episode JSONs or a directory of *.json replays"
    )
    ap.add_argument(
        "--teams",
        nargs="+",
        default=list(DEFAULT_EXPERT_TEAMS),
        help="expert team names whose seat's decisions are scored",
    )
    ap.add_argument(
        "--limit", type=int, default=1500, help="max replays to read"
    )
    args = ap.parse_args(argv)

    rows = retreat_gap_rows(load_replays(args.source, limit=args.limit), args.teams)
    summary = summarize(rows)
    print(f"expert teams: {', '.join(args.teams)}")
    print(f"real expert RETREAT decisions scored: {summary['n']}")
    for bucket in ("agree", "preempted", "threshold_miss"):
        n = summary["counts"].get(bucket, 0)
        pct = (n / summary["n"] * 100) if summary["n"] else 0.0
        print(f"  {bucket:<15} {n:<5} ({pct:.1f}%)")
    print("\nthreshold_miss active hp ratio at decision time (0.1-wide bins):")
    for b in sorted(summary["threshold_miss_hp_ratio_bins"]):
        print(f"  {b:.1f}-{b + 0.1:.1f}: {summary['threshold_miss_hp_ratio_bins'][b]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
