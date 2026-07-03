"""Retreat-target gap miner (plan U82, LOOP_BRIEF L6, re-testing the
`analysis/retreat_gap_conditional.md` "tempo / matchup swap" theory).

`retreat_gap_conditional.md` found that 464 of 614 (75.6%) of the pilot's
missed RETREAT decisions happen while the active is barely hurt (>=90% of its
max HP), and theorized -- but did not measure -- that top players retreat
there for a matchup swap: bringing in a specific bench attacker regardless of
health. That miner only reads the MAIN decision (retreat vs not); it could not
test the theory because it never looks at WHICH bench Pokemon the expert
actually brings in. That is a separate CARD decision, SelectContext.SWITCH
(analysis/replay_trace.CTX_SWITCH), fired as the follow-up pick right after a
MAIN RETREAT choice.

Reading agents/heuristics.py confirms the shipped pilot has no rule for this
decision either: `_choose_card_select`'s GAIN_POKEMON_CONTEXTS set omits
SWITCH, so every retreat-target pick falls to `_first_legal`, the same
"arbitrary index 0" shape the promote gap had before analysis/promote_gap_miner.py
measured it. This module runs the same profile promote_gap_miner.py built
(hp ratio, energy, type matchup, index zero) over every real expert SWITCH
decision, split by the active's HP ratio at decision time, so the matchup-swap
theory is measured directly instead of assumed.

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
    CTX_SWITCH,
    iter_expert_card_decisions,
    team_seat,
)

HIGH_HP_THRESHOLD = 0.9


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


def _active_hp_ratio(me):
    """hp/maxHp of the deciding seat's own active at decision time, or None."""
    active = me.get("active") if isinstance(me, dict) else None
    mon = active[0] if isinstance(active, list) and active and active[0] else None
    if not isinstance(mon, dict):
        return None
    hp = mon.get("hp", 0)
    mx = mon.get("maxHp") or hp
    if not mx:
        return None
    return hp / mx


def _active_card_id(me):
    """Card id of the deciding seat's own active at decision time, or None."""
    active = me.get("active") if isinstance(me, dict) else None
    mon = active[0] if isinstance(active, list) and active and active[0] else None
    return mon.get("id") if isinstance(mon, dict) else None


def _opponent_active_id(obs, seat):
    """Card id of the opponent's active Pokemon at decision time, or None.

    Mirrors `analysis.promote_gap_miner._opponent_active_id` (2-player, opponent
    is the other seat) so both miners read the matchup feature identically.
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


def retreat_target_rows(replays, expert_teams, pilot_choose=None):
    """One row per real expert retreat-target (SWITCH) decision.

    For every scorable expert CARD decision in the CTX_SWITCH context, runs the
    pilot (agents.heuristics.choose by default, or an injected `pilot_choose`
    for tests) on the same observation and records whether it agrees with the
    expert's played index, plus per-candidate profile stats (hp ratio, energy
    count, type matchup vs the opponent's active) mirroring
    `analysis.promote_gap_miner.promote_gap_rows`. Each row also carries the
    deciding seat's OWN active hp ratio and its matchup score at decision time,
    plus the delta between the played target's matchup and the outgoing
    active's matchup, so a caller can test the "swap to a better matchup while
    barely hurt" theory directly. Pure, never raises: a pilot exception counts
    as a disagreement rather than aborting the batch.
    """
    if pilot_choose is None:
        from agents.heuristics import choose as pilot_choose

    rows = []
    for replay, label in replays:
        seat = team_seat(replay, expert_teams)
        if seat is None:
            continue
        for obs, played in iter_expert_card_decisions(replay, seat, {CTX_SWITCH}):
            state = obs.get("current") or {}
            players = state.get("players") or []
            me = players[seat] if 0 <= seat < len(players) else {}
            me = me if isinstance(me, dict) else {}
            bench = me.get("bench")
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

            active_ratio = _active_hp_ratio(me)
            active_id = _active_card_id(me)
            active_matchup = (
                matchup_score(active_id, opp_id)
                if active_id is not None and opp_id is not None
                else None
            )
            played_matchup = matchups.get(played)
            matchup_delta = (
                played_matchup - active_matchup
                if played_matchup is not None and active_matchup is not None
                else None
            )

            rows.append(
                {
                    "episode": label,
                    "n_options": len(options),
                    "agree": pilot_idx == played,
                    "active_hp_ratio": active_ratio,
                    "high_hp": (
                        active_ratio is not None and active_ratio >= HIGH_HP_THRESHOLD
                    ),
                    "played_hp_ratio": ratios.get(played),
                    "played_is_max_hp_ratio": (
                        max_ratio_idx is not None and played == max_ratio_idx
                    ),
                    "played_is_max_energy": (
                        max_energy_idx is not None and played == max_energy_idx
                    ),
                    "played_is_index_zero": played == 0,
                    "played_matchup_score": played_matchup,
                    "played_is_best_matchup": (
                        max_matchup_idx is not None and played == max_matchup_idx
                    ),
                    "active_matchup_score": active_matchup,
                    "matchup_delta": matchup_delta,
                    "matchup_improves": (
                        matchup_delta is not None and matchup_delta > 0
                    ),
                }
            )
    return rows


def _rate(rows, key) -> float:
    n = len(rows)
    return (sum(1 for r in rows if r[key]) / n) if n else 0.0


def summarize(rows) -> dict:
    """Overall and high/lower-HP-split profile of the real retreat-target pick.

    Splits on the SAME active_hp_ratio >= 0.9 threshold `retreat_gap_miner`'s
    threshold_miss bucket used, so the "barely hurt, tempo/matchup swap" theory
    can be checked against exactly the population it was proposed for. Pure.
    """
    high = [r for r in rows if r["high_hp"]]
    low = [r for r in rows if not r["high_hp"]]

    def _profile(subset):
        return {
            "n": len(subset),
            "agree_rate": _rate(subset, "agree"),
            "max_hp_ratio_rate": _rate(subset, "played_is_max_hp_ratio"),
            "max_energy_rate": _rate(subset, "played_is_max_energy"),
            "best_matchup_rate": _rate(subset, "played_is_best_matchup"),
            "matchup_improves_rate": _rate(subset, "matchup_improves"),
            "index_zero_rate": _rate(subset, "played_is_index_zero"),
        }

    overall = _profile(rows)
    overall["high_hp"] = _profile(high)
    overall["lower_hp"] = _profile(low)
    return overall


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

    rows = retreat_target_rows(load_replays(args.source, limit=args.limit), args.teams)
    summary = summarize(rows)
    print(f"expert teams: {', '.join(args.teams)}")
    print(f"real expert retreat-target (SWITCH) decisions scored: {summary['n']}")

    def _print(label, prof):
        print(f"\n{label} (n={prof['n']}):")
        print(f"  pilot (_first_legal) agreement rate: {prof['agree_rate'] * 100:.1f}%")
        print(f"  expert picked the max hp-ratio bench option: {prof['max_hp_ratio_rate'] * 100:.1f}%")
        print(f"  expert picked the max-energy bench option:  {prof['max_energy_rate'] * 100:.1f}%")
        print(f"  expert picked the best type-matchup option: {prof['best_matchup_rate'] * 100:.1f}%")
        print(f"  target matchup beats outgoing active's:     {prof['matchup_improves_rate'] * 100:.1f}%")
        print(f"  expert picked bench index 0:                {prof['index_zero_rate'] * 100:.1f}%")

    _print("overall", summary)
    _print("high-HP active (>=0.9)", summary["high_hp"])
    _print("lower-HP active (<0.9)", summary["lower_hp"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
