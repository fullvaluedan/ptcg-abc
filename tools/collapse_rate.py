"""Measure the empty-bench early_collapse RATE per deck in heuristic self-play.

Win rate cannot separate the staged consistency decks (ultraball, trolley) from
the baseline combo deck: empty-bench early_collapse is a minority of self-play
games and the only upside is against the diverse ladder field, which a mirror
gauntlet cannot show. But the deck change targets early_collapse directly, and
THAT is measurable offline. For each deck we run N heuristic-vs-heuristic mirror
games, read env.toJSON, and classify the loser of each game. The fraction of
games lost to empty-bench early_collapse is the exact failure the consistency
decks aim to cut; whichever deck cuts it most is the better ladder candidate.

Important reading: the mirror over-states the absolute rate (both seats pilot the
same 6-basic glass cannon, so a lone-active knockout is the dominant ending). The
signal is the RELATIVE reduction versus baseline, not the absolute level. On the
ladder only our deck carries the fix, so a lower mirror collapse rate means our
own seat collapses less often.

Dev tool only; never shipped. The engine is a per process singleton, so matches
run sequentially in process (one fresh env per match).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.loss_classifier import classify_loss, parse_replay  # noqa: E402
from tools import opponents  # noqa: E402
from tools.deck_match import deck_bound  # noqa: E402
from tools.deck_validate import read_deck  # noqa: E402
from tools.gauntlet import _wilson  # noqa: E402


def loser_bucket(replay) -> tuple | None:
    """Classify the losing seat of one game.

    Returns (bucket, my_bench_end) for whichever seat lost, or None if the game
    was a draw or unknown. Parsing from each seat in turn finds the one loss; in a
    decided game exactly one seat reads as a loss, so the first hit is the loser.
    Pure over the replay JSON; no engine, no network.
    """
    for seat in (0, 1):
        dg = parse_replay(replay, our_index=seat)
        if dg.get("outcome") != "loss":
            continue
        return classify_loss(dg), dg.get("my_bench_end")
    return None


def measure_deck(deck_ids, n_games: int, policy="heuristic", env_factory=None) -> dict:
    """Run n mirror games on one deck and tally how the loser lost each game.

    env_factory makes a fresh cabt env per game (defaults to the real engine);
    injecting it keeps the tally logic testable without the native singleton.
    """
    if env_factory is None:
        from ptcg_agent.engine import make_env

        env_factory = make_env
    policy_fn = opponents.get(policy)
    a = deck_bound(policy_fn, deck_ids)
    b = deck_bound(policy_fn, deck_ids)
    buckets: dict = {}
    early_collapse = 0
    decided = 0
    for i in range(n_games):
        env = env_factory()
        env.run([b, a] if i % 2 == 1 else [a, b])
        outcome = loser_bucket(env.toJSON())
        if outcome is None:
            continue  # a draw, no loser to classify
        decided += 1
        bucket, _bench = outcome
        buckets[bucket] = buckets.get(bucket, 0) + 1
        if bucket == "early_collapse":
            early_collapse += 1
    lo, hi = _wilson(early_collapse, n_games) if n_games else (0.0, 0.0)
    return {
        "games": n_games,
        "decided": decided,
        "early_collapse": early_collapse,
        "early_collapse_rate": early_collapse / n_games if n_games else 0.0,
        "early_collapse_ci95": (round(lo, 3), round(hi, 3)),
        "buckets": buckets,
    }


def compare(deck_paths, n_games: int, policy="heuristic") -> dict:
    """Measure each deck and rank by lowest empty-bench early_collapse rate."""
    rows = {}
    for p in deck_paths:
        name = Path(p).stem
        rows[name] = measure_deck(read_deck(p), n_games, policy)
    ranked = sorted(rows.items(), key=lambda kv: kv[1]["early_collapse_rate"])
    return {"policy": policy, "n_games": n_games, "decks": rows, "ranked_best_first": [n for n, _ in ranked]}


def _format(result: dict) -> str:
    lines = [
        f"empty-bench early_collapse rate, {result['policy']} self-play, "
        f"n={result['n_games']}/deck (lower is better):"
    ]
    for name in result["ranked_best_first"]:
        r = result["decks"][name]
        ci = r["early_collapse_ci95"]
        lines.append(
            f"  {name:10s} {r['early_collapse']:3d}/{r['games']} "
            f"({r['early_collapse_rate']:.1%}, 95% CI {ci[0]:.1%} to {ci[1]:.1%})  "
            f"buckets {r['buckets']}"
        )
    lines.append(f"  fewest collapses: {result['ranked_best_first'][0] if result['ranked_best_first'] else None}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("decks", nargs="+", help="deck csv paths")
    ap.add_argument("-p", "--policy", default="heuristic")
    ap.add_argument("-n", "--games", type=int, default=80)
    args = ap.parse_args()
    print(_format(compare(args.decks, args.games, args.policy)))


if __name__ == "__main__":
    main()
