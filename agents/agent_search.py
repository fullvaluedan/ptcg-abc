"""Determinized search agent for the Pokemon TCG AI Battle Challenge (cabt).

Phase 3 agent (U5). At a MAIN decision it samples plausible hidden state, runs
determinized rollouts of each candidate first move through the engine's native
search_* forward model, and plays the highest expected value move within the time
bank. Every other decision (yes/no, counts, energy, discards) and every failure
path falls back to the heuristic, then to a guaranteed legal selection, so the
agent never forfeits by raising.

Self contained for submission: the entrypoint is the module level agent(obs).
determinize, rollout, eval, timebudget, and heuristics import either from their
package (local) or as top level modules (inside a built submission).
"""
import os
import random
import time
from pathlib import Path

try:
    from agents import heuristics
except ImportError:  # inside a submission, support modules sit at the top level
    import heuristics

try:
    from search import rollout
    from search.determinize import determinize
    from search.timebudget import TimeBudget
except ImportError:
    import rollout
    from determinize import determinize
    from timebudget import TimeBudget


def _read_deck():
    candidates = [
        "deck.csv",
        "/kaggle_simulations/agent/deck.csv",
        str(Path(__file__).resolve().parents[1] / "decks" / "baseline.csv"),
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path) as f:
                ids = [int(line) for line in f.read().split("\n") if line.strip()]
            if len(ids) >= 60:
                return ids[:60]
    raise FileNotFoundError("deck.csv not found in: " + ", ".join(candidates))


_DECK = _read_deck()
# Fixed seed keeps a match reproducible under a fixed environment seed (the gate
# wants stable argmax selection); the soft per-move cap is overridable so the
# gauntlet can trade depth for throughput without touching code.
_SEARCH_SEED = 20260630
_RNG = random.Random(_SEARCH_SEED)
_SOFT_CAP = float(os.environ.get("PTCG_SEARCH_BUDGET", "0.5"))
# An optional hard cap on determinizations per decision; the gauntlet sets it to
# trade depth for throughput. 0 means time-bounded only.
_MAX_DETS = int(os.environ.get("PTCG_SEARCH_DETS", "0")) or None
_BUDGET = TimeBudget(soft_cap=_SOFT_CAP)


def _is_legal(move, sel) -> bool:
    n = len(sel.get("option", []))
    if not isinstance(move, list) or len(set(move)) != len(move):
        return False
    if not (sel.get("minCount", 1) <= len(move) <= sel.get("maxCount", 1)):
        return False
    return all(isinstance(i, int) and 0 <= i < n for i in move)


def _searchable(sel) -> bool:
    """A MAIN decision with more than one single-index choice is worth searching."""
    return (
        sel.get("type") == heuristics.SEL_MAIN
        and sel.get("maxCount", 1) == 1
        and sel.get("minCount", 1) <= 1
        and len(sel.get("option", [])) > 1
    )


def agent(obs):
    sel = obs.get("select")
    if sel is None:
        # Deck selection opens every match, so reset the per-match thinking bank
        # and the sampler seed, which keeps each match reproducible even when a
        # gauntlet runs many matches in one process.
        _BUDGET.spent = 0.0
        _RNG.seed(_SEARCH_SEED)
        return _DECK
    try:
        if _searchable(sel) and obs.get("search_begin_input"):
            budget = _BUDGET.allot()
            if budget > 0:
                start = time.perf_counter()
                move = rollout.search_decision(
                    obs, _DECK, budget, _RNG, determinize,
                    max_determinizations=_MAX_DETS,
                )
                _BUDGET.record(time.perf_counter() - start)
                if move is not None and _is_legal(move, sel):
                    return move
    except Exception:
        pass
    # Fallback: the heuristic, then any guaranteed legal selection.
    try:
        move = heuristics.choose(obs)
        if _is_legal(move, sel):
            return move
    except Exception:
        pass
    try:
        return heuristics._first_legal(sel)
    except Exception:
        return [0]
