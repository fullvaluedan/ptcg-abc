"""Determinized search agent for the Pokemon TCG AI Battle Challenge (cabt).

Phase 3 agent (U5). At a MAIN decision it samples plausible hidden state, runs
determinized rollouts of each candidate first move through the engine's native
search_* forward model, and plays the highest expected value move within the time
bank. Every other decision (yes/no, counts, energy, discards) and every failure
path falls back to the heuristic, then to a guaranteed legal selection, so the
agent never forfeits by raising.

Self contained for submission: the entrypoint is the module level agent(obs).
determinize, rollout, eval, timebudget, and heuristics import either from their
package (local) or as top level modules (inside a built submission).
"""
import os
import random
import time
from pathlib import Path

try:
    from agents import heuristics
except ImportError:  # inside a submission, support modules sit at the top level
    import heuristics

try:
    from search import rollout
    from search import endgame as endgame_solver
    from search.determinize import determinize
    from search.timebudget import TimeBudget
except ImportError:
    import rollout
    import endgame as endgame_solver
    from determinize import determinize
    from timebudget import TimeBudget

try:
    from analysis import archetype
except ImportError:
    import archetype


def _read_deck():
    # The grader loads main.py with exec() and does NOT define __file__, so the
    # repo-relative candidate is only built when __file__ exists (local import).
    # Referencing __file__ unconditionally raised NameError at module load under
    # the grader and marked the whole agent ERROR.
    candidates = [
        "deck.csv",
        "/kaggle_simulations/agent/deck.csv",
    ]
    if "__file__" in globals():
        candidates.append(
            str(Path(__file__).resolve().parents[1] / "decks" / "baseline.csv")
        )
    for path in candidates:
        if os.path.exists(path):
            with open(path) as f:
                ids = [int(line) for line in f.read().split("\n") if line.strip()]
            if len(ids) >= 60:
                return ids[:60]
    raise FileNotFoundError("deck.csv not found in: " + ", ".join(candidates))


_DECK = _read_deck()
# Fixed seed keeps a match reproducible under a fixed environment seed (the gate
# wants stable argmax selection); the soft per-move cap is overridable so the
# gauntlet can trade depth for throughput without touching code.
_SEARCH_SEED = 20260630
_RNG = random.Random(_SEARCH_SEED)
_SOFT_CAP = float(os.environ.get("PTCG_SEARCH_BUDGET", "0.5"))
# An optional hard cap on determinizations per decision; the gauntlet sets it to
# trade depth for throughput. 0 means time-bounded only.
_MAX_DETS = int(os.environ.get("PTCG_SEARCH_DETS", "0")) or None
# Optional rollout depth cut-off. 0 (the default) rolls every line out to a
# terminal result; a positive value stops early and trusts the board value
# function, trading rollout accuracy for more samples per decision.
_ROLLOUT_DEPTH = int(os.environ.get("PTCG_ROLLOUT_DEPTH", "0")) or None
# Endgame solver (U9): in a small, near-decided position, spend a larger slice of
# the bank and more determinizations on the pivotal decision. On by default; the
# gauntlet can disable it (PTCG_ENDGAME=0) to A/B the effect.
_ENDGAME = os.environ.get("PTCG_ENDGAME", "1") != "0"
_BUDGET = TimeBudget(soft_cap=_SOFT_CAP)


def _is_legal(move, sel) -> bool:
    n = len(sel.get("option", []))
    if not isinstance(move, list) or len(set(move)) != len(move):
        return False
    if not (sel.get("minCount", 1) <= len(move) <= sel.get("maxCount", 1)):
        return False
    return all(isinstance(i, int) and 0 <= i < n for i in move)


def _searchable(sel) -> bool:
    """A MAIN decision with more than one single-index choice is worth searching."""
    return (
        sel.get("type") == heuristics.SEL_MAIN
        and sel.get("maxCount", 1) == 1
        and sel.get("minCount", 1) <= 1
        and len(sel.get("option", [])) > 1
    )


def agent(obs):
    sel = obs.get("select")
    if sel is None:
        # Deck selection opens every match, so reset the per-match thinking bank
        # and the sampler seed, which keeps each match reproducible even when a
        # gauntlet runs many matches in one process.
        _BUDGET.spent = 0.0
        _RNG.seed(_SEARCH_SEED)
        return _DECK
    # Safety 1 (KTD5): take a guaranteed knockout now, even if search disagrees.
    try:
        lethal = heuristics.lethal_move(obs, sel)
        if lethal is not None and _is_legal(lethal, sel):
            return lethal
    except Exception:
        pass
    try:
        # Safety 2 (KTD2): once the thinking bank is at risk, skip search and
        # answer instantly from the heuristic so we never approach a timeout.
        # Also skip when the match-time engine does not expose the search forward
        # model (the Kaggle grader provides card data but not search_*, so search
        # is inert on the ladder; see rollout.search_api_available). The heuristic
        # is then our policy, which is exactly the fallback below, so this only
        # avoids paying a swallowed ImportError on every searchable decision.
        if (
            _searchable(sel)
            and obs.get("search_begin_input")
            and not _BUDGET.at_risk
            and rollout.search_api_available()
        ):
            # Escalate the per-move soft cap and determinization budget on pivotal
            # decisions so they are searched harder; both stay bounded by the hard
            # time guard inside allot. Tiered: the near-decided endgame gets the
            # largest boost, a closing prize-race turn (still a full deck) gets a
            # moderate boost, and a leading MAIN decision keeps the small default.
            if _ENDGAME and endgame_solver.is_endgame(obs):
                cap = endgame_solver.endgame_soft_cap(_SOFT_CAP)
                dets = endgame_solver.endgame_dets(_MAX_DETS)
            elif _ENDGAME and endgame_solver.is_prize_race(obs):
                cap = endgame_solver.prize_race_soft_cap(_SOFT_CAP)
                dets = endgame_solver.prize_race_dets(_MAX_DETS)
            else:
                cap = None
                dets = _MAX_DETS
            budget = _BUDGET.allot(cap)
            if budget > 0:
                start = time.perf_counter()
                # Bias the determinization prior toward the opponent's likely
                # archetype, falling back to the mirror prior (with revealed cards
                # merged in) when nothing is recognized.
                try:
                    prior = archetype.opponent_prior(obs, _DECK)
                except Exception:
                    prior = None
                move = rollout.search_decision(
                    obs, _DECK, budget, _RNG, determinize, opponent_prior=prior,
                    max_determinizations=dets, value_depth=_ROLLOUT_DEPTH,
                )
                _BUDGET.record(time.perf_counter() - start)
                if move is not None and _is_legal(move, sel):
                    return heuristics.cap_count_for_deckout(move, sel, obs)
    except Exception:
        pass
    # Fallback: the heuristic, then any guaranteed legal selection.
    try:
        move = heuristics.choose(obs)
        if _is_legal(move, sel):
            return heuristics.cap_count_for_deckout(move, sel, obs)
    except Exception:
        pass
    try:
        return heuristics._first_legal(sel)
    except Exception:
        return [0]
