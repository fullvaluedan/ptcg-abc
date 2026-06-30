"""Head to head deck matrix for the two deck portfolio (U11).

The agents bind their own deck at the deck selection step, so to measure decks
rather than policies we wrap a policy agent so it returns a chosen deck at
selection and otherwise plays normally. The same policy then pilots every deck,
and the matrix isolates the deck matchup: which deck beats which, and which is
the stronger overall pick to submit.

The native engine is a per process singleton, so matches run sequentially in
process (one fresh env per match via run_match). Dev tool only; never shipped.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ptcg_agent.engine import run_match  # noqa: E402
from tools import opponents  # noqa: E402
from tools.deck_validate import read_deck  # noqa: E402
from tools.gauntlet import _wilson  # noqa: E402


def deck_bound(policy_fn, deck_ids):
    """Wrap a policy agent so it pilots a fixed deck.

    At the deck selection step (select is None) it returns deck_ids; on every
    live decision it defers to the policy agent unchanged. The policy is the same
    object for both seats, so the only thing that varies in a matchup is the deck.
    """
    deck = list(deck_ids)

    def agent(obs):
        if obs.get("select") is None:
            return deck
        return policy_fn(obs)

    return agent


def head_to_head(deck_a, deck_b, policy="heuristic", n_matches=20) -> dict:
    """Play deck_a vs deck_b under one policy, alternating first player."""
    policy_fn = opponents.get(policy)
    a = deck_bound(policy_fn, deck_a)
    b = deck_bound(policy_fn, deck_b)
    wins = draws = losses = 0
    for i in range(n_matches):
        res = run_match(a, b, swap_first=(i % 2 == 1))
        r = res["reward_a"]
        if r == 1:
            wins += 1
        elif r == 0:
            draws += 1
        else:
            losses += 1
    lo, hi = _wilson(wins, n_matches)
    return {
        "matches": n_matches,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": wins / n_matches if n_matches else 0.0,
        "win_rate_ci95": (round(lo, 3), round(hi, 3)),
    }


def matrix(deck_paths, policy="heuristic", n_matches=20) -> dict:
    """Round robin matrix over deck files; each cell is the row deck's win rate.

    Returns the per pairing results plus an overall win rate per deck (its mean
    win rate across opponents), which selects the stronger deck to submit.
    """
    decks = {Path(p).stem: read_deck(p) for p in deck_paths}
    names = list(decks)
    cells = {}
    for a in names:
        for b in names:
            if a == b:
                continue
            cells[(a, b)] = head_to_head(decks[a], decks[b], policy, n_matches)
    overall = {}
    for a in names:
        rates = [cells[(a, b)]["win_rate"] for b in names if b != a]
        overall[a] = sum(rates) / len(rates) if rates else 0.0
    best = max(overall, key=overall.get) if overall else None
    return {"policy": policy, "decks": names, "cells": cells, "overall": overall, "best": best}


def _format(result: dict) -> str:
    lines = [f"deck matrix (policy={result['policy']}):"]
    for (a, b), s in result["cells"].items():
        ci = s["win_rate_ci95"]
        lines.append(
            f"  {a} vs {b}: {s['win_rate']:.1%} "
            f"(W/D/L {s['wins']}/{s['draws']}/{s['losses']}, "
            f"95% CI {ci[0]:.1%} to {ci[1]:.1%})"
        )
    lines.append("  overall win rate:")
    for name, rate in sorted(result["overall"].items(), key=lambda kv: -kv[1]):
        lines.append(f"    {name}: {rate:.1%}")
    lines.append(f"  stronger pick: {result['best']}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("decks", nargs="+", help="deck csv paths")
    ap.add_argument("-p", "--policy", default="heuristic")
    ap.add_argument("-n", "--matches", type=int, default=20)
    args = ap.parse_args()
    print(_format(matrix(args.decks, args.policy, args.matches)))


if __name__ == "__main__":
    main()
