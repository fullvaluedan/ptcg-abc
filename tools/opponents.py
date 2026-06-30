"""Opponent registry for the gauntlet.

Resolves opponent names to agent callables. Sets up sys.path so the local agents
import without installation. Frozen snapshots of past versions get added here as
the project grows.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def names() -> list:
    return ["random", "first", "baseline", "heuristic"]


def get(name):
    """Return the agent callable for a registered opponent name."""
    if name in ("random", "first"):
        from kaggle_environments.envs.cabt.cabt import random_agent, first_agent

        return {"random": random_agent, "first": first_agent}[name]
    if name == "baseline":
        from agents.agent_baseline import agent

        return agent
    if name == "heuristic":
        from agents.agent_heuristic import agent

        return agent
    raise KeyError(f"Unknown agent '{name}'. Known: {names()}")
