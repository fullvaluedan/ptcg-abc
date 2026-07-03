"""Measure whether PTCG_ATTACK_FIRST actually FLIPS a real pilot decision on trolley.

The attack-before-attach lever (U93, staged off behind PTCG_ATTACK_FIRST) lives in
heuristics.choose's _resolve_attack_first: when a positive-value attack is already
legal THIS decision (using energy already attached) and an ATTACH option is also
legal, it takes the attack now instead of the discretionary attach. The lever is
motivated by U91's confirmed game-plan mining finding (analysis/gameplan_claims_
bracket_4.md): winners attach-before-attack, and bank energy without attacking,
LESS often than losers on real bracket_4 replays (both gates pass, n>1400/side).

Same discipline as measure_energy_seq/measure_bench_dig/measure_worlds: CAN-fire is
not the same as MATTERS. A condition that is satisfiable by the card pool but never
actually met in real captured positions would flip ~0 decisions and waste a scarce
daily ladder slot on a bracket-ring A/B that can never show a difference. This tool
answers it empirically: it captures real mid-game MAIN observations where BOTH an
ATTACH and a legal ATTACK option are offered from a trolley-piloted match, then for
each toggles heuristics._ATTACK_FIRST off and on and compares the end-to-end pilot
decision choose() returns.

If the lever flips ~0 decisions here, it is inert in practice on trolley; do NOT
spend a bracket-ring slot on it. This measurement can only REFUTE the lever as inert
or confirm it is LIVE (changes real decisions); it makes no win-rate claim (offline
weak-bot play is not ladder-predictive per meta.md) -- a live lever still needs the
bracket-ring A/B (>=+5pp, gauntlet-direction agreement) before any ladder slot.

Dev/measurement tool only; never shipped, touches no shipped code path (the
_ATTACK_FIRST flag is toggled on the imported module attribute, read once at import
in heuristics.py, and restored in a finally), so the frozen batch stays
byte-identical and the pending A/B is unpolluted. The native engine is a per-process
singleton, so it runs one match in process.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agents import heuristics as h  # noqa: E402
from ptcg_agent.engine import ensure_official_cg, make_env  # noqa: E402
from tools import opponents  # noqa: E402
from tools.deck_match import deck_bound  # noqa: E402
from tools.deck_validate import read_deck  # noqa: E402


def capture_attack_attach_obs(deck_ids, limit=8, min_turn=3, max_matches=10):
    """Play heuristic-vs-random matches piloting deck_ids and collect MAIN
    observations that offer BOTH an ATTACH and an ATTACK option (where the lever
    can bite). A single match rarely visits this exact overlap more than once or
    twice, so this plays up to max_matches matches, stopping early once limit
    positions are captured.
    """
    piloted = deck_bound(opponents.get("heuristic"), deck_ids)
    captured: list = []

    def capturing(obs):
        sel = obs.get("select")
        if (
            len(captured) < limit
            and sel is not None
            and sel.get("type") == h.SEL_MAIN
            and sel.get("maxCount", 1) == 1
            and (obs.get("current") or {}).get("turn", 0) >= min_turn
        ):
            groups = h.options_by_type(sel.get("option", []))
            if h.OPT_ATTACH in groups and h.OPT_ATTACK in groups:
                captured.append(obs)
        return piloted(obs)

    for _ in range(max_matches):
        if len(captured) >= limit:
            break
        make_env().run([capturing, "random"])
    return captured


def _decide(obs, attack_first):
    """Return (ba_value, chosen_option) under an _ATTACK_FIRST setting.

    ba_value is the effective damage of the best legal attack in this position (a
    fixed property of the observation, independent of the flag), so the report can
    show whether a "live" attack was actually on the table. The flag is toggled on
    the imported module attribute and restored in a finally, so no shipped code path
    is mutated.
    """
    saved = h._ATTACK_FIRST
    h._ATTACK_FIRST = attack_first
    try:
        chosen = h.choose(obs)
    finally:
        h._ATTACK_FIRST = saved
    chosen_opt = chosen[0] if isinstance(chosen, list) and chosen else None
    return chosen_opt


def _ba_value(obs):
    sel = obs.get("select") or {}
    groups = h.options_by_type(sel.get("option", []))
    state = obs.get("current") or {}
    yi = state.get("yourIndex", 0)
    players = state.get("players") or []
    me = players[yi] if len(players) > yi else {}
    opp = players[1 - yi] if len(players) > 1 - yi else {}
    my_active = h._active(me)
    opp_active = h._active(opp)
    my_active_id = my_active.get("id") if my_active else None
    opp_active_id = opp_active.get("id") if opp_active else None
    opp_active_hp = opp_active.get("hp") if opp_active else None
    ba = h.best_attack(groups, my_active_id, opp_active_id, opp_active_hp)
    return ba[1] if ba is not None else None


def measure(deck_path, limit=8):
    deck_ids = read_deck(deck_path)
    ensure_official_cg()
    positions = capture_attack_attach_obs(deck_ids, limit=limit)
    rows = []
    for obs in positions:
        turn = (obs.get("current") or {}).get("turn")
        ba_value = _ba_value(obs)
        ch_off = _decide(obs, False)
        ch_on = _decide(obs, True)
        rows.append({
            "turn": turn,
            "ba_value": ba_value,
            "choose_off": ch_off,
            "choose_on": ch_on,
            "choose_flip": ch_off != ch_on,
        })
    return {"deck": Path(deck_path).stem, "rows": rows}


def _format(result):
    lines = [
        f"attack-first decision effect on {result['deck']} "
        f"(heuristic pilot, real captured ATTACH+ATTACK positions):",
        "  turn  ba_value  choose_off  choose_on  choose_flip",
    ]
    for r in result["rows"]:
        lines.append(
            f"  {str(r['turn']):>4s}  {str(r['ba_value']):>8s}  "
            f"{str(r['choose_off']):>10s}  {str(r['choose_on']):>9s}  "
            f"{str(r['choose_flip']):>11s}"
        )
    n = len(result["rows"])
    if n:
        flips = sum(1 for r in result["rows"] if r["choose_flip"])
        lines.append(f"  positions captured (attach and attack both legal): {n}")
        lines.append(f"  positions with a positive-value attack on the table: "
                     f"{sum(1 for r in result['rows'] if (r['ba_value'] or 0) > 0)}/{n}")
        lines.append(f"  attack-first flipped the pilot decision on {flips}/{n} positions")
        if flips == 0:
            lines.append(
                "  => PTCG_ATTACK_FIRST changes no decision on these trolley positions; it is "
                "inert in practice here, do NOT spend a bracket-ring slot on it."
            )
        else:
            lines.append(
                "  => PTCG_ATTACK_FIRST is live on trolley (changes real decisions); the "
                "bracket-ring A/B is the next honest check before any ladder slot."
            )
    else:
        lines.append("  no ATTACH+ATTACK positions captured; increase -n or the match length")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck", nargs="?", default=str(_ROOT / "decks" / "trolley.csv"),
                    help="deck csv path (default: decks/trolley.csv, the shipped batch deck)")
    ap.add_argument("-n", "--positions", type=int, default=8,
                    help="max mid-game MAIN attach+attack positions to capture and measure")
    args = ap.parse_args()
    print(_format(measure(args.deck, limit=args.positions)))


if __name__ == "__main__":
    main()
