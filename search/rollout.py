"""Drive the engine's native search_* forward model through determinized rollouts.

For one determinization and one candidate first move, begin a fresh search state,
play the candidate, then roll to a terminal result with the heuristic policy and
read the value. The heuristic is the rollout policy and the agent's fallback, so
rollouts make the same rule aware choices the live agent would. search_decision
aggregates expected value across determinizations and candidate first moves and
returns the best first move, all within a wall-clock budget.

Pure over cg.api (located lazily) and the bundled heuristics, so it ships next to
main.py. The native core is a process-global singleton: search_begin opens a state
keyed by searchId, search_release frees it, search_end resets between decisions.
"""
from __future__ import annotations

import sys
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path

try:
    from agents import heuristics
except ImportError:  # inside a submission, support modules sit at the top level
    import heuristics

try:
    from search import eval as ev
except ImportError:
    import eval as ev

# Cap a single rollout so a non-terminating line (the heuristic is stateless and
# could in principle stall) can never hang the agent. A real game ends well under
# this many selections.
ROLLOUT_MAX_STEPS = 400


def _ensure_cg_on_path() -> None:
    try:
        import cg.api  # noqa: F401

        return
    except ImportError:
        pass
    here = Path(__file__).resolve()
    for parent in here.parents:
        for sub in ("data", "vendor"):
            if (parent / sub / "cg" / "api.py").exists():
                p = str(parent / sub)
                if p not in sys.path:
                    sys.path.insert(0, p)
                return


@lru_cache(maxsize=1)
def _cg():
    """The cg.api forward-model functions, imported once."""
    _ensure_cg_on_path()
    from cg.api import (
        search_begin,
        search_end,
        search_release,
        search_step,
        to_observation_class,
    )

    return search_begin, search_step, search_end, search_release, to_observation_class


def _legal(move, sel) -> bool:
    if sel is None or not isinstance(move, list):
        return False
    n = len(sel.get("option", []))
    if len(set(move)) != len(move):
        return False
    if not (sel.get("minCount", 1) <= len(move) <= sel.get("maxCount", 1)):
        return False
    return all(isinstance(i, int) and 0 <= i < n for i in move)


def _policy(observation) -> list:
    """Choose a legal rollout move from a search Observation dataclass.

    Converts the dataclass to the dict shape the heuristic consumes, then falls
    back to a guaranteed legal selection if the heuristic declines or errors.
    """
    obs_dict = asdict(observation)
    sel = obs_dict.get("select")
    try:
        move = heuristics.choose(obs_dict)
        if _legal(move, sel):
            return move
    except Exception:
        pass
    return heuristics._first_legal(sel) if sel is not None else [0]


def rollout(search_id, first_select, your_index, search_step,
            max_steps=ROLLOUT_MAX_STEPS) -> float:
    """Play first_select from search_id, roll to terminal, return our value."""
    cur = search_step(search_id, first_select)
    for _ in range(max_steps):
        obs = cur.observation
        state = obs.current
        if state is not None:
            tv = ev.terminal_value(state.result, your_index)
            if tv is not None:
                return tv
        sel = obs.select
        if sel is None:
            break
        cur = search_step(cur.searchId, _policy(obs))
    state = cur.observation.current
    if state is None:
        return ev.DRAW
    return ev.shaped_value(asdict(state), your_index)


def search_decision(obs, your_full_deck, budget_seconds, rng, determinize,
                    opponent_prior=None, max_steps=ROLLOUT_MAX_STEPS,
                    max_determinizations=None, clock=None):
    """Score each candidate first move by determinized rollouts; return the best.

    Returns a single-element index list for the highest mean-value first move, or
    None if no rollout completed (the caller should then use the heuristic). Each
    (determinization, candidate) pair opens its own search state because the
    native model has no fork: a state can only be stepped forward, then released.
    A fixed max_determinizations bounds the work (and makes selection reproducible
    under a fixed seed) independent of wall-clock noise.
    """
    if clock is None:
        from time import perf_counter as clock
    search_begin, search_step, search_end, search_release, to_obs = _cg()

    sel = obs["select"]
    n = len(sel["option"])
    your_index = obs["current"]["yourIndex"]
    totals = [0.0] * n
    counts = [0] * n
    obs_class = to_obs(obs)
    start = clock()
    dets = 0
    try:
        while clock() - start < budget_seconds and (
            max_determinizations is None or dets < max_determinizations
        ):
            dets += 1
            det = determinize(obs, your_full_deck, rng, opponent_prior)
            kwargs = det.as_search_begin_kwargs()
            # Evaluate every candidate within this determinization before checking
            # the clock again, so each candidate keeps an equal number of samples.
            # Cutting off mid loop would starve high-index candidates and bias the
            # argmax toward the front of the option list.
            for ci in range(n):
                try:
                    root = search_begin(obs_class, **kwargs)
                except Exception:
                    # The determinization was rejected; abandon it entirely and
                    # sample a fresh one on the next loop. Same kwargs for every
                    # candidate, so this fails (if at all) before any are counted.
                    break
                try:
                    value = rollout(
                        root.searchId, [ci], your_index, search_step, max_steps
                    )
                except Exception:
                    # A first move we cannot even simulate is not trustworthy, so
                    # score it as a loss rather than dropping it; that also keeps
                    # the sample counts equal across candidates.
                    value = ev.LOSS
                finally:
                    try:
                        search_release(root.searchId)
                    except Exception:
                        pass
                totals[ci] += value
                counts[ci] += 1
    finally:
        try:
            search_end()
        except Exception:
            pass

    scored = [(totals[i] / counts[i], -i, i) for i in range(n) if counts[i] > 0]
    if not scored:
        return None
    return [max(scored)[2]]
