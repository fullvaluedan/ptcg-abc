"""Measure whether the pilot BENCH-DEVELOPMENT guard mechanically cuts OUR OWN
empty-bench board-out rate, holding the deck and the opponent fixed.

collapse_rate.py measures the DECK contribution to the #1 loss bucket (empty-bench
early_collapse): it compares whole decks in heuristic self-play and ranks by which
deck endures the opening board-out best. That answered "which deck" and drove the
trolley choice. It does NOT isolate the PILOT contribution, which the brief names as
the #1 piloting gap: the heuristic benches a Basic first whenever the bench is thin
(_bench_is_thin / choose_play / _choose_card_select, all gated on THIN_BENCH) BEFORE
any other play, so a lone active knocked out is not the end of the game. That guard
is a property of the pilot, not the deck.

A symmetric mirror (toggling the guard on BOTH seats at once, as collapse_rate does)
cannot isolate it: it changes our play AND the opponent's simultaneously, so the
loser's bucket reflects both. This tool runs a CONTROLLED experiment instead. Both
seats pilot the same deck with the same heuristic and the OPPONENT seat's guard is
pinned ON; only OUR seat's guard is toggled off vs on, and only OUR seat's losses
are classified. The opponent pressure is therefore identical across the two runs and
the ONLY variable is our own bench-development guard, so a change in our board-out
rate is attributable to the guard alone. This is the on-ladder situation in
miniature: a fixed field, our seat the only thing that varies.

Mechanism: agents.heuristics.THIN_BENCH is a module global read live by choose() on
every decision. Matches run sequentially and single threaded (the native engine is a
per process singleton), so each seat sets THIN_BENCH to its own value immediately
before its synchronous choose() call; the two seats never interleave, so they carry
different effective guards despite sharing the global. The global is RESTORED in a
finally, so no shipped code path is mutated and the frozen submission batch stays
byte-identical.

Read the CONTRAST, not the absolute level: the trolley glass cannon boards out often
under mirror pressure (collapse_rate documents the same over-statement), so the
signal is the RELATIVE change our guard buys, not the raw rate. A clear reduction
confirms the #1 pilot lever works MECHANICALLY on the #1 loss metric. It does NOT
claim a win rate: offline mirror play is not ladder-predictive (meta.md); the ladder
remains the judge of whether cutting board-out lifts the score. Dev tool only; never
shipped, touches no shipped code path.
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

# THIN_BENCH value that disables the develop-first guard: with the threshold at 0,
# my_bench_count (>= 0) is never < 0, so _bench_is_thin is always false and choose()
# keeps the prior first-play behavior on every decision.
_GUARD_OFF = 0


def _seat(deck_ids, thin_bench):
    """A seat that pilots deck_ids with the heuristic under a pinned THIN_BENCH.

    THIN_BENCH is set immediately before each synchronous choose() call, so this
    seat carries its own guard value even though the module global is shared. At the
    deck-selection step (select is None) it returns the fixed deck.
    """
    deck = list(deck_ids)

    def agent(obs):
        if obs.get("select") is None:
            return deck
        heuristics.THIN_BENCH = thin_bench
        return heuristics.choose(obs)

    return agent


def _run_setting(deck_ids, our_thin_bench, opp_thin_bench, n_games, env_factory):
    """Play n games with our guard at our_thin_bench, opponent's pinned on.

    Alternates the first player; classifies only OUR seat each game. Returns a tally
    of our outcomes and how often we lost specifically to empty-bench early_collapse.
    """
    early_collapse = our_losses = decided = 0
    buckets: dict = {}
    for i in range(n_games):
        env = env_factory()
        us = _seat(deck_ids, our_thin_bench)
        opp = _seat(deck_ids, opp_thin_bench)
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
    """Our empty-bench board-out rate with our guard off vs on, opponent pinned on."""
    if env_factory is None:
        from ptcg_agent.engine import make_env

        env_factory = make_env
    deck_ids = read_deck(deck_path)
    shipped = heuristics.THIN_BENCH
    try:
        off = _run_setting(deck_ids, _GUARD_OFF, shipped, n_games, env_factory)
        on = _run_setting(deck_ids, shipped, shipped, n_games, env_factory)
    finally:
        heuristics.THIN_BENCH = shipped
    return {
        "deck": Path(deck_path).stem,
        "n_games": n_games,
        "thin_bench": shipped,
        "off": off,
        "on": on,
    }


def sweep(deck_path, values, n_games: int, env_factory=None) -> dict:
    """Our empty-bench board-out rate at each of several OUR-seat THIN_BENCH values.

    The off-vs-on measure() answers "does the guard help at all" (threshold 0 vs the
    shipped 2). This answers the follow-on the brief poses: if empty-bench collapse
    persists, does RAISING the threshold (bench a Basic first until the bench is
    wider) cut our board-out FURTHER, and where does it stop paying? Each value in
    `values` is run on OUR seat against the same pinned-on opponent (shipped
    THIN_BENCH), so the field is identical across settings and the only variable is
    how wide our own develop-first guard insists the bench gets. Reads the CONTRAST
    across thresholds, not the absolute level (mirror play over-states board-out;
    see the module docstring). Restores the global in a finally so no shipped path is
    mutated. This is a mechanical board-out measurement, NOT a win-rate claim: the
    ladder judges whether a lower board-out lifts the score (meta.md).
    """
    if env_factory is None:
        from ptcg_agent.engine import make_env

        env_factory = make_env
    deck_ids = read_deck(deck_path)
    shipped = heuristics.THIN_BENCH
    settings = []
    try:
        for v in values:
            settings.append((v, _run_setting(deck_ids, v, shipped, n_games, env_factory)))
    finally:
        heuristics.THIN_BENCH = shipped
    return {
        "deck": Path(deck_path).stem,
        "n_games": n_games,
        "opp_thin_bench": shipped,
        "settings": settings,
    }


def _format_sweep(result: dict) -> str:
    settings = result["settings"]
    lines = [
        f"OUR-seat THIN_BENCH sweep on {result['deck']} (opponent guard pinned on at "
        f"THIN_BENCH={result['opp_thin_bench']}), n={result['n_games']}/setting:",
    ]
    for v, r in settings:
        lines.append(
            f"  THIN_BENCH={v:<2d} our early_collapse {r['early_collapse']:3d}/{r['games']} "
            f"({r['early_collapse_rate']:.1%})  CI95 {r['early_collapse_ci95']}  "
            f"our losses {r['our_losses']}  buckets {r['loss_buckets']}"
        )
    shipped = result["opp_thin_bench"]
    best_v, best_r = min(settings, key=lambda s: (s[1]["early_collapse_rate"], s[0]))
    base = next((r for v, r in settings if v == shipped), None)
    lines.append(
        f"  => lowest board-out at THIN_BENCH={best_v} ({best_r['early_collapse_rate']:.1%})"
    )
    if base is None or best_v == shipped:
        lines.append(
            f"  => the shipped THIN_BENCH={shipped} is the board-out floor of this sweep; "
            "no other threshold does mechanically better."
        )
        return "\n".join(lines)
    direction = "raising" if best_v > shipped else "lowering"
    delta = base["early_collapse_rate"] - best_r["early_collapse_rate"]
    # A difference is a real lever only when the two Wilson intervals do not overlap;
    # otherwise it is inside the sampling noise at this n and claims nothing.
    base_lo, base_hi = base["early_collapse_ci95"]
    best_lo, best_hi = best_r["early_collapse_ci95"]
    separated = best_hi < base_lo or base_hi < best_lo
    if separated and delta > 0:
        lines.append(
            f"  => {direction} to THIN_BENCH={best_v} cuts our board-out {delta:.1%} absolute "
            "with non-overlapping CIs; a candidate next lever (ladder is the judge)."
        )
    else:
        lines.append(
            f"  => {direction} to THIN_BENCH={best_v} shifts board-out {delta:+.1%} but the "
            f"CIs overlap the shipped {shipped}; within noise at n={result['n_games']}, no "
            "clear lever. Raise -n to resolve, or hold the shipped threshold."
        )
    return "\n".join(lines)


def _format(result: dict) -> str:
    off, on = result["off"], result["on"]
    off_rate, on_rate = off["early_collapse_rate"], on["early_collapse_rate"]
    reduction = (off_rate - on_rate) / off_rate if off_rate else 0.0
    lines = [
        f"pilot bench-development guard effect on {result['deck']} (our seat only, "
        f"opponent guard pinned on), n={result['n_games']}/setting:",
        f"  OUR guard OFF (THIN_BENCH=0)  our early_collapse "
        f"{off['early_collapse']:3d}/{off['games']} ({off_rate:.1%})  "
        f"CI95 {off['early_collapse_ci95']}  our losses {off['our_losses']}  "
        f"buckets {off['loss_buckets']}",
        f"  OUR guard ON  (THIN_BENCH={result['thin_bench']})  our early_collapse "
        f"{on['early_collapse']:3d}/{on['games']} ({on_rate:.1%})  "
        f"CI95 {on['early_collapse_ci95']}  our losses {on['our_losses']}  "
        f"buckets {on['loss_buckets']}",
        f"  relative reduction from our guard (positive = less board-out): "
        f"{reduction:+.1%} ({off_rate:.1%} -> {on_rate:.1%})",
    ]
    if on_rate < off_rate:
        lines.append(
            "  => our bench guard MECHANICALLY cuts our empty-bench board-out under a "
            "fixed opponent; the ladder judges whether that lifts the score."
        )
    elif on_rate == off_rate:
        lines.append(
            "  => no measured difference at this n; raise -n, or the guard is inert on "
            "this deck (our bench fills without it)."
        )
    else:
        lines.append(
            "  => our guard did NOT reduce our board-out here; the bench-development "
            "lever is not demonstrably the board-out fix offline, investigate before "
            "relying on it."
        )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck", nargs="?", default=str(_ROOT / "decks" / "trolley.csv"),
                    help="deck csv path (default: decks/trolley.csv, the shipped floor deck)")
    ap.add_argument("-n", "--games", type=int, default=80,
                    help="games per setting (our guard off, our guard on)")
    ap.add_argument("--sweep", default=None,
                    help="comma-separated OUR-seat THIN_BENCH values to sweep instead of "
                         "the off-vs-on contrast, e.g. 0,1,2,3,4")
    args = ap.parse_args()
    if args.sweep:
        values = [int(v) for v in args.sweep.split(",") if v.strip() != ""]
        print(_format_sweep(sweep(args.deck, values, args.games)))
    else:
        print(_format(measure(args.deck, args.games)))


if __name__ == "__main__":
    main()
