"""Run a single local cabt match between two agents and print the result.

Usage:
    python tools/local_match.py [agent_a] [agent_b]

Each agent is a built in reference name: random or first. Defaults to
random vs first.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ptcg_agent.engine import run_match  # noqa: E402


def resolve(name):
    from kaggle_environments.envs.cabt.cabt import random_agent, first_agent

    return {"random": random_agent, "first": first_agent}[name]


def main(argv):
    a = argv[1] if len(argv) > 1 else "random"
    b = argv[2] if len(argv) > 2 else "first"
    res = run_match(resolve(a), resolve(b))
    print(
        f"{a} (a) vs {b} (b): winner={res['winner']} "
        f"reward_a={res['reward_a']} reward_b={res['reward_b']} steps={res['steps']}"
    )


if __name__ == "__main__":
    main(sys.argv)
