"""Measure whether PTCG_BENCH_FLOOR actually CHANGES a decision at value_depth>0.

measure_leaf_eval.py proved the three leaf-eval terms (attached-energy a325b32,
active-weighted health 94b0fc2, convex empty-bench floor cf462e0) are inert on the
shipped/default stack: at value_depth=None every rollout runs to a TERMINAL result and
board_value is consulted ~0 times per decision, so the eval-term flags can only fire
once PTCG_ROLLOUT_DEPTH>0 cuts rollouts off at the leaf. That measurement showed the
bench-floor term FIRES at a positive depth (320-354 board_value consultations/decision
at depth 8), but firing is not the same as mattering. The standing batch plan's SECOND
submission is "flip PTCG_ROLLOUT_DEPTH positive TOGETHER WITH PTCG_BENCH_FLOOR". Two
unanswered, slot-gating questions remain for THAT submission:

  1. Efficacy: at a positive value_depth, does turning PTCG_BENCH_FLOOR on actually flip
     the CHOSEN decision on any real position? A term that is consulted 349 times per
     decision but never changes the argmax is still a wasted daily ladder slot (the same
     "fires != matters" trap the soft-cap keystone was measured against in
     measure_worlds.py). This tool holds the determinizations fixed (a fixed
     max_determinizations + a fresh Random(_SEED) per run) so the ONLY difference between
     the off and on runs is the bench-floor term, and reports how many captured
     decisions it flips.

  2. Fidelity: a shallow (depth-cut) rollout trades terminal accuracy for more worlds
     per decision, but if the depth-D argmax disagrees with the terminal argmax on most
     positions, flipping PTCG_ROLLOUT_DEPTH positive is a blind regression regardless of
     the bench floor. This tool also reports how often the depth-D decision agrees with
     the terminal (value_depth=None) decision on the same fixed worlds.

Read the CONTRAST. If bench-floor flips ~0 decisions even where it fires, do NOT spend a
slot on it; if depth-D tracks terminal poorly, be cautious flipping the rollout cutoff.
Neither result claims a win rate (offline weak-bot play is not ladder-predictive per
meta.md); the measurement can only REFUTE a lever as inert, exactly as measure_leaf_eval
and measure_worlds did. Dev/measurement tool only; never shipped, touches no shipped
code path (the bench-floor flag is toggled on the imported module attribute and restored
in a finally), so the frozen batch stays byte-identical and the pending A/B is unpolluted.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis import archetype  # noqa: E402
from ptcg_agent.engine import ensure_official_cg  # noqa: E402
from search import eval as ev  # noqa: E402
from search import rollout  # noqa: E402
from tools.deck_validate import read_deck  # noqa: E402
from tools.measure_leaf_eval import capture_main_obs, rollout_determinize  # noqa: E402

_SEED = 20260630
# A fixed determinization count makes the off/on runs sample the identical worlds, so a
# difference in the chosen argmax is attributable to the bench-floor term alone. 12 is
# the median worlds/decision measure_worlds.py observed at the shipped 2.0s cap.
_DETS = 12


def _decide(obs, deck_ids, value_depth, bench_floor, prior,
            budget_seconds=60.0, robust_coef=0.25):
    """Return the chosen option index for one decision under a fixed world sample.

    A large budget with a fixed max_determinizations makes the determinization count
    (not the wall clock) the binding limit, so a fresh Random(_SEED) replays the exact
    same worlds for every call and only value_depth / bench_floor vary. ev._BENCH_FLOOR
    is toggled on the imported module attribute (read once at import in eval.py) and
    restored in a finally, so no shipped code path is mutated.
    """
    rng = random.Random(_SEED)
    saved = ev._BENCH_FLOOR
    ev._BENCH_FLOOR = bench_floor
    try:
        best = rollout.search_decision(
            obs, deck_ids, budget_seconds, rng, rollout_determinize(),
            opponent_prior=prior, max_determinizations=_DETS,
            value_depth=value_depth, robust_coef=robust_coef,
        )
    finally:
        ev._BENCH_FLOOR = saved
    return None if best is None else best[0]


def measure(deck_path, value_depth=8, limit=6):
    deck_ids = read_deck(deck_path)
    ensure_official_cg()
    if not rollout.search_api_available():
        raise SystemExit("no cg.api forward model reachable; cannot measure bench floor")
    positions = capture_main_obs(deck_ids, limit=limit)
    rows = []
    for obs in positions:
        turn = (obs.get("current") or {}).get("turn")
        n_opt = len(obs["select"].get("option", []))
        try:
            prior = archetype.opponent_prior(obs, deck_ids)
        except Exception:
            prior = None
        terminal = _decide(obs, deck_ids, None, False, prior)
        depth_off = _decide(obs, deck_ids, value_depth, False, prior)
        depth_on = _decide(obs, deck_ids, value_depth, True, prior)
        rows.append({
            "turn": turn,
            "options": n_opt,
            "terminal": terminal,
            "depth_off": depth_off,
            "depth_on": depth_on,
            "bench_flip": depth_off != depth_on,
            "tracks_terminal": depth_off == terminal,
        })
    return {"deck": Path(deck_path).stem, "value_depth": value_depth, "rows": rows}


def _format(result):
    d = result["value_depth"]
    lines = [
        f"bench-floor decision effect on {result['deck']} at value_depth {d} "
        f"(shipped forward model, {_DETS} fixed worlds, robust_coef 0.25):",
        "  turn  options  terminal  depth_off  depth_on  bench_flip  tracks_terminal",
    ]
    for r in result["rows"]:
        lines.append(
            f"  {str(r['turn']):>4s}  {r['options']:>7d}  {str(r['terminal']):>8s}  "
            f"{str(r['depth_off']):>9s}  {str(r['depth_on']):>8s}  "
            f"{str(r['bench_flip']):>10s}  {str(r['tracks_terminal']):>15s}"
        )
    n = len(result["rows"])
    if n:
        flips = sum(1 for r in result["rows"] if r["bench_flip"])
        tracks = sum(1 for r in result["rows"] if r["tracks_terminal"])
        lines.append(f"  bench-floor flipped the decision on {flips}/{n} positions")
        lines.append(f"  depth-{d} tracked the terminal decision on {tracks}/{n} positions")
        if flips == 0:
            lines.append(
                "  => PTCG_BENCH_FLOOR changes no decision here even at depth>0; it is "
                "inert in practice, do NOT spend a slot on the bench floor."
            )
        else:
            lines.append(
                "  => PTCG_BENCH_FLOOR is live at depth>0 (changes real decisions); the "
                "ladder must judge whether the change helps."
            )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck", nargs="?", default=str(_ROOT / "decks" / "trolley.csv"),
                    help="deck csv path (default: decks/trolley.csv, the shipped batch deck)")
    ap.add_argument("-d", "--depth", type=int, default=8,
                    help="positive value_depth (rollout cutoff) to measure at")
    ap.add_argument("-n", "--positions", type=int, default=6,
                    help="max mid-game MAIN positions to capture and measure")
    args = ap.parse_args()
    print(_format(measure(args.deck, value_depth=args.depth, limit=args.positions)))


if __name__ == "__main__":
    main()
