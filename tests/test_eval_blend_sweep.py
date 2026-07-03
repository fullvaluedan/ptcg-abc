import json
import sys

import tools.eval_blend_sweep as sweep_mod
from tools.eval_blend_sweep import WEIGHTS, run_sweep


def test_run_weight_bakes_blend_into_env(monkeypatch):
    captured = {}

    def fake_run_parallel_gauntlet(agent, opponents, n, jobs=None, python_exe=None, env=None):
        captured["agent"] = agent
        captured["opponents"] = opponents
        captured["n"] = n
        captured["env"] = env
        return {"win_rate": 0.5, "matches": n, "wins": n // 2, "shard_errors": []}

    monkeypatch.setattr(sweep_mod, "run_parallel_gauntlet", fake_run_parallel_gauntlet)
    sweep_mod._run_weight("search", ["deck:aggro"], 10, 0.25, sys.executable)

    assert captured["agent"] == "search"
    assert captured["opponents"] == ["deck:aggro"]
    assert captured["n"] == 10
    assert captured["env"]["PTCG_EVAL_BLEND"] == "0.25"


def test_run_weight_raises_on_shard_errors(monkeypatch):
    def fake_run_parallel_gauntlet(agent, opponents, n, jobs=None, python_exe=None, env=None):
        return {"win_rate": 0.0, "matches": 0, "wins": 0, "shard_errors": ["shard 0: boom"]}

    monkeypatch.setattr(sweep_mod, "run_parallel_gauntlet", fake_run_parallel_gauntlet)
    try:
        sweep_mod._run_weight("search", ["deck:aggro"], 10, 0.5, sys.executable)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "shard 0: boom" in str(exc)


def _fake_result(win_rate, n=200):
    return {"win_rate": win_rate, "matches": n, "wins": int(win_rate * n), "shard_errors": []}


def test_run_sweep_runs_every_weight_and_picks_best(monkeypatch):
    seen = []

    def fake_run_weight(agent, opponents, n, weight, python_exe, jobs=None):
        seen.append(weight)
        # a midpoint beats both endpoints
        rates = {0.0: 0.60, 0.25: 0.61, 0.5: 0.66, 0.75: 0.62, 1.0: 0.605}
        return _fake_result(rates[weight])

    monkeypatch.setattr(sweep_mod, "_run_weight", fake_run_weight)
    result = run_sweep("search", ["deck:aggro"], 200, weights=WEIGHTS)

    assert seen == list(WEIGHTS)
    assert len(result["weights"]) == 5
    assert result["best"]["weight"] == 0.5
    assert result["endpoints_beaten"] is True


def test_run_sweep_endpoint_wins_is_not_endpoints_beaten(monkeypatch):
    def fake_run_weight(agent, opponents, n, weight, python_exe, jobs=None):
        rates = {0.0: 0.68, 0.25: 0.60, 0.5: 0.61, 0.75: 0.62, 1.0: 0.65}
        return _fake_result(rates[weight])

    monkeypatch.setattr(sweep_mod, "_run_weight", fake_run_weight)
    result = run_sweep("search", ["deck:aggro"], 200, weights=WEIGHTS)

    assert result["best"]["weight"] == 0.0
    assert result["endpoints_beaten"] is False


def test_run_sweep_checkpoint_skips_cached_weights(tmp_path, monkeypatch):
    checkpoint = tmp_path / "progress.json"
    checkpoint.write_text(json.dumps({"0.0": _fake_result(0.5)}))
    calls = []

    def fake_run_weight(agent, opponents, n, weight, python_exe, jobs=None):
        calls.append(weight)
        return _fake_result(0.5)

    monkeypatch.setattr(sweep_mod, "_run_weight", fake_run_weight)
    result = run_sweep("search", ["deck:aggro"], 200, weights=(0.0, 0.5), checkpoint_path=checkpoint)

    assert calls == [0.5]  # 0.0 was cached, not re-run
    assert len(result["weights"]) == 2
    saved = json.loads(checkpoint.read_text())
    assert set(saved.keys()) == {"0.0", "0.5"}
