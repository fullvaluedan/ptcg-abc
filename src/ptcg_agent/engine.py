"""Thin wrapper over the local cabt engine.

Runs matches via kaggle_environments and makes the official cg/ SDK importable
for the typed Observation classes and (later) the forward model. No agent logic
lives here. Decks are supplied by each agent at the deck selection step, so the
harness does not pass decks to the environment.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# The official cg/ package (cg.api, the forward model, card data) ships in the
# gitignored competition data. Look for it there or in an optional vendor dir.
_CG_SEARCH = [REPO_ROOT / "vendor", REPO_ROOT / "data"]


def ensure_official_cg() -> Path:
    """Put the official cg/ package on sys.path so `import cg.api` works locally.

    Returns the parent directory added to sys.path. Raises a clear error if the
    package is missing, since it is competition data that must be downloaded.
    """
    for parent in _CG_SEARCH:
        if (parent / "cg" / "api.py").exists():
            p = str(parent)
            if p not in sys.path:
                sys.path.insert(0, p)
            return parent
    searched = " or ".join(str(p / "cg") for p in _CG_SEARCH)
    raise FileNotFoundError(
        "Official cg/ package not found under "
        + searched
        + ". Download it with the Kaggle CLI into data/cg/ (competition data, gitignored)."
    )


def make_env(debug: bool = False):
    """Create a cabt environment. Agents supply their own decks at selection."""
    from kaggle_environments import make

    return make("cabt", debug=debug)


def run_match(agent_a, agent_b, swap_first: bool = False) -> dict:
    """Run one match and return a result dict keyed to the original (a, b) order.

    agent_a and agent_b are callables taking the observation dict and returning
    list[int], or string names of registered cabt agents. With swap_first=True,
    agent_b takes the first seat but rewards are still reported as a and b.
    """
    order = [agent_b, agent_a] if swap_first else [agent_a, agent_b]
    env = make_env()
    env.run(order)
    last = env.steps[-1]
    r0, r1 = last[0]["reward"], last[1]["reward"]
    reward_a, reward_b = (r1, r0) if swap_first else (r0, r1)
    return {
        "reward_a": reward_a,
        "reward_b": reward_b,
        "winner": _winner(reward_a, reward_b),
        "steps": len(env.steps),
        "a_seat": 1 if swap_first else 0,
    }


def _winner(reward_a, reward_b) -> str:
    if reward_a > reward_b:
        return "a"
    if reward_b > reward_a:
        return "b"
    return "draw"
