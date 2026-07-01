"""The CEM tunable-parameter surface (plan U6): schema, env mapping, wiring.

tools/weight_space.py names the pilot-plus-leaf-eval weight vector the optimizer
searches; agents/heuristics.py and search/eval.py read the matching PTCG_W_*
overrides at import. These tests pin the three properties the optimizer relies on:

  1. the schema's defaults never drift from the shipped module constants (else a
     tuned vector's "default" element would silently change behavior),
  2. the default vector maps to an EMPTY override set, so an un-tuned build stays
     byte-identical (the ship guarantee the boolean levers already hold), and
  3. a baked override actually reaches the shipped constant at import (the same
     clean-runtime contract test_build_submission_env pins for the flags).
"""
import importlib
import os

from tools import weight_space as ws


def _constants_with(env: dict, module_name: str, attrs):
    """Reload a module with env vars set, snapshot attrs, then restore and reload.

    Mirrors test_build_submission_env: set the PTCG_W_* keys, reload so the module
    body re-reads os.environ, capture the requested constants WHILE the env is
    still set (reload mutates the module object in place, so the values must be
    read before the restore reload resets them), then restore the prior
    environment and reload again so later tests see the shipped defaults. Returns
    the captured {attr: value} snapshot.
    """
    module = importlib.import_module(module_name)
    prev = {k: os.environ.get(k) for k in env}
    try:
        for k, v in env.items():
            os.environ[k] = v
        importlib.reload(module)
        return {a: getattr(module, a) for a in attrs}
    finally:
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        importlib.reload(module)


# --- schema shape ---------------------------------------------------------

def test_keys_are_unique_prefixed_env_vars():
    keys = ws.keys()
    assert len(keys) == len(set(keys)), "duplicate env key in PARAM_SPACE"
    assert all(k.startswith("PTCG_W_") for k in keys)


def test_defaults_and_bounds_align():
    defaults = ws.defaults()
    bounds = ws.bounds()
    assert len(defaults) == len(bounds) == len(ws.PARAM_SPACE)
    for value, (low, high) in zip(defaults, bounds):
        assert low <= value <= high, f"default {value} outside [{low}, {high}]"


def test_vector_size_is_in_the_planned_range():
    # KTD3 sizes the genome at 10 to 40 numbers; keep it inside that band.
    assert 10 <= len(ws.PARAM_SPACE) <= 40


# --- env mapping ----------------------------------------------------------

def test_default_vector_maps_to_empty_override():
    # The default vector is the shipped build: no PTCG_W_* baked, byte-identical.
    assert ws.vector_to_env(ws.defaults()) == {}


def test_vector_to_env_casts_int_knobs():
    # An int knob given a fractional sample must ship an integer string, never
    # "3.7", or the shipped int() cast would reject it or truncate surprisingly.
    vec = list(ws.defaults())
    idx = ws.keys().index("PTCG_W_THIN_BENCH")
    vec[idx] = 3.7
    env = ws.vector_to_env(vec)
    assert env["PTCG_W_THIN_BENCH"] == "3"


def test_vector_to_env_clamps_out_of_bounds():
    vec = list(ws.defaults())
    idx = ws.keys().index("PTCG_W_RETREAT_HP_RATIO")
    vec[idx] = 99.0  # far above the high bound
    env = ws.vector_to_env(vec)
    low, high = ws.bounds()[idx]
    assert float(env["PTCG_W_RETREAT_HP_RATIO"]) == high


def test_clamp_is_elementwise_into_bounds():
    lows = [b[0] for b in ws.bounds()]
    highs = [b[1] for b in ws.bounds()]
    below = ws.clamp([lo - 100 for lo in lows])
    above = ws.clamp([hi + 100 for hi in highs])
    assert below == lows
    assert above == highs


# --- no drift: schema defaults mirror the shipped constants ---------------

def test_pilot_defaults_match_heuristics_constants():
    from agents import heuristics

    importlib.reload(heuristics)  # ensure a clean-env read of the constants
    expected = {
        "PTCG_W_THIN_BENCH": heuristics.THIN_BENCH,
        "PTCG_W_RETREAT_HP_RATIO": heuristics.RETREAT_HP_RATIO,
        "PTCG_W_DECKOUT_THRESHOLD": heuristics.DECKOUT_THRESHOLD,
        "PTCG_W_DRAW_CONSERVE_THRESHOLD": heuristics.DRAW_CONSERVE_THRESHOLD,
    }
    space = {k: d for k, d, *_ in ws.PARAM_SPACE}
    for key, live in expected.items():
        assert space[key] == live, f"{key} default drifted from heuristics"


def test_eval_defaults_match_eval_constants():
    from search import eval as ev

    importlib.reload(ev)
    expected = {
        "PTCG_W_PRIZE_SHAPING": ev.PRIZE_SHAPING,
        "PTCG_W_HP_SHAPING": ev.HP_SHAPING,
        "PTCG_W_ACTIVE_HP_WEIGHT": ev.ACTIVE_HP_WEIGHT,
        "PTCG_W_BOARD_SHAPING": ev.BOARD_SHAPING,
        "PTCG_W_ENERGY_SHAPING": ev.ENERGY_SHAPING,
        "PTCG_W_BENCH_FLOOR_SHAPING": ev.BENCH_FLOOR_SHAPING,
        "PTCG_W_BENCH_TARGET": ev.BENCH_TARGET,
    }
    space = {k: d for k, d, *_ in ws.PARAM_SPACE}
    for key, live in expected.items():
        assert space[key] == live, f"{key} default drifted from eval"


# --- wiring: a baked override reaches the shipped constant -----------------

def test_env_override_reaches_pilot_constant():
    snap = _constants_with(
        {"PTCG_W_THIN_BENCH": "4"}, "agents.heuristics", ["THIN_BENCH"]
    )
    assert snap["THIN_BENCH"] == 4
    # restored to the shipped default after the finally block reloads
    from agents import heuristics
    assert heuristics.THIN_BENCH == 2


def test_env_override_reaches_eval_constant():
    snap = _constants_with(
        {"PTCG_W_BENCH_TARGET": "5"}, "search.eval", ["BENCH_TARGET"]
    )
    assert snap["BENCH_TARGET"] == 5
    from search import eval as ev
    assert ev.BENCH_TARGET == 3


def test_malformed_env_falls_back_to_default_without_raising():
    snap = _constants_with(
        {"PTCG_W_THIN_BENCH": "not-a-number"}, "agents.heuristics", ["THIN_BENCH"]
    )
    assert snap["THIN_BENCH"] == 2
