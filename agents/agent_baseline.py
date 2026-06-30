"""Baseline agent for the Pokemon TCG AI Battle Challenge (cabt).

Self contained on purpose: it ships unchanged as the submission main.py, and is
also importable as a local agent. It returns the deck at selection, otherwise a
random legal set of option indices, and never raises (an error forfeits the
match).
"""
import os
import random
from pathlib import Path


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
    sel = obs["select"]
    if sel is None:
        return _DECK
    try:
        return random.sample(range(len(sel["option"])), sel["maxCount"])
    except Exception:
        # Minimal legal fallback so the agent never forfeits by raising.
        low = sel.get("minCount", 1) if hasattr(sel, "get") else 1
        return list(range(min(max(low, 1), len(sel["option"]))))
