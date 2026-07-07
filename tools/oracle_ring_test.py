"""U109: oracle bound test for the determinized search lane.

The shipped agent is the pure heuristic. A prior attempt at match-time
determinized search failed hard on the real ladder (431.4 vs the heuristic's
569.6) because its opponent model assumed the opponent runs OUR OWN deck (the
mirror prior), which is systematically wrong against a varied field
(analysis/search_recovered_on_ladder.md). Weeks 2-3 of the 30-day roadmap
propose spending real effort building a learned field-calibrated prior for
determinize's opponent_prior parameter, but that is only worth funding if
search's ceiling is above the heuristic's ceiling in the first place.

This module answers that cheaply: hand determinize the ring opponent's ACTUAL
true decklist as opponent_prior (search/determinize.py line 214), the best
possible opponent model, an oracle rather than a learned approximation, for
each specific matchup. If search with an oracle prior still cannot beat our
best ring-confirmed heuristic build, no learned prior (necessarily worse than
the oracle) can ever close the gap either, and the whole search lane should be
killed per docs/ROADMAP-30D.md section 6's Jul 13 criterion.

Two arms, same run, same 9 ring opponents (tools/ring_calibrate.ring_names()):
  Arm A (incumbent): heuristic+yushin+ability+attack_first, the U112-confirmed
    stacked build (analysis/u112_stacked_ring_confirmation.md, 0.860 at n=100).
  Arm B (oracle-search): agent_search's rollout.search_decision driven with
    opponent_prior forced to the TRUE decklist of whichever ring opponent is
    about to be played, on the same yushin deck as arm A. The round-robin loop
    below builds a fresh oracle agent per opponent name rather than one static
    agent that guesses its opponent's identity, since guessing would defeat
    the whole point of an oracle upper bound.

Decision gate per plan U109: oracle beats the stacked incumbent by more than
+0.05 same-run at n=40/arm.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ptcg_agent.engine import run_match  # noqa: E402
from tools import opponents, ring_calibrate  # noqa: E402

DEFAULT_MATCHES = 40
GATE_THRESHOLD = 0.05
# The U112-confirmed incumbent's deck and lever settings (analysis/u112_stacked_
# ring_confirmation.md arm 3: heuristic+yushin+ability+attack_first, 0.860 at n=100).
INCUMBENT_DECK = "candidate_yushin_ito"


def _incumbent_agent_factory():
    """heuristic+yushin+ability+attack_first (the U112-confirmed stacked incumbent)."""
    def factory():
        from agents import heuristics as H

        base_agent = opponents.get(f"deck:{INCUMBENT_DECK}")

        def agent(obs):
            orig_ability = H._ABILITY
            orig_attack_first = H._ATTACK_FIRST
            H._ABILITY = True
            H._ATTACK_FIRST = True
            try:
                return base_agent(obs)
            finally:
                H._ABILITY = orig_ability
                H._ATTACK_FIRST = orig_attack_first

        return agent

    return factory


def _opponent_true_decklist(opponent_name) -> list:
    """The 60 card ids for a clone:<family> ring opponent's real decklist on disk.

    Reuses opponents._read_deck_csv against the same decks/<family>.csv path
    _clone_opponent already loads for that opponent, so the oracle prior is
    read from the identical source of truth the opponent itself plays.
    """
    if not opponent_name.startswith("clone:"):
        raise ValueError(f"not a clone: ring opponent: {opponent_name}")
    family = opponent_name[len("clone:"):]
    path = _ROOT / "decks" / f"{family}.csv"
    return opponents._read_deck_csv(path)


def _oracle_search_agent_factory(oracle_prior):
    """agent_search's rollout, but opponent_prior is forced to oracle_prior.

    Deliberately bypasses agent_search.py's own archetype-guessing opponent
    prior (analysis/archetype.py's opponent_prior) entirely: the whole point of
    an oracle test is the unfair advantage of the true decklist, not a better
    guess. Mirrors agent_search.agent's decision structure (lethal safety
    first, thin-bench deferral to the heuristic, budget-gated search, and a
    heuristic/first-legal fallback) but always calls search/determinize.py's
    determinize with the oracle prior instead of a guessed or mirror one, and
    pilots INCUMBENT_DECK so the only difference from arm A is the opponent
    model available to search, not the deck.
    """
    def factory():
        from agents import agent_search
        from agents import heuristics as H
        from search import rollout
        from search.determinize import determinize
        from search.timebudget import TimeBudget

        deck = opponents.get(f"deck:{INCUMBENT_DECK}")({"select": None})
        budget = TimeBudget(soft_cap=agent_search._SOFT_CAP)
        rng = random.Random(agent_search._SEARCH_SEED)

        def agent(obs):
            sel = obs.get("select")
            if sel is None:
                budget.spent = 0.0
                rng.seed(agent_search._SEARCH_SEED)
                return deck
            try:
                lethal = H.lethal_move(obs, sel)
                if lethal is not None and agent_search._is_legal(lethal, sel):
                    return lethal
            except Exception:
                pass
            try:
                if (
                    agent_search._searchable(sel)
                    and obs.get("search_begin_input")
                    and not budget.at_risk
                    and rollout.search_api_available()
                    and not H._bench_is_thin(obs)
                ):
                    b = budget.allot()
                    if b > 0:
                        import time

                        start = time.perf_counter()
                        move = rollout.search_decision(
                            obs, deck, b, rng, determinize,
                            opponent_prior=oracle_prior,
                        )
                        budget.record(time.perf_counter() - start)
                        if move is not None and agent_search._is_legal(move, sel):
                            return H.cap_count_for_deckout(move, sel, obs)
            except Exception:
                pass
            try:
                move = H.choose(obs)
                if agent_search._is_legal(move, sel):
                    return H.cap_count_for_deckout(move, sel, obs)
            except Exception:
                pass
            try:
                return H._first_legal(sel)
            except Exception:
                return [0]

        return agent

    return factory


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


def _oracle_ring_win_rate(opponent_names, n_matches):
    """Round-robin the oracle-search agent, rebuilding it per opponent so each
    matchup gets THAT opponent's true decklist as opponent_prior.

    A static agent cannot see which opponent it is about to face (engine.
    run_match hands both callables the same observation shape), so the oracle
    prior must be selected by the loop before the match starts, not guessed by
    the agent from observations. This is what makes the test an oracle
    (deliberately unfair information) rather than another learned-prior
    attempt.
    """
    if not opponent_names or n_matches <= 0:
        return 0.0, 0, 0, 0, 0
    wins = draws = losses = 0
    for i in range(n_matches):
        opp_name = opponent_names[i % len(opponent_names)]
        oracle_prior = _opponent_true_decklist(opp_name)
        agent_fn = _oracle_search_agent_factory(oracle_prior)()
        opp_fn = opponents.get(opp_name)
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


def run_oracle_bound_test(n_matches=DEFAULT_MATCHES) -> dict:
    """Run both arms in one invocation and return {arm_name: {win_rate, ...}}."""
    opponent_names = ring_calibrate.ring_names()
    if not opponent_names:
        raise RuntimeError(
            "no clone: opponents available; run tools/bracket_decks.py or check decks/"
        )

    results = {}

    incumbent_fn = _incumbent_agent_factory()()
    win_rate, wins, draws, losses, n = _ring_win_rate(incumbent_fn, opponent_names, n_matches)
    results["arm_a_stacked_incumbent"] = {
        "win_rate": win_rate, "wins": wins, "draws": draws, "losses": losses, "n": n,
    }
    print(f"arm_a_stacked_incumbent: {win_rate:.3f} ({wins}-{draws}-{losses}, n={n})")

    win_rate, wins, draws, losses, n = _oracle_ring_win_rate(opponent_names, n_matches)
    results["arm_b_oracle_search"] = {
        "win_rate": win_rate, "wins": wins, "draws": draws, "losses": losses, "n": n,
    }
    print(f"arm_b_oracle_search: {win_rate:.3f} ({wins}-{draws}-{losses}, n={n})")

    return results


def _main(argv=None):
    ap = argparse.ArgumentParser(description="U109 oracle bound test")
    ap.add_argument("-n", "--matches", type=int, default=DEFAULT_MATCHES,
                     help="games per arm (default %(default)s)")
    args = ap.parse_args(argv)

    print(f"Running U109 oracle bound test (n={args.matches} per arm)...")
    results = run_oracle_bound_test(n_matches=args.matches)

    print("\n" + "=" * 60)
    print("Results:")
    print(json.dumps(results, indent=2))

    incumbent_wr = results["arm_a_stacked_incumbent"]["win_rate"]
    oracle_wr = results["arm_b_oracle_search"]["win_rate"]
    delta = oracle_wr - incumbent_wr

    print("\n" + "=" * 60)
    print(f"Arm A (stacked incumbent):     {incumbent_wr:.3f}")
    print(f"Arm B (oracle-search):         {oracle_wr:.3f}")
    print(f"Delta (oracle - incumbent):    {delta:+.3f}")
    print(f"Gate threshold (>+{GATE_THRESHOLD:.2f}):     {'PASS' if delta > GATE_THRESHOLD else 'FAIL'}")

    return 0 if delta > GATE_THRESHOLD else 2


if __name__ == "__main__":
    raise SystemExit(_main())
