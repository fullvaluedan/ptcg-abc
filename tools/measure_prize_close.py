"""Measure whether PTCG_PRIZE_CLOSE actually FLIPS a real pilot decision on trolley.

The prize-close optimization lever (U105, staged off behind PTCG_PRIZE_CLOSE) modifies
_resolve_attack() to prioritize lethal attacks when we have 1-2 prizes remaining. When
on, if a lethal attack is available and we're close on prizes, we take it to win
immediately instead of other actions (like attach/bench/play). The lever is motivated
by the blindspot audit (P8): agents should make game-ending decisions when prizes are
low (opponent at 0 prizes = instant win).

Same discipline as measure_attack_first: CAN-fire is not the same as MATTERS. A
condition that is satisfiable in theory but never actually met in real captured
positions would flip ~0 decisions and waste a scarce daily ladder slot. This tool
captures real mid-game MAIN observations where 1-2 prizes remain and an ATTACK option
is offered with a lethal attack available, then toggles heuristics._PRIZE_CLOSE off
and on and compares the end-to-end pilot decision choose() returns.

If the lever flips ~0 decisions here, it is inert in practice on trolley; do NOT
spend a hard-ring slot on it. This measurement can only REFUTE the lever as inert
or confirm it is LIVE (changes real decisions); it makes no win-rate claim -- a live
lever still needs the hard-ring A/B (>=+5pp, gauntlet-direction agreement) before any
ladder slot.

Dev/measurement tool only; never shipped, touches no shipped code path (the
_PRIZE_CLOSE flag is toggled on the imported module attribute, read once at import
in heuristics.py, and restored in a finally), so the frozen batch stays byte-identical.
The native engine is a per-process singleton, so it runs one match in process.
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


def capture_prize_close_obs(deck_ids, limit=8, max_matches=10):
    """Play heuristic-vs-random matches piloting deck_ids and collect MAIN
    observations where we have 1-2 prizes remaining and an ATTACK option is offered.
    We'll later filter to positions where a lethal attack is actually available.
    A single match rarely visits this exact overlap more than once or twice, so this
    plays up to max_matches matches, stopping early once limit positions are captured.
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
        ):
            # Check if we have 1-2 prizes remaining
            our_prizes = h._our_prize_count(obs)
            if 0 < our_prizes <= 2:
                groups = h.options_by_type(sel.get("option", []))
                if h.OPT_ATTACK in groups:
                    captured.append(obs)
        return piloted(obs)

    for _ in range(max_matches):
        if len(captured) >= limit:
            break
        make_env().run([capturing, "random"])
    return captured


def _decide(obs, prize_close):
    """Return chosen_option under a _PRIZE_CLOSE setting.

    The flag is toggled on the imported module attribute and restored in a finally,
    so no shipped code path is mutated.
    """
    saved = h._PRIZE_CLOSE
    h._PRIZE_CLOSE = prize_close
    try:
        chosen = h.choose(obs)
    finally:
        h._PRIZE_CLOSE = saved
    chosen_opt = chosen[0] if isinstance(chosen, list) and chosen else None
    return chosen_opt


def _best_attack_info(obs):
    """Return (is_lethal, damage) for the best available attack, or (False, None) if unknown.

    This is the decision-independent property of the observation (same regardless
    of flag), so the report can show whether a lethal attack was actually available.
    """
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
    if ba is not None:
        # best_attack returns (index, eff_damage, is_lethal)
        return (ba[2], ba[1])  # (is_lethal, damage)
    return (False, None)


def measure(deck_path, limit=8):
    deck_ids = read_deck(deck_path)
    ensure_official_cg()
    positions = capture_prize_close_obs(deck_ids, limit=limit)
    rows = []
    for obs in positions:
        turn = (obs.get("current") or {}).get("turn")
        our_prizes = h._our_prize_count(obs)
        is_lethal, ba_dmg = _best_attack_info(obs)
        ch_off = _decide(obs, False)
        ch_on = _decide(obs, True)
        rows.append({
            "turn": turn,
            "our_prizes": our_prizes,
            "attack_is_lethal": is_lethal,
            "attack_damage": ba_dmg,
            "choose_off": ch_off,
            "choose_on": ch_on,
            "choose_flip": ch_off != ch_on,
        })
    return {"deck": Path(deck_path).stem, "rows": rows}


def _format(result):
    lines = [
        f"prize-close decision effect on {result['deck']} "
        f"(heuristic pilot, real captured 1-2-prize ATTACK-offered positions):",
        "  turn  prizes  lethal  dmg  choose_off  choose_on  choose_flip",
    ]
    for r in result["rows"]:
        lines.append(
            f"  {str(r['turn']):>4s}  {str(r['our_prizes']):>6s}  "
            f"{str(r['attack_is_lethal']):>6s}  {str(r['attack_damage']):>4s}  "
            f"{str(r['choose_off']):>10s}  {str(r['choose_on']):>9s}  "
            f"{str(r['choose_flip']):>11s}"
        )
    n = len(result["rows"])
    if n:
        flips = sum(1 for r in result["rows"] if r["choose_flip"])
        lethal_count = sum(1 for r in result["rows"] if r["attack_is_lethal"])
        lines.append(f"  positions captured (1-2 prizes + attack offered): {n}")
        lines.append(f"  positions with a lethal attack available: "
                     f"{lethal_count}/{n}")
        lines.append(f"  prize-close flipped the pilot decision on {flips}/{n} positions")
        if flips == 0:
            lines.append(
                "  => PTCG_PRIZE_CLOSE changes no decision on these trolley positions; it is "
                "inert in practice here, do NOT spend a hard-ring slot on it."
            )
        else:
            lines.append(
                "  => PTCG_PRIZE_CLOSE is live on trolley (changes real decisions); the "
                "hard-ring A/B is the next honest check before any ladder slot."
            )
    else:
        lines.append("  no 1-2-prize positions captured; increase -n or the match length")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck", nargs="?", default=str(_ROOT / "decks" / "trolley.csv"),
                    help="deck csv path (default: decks/trolley.csv, the shipped batch deck)")
    ap.add_argument("-n", "--positions", type=int, default=8,
                    help="max mid-game MAIN 1-2-prize positions to capture and measure")
    args = ap.parse_args()
    print(_format(measure(args.deck, limit=args.positions)))


if __name__ == "__main__":
    main()
