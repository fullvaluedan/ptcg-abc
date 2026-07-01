"""Measure whether PTCG_ENERGY_SEQ actually FLIPS a real pilot decision on trolley.

The energy-attach sequencing lever (4196f8b, staged off behind PTCG_ENERGY_SEQ) lives
in heuristics._choose_attach: once the active can already pay for its cheapest attack,
it steers the attachment onto the strongest still-underpowered benched payoff attacker
instead of overloading the front-line active. The standing batch plan lists "flip
PTCG_ENERGY_SEQ=1" as a separate single-variable A/B against the trolley floor.

Unlike the three leaf-eval terms (measure_leaf_eval proved they are inert unless
PTCG_ROLLOUT_DEPTH>0 cuts rollouts at the leaf), energy-seq lives in the HEURISTIC path,
which is the direct ladder policy on the thin-bench / at-risk / lethal turns the search
agent defers, and the rollout policy otherwise. And it is live-by-construction on the
trolley deck: Kyogre is a Basic with a 3-energy attack, so a benched Kyogre (max cost 3)
sitting behind a cheap active (Snover / Kyogre open at cost 1) satisfies the redirect
trigger (max_cost 3 > active cheapest 1) from the deck's own card structure alone.

But CAN-fire is not the same as MATTERS. A redirect condition that is satisfiable by the
card pool but never actually met in real captured positions still flips ~0 decisions and
would waste a scarce daily ladder slot (the same "fires != matters" trap measure_worlds
caught for the soft-cap keystone and measure_bench_floor re-checked for the bench floor).

This tool answers it empirically, mirroring measure_bench_floor: it captures real mid-game
MAIN observations with an ATTACH option available from a trolley-piloted match, then for
each toggles heuristics._ENERGY_SEQ off and on and compares BOTH the isolated attach target
(_choose_attach) and the end-to-end pilot decision (choose). Read the CONTRAST:

  - attach_flip: does energy-seq change which Pokemon _choose_attach powers up? This is the
    lever's direct effect wherever the pilot actually attaches.
  - choose_flip: does energy-seq change the option choose() finally returns? choose() only
    reaches the attach branch when it is not taking a lethal / rare-candy / evolve / play,
    so this is the faithful ladder-decision flip rate on these positions.

If energy-seq flips ~0 decisions here, it is inert in practice on trolley; do NOT spend a
slot on it. Neither result claims a win rate (offline weak-bot play is not ladder-predictive
per meta.md); the measurement can only REFUTE the lever as inert, exactly as
measure_leaf_eval, measure_bench_floor, and measure_worlds did.

Dev/measurement tool only; never shipped, touches no shipped code path (the _ENERGY_SEQ flag
is toggled on the imported module attribute, read once at import in heuristics.py, and
restored in a finally), so the frozen batch stays byte-identical and the pending A/B is
unpolluted. The native engine is a per-process singleton, so it runs one match in process.
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


def capture_attach_obs(deck_ids, limit=8, min_turn=3):
    """Play one heuristic-vs-random match piloting deck_ids and collect MAIN
    observations that expose an ATTACH option (where energy-seq can bite).

    deck_bound makes the heuristic pilot the exact deck the batch ships, so the
    captured positions match the batch. Energy-seq is a pure heuristic lever, so
    no search forward model is required to drive it.
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
            if h.OPT_ATTACH in groups:
                captured.append(obs)
        return piloted(obs)

    make_env().run([capturing, "random"])
    return captured


def _me(obs):
    state = obs.get("current") or {}
    yi = state.get("yourIndex", 0)
    players = state.get("players") or []
    return players[yi] if len(players) > yi else {}


def _decide(obs, energy_seq):
    """Return (attach_target, chosen_option, attached_at_attach) under a flag setting.

    attach_target is the index _choose_attach returns for this position's attach
    options; chosen_option is the option choose() finally returns; the attach flag is
    toggled on the imported module attribute and restored in a finally, so no shipped
    code path is mutated.
    """
    sel = obs.get("select") or {}
    groups = h.options_by_type(sel.get("option", []))
    attach = groups.get(h.OPT_ATTACH, [])
    me = _me(obs)
    saved = h._ENERGY_SEQ
    h._ENERGY_SEQ = energy_seq
    try:
        attach_target = h._choose_attach(attach, me) if attach else None
        chosen = h.choose(obs)
    finally:
        h._ENERGY_SEQ = saved
    chosen_opt = chosen[0] if isinstance(chosen, list) and chosen else None
    attach_idxs = {i for i, _ in attach}
    return attach_target, chosen_opt, chosen_opt in attach_idxs


def measure(deck_path, limit=8):
    deck_ids = read_deck(deck_path)
    ensure_official_cg()
    positions = capture_attach_obs(deck_ids, limit=limit)
    rows = []
    for obs in positions:
        turn = (obs.get("current") or {}).get("turn")
        n_attach = len(h.options_by_type(obs["select"].get("option", [])).get(h.OPT_ATTACH, []))
        at_off, ch_off, attached_off = _decide(obs, False)
        at_on, ch_on, attached_on = _decide(obs, True)
        rows.append({
            "turn": turn,
            "attach_opts": n_attach,
            "attach_off": at_off,
            "attach_on": at_on,
            "attach_flip": at_off != at_on,
            "pilot_attaches": attached_off,
            "choose_off": ch_off,
            "choose_on": ch_on,
            "choose_flip": ch_off != ch_on,
        })
    return {"deck": Path(deck_path).stem, "rows": rows}


def _format(result):
    lines = [
        f"energy-seq decision effect on {result['deck']} "
        f"(heuristic pilot, real captured ATTACH positions):",
        "  turn  attach_opts  attach_off  attach_on  attach_flip  pilot_attaches  choose_flip",
    ]
    for r in result["rows"]:
        lines.append(
            f"  {str(r['turn']):>4s}  {r['attach_opts']:>11d}  "
            f"{str(r['attach_off']):>10s}  {str(r['attach_on']):>9s}  "
            f"{str(r['attach_flip']):>11s}  {str(r['pilot_attaches']):>14s}  "
            f"{str(r['choose_flip']):>11s}"
        )
    n = len(result["rows"])
    if n:
        attach_flips = sum(1 for r in result["rows"] if r["attach_flip"])
        choose_flips = sum(1 for r in result["rows"] if r["choose_flip"])
        attaches = sum(1 for r in result["rows"] if r["pilot_attaches"])
        lines.append(f"  positions captured (attach available): {n}")
        lines.append(f"  positions where the pilot actually attaches: {attaches}/{n}")
        lines.append(f"  energy-seq flipped the attach target on {attach_flips}/{n} positions")
        lines.append(f"  energy-seq flipped the pilot decision on {choose_flips}/{n} positions")
        if choose_flips == 0 and attach_flips == 0:
            lines.append(
                "  => PTCG_ENERGY_SEQ changes no decision on these trolley positions; it is "
                "inert in practice here, do NOT spend a slot on it."
            )
        else:
            lines.append(
                "  => PTCG_ENERGY_SEQ is live on trolley (changes real attach decisions); the "
                "ladder must judge whether the change helps."
            )
    else:
        lines.append("  no ATTACH positions captured; increase -n or the match length")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck", nargs="?", default=str(_ROOT / "decks" / "trolley.csv"),
                    help="deck csv path (default: decks/trolley.csv, the shipped batch deck)")
    ap.add_argument("-n", "--positions", type=int, default=8,
                    help="max mid-game MAIN attach positions to capture and measure")
    args = ap.parse_args()
    print(_format(measure(args.deck, limit=args.positions)))


if __name__ == "__main__":
    main()
