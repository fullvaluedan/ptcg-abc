"""U5 part 2: search_* rollout driver, value, time budget, and the search agent.

These cover the unit's remaining test scenarios: rollouts reach a terminal result
through search_step, argmax selection is stable under a fixed seed, the agent
degrades to the heuristic when the forward model raises, total thinking time stays
bounded by the bank, and the agent never returns an illegal move over a full
match. agent_baseline is imported at module load (before make_env) to avoid a
namespace-package collision with kaggle's bundled lux agents module.
"""
import random
from pathlib import Path

import agents.agent_baseline as baseline
import agents.agent_search as agent_search
from search import eval as ev
from search import rollout
from search.determinize import determinize
from search.timebudget import HARD_BANK, SAFETY_RESERVE, SOFT_CAP, TimeBudget

ROOT = Path(__file__).resolve().parents[1]


def _deck():
    ids = [int(x) for x in (ROOT / "decks" / "baseline.csv").read_text().split("\n") if x.strip()]
    return ids[:60]


# --- eval.py -----------------------------------------------------------------

def test_terminal_value_maps_results():
    assert ev.terminal_value(-1, 0) is None      # ongoing
    assert ev.terminal_value(0, 0) == ev.WIN      # we are player 0 and won
    assert ev.terminal_value(1, 0) == ev.LOSS     # opponent won
    assert ev.terminal_value(2, 0) == ev.DRAW     # draw


def test_shaped_value_prefers_taking_prizes():
    # We (index 0) have fewer prizes left, so we are closer to winning: positive.
    state = {"result": -1, "players": [{"prize": [None, None]},
                                       {"prize": [None] * 6}]}
    good = ev.shaped_value(state, 0)
    assert 0 < good <= ev.PRIZE_SHAPING
    # Mirror it: the opponent is ahead, so our value is the negation.
    assert ev.shaped_value(state, 1) == -good


def test_shaped_value_returns_terminal_when_decided():
    state = {"result": 0, "players": [{"prize": [None] * 6}, {"prize": []}]}
    assert ev.shaped_value(state, 0) == ev.WIN


# --- timebudget.py -----------------------------------------------------------

def test_budget_respects_soft_cap_and_shrinks():
    b = TimeBudget(hard_bank=100.0, soft_cap=0.5)
    assert b.allot() == 0.5                 # soft cap binds while the bank is full
    b.record(100.0)                          # spend the whole bank
    assert b.allot() == 0.0                  # nothing left to commit
    assert b.exhausted


def test_budget_reserve_fraction_binds_when_bank_low():
    b = TimeBudget(hard_bank=100.0, soft_cap=10.0)
    b.record(98.0)
    # remaining 2.0, reserve fraction 0.25 -> 0.5, which is below the 10.0 cap.
    assert b.allot() == 0.5


def test_default_hard_bank_under_real_ceiling():
    assert HARD_BANK < 600.0


def test_default_soft_cap_samples_more_worlds():
    # The default per-move cap was raised to use more of the otherwise idle 600s
    # bank: each determinized rollout runs to terminal, so a tiny cap bought about
    # one hidden-world sample per decision and starved the variance penalty and
    # field prior (both need several worlds). At a full bank allot returns the full
    # cap, so a decision may sample proportionally more worlds than the old 0.5s.
    assert SOFT_CAP >= 2.0
    assert TimeBudget().allot() == SOFT_CAP


def test_full_match_of_default_decisions_never_reaches_the_guard():
    # Raising the default cap must not risk a timeout. Spend the full default cap on
    # a very generous count of searchable decisions (far more than a real match's
    # ~20-40) and confirm cumulative time stays clear of the at-risk guard, so the
    # agent keeps searching without ever approaching the 540s hard bank.
    b = TimeBudget()
    for _ in range(120):
        b.record(b.allot())
    assert b.spent < HARD_BANK - SAFETY_RESERVE
    assert not b.at_risk


# --- rollout legality helper -------------------------------------------------

def test_legal_rejects_out_of_range_and_duplicates():
    sel = {"option": [0, 1, 2], "minCount": 1, "maxCount": 1}
    assert rollout._legal([1], sel)
    assert not rollout._legal([3], sel)       # out of range
    assert not rollout._legal([0, 0], sel)    # duplicate and wrong length
    assert not rollout._legal("x", sel)       # not a list


# --- robust candidate selection (variance-penalized argmax) -------------------

def test_best_candidate_zero_coef_is_mean_argmax():
    # coef 0 is the plain mean argmax, and ties break toward the lower index,
    # byte-identical to the prior max((mean, -i, i)) selection.
    assert rollout._best_candidate([0.5, 1.0], [0.0, 0.0], [1, 1], 0.0) == 1
    assert rollout._best_candidate([1.0, 1.0], [0.0, 0.0], [1, 1], 0.0) == 0


def test_best_candidate_penalizes_world_to_world_spread():
    # Both candidates average 0, but candidate 0 swings wildly across worlds
    # (values 1,1,-1,-1) while candidate 1 is steady (0.2,0.2,-0.2,-0.2). The mean
    # argmax breaks the tie to index 0; the robust penalty prefers the steady move.
    totals = [0.0, 0.0]
    sqtotals = [4.0, 0.16]
    counts = [4, 4]
    assert rollout._best_candidate(totals, sqtotals, counts, 0.0) == 0
    assert rollout._best_candidate(totals, sqtotals, counts, 0.25) == 1


def test_best_candidate_keeps_a_clear_winner():
    # Candidate 0 has a clearly higher mean (0.5) despite higher variance;
    # candidate 1 is a steady but weak 0.1. A modest coef must not override the
    # clear lead: 0.5 - 0.25*std still beats 0.1.
    totals = [2.0, 0.4]
    sqtotals = [4.0, 0.04]     # cand0 var 0.75 std ~0.866; cand1 var 0
    counts = [4, 4]
    assert rollout._best_candidate(totals, sqtotals, counts, 0.25) == 0


def test_best_candidate_none_when_nothing_sampled():
    assert rollout._best_candidate([0.0, 0.0], [0.0, 0.0], [0, 0], 0.25) is None


def test_agent_passes_robust_coef_to_search(monkeypatch):
    """The search agent forwards its PTCG_SEARCH_ROBUST coefficient to the driver."""
    from agents import heuristics

    sel = {
        "type": heuristics.SEL_MAIN, "minCount": 1, "maxCount": 1,
        "option": [{"type": heuristics.OPT_END}, {"type": heuristics.OPT_PLAY}],
    }
    state = {
        "yourIndex": 0,
        "players": [
            # A healthy bench (>= THIN_BENCH) so the early_collapse deferral does
            # not fire and search actually runs; this test is about the robust
            # coefficient reaching the driver, not the bench guard.
            {"active": [None], "bench": [{"id": 1}, {"id": 2}], "deckCount": 40,
             "prize": [None] * 5, "hand": []},
            {"active": [None], "bench": [], "prize": [None] * 5},
        ],
    }
    obs = {"select": sel, "current": state, "search_begin_input": "x"}

    captured = {}

    def spy(*a, **k):
        captured.update(k)
        return [0]

    monkeypatch.setattr(agent_search, "_BUDGET", TimeBudget(soft_cap=0.5))
    monkeypatch.setattr(agent_search.rollout, "search_api_available", lambda: True)
    monkeypatch.setattr(agent_search.rollout, "search_decision", spy)
    agent_search.agent(obs)
    assert captured.get("robust_coef") == agent_search._ROBUST_COEF


def test_agent_defers_to_heuristic_when_bench_is_thin(monkeypatch):
    """A thin bench skips search: the proven bench-development guard drives the turn.

    Recovered on-ladder search (ref 54218335) still lost 9 of 11 games to
    early_collapse because a searched MAIN move bypasses the heuristic's bench
    guard. On a thin bench the agent must NOT reach search_decision and must
    return a legal heuristic move instead, transplanting the guard into search.
    """
    from agents import heuristics

    sel = {
        "type": heuristics.SEL_MAIN, "minCount": 1, "maxCount": 1,
        "option": [{"type": heuristics.OPT_END}, {"type": heuristics.OPT_PLAY}],
    }
    state = {
        "yourIndex": 0,
        "players": [
            # Lone active, empty bench: the early_collapse danger zone.
            {"active": [None], "bench": [], "deckCount": 40,
             "prize": [None] * 5, "hand": []},
            {"active": [None], "bench": [], "prize": [None] * 5},
        ],
    }
    obs = {"select": sel, "current": state, "search_begin_input": "x"}
    assert heuristics._bench_is_thin(obs) is True

    def tracker(*a, **k):
        raise AssertionError("search must not run on a thin bench")

    monkeypatch.setattr(agent_search, "_BUDGET", TimeBudget(soft_cap=0.5))
    monkeypatch.setattr(agent_search.rollout, "search_api_available", lambda: True)
    monkeypatch.setattr(agent_search.rollout, "search_decision", tracker)
    move = agent_search.agent(obs)
    assert agent_search._is_legal(move, sel)


# --- integration: capture a real MAIN observation ----------------------------

def _capture_main_obs(attempts=8):
    from ptcg_agent.engine import make_env

    captured = {}

    def capturing(obs):
        sel = obs.get("select")
        if (
            "obs" not in captured
            and sel is not None
            and sel.get("type") == 0
            and sel.get("maxCount", 1) == 1
            and len(sel.get("option", [])) > 1
            and obs.get("search_begin_input")
            and (obs.get("current") or {}).get("turn", 0) >= 3
        ):
            captured["obs"] = obs
        return baseline.agent(obs)

    # The engine and the random opponent are stochastic, so an occasional game
    # never reaches a turn>=3 MAIN decision with more than one option (a quick
    # mulligan-heavy or short game). Replay fresh games until one yields a
    # capturable observation, so the capture does not flake under a shuffled
    # global RNG seed (pytest-randomly).
    for _ in range(attempts):
        make_env().run([capturing, "random"])
        if "obs" in captured:
            break
    return captured.get("obs")


# Test scenario: rollouts reach a terminal result and the driver returns a legal
# single first move. The determinization sampler is reproducible under a fixed
# seed (asserted directly), but the argmax over rollouts is not, because the
# native forward model flips coins from its own unseeded RNG; the agent only
# relies on the mean over many determinizations, not on a single reproducible run.
def test_search_decision_returns_legal_move_and_reproducible_sampling():
    obs = _capture_main_obs()
    assert obs is not None, "failed to capture a mid-game MAIN observation"

    n = len(obs["select"]["option"])
    move = rollout.search_decision(
        obs, _deck(), budget_seconds=1e9, rng=random.Random(42),
        determinize=determinize, max_determinizations=3,
        clock=lambda: 0.0,
    )
    assert move is not None
    assert isinstance(move, list) and len(move) == 1 and 0 <= move[0] < n

    # The hidden-state sampling itself is deterministic given the seed.
    s1 = determinize(obs, _deck(), random.Random(7))
    s2 = determinize(obs, _deck(), random.Random(7))
    assert s1 == s2


# Test scenario: the agent degrades to the heuristic if the search layer raises,
# and still returns a legal move.
def test_agent_falls_back_to_heuristic_on_search_error(monkeypatch):
    obs = _capture_main_obs()
    assert obs is not None

    def boom(*a, **k):
        raise RuntimeError("forward model unavailable")

    monkeypatch.setattr(agent_search.rollout, "search_decision", boom)
    move = agent_search.agent(obs)
    sel = obs["select"]
    assert agent_search._is_legal(move, sel)


# Test scenario: deck selection returns the 60-card deck unchanged.
def test_agent_returns_deck_at_selection():
    move = agent_search.agent({"select": None})
    assert len(move) == 60


# --- forward-model availability probe ----------------------------------------
# On the ladder `import cg.api` resolved a module that carries card data (so the
# heuristic plays) but NOT the search_* forward model, so determinized search was
# inert. We now force-load our OWN bundled cg package under a private name, which
# carries the wrappers and its own native lib, so search recovers even under a
# shadowed top-level cg.api. search_api_available reports whether a forward model
# is reachable at all; the agent gates search on it.

def _clear_forward_caches():
    # Guard each clear: tests may monkeypatch these to plain functions (no cache).
    for fn in (
        rollout.search_api_available,
        rollout._resolve_api,
        rollout._forward_api,
        rollout._cg,
    ):
        clear = getattr(fn, "cache_clear", None)
        if clear is not None:
            clear()


def _stub_forward_module():
    import types

    m = types.ModuleType("_stub_forward")
    for name in rollout._SEARCH_FUNCS:
        setattr(m, name, lambda *a, **k: None)
    return m


def test_search_api_available_true_with_full_cg():
    _clear_forward_caches()
    # The repo's bundled cg package exposes the full forward model.
    assert rollout.search_api_available() is True
    _clear_forward_caches()


def test_resolve_prefers_ambient_and_skips_bundled_load(monkeypatch):
    # When the ambient cg.api already exposes the forward model (self-play, local,
    # and any match where our bundled cg IS the top-level cg), the resolver must use
    # it and NEVER force-load a second native instance (double GameInitialize would
    # fault; see KTD4).
    called = {"n": 0}

    def boom():
        called["n"] += 1
        raise AssertionError("_forward_api must not run when ambient cg.api is full")

    monkeypatch.setattr(rollout, "_forward_api", boom)
    _clear_forward_caches()
    assert rollout.search_api_available() is True
    assert called["n"] == 0
    _clear_forward_caches()


def test_resolve_falls_back_to_bundled_when_shadowed(monkeypatch):
    import sys
    import types

    # Mimic the ladder condition: the ambient cg.api carries card data but NOT the
    # forward model. The resolver must fall back to our force-loaded bundled package
    # (stubbed here so the test does not trigger a real second native load), so the
    # probe reports True and _cg returns callables from that fallback module.
    stub = types.ModuleType("cg.api")
    stub.all_card_data = lambda: []
    stub.all_attack = lambda: []
    monkeypatch.setitem(sys.modules, "cg.api", stub)
    fake = _stub_forward_module()
    monkeypatch.setattr(rollout, "_forward_api", lambda: fake)

    _clear_forward_caches()
    assert rollout.search_api_available() is True
    assert rollout._resolve_api() is fake
    assert all(callable(f) for f in rollout._cg())
    _clear_forward_caches()


def test_bundled_cg_dir_found_without_module_file():
    # The grader execs main.py without a module __file__. The bundled-package
    # locator must still resolve our cg/ via cwd or sys.path, or the shadowed-ladder
    # recovery could never fire at match time.
    g = rollout.__dict__
    saved = g.pop("__file__", None)
    try:
        found = rollout._bundled_cg_dir()
    finally:
        if saved is not None:
            g["__file__"] = saved
    assert found is not None
    assert (found / "api.py").exists() and (found / "sim.py").exists()


def test_forward_api_loads_a_separate_native_instance(tmp_path, monkeypatch):
    # The crux of the shadowed-ladder recovery: force-loading our OWN bundled cg
    # from its own path is a SEPARATE native instance from the engine's, so its
    # one-time GameInitialize is a first call and does not collide (KTD4). Copy the
    # bundled cg to a distinct path (the match-time condition: our cg lives at a
    # different path than the grader's) and drive the real _forward_api loader
    # against it, proving a working forward model loads alongside the already
    # initialized ambient one.
    import shutil
    import sys

    src = rollout._bundled_cg_dir()
    assert src is not None
    dest = tmp_path / "cg"
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__"))

    # Isolate from the real private module so this load is genuinely fresh and does
    # not leave the production name pointing at the temp copy.
    saved = {k: v for k, v in sys.modules.items() if k.startswith(rollout._PRIV_CG_NAME)}
    for k in saved:
        del sys.modules[k]
    monkeypatch.setattr(rollout, "_bundled_cg_dir", lambda: dest)
    rollout._forward_api.cache_clear()
    try:
        api = rollout._forward_api()
        assert api is not None
        assert all(hasattr(api, name) for name in rollout._SEARCH_FUNCS)
        # The separate native lib actually initialized (card DB is readable).
        assert len(api.all_card_data()) > 0
    finally:
        for k in [k for k in sys.modules if k.startswith(rollout._PRIV_CG_NAME)]:
            del sys.modules[k]
        sys.modules.update(saved)
        rollout._forward_api.cache_clear()


def test_forward_api_purges_stale_module_on_validation_failure(tmp_path, monkeypatch):
    # If a force-loaded cg package loads but lacks the search_* wrappers, it must be
    # purged from sys.modules so a later (cache-cleared) retry re-execs from disk
    # rather than returning the stale module. Build a fake cg/ whose api.py defines
    # none of the wrappers.
    import sys

    fake = tmp_path / "cg"
    fake.mkdir()
    (fake / "__init__.py").write_text("")
    (fake / "sim.py").write_text("lib = object()\n")
    (fake / "api.py").write_text("# no search_* wrappers here\nvalue = 1\n")

    monkeypatch.setattr(rollout, "_bundled_cg_dir", lambda: fake)
    saved = {k: v for k, v in sys.modules.items() if k.startswith(rollout._PRIV_CG_NAME)}
    for k in saved:
        del sys.modules[k]
    rollout._forward_api.cache_clear()
    try:
        assert rollout._forward_api() is None
        # No _ptcg_forward_cg* entries should linger.
        assert not any(k.startswith(rollout._PRIV_CG_NAME) for k in sys.modules)
    finally:
        for k in [k for k in sys.modules if k.startswith(rollout._PRIV_CG_NAME)]:
            del sys.modules[k]
        sys.modules.update(saved)
        rollout._forward_api.cache_clear()


def test_search_api_available_false_without_bundled_package(monkeypatch):
    import sys
    import types

    # No bundled package to force-load AND the ambient cg.api lacks the forward
    # model: search is genuinely unavailable and the probe reports False (the agent
    # then stays on the heuristic, never paying a per-decision ImportError).
    monkeypatch.setattr(rollout, "_forward_api", lambda: None)
    stub = types.ModuleType("cg.api")
    stub.all_card_data = lambda: []
    stub.all_attack = lambda: []
    monkeypatch.setitem(sys.modules, "cg.api", stub)

    _clear_forward_caches()
    assert rollout.search_api_available() is False
    _clear_forward_caches()


def test_agent_skips_search_when_forward_model_absent(monkeypatch):
    obs = _capture_main_obs()
    assert obs is not None

    # Force the inert-ladder condition and prove search_decision is never reached,
    # yet the agent still returns a legal heuristic move (no swallowed error path).
    monkeypatch.setattr(rollout, "search_api_available", lambda: False)
    called = {"n": 0}

    def tracker(*a, **k):
        called["n"] += 1
        raise AssertionError("search_decision must not run when the API is absent")

    monkeypatch.setattr(agent_search.rollout, "search_decision", tracker)
    move = agent_search.agent(obs)
    assert called["n"] == 0
    assert agent_search._is_legal(move, obs["select"])


# Test scenario: the agent never returns an illegal move across a full match and
# the result is a clean win or loss (run with a tight budget for speed).
def test_search_agent_completes_match(monkeypatch):
    from ptcg_agent.engine import make_env

    # Reset the shared module budget and shrink the per-move cap so the match runs
    # quickly; each gauntlet match gets its own process and so its own budget.
    monkeypatch.setattr(agent_search, "_BUDGET", TimeBudget(soft_cap=0.02))
    illegal = {"count": 0}

    def guarded(obs):
        move = agent_search.agent(obs)
        sel = obs.get("select")
        if sel is not None and not agent_search._is_legal(move, sel):
            illegal["count"] += 1
        return move

    env = make_env()
    env.run([guarded, "random"])
    reward = env.steps[-1][0]["reward"]
    assert reward in (-1, 0, 1)
    assert illegal["count"] == 0
