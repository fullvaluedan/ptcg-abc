"""Gauntlet eval harness: score an agent against a pool of opponents.

Runs matches sequentially. The native engine is a per process singleton, so
concurrent matches in one process are unsafe; parallel workers each running a
sequential batch are a future optimization for large run sizes. Reports win rate
with a Wilson confidence interval, average and max decision time, and invalid
move rate (our agent should never produce an illegal move).
"""
import argparse
import math
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ptcg_agent.engine import run_match  # noqa: E402
from tools import opponents  # noqa: E402


def _is_legal(move, obs) -> bool:
    sel = obs["select"]
    if sel is None:
        return isinstance(move, list) and len(move) == 60
    n = len(sel["option"])
    if not isinstance(move, list) or len(set(move)) != len(move):
        return False
    if not (sel["minCount"] <= len(move) <= sel["maxCount"]):
        return False
    return all(0 <= i < n for i in move)


def _instrument(fn, record):
    def wrapped(obs):
        t0 = time.perf_counter()
        move = fn(obs)
        record["times"].append(time.perf_counter() - t0)
        if not _is_legal(move, obs):
            record["invalid"] += 1
        return move

    return wrapped


def _wilson(wins, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def run_gauntlet(agent_name, opponent_names, n_matches):
    """Play n_matches split across the opponents, alternating first player."""
    agent_fn = opponents.get(agent_name)
    rewards, times, invalid = [], [], 0
    for i in range(n_matches):
        opp_fn = opponents.get(opponent_names[i % len(opponent_names)])
        rec = {"times": [], "invalid": 0}
        wrapped = _instrument(agent_fn, rec)
        res = run_match(wrapped, opp_fn, swap_first=(i % 2 == 1))
        rewards.append(res["reward_a"])
        times.extend(rec["times"])
        invalid += rec["invalid"]
    n = len(rewards)
    wins = sum(1 for r in rewards if r == 1)
    draws = sum(1 for r in rewards if r == 0)
    losses = sum(1 for r in rewards if r == -1)
    lo, hi = _wilson(wins, n)
    return {
        "agent": agent_name,
        "opponents": opponent_names,
        "matches": n,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": wins / n if n else 0.0,
        "win_rate_ci95": (round(lo, 3), round(hi, 3)),
        "avg_decision_ms": round(1000 * sum(times) / len(times), 3) if times else 0.0,
        "max_decision_ms": round(1000 * max(times), 3) if times else 0.0,
        "decisions": len(times),
        "invalid_moves": invalid,
        "invalid_rate": round(invalid / len(times), 6) if times else 0.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent", help="agent under test (e.g. baseline)")
    ap.add_argument("opponents", nargs="+", help="opponent names (e.g. random first)")
    ap.add_argument("-n", "--matches", type=int, default=100)
    args = ap.parse_args()
    s = run_gauntlet(args.agent, args.opponents, args.matches)
    ci = s["win_rate_ci95"]
    print(f"{s['agent']} vs {s['opponents']} over {s['matches']} matches")
    print(f"  win rate: {s['win_rate']:.1%}  (95% CI {ci[0]:.1%} to {ci[1]:.1%})")
    print(f"  W/D/L: {s['wins']}/{s['draws']}/{s['losses']}")
    print(f"  decision time: avg {s['avg_decision_ms']} ms, max {s['max_decision_ms']} ms over {s['decisions']} decisions")
    print(f"  invalid moves: {s['invalid_moves']} ({s['invalid_rate']:.4%})")


if __name__ == "__main__":
    main()
