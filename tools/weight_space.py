"""Canonical tunable-parameter space for the CEM self-improvement optimizer.

OFFLINE ONLY. This module is never bundled into a submission; it names the
pilot-plus-leaf-eval constants that the Cross-Entropy-Method optimizer
(tools/cem_tune.py) searches over, and maps a weight vector to the PTCG_W_*
environment overrides that the shipped modules read at import
(agents/heuristics.py, search/eval.py) and that tools/build_submission.py --env
bakes into a tarball's clean-runtime prelude.

Split of concerns (KTD1, KTD3, KTD6): the shipped modules each read their own
PTCG_W_* keys directly, exactly like the boolean PTCG_* levers, so the ship path
takes on no new import and an un-tuned build stays byte-identical. This module is
the single place that enumerates the whole vector, its bounds, and the env
mapping, so the optimizer has one genome to evolve and the developer has one list
to reason about. The defaults here MUST mirror the constants hard-coded in the
shipped modules; tests/test_weight_space.py asserts they never drift.

Each entry is (env_key, default, low, high, cast). `default` mirrors the shipped
constant; `low`/`high` bound the CEM search; `cast` rounds a continuous CEM
sample to the type the constant needs (an int knob like the bench width, a float
knob like the retreat ratio and the eval shaping weights).
"""
from __future__ import annotations

# (env_key, default, low, high, cast)
PARAM_SPACE = (
    # Pilot: agents/heuristics.py. These govern the deployable player and are the
    # load-bearing knobs, because the ladder judges the pilot (KTD1).
    ("PTCG_W_THIN_BENCH", 2, 1, 4, int),
    ("PTCG_W_RETREAT_HP_RATIO", 0.34, 0.1, 0.6, float),
    ("PTCG_W_DECKOUT_THRESHOLD", 5, 2, 12, int),
    ("PTCG_W_DRAW_CONSERVE_THRESHOLD", 8, 3, 15, int),
    # Leaf eval: search/eval.py. These tune the offline teacher's leaf value
    # (KTD3); they shape label generation and validation, not the shipped pilot
    # path, so they are searched too but are not what the live rating turns on.
    ("PTCG_W_PRIZE_SHAPING", 0.5, 0.2, 0.9, float),
    ("PTCG_W_HP_SHAPING", 0.15, 0.0, 0.4, float),
    ("PTCG_W_ACTIVE_HP_WEIGHT", 0.6, 0.3, 0.9, float),
    ("PTCG_W_BOARD_SHAPING", 0.05, 0.0, 0.2, float),
    ("PTCG_W_ENERGY_SHAPING", 0.05, 0.0, 0.2, float),
    ("PTCG_W_BENCH_FLOOR_SHAPING", 0.08, 0.0, 0.2, float),
    ("PTCG_W_BENCH_TARGET", 3, 1, 5, int),
)


def keys() -> list:
    """The env keys in PARAM_SPACE order (the vector's axis labels)."""
    return [p[0] for p in PARAM_SPACE]


def defaults() -> list:
    """The default weight vector, in PARAM_SPACE order.

    This is the shipped configuration: passed through vector_to_env it yields an
    empty override map (see vector_to_env), so it names the byte-identical build.
    """
    return [p[1] for p in PARAM_SPACE]


def bounds() -> list:
    """(low, high) pairs in PARAM_SPACE order, for the CEM sampler to clamp to."""
    return [(p[2], p[3]) for p in PARAM_SPACE]


def clamp(vector) -> list:
    """Clamp a raw vector element-wise into the parameter bounds (no casting)."""
    out = []
    for value, (_key, _default, low, high, _cast) in zip(vector, PARAM_SPACE):
        out.append(min(high, max(low, value)))
    return out


def vector_to_env(vector) -> dict:
    """Map a weight vector to the {PTCG_W_*: "value"} overrides to bake or inject.

    Each element is clamped into bounds, cast to the constant's type (so an int
    knob never ships a fractional string), and stringified. Only entries that
    differ from the shipped default are emitted, so the default vector yields an
    empty map and the build stays byte-identical (build_submission skips the
    prelude on an empty env). The optimizer feeds the result to
    build_submission.py --env for the ladder A/B, or into os.environ for an
    offline gauntlet; the shipped modules read the same keys back at import.
    """
    env = {}
    for value, (key, default, low, high, cast) in zip(vector, PARAM_SPACE):
        cast_value = cast(min(high, max(low, value)))
        if cast_value != cast(default):
            env[key] = str(cast_value)
    return env
