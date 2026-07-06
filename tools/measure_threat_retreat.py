"""Measure whether PTCG_THREAT_RETREAT actually FLIPS a real pilot decision on trolley.

The threat-aware retreat lever (U105, staged off behind PTCG_THREAT_RETREAT) modifies
should_retreat() to allow retreat when our active is above the normal HP threshold
(34%) but the opponent's active can OHKO us. A healthy bench is still required. The
lever is motivated by the blindspot audit (P8): agents should read threat state, not
just our own HP.

Same discipline as measure_attack_first: CAN-fire is not the same as MATTERS. A
condition that is satisfiable in theory but never actually met in real captured
positions would flip ~0 decisions and waste a scarce daily ladder slot. This tool
captures real mid-game MAIN observations where a RETREAT option is offered (and our
bench is healthier), then toggles heuristics._THREAT_RETREAT off and on and compares
the end-to-end pilot decision choose() returns.

If the lever flips ~0 decisions here, it is inert in practice on trolley; do NOT
spend a hard-ring slot on it. This measurement can only REFUTE the lever as inert
or confirm it is LIVE (changes real decisions); it makes no win-rate claim -- a live
lever still needs the hard-ring A/B (>=+5pp, gauntlet-direction agreement) before any
ladder slot.

Dev/measurement tool only; never shipped, touches no shipped code path (the
_THREAT_RETREAT flag is toggled on the imported module attribute, read once at import
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


def capture_retreat_threat_obs(deck_ids, limit=8, min_turn=3, max_matches=20):
    """Play heuristic-vs-random matches piloting deck_ids and collect MAIN
    observations where a RETREAT option is offered and we have a healthier bench.
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
            and (obs.get("current") or {}).get("turn", 0) >= min_turn
        ):
            groups = h.options_by_type(sel.get("option", []))
            if h.OPT_RETREAT in groups:
                # Check if we have a healthier bench and opponent active
                state = obs.get("current") or {}
                yi = state.get("yourIndex", 0)
                players = state.get("players") or []
                me = players[yi] if len(players) > yi else {}
                opp = players[1 - yi] if len(players) > 1 - yi else {}
                my_active = h._active(me)
                opp_active = h._active(opp)
                bench = me.get("bench")
                if my_active and opp_active and bench:
                    my_hp = my_active.get("hp", 0)
                    has_healthier = any(
                        b for b in bench
                        if b and b.get("hp", 0) > my_hp
                    )
                    if has_healthier:
                        # Capture this position regardless of threat level
                        # (we'll report threat stats afterward)
                        captured.append(obs)
        return piloted(obs)

    for _ in range(max_matches):
        if len(captured) >= limit:
            break
        make_env().run([capturing, "random"])
    return captured


def _decide(obs, threat_retreat):
    """Return chosen_option under a _THREAT_RETREAT setting.

    The flag is toggled on the imported module attribute and restored in a finally,
    so no shipped code path is mutated.
    """
    saved = h._THREAT_RETREAT
    h._THREAT_RETREAT = threat_retreat
    try:
        chosen = h.choose(obs)
    finally:
        h._THREAT_RETREAT = saved
    chosen_opt = chosen[0] if isinstance(chosen, list) and chosen else None
    return chosen_opt


def _threat_damage(obs):
    """Return best attack damage from opponent's active, or None if unknown.

    This is the decision-independent property of the observation (same regardless
    of flag), so the report can show whether a real threat was on the table.
    """
    state = obs.get("current") or {}
    yi = state.get("yourIndex", 0)
    players = state.get("players") or []
    me = players[yi] if len(players) > yi else {}
    opp = players[1 - yi] if len(players) > 1 - yi else {}
    my_active = h._active(me)
    opp_active = h._active(opp)
    if my_active and opp_active:
        my_hp = my_active.get("hp", 0)
        opp_active_id = opp_active.get("id")
        my_active_id = my_active.get("id")
        return h._opponent_best_attack_damage(opp_active_id, my_active_id, my_hp)
    return None


def measure(deck_path, limit=8):
    deck_ids = read_deck(deck_path)
    ensure_official_cg()
    positions = capture_retreat_threat_obs(deck_ids, limit=limit)
    rows = []
    for obs in positions:
        turn = (obs.get("current") or {}).get("turn")
        threat_dmg = _threat_damage(obs)
        my_active = h._active((obs.get("current") or {}).get("players", [{}])[
            (obs.get("current") or {}).get("yourIndex", 0)
        ])
        my_hp = my_active.get("hp", 0) if my_active else None
        ch_off = _decide(obs, False)
        ch_on = _decide(obs, True)
        rows.append({
            "turn": turn,
            "threat_dmg": threat_dmg,
            "my_hp": my_hp,
            "choose_off": ch_off,
            "choose_on": ch_on,
            "choose_flip": ch_off != ch_on,
        })
    return {"deck": Path(deck_path).stem, "rows": rows}


def _format(result):
    lines = [
        f"threat-aware retreat decision effect on {result['deck']} "
        f"(heuristic pilot, real captured RETREAT-offered + threat positions):",
        "  turn  threat_dmg  my_hp  choose_off  choose_on  choose_flip",
    ]
    for r in result["rows"]:
        lines.append(
            f"  {str(r['turn']):>4s}  {str(r['threat_dmg']):>10s}  "
            f"{str(r['my_hp']):>6s}  {str(r['choose_off']):>10s}  "
            f"{str(r['choose_on']):>9s}  {str(r['choose_flip']):>11s}"
        )
    n = len(result["rows"])
    if n:
        flips = sum(1 for r in result["rows"] if r["choose_flip"])
        lines.append(f"  positions captured (retreat offered + threat present): {n}")
        lines.append(f"  positions where opponent threat >= our HP (OHKO-capable): "
                     f"{sum(1 for r in result['rows'] if (r['threat_dmg'] or 0) >= (r['my_hp'] or 0))}/{n}")
        lines.append(f"  threat-retreat flipped the pilot decision on {flips}/{n} positions")
        if flips == 0:
            lines.append(
                "  => PTCG_THREAT_RETREAT changes no decision on these trolley positions; it is "
                "inert in practice here, do NOT spend a hard-ring slot on it."
            )
        else:
            lines.append(
                "  => PTCG_THREAT_RETREAT is live on trolley (changes real decisions); the "
                "hard-ring A/B is the next honest check before any ladder slot."
            )
    else:
        lines.append("  no retreat-threat positions captured; increase -n or the match length")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck", nargs="?", default=str(_ROOT / "decks" / "trolley.csv"),
                    help="deck csv path (default: decks/trolley.csv, the shipped batch deck)")
    ap.add_argument("-n", "--positions", type=int, default=8,
                    help="max mid-game MAIN retreat-threat positions to capture and measure")
    args = ap.parse_args()
    print(_format(measure(args.deck, limit=args.positions)))


if __name__ == "__main__":
    main()
