"""Dict first helpers over the cabt observation.

Reading the raw dict avoids dataclass conversion overhead in hot decision loops.
Use typed() only when the official dataclasses are genuinely more convenient.
"""
from __future__ import annotations


def is_deck_selection(obs) -> bool:
    """True when the engine is asking for the 60 card deck (select is None)."""
    return obs.get("select") is None


def select(obs):
    return obs.get("select")


def options(obs) -> list:
    sel = obs.get("select")
    return sel["option"] if sel else []


def min_count(obs) -> int:
    sel = obs.get("select")
    return sel["minCount"] if sel else 0


def max_count(obs) -> int:
    sel = obs.get("select")
    return sel["maxCount"] if sel else 0


def state(obs):
    return obs.get("current")


def your_index(obs):
    s = obs.get("current")
    return s["yourIndex"] if s else None


def result(obs) -> int:
    """Match result: -1 ongoing, 0 player0 wins, 1 player1 wins, 2 draw."""
    s = obs.get("current")
    return s["result"] if s else -1


def typed(obs):
    """Convert the observation dict to the official Observation dataclass."""
    from ptcg_agent.engine import ensure_official_cg

    ensure_official_cg()
    from cg.api import to_observation_class

    return to_observation_class(obs)
