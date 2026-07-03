"""Held-out KTD1/KTD4 gate for a CEM candidate (plan U83, LOOP_BRIEF L7 step c).

tools/cem_held_out_gate.py replays the hand computation every prior CEM verdict
(analysis/cem_run_prio.md, analysis/cem_run_prio_pooled.md) made by hand: score
the default vector and the tuned vector on the held-out 'test' split only, diff
their agreement, and require a STRICTLY POSITIVE delta to WIN (zero or negative
BLOCKS, matching the pooled run's own recorded verdict on a flat zero delta).
These tests use a canned runner (no engine, no real games), same style as
test_cem_tune.py's evaluator wiring tests.
"""
import json

import pytest

from tools import cem_held_out_gate as gate_mod
from tools import weight_space as ws


def _runner_for(agreements):
    """A fake evaluate_raw runner keyed by whether PTCG_W_* overrides are baked.

    `agreements` is (default_agreement, tuned_agreement); the default vector
    bakes no overrides (test_default_vector_bakes_no_overrides in
    test_cem_tune.py already pins that contract), so the fake runner tells the
    two calls apart the same way the real evaluator distinguishes candidates.
    """
    default_agreement, tuned_agreement = agreements

    def runner(env, payload, python):
        is_default = not any(k.startswith("PTCG_W_") for k in env)
        agreement = default_agreement if is_default else tuned_agreement
        return json.dumps({"win_rate": None, "agreement": agreement})

    return runner


def _tuned_vector():
    vec = list(ws.defaults())
    vec[ws.keys().index("PTCG_W_THIN_BENCH")] = 4
    return vec


# --- held_out_spec -----------------------------------------------------------

def test_held_out_spec_always_scores_the_test_split():
    spec = gate_mod.held_out_spec("some/path", is_teacher=True)
    assert spec["split"] == "test"
    assert spec["teacher_labels"] == "some/path"
    assert "replays" not in spec


def test_held_out_spec_replays_source():
    spec = gate_mod.held_out_spec("some/replays.zip", is_teacher=False)
    assert spec["replays"] == "some/replays.zip"
    assert "teacher_labels" not in spec


# --- gate: verdict logic -----------------------------------------------------

def test_gate_wins_on_a_strictly_positive_delta():
    runner = _runner_for((0.500, 0.600))
    result = gate_mod.gate(_tuned_vector(), "corpus/", runner=runner)
    assert result["default_agreement"] == 0.500
    assert result["tuned_agreement"] == 0.600
    assert result["delta"] == pytest.approx(0.100)
    assert result["verdict"] == gate_mod.WIN


def test_gate_blocks_on_exactly_zero_delta():
    # Pinned to the pooled run's real recorded verdict: 7/30 == 7/30 is flat
    # transfer, not evidence of improvement, so it BLOCKS rather than WINs.
    runner = _runner_for((0.2333, 0.2333))
    result = gate_mod.gate(_tuned_vector(), "corpus/", runner=runner)
    assert result["delta"] == 0.0
    assert result["verdict"] == gate_mod.BLOCKED


def test_gate_blocks_on_a_negative_delta():
    runner = _runner_for((0.600, 0.500))
    result = gate_mod.gate(_tuned_vector(), "corpus/", runner=runner)
    assert result["delta"] == pytest.approx(-0.100)
    assert result["verdict"] == gate_mod.BLOCKED


def test_gate_blocks_when_either_side_has_no_evidence():
    runner = _runner_for((None, 0.700))
    result = gate_mod.gate(_tuned_vector(), "corpus/", runner=runner)
    assert result["delta"] is None
    assert result["verdict"] == gate_mod.BLOCKED


def test_gate_default_vector_bakes_no_overrides_in_either_call():
    seen_envs = []

    def runner(env, payload, python):
        seen_envs.append(dict(env))
        return json.dumps({"win_rate": None, "agreement": 0.5})

    gate_mod.gate(_tuned_vector(), "corpus/", runner=runner)
    # First call is the default vector: no PTCG_W_* overrides baked.
    assert not any(k.startswith("PTCG_W_") for k in seen_envs[0])
    # Second call is the tuned vector: its override IS baked.
    assert seen_envs[1]["PTCG_W_THIN_BENCH"] == "4"


def test_gate_spec_is_pinned_to_the_test_split_for_both_calls():
    seen_payloads = []

    def runner(env, payload, python):
        seen_payloads.append(json.loads(payload))
        return json.dumps({"win_rate": None, "agreement": 0.5})

    gate_mod.gate(_tuned_vector(), "corpus/", limit=500, teams=["a", "b"], runner=runner)
    assert len(seen_payloads) == 2
    for payload in seen_payloads:
        assert payload["split"] == "test"
        assert payload["teacher_labels"] == "corpus/"
        assert payload["limit"] == 500
        assert payload["teams"] == ["a", "b"]


# --- gate_from_cem_result: loads a cem_tune --out JSON -----------------------

def test_gate_from_cem_result_reads_the_best_vector(tmp_path):
    tuned_vector = _tuned_vector()
    result_path = tmp_path / "cem_result.json"
    result_path.write_text(
        json.dumps({"best": {"fitness": 0.9, "vector": tuned_vector}}),
        encoding="utf-8",
    )
    runner = _runner_for((0.4, 0.5))
    result = gate_mod.gate_from_cem_result(str(result_path), "corpus/", runner=runner)
    assert result["verdict"] == gate_mod.WIN
    assert result["delta"] == pytest.approx(0.1)


# --- CLI ----------------------------------------------------------------

def test_main_requires_a_label_source(capsys):
    with pytest.raises(SystemExit):
        gate_mod.main(["--result", "unused.json"])


def test_main_prints_the_verdict_json(tmp_path, monkeypatch, capsys):
    result_path = tmp_path / "cem_result.json"
    result_path.write_text(
        json.dumps({"best": {"fitness": 0.9, "vector": _tuned_vector()}}),
        encoding="utf-8",
    )

    def fake_gate_from_cem_result(*args, **kwargs):
        return {
            "default_agreement": 0.4,
            "tuned_agreement": 0.5,
            "delta": 0.1,
            "verdict": gate_mod.WIN,
        }

    monkeypatch.setattr(gate_mod, "gate_from_cem_result", fake_gate_from_cem_result)
    rc = gate_mod.main(["--result", str(result_path), "--teacher-labels", "corpus/"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["verdict"] == gate_mod.WIN
