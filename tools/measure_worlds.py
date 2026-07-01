"""Measure how many hidden worlds the search agent samples per MAIN decision.

The pending search_trolley batch stacks changes that ALL need more than one
determinized world per decision to do anything: the robust argmax (e44e170) needs
world-to-world spread to penalize, and the field prior (c694484 + 3ba6bf2) needs
several draws to average toward the modeled opponent. The keystone that is supposed
to feed them is the soft-cap raise 0.5 -> 2.0 (4ab2750). But that only delivers
multiple worlds if a full candidate sweep (a determinized rollout to a terminal
result for EVERY candidate first move) finishes well under the 2.0s cap. If a sweep
is slower than the budget, an ordinary decision still samples exactly ONE world and
the whole stacked batch is effectively inert, and the hard-won 00:00 ladder slot
would be spent on a batch that cannot fire.

The grader-lock test proves the build loads and finishes a match; it does NOT prove
the keystone fires. This tool answers that empirically: it captures real mid-game
MAIN observations from a trolley-piloted match, then drives rollout.search_decision
(the exact shipped decision path, real native forward model, shipped robust_coef)
at the OLD 0.5s cap and the NEW 2.0s cap, counting how many worlds each decision
samples. determinize is passed INTO search_decision, so a counting wrapper reads the
world count exactly with zero change to the shipped code.

Dev/measurement tool only; never shipped. The native engine is a per-process
singleton, so it runs one match in process. Read the RELATIVE lift (2.0s worlds vs
0.5s worlds): the keystone fires when the raised cap samples strictly more worlds on
an ordinary decision, and it is fully effective when 2.0s reaches >= 2 worlds so the
variance penalty and field-prior average have something to work with.
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
from search import rollout  # noqa: E402
from search.determinize import determinize  # noqa: E402
from tools import opponents  # noqa: E402
from tools.deck_match import deck_bound  # noqa: E402
from tools.deck_validate import read_deck  # noqa: E402

_SEED = 20260630


def capture_main_obs(deck_ids, policy="heuristic", limit=6, min_turn=3):
    """Play one match piloting deck_ids and collect real mid-game MAIN observations.

    Mirrors the shipped agent's searchable gate: a MAIN selection, more than one
    option, a search_begin_input present, past the opening. deck_bound makes the
    heuristic pilot the exact deck the batch ships, so the captured positions (and
    thus the sweep cost we measure) match the batch.
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


def count_worlds(obs, deck_ids, budget_seconds, robust_coef=0.25):
    """Run one search_decision at a time budget; return the worlds it sampled.

    A counting wrapper around determinize (which search_decision calls once per
    world) reads the count with zero change to shipped code. opponent_prior is
    computed exactly as the agent does, so the per-world determinization cost we
    time is the shipped cost.
    """
    calls = [0]

    def counting(o, d, rng, prior=None):
        calls[0] += 1
        return determinize(o, d, rng, prior)

    try:
        prior = archetype.opponent_prior(obs, deck_ids)
    except Exception:
        prior = None
    rng = random.Random(_SEED)
    rollout.search_decision(
        obs, deck_ids, budget_seconds, rng, counting, opponent_prior=prior,
        value_depth=None, robust_coef=robust_coef,
    )
    return calls[0]


def measure(deck_path, caps=(0.5, 2.0), limit=6):
    deck_ids = read_deck(deck_path)
    ensure_official_cg()
    if not rollout.search_api_available():
        raise SystemExit("no cg.api forward model reachable; cannot measure worlds")
    positions = capture_main_obs(deck_ids, limit=limit)
    rows = []
    for obs in positions:
        turn = (obs.get("current") or {}).get("turn")
        n_opt = len(obs["select"].get("option", []))
        worlds = {cap: count_worlds(obs, deck_ids, cap) for cap in caps}
        rows.append({"turn": turn, "options": n_opt, "worlds": worlds})
    return {"deck": Path(deck_path).stem, "caps": list(caps), "rows": rows}


def _median(values):
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def _format(result):
    caps = result["caps"]
    lines = [
        f"worlds sampled per MAIN decision on {result['deck']} "
        f"(shipped robust_coef, real forward model):",
        "  turn  options  " + "  ".join(f"{c}s" for c in caps),
    ]
    for r in result["rows"]:
        cells = "  ".join(f"{r['worlds'][c]:>3d}" for c in caps)
        lines.append(f"  {str(r['turn']):>4s}  {r['options']:>7d}  {cells}")
    if result["rows"]:
        lines.append("  median  worlds/decision:")
        for c in caps:
            med = _median([r["worlds"][c] for r in result["rows"]])
            lines.append(f"    {c}s cap -> {med}")
        med_old = _median([r["worlds"][caps[0]] for r in result["rows"]])
        med_new = _median([r["worlds"][caps[-1]] for r in result["rows"]])
        fires = med_new > med_old
        effective = med_new >= 2
        lines.append(
            f"  keystone fires (2.0s samples more worlds than 0.5s): {fires}; "
            f"effective (2.0s reaches >= 2 worlds): {effective}"
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
