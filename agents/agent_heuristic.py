"""Rules aware heuristic agent for the Pokemon TCG AI Battle Challenge (cabt).

Phase 2 agent. Returns the deck at selection, otherwise delegates the live
decision to heuristics.choose: take a knockout when available, evolve and develop
and attach energy, retreat an endangered active, otherwise attack with the best
option. Never raises (an exception forfeits the match).

Self contained for submission: the entrypoint is the module level agent(obs).
heuristics.py is imported either as agents.heuristics (local) or as a top level
heuristics module (inside a built submission), so both layouts work unchanged.
"""
import os
from pathlib import Path

try:
    from agents import heuristics
except ImportError:  # inside a submission, main.py and heuristics.py sit together
    import heuristics


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


def agent(obs):
    sel = obs.get("select")
    if sel is None:
        return _DECK
    try:
        move = heuristics.choose(obs)
        if _is_legal(move, sel):
            return move
    except Exception:
        pass
    # Guaranteed legal fallback so the agent never forfeits by raising.
    try:
        return heuristics._first_legal(sel)
    except Exception:
        return [0]


def _is_legal(move, sel) -> bool:
    n = len(sel.get("option", []))
    if not isinstance(move, list) or len(set(move)) != len(move):
        return False
    if not (sel.get("minCount", 1) <= len(move) <= sel.get("maxCount", 1)):
        return False
    return all(isinstance(i, int) and 0 <= i < n for i in move)
