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

import importlib
import importlib.util
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
    # The grader has no __file__ but bundles cg/ at the top level, so the import
    # above already returned; guard the fallback so it never raises NameError.
    if "__file__" not in globals():
        return
    here = Path(__file__).resolve()
    for parent in here.parents:
        for sub in ("data", "vendor"):
            if (parent / sub / "cg" / "api.py").exists():
                p = str(parent / sub)
                if p not in sys.path:
                    sys.path.insert(0, p)
                return


# The forward-model functions the determinized search needs on top of the card
# data (all_card_data, all_attack) the heuristic already uses.
_SEARCH_FUNCS = (
    "search_begin",
    "search_step",
    "search_end",
    "search_release",
    "to_observation_class",
)

# Private module name under which we force-load OUR OWN bundled cg package, so it
# can never collide with whatever the match-time engine registered as top-level
# `cg` in sys.modules.
_PRIV_CG_NAME = "_ptcg_forward_cg"


def _bundled_cg_dir() -> Path | None:
    """Locate our own bundled cg/ package directory on disk.

    In a submission cg/ sits beside main.py at the top level; in the repo it is
    data/cg (gitignored) or vendor/cg. We only accept a directory that carries
    both api.py (the Python forward-model wrappers) and sim.py (which loads our
    own native lib), so the package we force-load is self-contained.

    The grader execs main.py without a module __file__, so we cannot rely on it:
    we also scan the working directory, the known match-time agent root, and every
    sys.path entry. That lets the fallback find our top-level cg/ at match time,
    where `import cg.api` resolves to the engine's shadow instead.
    """
    roots: list[Path] = []
    if "__file__" in globals():
        roots.extend(Path(__file__).resolve().parents)
    try:
        roots.append(Path.cwd())
    except Exception:
        pass
    roots.append(Path("/kaggle_simulations/agent"))
    for entry in sys.path:
        if entry:
            try:
                roots.append(Path(entry))
            except Exception:
                continue
    seen: set[str] = set()
    for parent in roots:
        for cand in (parent / "cg", parent / "data" / "cg", parent / "vendor" / "cg"):
            key = str(cand)
            if key in seen:
                continue
            seen.add(key)
            try:
                if (cand / "api.py").exists() and (cand / "sim.py").exists():
                    return cand
            except Exception:
                continue
    return None


def _ambient_api():
    """The ambient `import cg.api` module IF it exposes the forward model.

    This is the module `from cg.api import ...` resolves to: our bundled cg in
    self-play and local runs, or whatever the match-time engine registered. Returns
    None when it lacks the search_* wrappers (the shadowed-ladder condition).
    """
    _ensure_cg_on_path()
    api = importlib.import_module("cg.api")
    if all(hasattr(api, name) for name in _SEARCH_FUNCS):
        return api
    return None


def _purge_private_cg() -> None:
    """Remove our force-loaded private cg package and all its submodules.

    A half-registered package (exec failed, or loaded but missing wrappers) would
    otherwise make the next `if _PRIV_CG_NAME not in sys.modules` skip a fresh load
    and hand back the stale module. Clear the parent and every submodule so a retry
    re-execs from disk.
    """
    for key in [k for k in sys.modules if k == _PRIV_CG_NAME or k.startswith(_PRIV_CG_NAME + ".")]:
        sys.modules.pop(key, None)


@lru_cache(maxsize=1)
def _forward_api():
    """Force-load our OWN bundled cg.api under a private name, as a fallback.

    Used only when the ambient cg.api lacks the forward model (the shadowed-ladder
    condition). Loading our bundled package by explicit path under a private module
    name binds search_* against our own cg.dll, independent of whatever the engine
    registered as top-level `cg`. Because our bundled native lib lives at our own
    path, it is a separate process instance from the engine's, so its one-time
    GameInitialize is a first call and does not collide with the engine's. Returns
    None (search then stays the heuristic fallback) if no self-contained bundled
    package can be loaded.

    NOTE: our sim.py runs GameInitialize once at import, and the native core is a
    process-global singleton (KTD4). We must NEVER force-load this when the ambient
    cg.api already IS our bundled package (same dll, already initialized), or the
    second GameInitialize faults. Callers must probe _ambient_api() first.
    """
    pkg_dir = _bundled_cg_dir()
    if pkg_dir is None:
        return None
    try:
        if _PRIV_CG_NAME not in sys.modules:
            spec = importlib.util.spec_from_file_location(
                _PRIV_CG_NAME,
                pkg_dir / "__init__.py",
                submodule_search_locations=[str(pkg_dir)],
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[_PRIV_CG_NAME] = module
            spec.loader.exec_module(module)
        api = importlib.import_module(f"{_PRIV_CG_NAME}.api")
    except Exception:
        _purge_private_cg()
        return None
    if not all(hasattr(api, name) for name in _SEARCH_FUNCS):
        # A package that loaded but lacks the wrappers is not usable; purge it so a
        # later cache-cleared retry re-execs from disk instead of returning this
        # stale module.
        _purge_private_cg()
        return None
    return api


@lru_cache(maxsize=1)
def _resolve_api():
    """Resolve a forward-model module, ambient first, bundled fallback second.

    Prefer the ambient cg.api whenever it exposes the forward model: that covers
    self-play, local runs, and any match where our bundled cg IS the top-level cg,
    with a single native instance and no double GameInitialize. Only when the
    ambient module lacks the wrappers (the shadowed-ladder condition ladder replays
    exposed) do we force-load our own bundled package as a separate native
    instance. Returns None when neither carries the forward model.
    """
    try:
        api = _ambient_api()
        if api is not None:
            return api
    except Exception:
        pass
    return _forward_api()


@lru_cache(maxsize=1)
def _cg():
    """The cg.api forward-model functions, resolved once."""
    api = _resolve_api()
    if api is None:
        # No forward model anywhere; surface a clear error (callers guard search on
        # search_api_available, so this only fires if that contract is bypassed).
        raise ImportError("no cg.api forward model (search_* functions) is reachable")
    return (
        api.search_begin,
        api.search_step,
        api.search_end,
        api.search_release,
        api.to_observation_class,
    )


@lru_cache(maxsize=1)
def search_api_available() -> bool:
    """True when a forward model with the search_* functions is reachable.

    The heuristic needs only card data (all_card_data, all_attack), which the
    match-time engine always provides, so the agent loads and plays regardless.
    Determinized search additionally needs the search_* forward model. Ladder
    replays showed `import cg.api` resolved a module WITHOUT those wrappers (every
    search decision drew about 0.02s from the 600s overage bank, the heuristic
    cost, never the per-move search budget), so search was inert. We now fall back
    to force-loading our OWN bundled package (its own wrappers and native lib) when
    the ambient cg.api is that stripped shadow, so this reports True whenever a
    working forward model can be reached. Never raises. The verification channel on
    the ladder is the overage-bank drawdown in the next replay: a working search
    shows about 0.5s draws instead of about 0.02s.
    """
    try:
        return _resolve_api() is not None
    except Exception:
        return False


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
            max_steps=ROLLOUT_MAX_STEPS, value_depth=None) -> float:
    """Play first_select from search_id, roll out, return our value.

    With value_depth None the rollout runs to a terminal result (the heuristic
    policy plus the real engine rules is a strong leaf evaluator). Set value_depth
    to cut the rollout off after that many policy selections and trust the board
    value function instead, trading rollout accuracy for more samples per decision.
    """
    cur = search_step(search_id, first_select)
    steps = 0
    for _ in range(max_steps):
        obs = cur.observation
        state = obs.current
        if state is not None:
            tv = ev.terminal_value(state.result, your_index)
            if tv is not None:
                return tv
            if value_depth is not None and steps >= value_depth:
                return ev.shaped_value(asdict(state), your_index)
        sel = obs.select
        if sel is None:
            break
        cur = search_step(cur.searchId, _policy(obs))
        steps += 1
    state = cur.observation.current
    if state is None:
        return ev.DRAW
    return ev.shaped_value(asdict(state), your_index)


def search_decision(obs, your_full_deck, budget_seconds, rng, determinize,
                    opponent_prior=None, max_steps=ROLLOUT_MAX_STEPS,
                    max_determinizations=None, clock=None, value_depth=None):
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
                        root.searchId, [ci], your_index, search_step, max_steps,
                        value_depth,
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
