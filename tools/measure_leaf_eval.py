"""Measure how often the leaf evaluation (board_value) actually fires per decision.

The last three agent-strength commits all live in search/eval.board_value: the
attached-energy term (a325b32), the active-weighted health term (94b0fc2), and the
convex empty-bench floor (cf462e0, gated by PTCG_BENCH_FLOOR). The standing batch
plan lists "flip PTCG_BENCH_FLOOR=1" as a SEPARATE single-variable A/B against the
trolley floor. But board_value is only ever consulted at a rollout LEAF: rollout()
returns it when value_depth is set and the cutoff is reached (rollout.py:294), or as
the fallback when a rollout runs the full ROLLOUT_MAX_STEPS without terminating
(rollout.py:303). The shipped default is value_depth=None (PTCG_ROLLOUT_DEPTH=0), so
every rollout runs to a TERMINAL result and board_value is consulted only in the rare
400-step-cap tail. If that tail is ~never hit on trolley, then PTCG_BENCH_FLOOR (and
the energy and active-health terms) are inert on the shipped stack, and flipping the
bench floor ALONE would spend a scarce daily ladder slot on a change that cannot fire.

This tool answers that empirically, mirroring measure_worlds.py: it captures real
mid-game MAIN observations from a trolley-piloted match, then drives the exact shipped
rollout.search_decision at the default value_depth=None and at a positive value_depth,
counting how many times board_value is consulted per decision at each. A counting
wrapper around search.eval.board_value reads the count with zero change to shipped
code. Read the CONTRAST: if the default samples ~0 leaf evaluations per decision and
the positive depth samples many, the three leaf-eval terms are confirmed inert unless
PTCG_ROLLOUT_DEPTH is also set, so the eval-term flags must be A/B'd TOGETHER with the
rollout cutoff, not as standalone single-variable flips.

Dev/measurement tool only; never shipped. The native engine is a per-process
singleton, so it runs one match in process.
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
from ptcg_agent.engine import ensure_official_cg, make_env  # noqa: E402
from search import eval as ev  # noqa: E402
from search import rollout  # noqa: E402
from tools import opponents  # noqa: E402
from tools.deck_match import deck_bound  # noqa: E402
from tools.deck_validate import read_deck  # noqa: E402

_SEED = 20260630


def capture_main_obs(deck_ids, policy="heuristic", limit=6, min_turn=3):
    """Play one match piloting deck_ids and collect real mid-game MAIN observations.

    Mirrors the shipped agent's searchable gate: a MAIN selection, more than one
    option, a search_begin_input present, past the opening. deck_bound makes the
    heuristic pilot the exact deck the batch ships, so the captured positions (and
    thus the rollout depths we measure) match the batch.
    """
    policy_fn = opponents.get(policy)
    piloted = deck_bound(policy_fn, deck_ids)
    captured: list = []

    def capturing(obs):
        sel = obs.get("select")
        if (
            len(captured) < limit
            and sel is not None
            and sel.get("type") == 0  # SelectType.MAIN
            and sel.get("maxCount", 1) == 1
            and len(sel.get("option", [])) > 1
            and obs.get("search_begin_input")
            and (obs.get("current") or {}).get("turn", 0) >= min_turn
        ):
            captured.append(obs)
        return piloted(obs)

    make_env().run([capturing, "random"])
    return captured


def count_leaf_evals(obs, deck_ids, value_depth, budget_seconds=2.0, robust_coef=0.25):
    """Run one search_decision at a value_depth; return board_value consultations.

    A counting wrapper around search.eval.board_value reads how often the leaf
    estimate is consulted with zero change to shipped code. opponent_prior and the
    budget/robust_coef are computed exactly as the agent does, so the rollout path we
    drive is the shipped path; only value_depth is varied.
    """
    calls = [0]
    real_board_value = ev.board_value

    def counting(state, your_index):
        calls[0] += 1
        return real_board_value(state, your_index)

    try:
        prior = archetype.opponent_prior(obs, deck_ids)
    except Exception:
        prior = None
    rng = random.Random(_SEED)
    ev.board_value = counting
    try:
        rollout.search_decision(
            obs, deck_ids, budget_seconds, rng, rollout_determinize(),
            opponent_prior=prior, value_depth=value_depth, robust_coef=robust_coef,
        )
    finally:
        ev.board_value = real_board_value
    return calls[0]


def rollout_determinize():
    """The shipped determinize, imported lazily so the module import stays cheap."""
    from search.determinize import determinize
    return determinize


def measure(deck_path, depths=(None, 8), limit=6):
    deck_ids = read_deck(deck_path)
    ensure_official_cg()
    if not rollout.search_api_available():
        raise SystemExit("no cg.api forward model reachable; cannot measure leaf evals")
    positions = capture_main_obs(deck_ids, limit=limit)
    rows = []
    for obs in positions:
        turn = (obs.get("current") or {}).get("turn")
        n_opt = len(obs["select"].get("option", []))
        evals = {d: count_leaf_evals(obs, deck_ids, d) for d in depths}
        rows.append({"turn": turn, "options": n_opt, "evals": evals})
    return {"deck": Path(deck_path).stem, "depths": list(depths), "rows": rows}


def _median(values):
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def _label(depth):
    return "terminal" if depth is None else f"depth {depth}"


def _format(result):
    depths = result["depths"]
    lines = [
        f"board_value consultations per MAIN decision on {result['deck']} "
        f"(shipped forward model, robust_coef 0.25):",
        "  turn  options  " + "  ".join(f"{_label(d):>9s}" for d in depths),
    ]
    for r in result["rows"]:
        cells = "  ".join(f"{r['evals'][d]:>9d}" for d in depths)
        lines.append(f"  {str(r['turn']):>4s}  {r['options']:>7d}  {cells}")
    if result["rows"]:
        lines.append("  median consultations/decision:")
        for d in depths:
            med = _median([r["evals"][d] for r in result["rows"]])
            lines.append(f"    {_label(d)} -> {med}")
        med_default = _median([r["evals"][depths[0]] for r in result["rows"]])
        inert = med_default == 0
        lines.append(
            f"  leaf eval inert on the shipped stack (terminal rollouts never "
            f"consult board_value): {inert}"
        )
        lines.append(
            "  => PTCG_BENCH_FLOOR / energy / active-health terms need "
            "PTCG_ROLLOUT_DEPTH>0 to fire; do NOT A/B the bench floor alone."
        )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck", nargs="?", default=str(_ROOT / "decks" / "trolley.csv"),
                    help="deck csv path (default: decks/trolley.csv, the shipped batch deck)")
    ap.add_argument("-n", "--positions", type=int, default=6,
                    help="max mid-game MAIN positions to capture and measure")
    args = ap.parse_args()
    print(_format(measure(args.deck, limit=args.positions)))


if __name__ == "__main__":
    main()
