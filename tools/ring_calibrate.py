"""Calibration gate for the top-player clone ring (plan U73).

The audited failure this closes: every offline proxy tried so far (the mirror
pool, the move-ranking validator) has gone 0-for-5 predicting real ladder
outcomes, because a candidate that only ever plays against copies of its own
strategy never gets punished for the mistakes a genuinely different opponent
would punish. U70-U72 built a different kind of foil: clone:<family>
opponents (tools/opponents.py) that pilot a real top-team's harvested deck
and pick the first legal option (the practical ceiling U71's trained-model
attempts could not beat on real top-player decisions), not our own strategic
ladder wearing a different deck.

This module is the pre-registered test of whether that foil is actually
predictive: replay six historical builds whose real ladder public score is
already known (five from analysis/proxy_calibration.py's KNOWN_LADDER plus
trolley_thick) against the clone ring at a fixed match count, then rank-
correlate the ring's win-rate ordering against the known ladder ordering.
Reuses analysis.proxy_calibration's Kendall-tau retrodiction math (already
unit-tested for tie-handling and the "too few builds" refuse-to-conclude
case) rather than re-deriving the same math a second time.

DECISION RULE, pre-registered here per the plan: tau >= 0.7 over >= 4 covered
builds means the ring REPLACES the mirror pool as the offline gate for every
future TRACK L candidate. Below that, the failure is recorded honestly
(analysis/ring_calibration.md) and the ladder stays the sole arbiter. A
passing ring still only gates FUTURE candidates; it never retroactively
overturns an already-pre-registered ladder A/B.
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

from analysis.proxy_calibration import calibrate as _tau_calibrate  # noqa: E402
from ptcg_agent.engine import run_match  # noqa: E402
from tools import opponents  # noqa: E402

# The six historical builds with a known ladder public score: proxy_calibration's
# five plus trolley_thick 446.2 (docs/plans/2026-07-03-002-feat-top-player-clone-
# ring-plan.md, U73).
KNOWN_LADDER = {
    "heuristic+trolley": 569.6,
    "heuristic+benchguard": 554.5,
    "search+trolley": 514.7,
    "meta_grimmsnarl": 510.1,
    "meta_archaludon": 382.5,
    "trolley_thick": 446.2,
}

# Looser than proxy_calibration's 0.8: the ring plays real games and so carries
# its own match-count noise on top of any true signal, unlike a hand-designed
# proxy score. Pre-registered in the plan, not tuned after seeing a result.
CORRELATION_THRESHOLD = 0.7
# A build set below this can only ever be perfectly concordant or discordant, so
# a smaller "calibration" is no evidence at all (mirrors proxy_calibration).
MIN_COVERAGE = 4
DEFAULT_MATCHES = 20


def _no_benchguard_trolley_agent():
    """heuristic+trolley (569.6): the pre-benchguard heuristic on the trolley deck.

    The bench-development guard (THIN_BENCH, shipped in ref 54215910) is now
    baked into every current heuristic build with no on/off flag; the 569.6 build
    predates it. b < THIN_BENCH is never true once THIN_BENCH is 0, so patching
    the module constant to 0 for just this build's games reproduces the pre-guard
    behavior without a second copy of choose_play.
    """
    from agents import heuristics as H

    inner = opponents.get("deck:trolley")

    def agent(obs):
        orig = H.THIN_BENCH
        H.THIN_BENCH = 0
        try:
            return inner(obs)
        finally:
            H.THIN_BENCH = orig

    return agent


def _search_trolley_agent():
    """search+trolley (514.7): agent_search piloting the trolley deck.

    agent_search resolves its own deck.csv from repo-relative candidates that
    never resolve to trolley outside a build tarball, so this wraps it to answer
    trolley at the deck-selection step. The real agent is still called once on
    that step (for its per-match search-budget/seed reset side effects); every
    other decision is unchanged.
    """
    from agents import agent_search

    deck = opponents.get("deck:trolley")({"select": None})

    def agent(obs):
        if obs.get("select") is None:
            agent_search.agent(obs)
            return deck
        return agent_search.agent(obs)

    return agent


# Build name -> zero-arg factory returning a fresh agent callable for one run.
# The four "current heuristic" builds postdate the bench guard (all submitted
# after ref 54215910) so today's default heuristic reproduces them as-is.
BUILD_FACTORIES = {
    "heuristic+trolley": _no_benchguard_trolley_agent,
    "heuristic+benchguard": lambda: opponents.get("deck:trolley"),
    "search+trolley": _search_trolley_agent,
    "meta_grimmsnarl": lambda: opponents.get("deck:meta_grimmsnarl"),
    "meta_archaludon": lambda: opponents.get("deck:meta_archaludon"),
    "trolley_thick": lambda: opponents.get("deck:trolley_thick"),
}


def ring_names() -> list:
    """clone:<family> opponent names for every qualifying family on disk."""
    return [f"clone:{fam}" for fam in opponents.clone_family_names()]


def _ring_win_rate(agent_fn, opponent_names, n_matches):
    """(win_rate, wins, draws, losses, n) for agent_fn round-robin over opponent_names."""
    if not opponent_names or n_matches <= 0:
        return 0.0, 0, 0, 0, 0
    wins = draws = losses = 0
    for i in range(n_matches):
        opp_fn = opponents.get(opponent_names[i % len(opponent_names)])
        res = run_match(agent_fn, opp_fn, swap_first=(i % 2 == 1))
        r = res["reward_a"]
        if r == 1:
            wins += 1
        elif r == -1:
            losses += 1
        else:
            draws += 1
    n = wins + draws + losses
    return (wins / n if n else 0.0), wins, draws, losses, n


def run_ring(n_matches=DEFAULT_MATCHES, builds=None, opponent_names=None) -> dict:
    """Ring win-rate stats for each historical build, fixed N per build.

    builds defaults to BUILD_FACTORIES (all six known builds); opponent_names
    defaults to ring_names() (every clone: family on disk). Returns
    {build_name: {"win_rate", "wins", "draws", "losses", "n"}}. Raises if no
    clone: opponent is available, since a ring of zero opponents cannot gate
    anything.
    """
    names = opponent_names if opponent_names is not None else ring_names()
    if not names:
        raise RuntimeError(
            "no clone: opponents available (no CLONE_FAMILIES decklist on disk); "
            "run tools/build_clone_dataset.py or check decks/ before calibrating"
        )
    factories = builds if builds is not None else BUILD_FACTORIES
    results = {}
    for name, factory in factories.items():
        agent_fn = factory()
        win_rate, wins, draws, losses, n = _ring_win_rate(agent_fn, names, n_matches)
        results[name] = {"win_rate": win_rate, "wins": wins, "draws": draws, "losses": losses, "n": n}
    return results


def calibrate_from_results(results, known=None, min_coverage=MIN_COVERAGE,
                            threshold=CORRELATION_THRESHOLD) -> dict:
    """The pre-registered U73 correlation gate over already-measured ring results.

    results maps build name -> {"win_rate": ..., ...} (run_ring's return shape,
    or a hand-built dict of the same shape for tests). Separated from run_ring so
    the gate math is unit-testable on planted orderings without playing real
    games in the test suite.
    """
    proxy_scores = {name: r["win_rate"] for name, r in results.items()}
    report = _tau_calibrate(
        proxy_scores, ladder=known or KNOWN_LADDER,
        min_coverage=min_coverage, threshold=threshold,
    )
    report["ring_results"] = results
    return report


def calibrate(n_matches=DEFAULT_MATCHES, builds=None, opponent_names=None,
              known=None, min_coverage=MIN_COVERAGE, threshold=CORRELATION_THRESHOLD) -> dict:
    """Play the ring, then grade it: the full U73 gate in one call."""
    results = run_ring(n_matches=n_matches, builds=builds, opponent_names=opponent_names)
    return calibrate_from_results(
        results, known=known, min_coverage=min_coverage, threshold=threshold
    )


def _main(argv=None):
    ap = argparse.ArgumentParser(description="Top-player clone ring calibration gate (U73)")
    ap.add_argument("-n", "--matches", type=int, default=DEFAULT_MATCHES,
                     help="games per build against the ring (default %(default)s)")
    args = ap.parse_args(argv)
    report = calibrate(n_matches=args.matches)
    print(json.dumps(report, indent=2, default=str))
    print()
    tau = report["tau"]
    tau_str = f"{tau:.3f}" if tau is not None else "None"
    if report["passes"]:
        print(f"PASS: ring tau={tau_str} >= {report['threshold']} over "
              f"{report['n_covered']}/{report['n_known']} builds. Ring replaces the "
              "mirror pool as the offline gate.")
    else:
        print(f"FAIL: ring tau={tau_str} < {report['threshold']} or coverage "
              f"{report['n_covered']} < {report['min_coverage']}. Ladder stays sole "
              "arbiter; record honestly, do not force it.")
    return 0 if report["passes"] else 2


if __name__ == "__main__":
    raise SystemExit(_main())
