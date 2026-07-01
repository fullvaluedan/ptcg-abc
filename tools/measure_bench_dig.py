"""Measure whether the DIG-for-a-Basic lever (PTCG_BENCH_DIG) mechanically cuts
OUR OWN empty-bench board-out rate, holding the deck and the opponent fixed.

measure_benchguard isolates the bench-ORDERING guard (bench a Basic you already
hold before another play). analysis/empty_bench_is_draw_variance.md showed that
guard has no purchase on the real collapse losses: in 94% of the empty-bench
decision moments in the ladder replays we held NO benchable Basic to reorder. The
finding points at the OTHER lever: when the bench is thin and we hold no Basic and
no direct bench-fetch trainer, DIG for one with a draw/search trainer this turn.
That is the choose_play branch gated on heuristics._BENCH_DIG (default off).

This runs the same controlled experiment as measure_benchguard so the two are
directly comparable: both seats pilot the same deck with the same heuristic, the
OPPONENT seat's dig lever is pinned at the shipped default (off), and only OUR
seat's lever is toggled off vs on. Only OUR seat's losses are classified, so the
opponent pressure is identical across the two runs and the ONLY variable is our
own dig lever. A change in our board-out rate is attributable to the lever alone.

Read the CONTRAST, not the absolute level: the trolley glass cannon boards out
often under mirror pressure (collapse_rate documents the same over-statement), so
the signal is the RELATIVE change the lever buys, and a claim is made only when the
two Wilson intervals do not overlap. This is a mechanical board-out measurement,
NOT a win-rate claim: offline mirror play is not ladder-predictive (meta.md); the
ladder remains the judge of whether cutting board-out lifts the score.

Mechanism: agents.heuristics._BENCH_DIG is a module global read live by choose_play
on every decision. Matches run sequentially and single threaded (the native engine
is a per process singleton), so each seat sets _BENCH_DIG to its own value
immediately before its synchronous choose() call; the two seats never interleave.
The global is RESTORED in a finally, so no shipped code path is mutated and the
frozen submission batch stays byte-identical. Dev tool only; never shipped.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agents import heuristics  # noqa: E402
from analysis.loss_classifier import classify_loss, parse_replay  # noqa: E402
from tools.deck_validate import read_deck  # noqa: E402
from tools.gauntlet import _wilson  # noqa: E402


def _seat(deck_ids, bench_dig):
    """A seat that pilots deck_ids with the heuristic under a pinned _BENCH_DIG.

    _BENCH_DIG is set immediately before each synchronous choose() call, so this
    seat carries its own lever value even though the module global is shared. At the
    deck-selection step (select is None) it returns the fixed deck.
    """
    deck = list(deck_ids)

    def agent(obs):
        if obs.get("select") is None:
            return deck
        heuristics._BENCH_DIG = bench_dig
        return heuristics.choose(obs)

    return agent


def _run_setting(deck_ids, our_dig, opp_dig, n_games, env_factory):
    """Play n games with our lever at our_dig, opponent's pinned at opp_dig.

    Alternates the first player; classifies only OUR seat each game.
    """
    early_collapse = our_losses = decided = 0
    buckets: dict = {}
    for i in range(n_games):
        env = env_factory()
        us = _seat(deck_ids, our_dig)
        opp = _seat(deck_ids, opp_dig)
        if i % 2 == 0:
            env.run([us, opp])
            our_index = 0
        else:
            env.run([opp, us])
            our_index = 1
        dg = parse_replay(env.toJSON(), our_index=our_index)
        outcome = dg.get("outcome")
        if outcome not in ("win", "loss"):
            continue  # a draw or unknown, not a decided result for our seat
        decided += 1
        if outcome == "loss":
            our_losses += 1
            bucket = classify_loss(dg)
            buckets[bucket] = buckets.get(bucket, 0) + 1
            if bucket == "early_collapse":
                early_collapse += 1
    lo, hi = _wilson(early_collapse, n_games) if n_games else (0.0, 0.0)
    return {
        "games": n_games,
        "decided": decided,
        "our_losses": our_losses,
        "early_collapse": early_collapse,
        "early_collapse_rate": early_collapse / n_games if n_games else 0.0,
        "early_collapse_ci95": (round(lo, 3), round(hi, 3)),
        "loss_buckets": buckets,
    }


def measure(deck_path, n_games: int, env_factory=None) -> dict:
    """Our empty-bench board-out rate with our dig lever off vs on, opponent pinned off."""
    if env_factory is None:
        from ptcg_agent.engine import make_env

        env_factory = make_env
    deck_ids = read_deck(deck_path)
    shipped = heuristics._BENCH_DIG  # shipped default (off)
    try:
        off = _run_setting(deck_ids, False, shipped, n_games, env_factory)
        on = _run_setting(deck_ids, True, shipped, n_games, env_factory)
    finally:
        heuristics._BENCH_DIG = shipped
    return {
        "deck": Path(deck_path).stem,
        "n_games": n_games,
        "off": off,
        "on": on,
    }


def _format(result: dict) -> str:
    off, on = result["off"], result["on"]
    off_rate, on_rate = off["early_collapse_rate"], on["early_collapse_rate"]
    reduction = (off_rate - on_rate) / off_rate if off_rate else 0.0
    lines = [
        f"dig-for-a-Basic lever effect on {result['deck']} (our seat only, opponent "
        f"dig pinned off), n={result['n_games']}/setting:",
        f"  OUR dig OFF  our early_collapse {off['early_collapse']:3d}/{off['games']} "
        f"({off_rate:.1%})  CI95 {off['early_collapse_ci95']}  our losses "
        f"{off['our_losses']}  buckets {off['loss_buckets']}",
        f"  OUR dig ON   our early_collapse {on['early_collapse']:3d}/{on['games']} "
        f"({on_rate:.1%})  CI95 {on['early_collapse_ci95']}  our losses "
        f"{on['our_losses']}  buckets {on['loss_buckets']}",
        f"  relative reduction from the dig lever (positive = less board-out): "
        f"{reduction:+.1%} ({off_rate:.1%} -> {on_rate:.1%})",
    ]
    # A difference is a real lever only when the two Wilson intervals do not overlap;
    # otherwise it is inside the sampling noise at this n and claims nothing.
    off_lo, off_hi = off["early_collapse_ci95"]
    on_lo, on_hi = on["early_collapse_ci95"]
    separated = on_hi < off_lo or off_hi < on_lo
    if on_rate < off_rate and separated:
        lines.append(
            "  => the dig lever MECHANICALLY cuts our empty-bench board-out with "
            "non-overlapping CIs; a candidate ladder A/B (the ladder is the judge)."
        )
    elif on_rate < off_rate:
        lines.append(
            f"  => direction favors the dig lever but the CIs overlap at n="
            f"{result['n_games']}; within noise, not yet a clear lever. Raise -n to "
            "resolve before spending a slot."
        )
    elif on_rate == off_rate:
        lines.append(
            "  => no measured difference at this n; the lever is inert on this deck "
            "(our thin-bench turns rarely lack both a Basic and a fetch)."
        )
    else:
        lines.append(
            "  => the dig lever did NOT reduce our board-out here; do not rely on it "
            "as the board-out fix. Deck density (trolley_thick) remains the lever."
        )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck", nargs="?", default=str(_ROOT / "decks" / "trolley.csv"),
                    help="deck csv path (default: decks/trolley.csv, the shipped floor deck)")
    ap.add_argument("-n", "--games", type=int, default=120,
                    help="games per setting (our dig off, our dig on)")
    args = ap.parse_args()
    print(_format(measure(args.deck, args.games)))


if __name__ == "__main__":
    main()
