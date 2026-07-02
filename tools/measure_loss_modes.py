"""Measure per-bucket loss rates for a full agent against an opponent pool (plan U6).

Unlike tools/collapse_rate.py (deck mirrors under one policy), this runs a real
agent from tools/opponents.py against a diverse opponent pool, the same shape of
match as tools/gauntlet.py's run_gauntlet, and captures env.toJSON() per game so
analysis/loss_classifier.py can bucket every one of our losses (deckout,
early_collapse, and the rest), not just an empty-bench mirror.

Used for U6's before-vs-after retrain comparison: run this once against the
currently shipped search/eval_model.json ("before"), swap in the retrained
model, then run it again ("after"). Each call should be a fresh process:
search/learned_eval.py caches the loaded model for the life of a process, so a
model swap mid-process would not be picked up.

Dev tool only; never shipped.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.loss_classifier import classify_batch, parse_replay  # noqa: E402
from tools import opponents  # noqa: E402

# The two buckets U6's gate cares about (plan: "compare deckout/early_collapse
# loss rates before vs after"). Every bucket is still reported via classify_batch's
# "buckets" field; these are just the ones the report highlights.
FOCUS_BUCKETS = ("deckout", "early_collapse")


def measure_agent(agent_name, opponent_names, n_games: int, env_factory=None) -> dict:
    """Play n_games (agent_name vs opponent_names, alternating first player like
    tools/gauntlet.py's run_gauntlet) and classify every one of our losses.

    env_factory makes a fresh cabt env per game (defaults to the real engine);
    injecting it keeps this testable without the native singleton.
    """
    if env_factory is None:
        from ptcg_agent.engine import make_env

        env_factory = make_env
    agent_fn = opponents.get(agent_name)
    digests = []
    for i in range(n_games):
        opp_fn = opponents.get(opponent_names[i % len(opponent_names)])
        swap = i % 2 == 1
        our_index = 1 if swap else 0
        env = env_factory()
        env.run([opp_fn, agent_fn] if swap else [agent_fn, opp_fn])
        digests.append(parse_replay(env.toJSON(), our_index=our_index))

    batch = classify_batch(digests)
    focus_counts = {b: batch["buckets"].get(b, 0) for b in FOCUS_BUCKETS}
    focus_rate_of_losses = {
        b: (focus_counts[b] / batch["losses"] if batch["losses"] else 0.0) for b in FOCUS_BUCKETS
    }
    focus_rate_of_games = {
        b: (focus_counts[b] / batch["games"] if batch["games"] else 0.0) for b in FOCUS_BUCKETS
    }
    return {
        "agent": agent_name,
        "opponents": list(opponent_names),
        **batch,
        "focus_buckets": list(FOCUS_BUCKETS),
        "focus_counts": focus_counts,
        "focus_rate_of_losses": focus_rate_of_losses,
        "focus_rate_of_games": focus_rate_of_games,
    }


def compare_before_after(before: dict, after: dict) -> dict:
    """Diff two measure_agent results bucket by bucket (plan U6's before/after gate).

    "improved" is True for a focus bucket when its rate-of-losses dropped from
    before to after (fewer of our losses fall in that bucket); ties count as not
    improved, matching the plan's "add features only if it did NOT improve" gate.
    """
    diffs = {}
    improved = {}
    for b in FOCUS_BUCKETS:
        before_rate = before["focus_rate_of_losses"][b]
        after_rate = after["focus_rate_of_losses"][b]
        diffs[b] = round(after_rate - before_rate, 4)
        improved[b] = after_rate < before_rate
    return {"diffs": diffs, "improved": improved}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("agent", help="agent under test (e.g. search)")
    ap.add_argument("opponents", nargs="+", help="opponent names (e.g. deck:aggro deck:control)")
    ap.add_argument("-n", "--matches", type=int, default=200)
    ap.add_argument("-o", "--out", help="write the JSON result to this path")
    args = ap.parse_args()
    result = measure_agent(args.agent, args.opponents, args.matches)
    print(json.dumps(result, indent=2))
    print(f"{result['games']} games, {result['wins']}W/{result['draws']}D/{result['losses']}L")
    for b in FOCUS_BUCKETS:
        print(
            f"  {b}: {result['focus_counts'][b]}/{result['losses']} losses "
            f"({result['focus_rate_of_losses'][b]:.1%} of losses)"
        )
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2))
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
