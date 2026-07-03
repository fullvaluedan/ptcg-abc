"""Promote-choice gap miner (plan U82, LOOP_BRIEF L6 "promote choice after a knockout").

A post-knockout promote (SelectContext.TO_ACTIVE, an empty active spot forcing a
pick from the bench) is a CARD select, not a MAIN category, so it was never
scored by the move-ranking breakdown (analysis/move_ranking_diverges_ability_gap.md
only covers MAIN decisions). Reading agents/heuristics.py shows the shipped pilot
has NO dedicated rule for it at all: `_choose_card_select`'s GAIN_POKEMON_CONTEXTS
set (SETUP_BENCH_POKEMON, TO_BENCH, TO_FIELD, TO_HAND) omits TO_ACTIVE, so every
promote decision falls straight to `_first_legal`, which always returns bench
index 0 regardless of any candidate's HP, energy investment, or anything else.
This is a genuine, previously-unmeasured blind spot distinct from ATTACH (already
root-caused as ordering) and RETREAT (already root-caused as a missing matchup
signal): here there is no rule to be preempted or under-thresholded, the pick is
simply arbitrary.

This module runs the shipped pilot on every real expert promote decision and
profiles what the top players actually pick, so a concrete replacement rule (e.g.
"promote the highest current HP") can be proposed and checked against real data
before it is built, rather than guessed.

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

from analysis.matchup_delta import matchup_score  # noqa: E402
from analysis.move_ranking_validator import (  # noqa: E402
    DEFAULT_EXPERT_TEAMS,
    load_replays,
)
from analysis.replay_trace import (  # noqa: E402
    AREA_BENCH,
    CTX_TO_ACTIVE,
    iter_expert_card_decisions,
    team_seat,
)


def _pilot_index(choice) -> int | None:
    """Normalize a pilot's return value to a single option index, or None."""
    if (
        isinstance(choice, (list, tuple))
        and len(choice) == 1
        and isinstance(choice[0], int)
        and not isinstance(choice[0], bool)
    ):
        return choice[0]
    return None


def _bench_hp_ratio(bench, idx):
    """hp/maxHp of the bench entry option `idx` resolves to, or None."""
    if not (0 <= idx < len(bench)):
        return None
    mon = bench[idx]
    if not isinstance(mon, dict):
        return None
    hp = mon.get("hp", 0)
    mx = mon.get("maxHp") or hp
    if not mx:
        return None
    return hp / mx


def _bench_energy_count(bench, idx):
    """Energy cards attached to bench entry option `idx`, or None if unresolvable."""
    if not (0 <= idx < len(bench)):
        return None
    mon = bench[idx]
    if not isinstance(mon, dict):
        return None
    energy = mon.get("energy")
    return len(energy) if isinstance(energy, list) else 0


def _bench_card_id(bench, idx):
    """Card id of bench entry option `idx`, or None if unresolvable."""
    if not (0 <= idx < len(bench)):
        return None
    mon = bench[idx]
    return mon.get("id") if isinstance(mon, dict) else None


def _opponent_active_id(obs, seat):
    """Card id of the opponent's active Pokemon at decision time, or None.

    Mirrors `agents.heuristics._active`'s own extraction (2-player, opponent is
    the other seat) so the matchup feature reads exactly what a live rule would.
    """
    state = obs.get("current") or {}
    players = state.get("players") or []
    opp_i = 1 - seat
    if not (0 <= opp_i < len(players)):
        return None
    opp = players[opp_i]
    if not isinstance(opp, dict):
        return None
    active = opp.get("active") or []
    mon = active[0] if active and active[0] is not None else None
    return mon.get("id") if isinstance(mon, dict) else None


def promote_gap_rows(replays, expert_teams, pilot_choose=None):
    """One row per real expert promote (post-knockout TO_ACTIVE) decision.

    For every scorable expert CARD decision in the CTX_TO_ACTIVE context, runs the
    pilot (agents.heuristics.choose by default, or an injected `pilot_choose` for
    tests) on the same observation and records whether it agrees with the expert's
    played index, plus per-candidate profile stats (each option's hp ratio and
    energy count, whether the expert's pick was the max-hp-ratio or max-energy
    option among the choices) so a caller can see what actually governs the real
    pick. Pure, never raises: a pilot exception counts as a disagreement rather
    than aborting the batch.
    """
    if pilot_choose is None:
        from agents.heuristics import choose as pilot_choose

    rows = []
    for replay, label in replays:
        seat = team_seat(replay, expert_teams)
        if seat is None:
            continue
        for obs, played in iter_expert_card_decisions(replay, seat, {CTX_TO_ACTIVE}):
            state = obs.get("current") or {}
            players = state.get("players") or []
            me = players[seat] if 0 <= seat < len(players) else {}
            bench = me.get("bench") if isinstance(me, dict) else None
            bench = bench if isinstance(bench, list) else []
            try:
                choice = pilot_choose(obs)
            except Exception:
                choice = None
            pilot_idx = _pilot_index(choice)

            options = (obs.get("select") or {}).get("option") or []
            bench_opts = {
                i: o.get("index")
                for i, o in enumerate(options)
                if isinstance(o, dict) and o.get("area") == AREA_BENCH
                and o.get("index") is not None
            }
            ratios = {i: _bench_hp_ratio(bench, idx) for i, idx in bench_opts.items()}
            energies = {i: _bench_energy_count(bench, idx) for i, idx in bench_opts.items()}
            known_ratios = {i: r for i, r in ratios.items() if r is not None}
            known_energies = {i: e for i, e in energies.items() if e is not None}
            max_ratio_idx = max(known_ratios, key=known_ratios.get, default=None)
            max_energy_idx = max(known_energies, key=known_energies.get, default=None)

            opp_id = _opponent_active_id(obs, seat)
            ids = {i: _bench_card_id(bench, idx) for i, idx in bench_opts.items()}
            matchups = (
                {i: matchup_score(cid, opp_id) for i, cid in ids.items() if cid is not None}
                if opp_id is not None
                else {}
            )
            max_matchup_idx = max(matchups, key=matchups.get, default=None)

            rows.append(
                {
                    "episode": label,
                    "n_options": len(options),
                    "agree": pilot_idx == played,
                    "played_hp_ratio": ratios.get(played),
                    "played_is_max_hp_ratio": (
                        max_ratio_idx is not None and played == max_ratio_idx
                    ),
                    "played_is_max_energy": (
                        max_energy_idx is not None and played == max_energy_idx
                    ),
                    "played_is_index_zero": played == 0,
                    "played_matchup_score": matchups.get(played),
                    "played_is_best_matchup": (
                        max_matchup_idx is not None and played == max_matchup_idx
                    ),
                }
            )
    return rows


def summarize(rows) -> dict:
    """Agreement rate plus how often the expert's pick matches simple profiles.

    Reports, over every scored promote decision, the pilot agreement rate (how
    often `_first_legal`'s index-0 guess happens to match) alongside four
    candidate signals for a real rule: how often the expert picked the highest hp
    ratio bench option, the most-energy bench option, the best type-matchup
    option (`analysis.matchup_delta.matchup_score` vs the opponent's active), or
    index 0 itself (the baseline `_first_legal` already produces for free). Pure.
    """
    n = len(rows)
    if n == 0:
        return {
            "n": 0,
            "agree_rate": 0.0,
            "max_hp_ratio_rate": 0.0,
            "max_energy_rate": 0.0,
            "best_matchup_rate": 0.0,
            "index_zero_rate": 0.0,
        }
    return {
        "n": n,
        "agree_rate": sum(1 for r in rows if r["agree"]) / n,
        "max_hp_ratio_rate": sum(1 for r in rows if r["played_is_max_hp_ratio"]) / n,
        "max_energy_rate": sum(1 for r in rows if r["played_is_max_energy"]) / n,
        "best_matchup_rate": sum(1 for r in rows if r["played_is_best_matchup"]) / n,
        "index_zero_rate": sum(1 for r in rows if r["played_is_index_zero"]) / n,
    }


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

    rows = promote_gap_rows(load_replays(args.source, limit=args.limit), args.teams)
    summary = summarize(rows)
    print(f"expert teams: {', '.join(args.teams)}")
    print(f"real expert promote (post-knockout TO_ACTIVE) decisions scored: {summary['n']}")
    print(f"  pilot (_first_legal) agreement rate: {summary['agree_rate'] * 100:.1f}%")
    print(f"  expert picked the max hp-ratio bench option: {summary['max_hp_ratio_rate'] * 100:.1f}%")
    print(f"  expert picked the max-energy bench option:  {summary['max_energy_rate'] * 100:.1f}%")
    print(f"  expert picked the best type-matchup option: {summary['best_matchup_rate'] * 100:.1f}%")
    print(f"  expert picked bench index 0:                {summary['index_zero_rate'] * 100:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
