"""The CEM self-improvement optimizer (plan U6): core math, anti-collapse, wiring.

tools/cem_tune.py searches the weight_space.PARAM_SPACE vector with the
Cross-Entropy Method and stages the winner as a build_submission --env override.
These tests pin the properties the engine relies on, WITHOUT the engine or the
dataset (fitness is a toy objective or a canned runner), so the whole suite stays
fast and deterministic:

  1. the CEM core converges to a known optimum on a solvable objective,
  2. the NON-NEGOTIABLE injected variance keeps the sampling std from collapsing,
     and with it OFF the std provably collapses (why the trick is mandatory),
  3. normalize/denormalize and sampling stay inside the parameter bounds,
  4. the two-signal fitness combines and tolerates a missing half, and
  5. a candidate's weights reach the evaluator env, and a run stages an env map.
"""
import json

import numpy as np
import pytest

from tools import cem_tune as ct
from tools import weight_space as ws


# --- normalize / denormalize / sampling stay in bounds --------------------

def test_normalize_denormalize_roundtrips_the_defaults():
    back = ct.denormalize(ct.normalize(ws.defaults()))
    assert np.allclose(back, np.array(ws.defaults(), dtype=float))


def test_defaults_normalize_inside_the_unit_box():
    unit = ct.normalize(ws.defaults())
    assert np.all(unit >= 0.0) and np.all(unit <= 1.0)


def test_denormalize_clips_out_of_box_input_to_bounds():
    low, high = ct._bounds_arrays()
    assert np.allclose(ct.denormalize(np.full(len(ws.PARAM_SPACE), -5.0)), low)
    assert np.allclose(ct.denormalize(np.full(len(ws.PARAM_SPACE), 5.0)), high)


def test_sample_population_stays_in_the_unit_box():
    rng = np.random.default_rng(0)
    dim = len(ws.PARAM_SPACE)
    pop = ct.sample_population(np.full(dim, 0.5), np.full(dim, 0.5), 200, rng)
    assert pop.shape == (200, dim)
    assert np.all(pop >= 0.0) and np.all(pop <= 1.0)


# --- a toy objective the optimizer should solve ---------------------------

def _distance_fitness(target):
    """Fitness that peaks at `target`, measured in normalized space so every dim
    weighs equally regardless of its real range."""
    t_unit = ct.normalize(target)

    def fitness(vector):
        u = ct.normalize(vector)
        return -float(np.sum((u - t_unit) ** 2))

    return fitness


def test_cem_converges_to_a_known_optimum():
    # A target away from the defaults, inside bounds on every dim. Derived from the
    # genome (60% of each dim's range) so it tracks PARAM_SPACE growth automatically.
    target = [low + 0.6 * (high - low) for _k, _d, low, high, _c in ws.PARAM_SPACE]
    assert len(target) == len(ws.PARAM_SPACE)
    cfg = ct.CEMConfig(
        population=40, elite=8, iterations=30, init_std=0.3,
        injected_variance=0.02, seed=1,
    )
    result = ct.cem_optimize(_distance_fitness(target), config=cfg)
    got = ct.normalize(result["best"]["vector"])
    want = ct.normalize(target)
    # Best-seen sample lands close to the optimum in normalized space.
    assert np.max(np.abs(got - want)) < 0.12


def test_reproducible_with_the_same_seed():
    target = list(ws.defaults())
    target[0] = 4
    cfg = ct.CEMConfig(population=30, elite=6, iterations=10, seed=7)
    a = ct.cem_optimize(_distance_fitness(target), config=cfg)
    b = ct.cem_optimize(_distance_fitness(target), config=cfg)
    assert a["best"]["vector"] == b["best"]["vector"]
    assert a["best"]["fitness"] == b["best"]["fitness"]


# --- injected variance is the anti-collapse mechanism ---------------------

def test_injected_variance_keeps_the_std_from_collapsing():
    target = list(ws.defaults())
    cfg = ct.CEMConfig(
        population=40, elite=8, iterations=25, init_std=0.3,
        injected_variance=0.05, seed=2,
    )
    result = ct.cem_optimize(_distance_fitness(target), config=cfg)
    # Every iteration's mean std is at least the injected floor (elite std >= 0,
    # plus the floor), so the search never freezes.
    assert min(rec["std_mean"] for rec in result["history"]) >= 0.05 - 1e-9


def test_without_injection_the_std_collapses():
    # Same objective, floor OFF: the elites agree and the std shrinks toward zero,
    # the premature-convergence failure the floor exists to prevent.
    target = list(ws.defaults())
    cfg = ct.CEMConfig(
        population=40, elite=8, iterations=25, init_std=0.3,
        injected_variance=0.0, seed=2,
    )
    result = ct.cem_optimize(_distance_fitness(target), config=cfg)
    final_std = result["history"][-1]["std_mean"]
    assert final_std < 0.02, f"expected collapse, std stayed {final_std}"


def test_update_distribution_reinflates_by_the_floor():
    dim = len(ws.PARAM_SPACE)
    # Identical elites => zero elite std => returned std equals the floor exactly.
    elites = np.tile(np.full(dim, 0.5), (5, 1))
    mean, std = ct.update_distribution(elites, injected_variance=0.07)
    assert np.allclose(mean, 0.5)
    assert np.allclose(std, 0.07)


# --- staged output: a run yields a bakeable env map -----------------------

def test_optimize_stages_a_bakeable_env_map():
    target = list(ws.defaults())
    target[ws.keys().index("PTCG_W_THIN_BENCH")] = 4
    cfg = ct.CEMConfig(population=40, elite=8, iterations=25, init_std=0.3, seed=3)
    result = ct.cem_optimize(_distance_fitness(target), config=cfg)
    env = result["best"]["env"]
    # The staged env is exactly vector_to_env of the winning vector: only non
    # default keys, all PTCG_W_* strings, ready for build_submission --env.
    assert env == ws.vector_to_env(result["best"]["vector"])
    assert all(k.startswith("PTCG_W_") and isinstance(v, str) for k, v in env.items())
    # It found the tuned knob (pushed the bench width up off the default of 2).
    assert int(env.get("PTCG_W_THIN_BENCH", "2")) >= 3


def test_non_finite_fitness_is_never_selected():
    # A fitness that returns -inf everywhere leaves the default as the best vector.
    result = ct.cem_optimize(
        lambda v: float("-inf"),
        config=ct.CEMConfig(population=10, elite=3, iterations=3, seed=0),
    )
    assert result["best"]["vector"] == list(ws.defaults())
    assert result["best"]["env"] == {}


# --- two-signal fitness ---------------------------------------------------

def test_aggregate_fitness_combines_both_signals():
    # Equal default weights average the two [0, 1] signals.
    assert ct.aggregate_fitness(0.6, 0.4) == 0.5


def test_aggregate_fitness_drops_a_missing_half():
    assert ct.aggregate_fitness(0.6, None, w_pool=0.5, w_val=0.5) == 0.3
    assert ct.aggregate_fitness(None, 0.8, w_pool=0.5, w_val=0.5) == 0.4


def test_aggregate_fitness_no_evidence_is_worst():
    assert ct.aggregate_fitness(None, None) == float("-inf")


# --- evaluator wiring: weights reach the child env, output is parsed -------

def test_evaluate_vector_bakes_weights_into_the_child_env():
    captured = {}

    def fake_runner(env, payload, python):
        captured["env"] = env
        captured["payload"] = payload
        return json.dumps({"win_rate": 0.7, "agreement": 0.3})

    vec = list(ws.defaults())
    vec[ws.keys().index("PTCG_W_THIN_BENCH")] = 4
    fitness = ct.evaluate_vector(vec, {"pool_matches": 10}, runner=fake_runner)
    # The candidate's tuned knob is baked into the child env like a real build.
    assert captured["env"]["PTCG_W_THIN_BENCH"] == "4"
    # The spec is forwarded on stdin.
    assert json.loads(captured["payload"])["pool_matches"] == 10
    # Both signals folded with the default equal weights: 0.35 + 0.15.
    assert fitness == 0.5


def test_default_vector_bakes_no_overrides():
    captured = {}

    def fake_runner(env, payload, python):
        captured["env"] = env
        return json.dumps({"win_rate": 0.5, "agreement": 0.5})

    ct.evaluate_vector(list(ws.defaults()), {}, runner=fake_runner)
    # An un-tuned candidate adds nothing, so the child stays byte-identical.
    assert all(not k.startswith("PTCG_W_") for k in captured["env"])


def test_evaluate_vector_ignores_stdout_pollution_before_the_json():
    # A transitively-imported module (kaggle_environments' OpenSpiel loader) can
    # log INFO/WARNING lines to stdout ahead of _internal_evaluate's own print;
    # the real payload is always the LAST line.
    polluted = (
        "[kaggle_environments.envs.open_spiel_env.open_spiel_env] INFO: loaded\n"
        "Loading environment werewolf failed: No module named 'litellm'\n"
        + json.dumps({"win_rate": 0.6, "agreement": None})
    )

    def fake_runner(env, payload, python):
        return polluted

    fitness = ct.evaluate_vector(list(ws.defaults()), {}, runner=fake_runner)
    assert fitness == 0.3


def test_evaluate_vector_raises_when_no_line_parses():
    def fake_runner(env, payload, python):
        return "not json\nstill not json\n"

    with pytest.raises(ValueError):
        ct.evaluate_vector(list(ws.defaults()), {}, runner=fake_runner)


def test_subprocess_fitness_maps_errors_to_worst_score():
    def boom(env, payload, python):
        raise RuntimeError("subprocess died")

    fitness = ct.subprocess_fitness({"pool_matches": 1})
    # Patch the module runner the closure ultimately calls.
    import tools.cem_tune as mod

    orig = mod._run_evaluator
    mod._run_evaluator = boom
    try:
        assert fitness(list(ws.defaults())) == float("-inf")
    finally:
        mod._run_evaluator = orig


def test_internal_evaluate_skips_unrequested_signals():
    # No pool_matches and no replays: both halves skipped, both None, no engine.
    assert ct._internal_evaluate({}) == {"win_rate": None, "agreement": None}


def _stub_replay_channel(monkeypatch, split_map):
    """Canned load/score/split so the agreement branch runs without the engine.

    Returns the mutable dict the fake scorer records the labels it was handed in,
    so a test can assert exactly which episodes survived the split filter.
    """
    import analysis.move_ranking_validator as mrv
    import analysis.replay_trace as rt

    pairs = [("A", "1.json"), ("B", "2.json"), ("C", "3.json")]
    seen = {}

    def fake_score(passed, choose, teams):
        seen["labels"] = [label for _rep, label in passed]
        return {"agreement": 0.5}

    monkeypatch.setattr(mrv, "load_replays", lambda src, limit=None: list(pairs))
    monkeypatch.setattr(mrv, "score_replays", fake_score)
    monkeypatch.setattr(rt, "split_of", lambda label: split_map[label])
    return seen


def test_internal_evaluate_filters_replays_to_the_requested_split(monkeypatch):
    # Only the train-bucket episodes reach the scorer; the held-out test bucket
    # (2.json here) is dropped so a tuning run never fits on it.
    seen = _stub_replay_channel(
        monkeypatch,
        {"1.json": "train", "2.json": "test", "3.json": "train"},
    )
    out = ct._internal_evaluate({"replays": "x", "split": "train"})
    assert out == {"win_rate": None, "agreement": 0.5}
    assert seen["labels"] == ["1.json", "3.json"]


def test_internal_evaluate_scores_all_replays_when_split_is_all(monkeypatch):
    # split "all" (or absent) applies no filter: every loaded episode is scored.
    seen = _stub_replay_channel(
        monkeypatch,
        {"1.json": "train", "2.json": "test", "3.json": "train"},
    )
    out = ct._internal_evaluate({"replays": "x", "split": "all"})
    assert out["agreement"] == 0.5
    assert seen["labels"] == ["1.json", "2.json", "3.json"]
