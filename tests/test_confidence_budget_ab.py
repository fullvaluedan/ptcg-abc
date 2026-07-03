import sys

import tools.confidence_budget_ab as ab_mod
from tools.confidence_budget_ab import run_ab


def test_run_arm_bakes_flag_into_env(monkeypatch):
    captured = {}

    def fake_run_parallel_gauntlet(agent, opponents, n, jobs=None, python_exe=None, env=None):
        captured["agent"] = agent
        captured["opponents"] = opponents
        captured["n"] = n
        captured["env"] = env
        return {"win_rate": 0.5, "matches": n, "wins": n // 2, "shard_errors": [],
                "avg_bank_spend_s": 10.0}

    monkeypatch.setattr(ab_mod, "run_parallel_gauntlet", fake_run_parallel_gauntlet)
    ab_mod._run_arm("search", ["deck:aggro"], 10, True, sys.executable)

    assert captured["agent"] == "search"
    assert captured["opponents"] == ["deck:aggro"]
    assert captured["n"] == 10
    assert captured["env"]["PTCG_CONFIDENCE_BUDGET"] == "1"

    ab_mod._run_arm("search", ["deck:aggro"], 10, False, sys.executable)
    assert captured["env"]["PTCG_CONFIDENCE_BUDGET"] == "0"


def test_run_arm_raises_on_shard_errors(monkeypatch):
    def fake_run_parallel_gauntlet(agent, opponents, n, jobs=None, python_exe=None, env=None):
        return {"win_rate": 0.0, "matches": 0, "wins": 0, "shard_errors": ["shard 0: boom"]}

    monkeypatch.setattr(ab_mod, "run_parallel_gauntlet", fake_run_parallel_gauntlet)
    try:
        ab_mod._run_arm("search", ["deck:aggro"], 10, True, sys.executable)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "shard 0: boom" in str(exc)


def _fake_result(win_rate, bank_spend, n=200):
    return {
        "win_rate": win_rate, "matches": n, "wins": int(win_rate * n),
        "shard_errors": [], "avg_bank_spend_s": bank_spend,
    }


def test_run_ab_passes_when_win_rate_holds_and_bank_spend_drops(monkeypatch):
    def fake_run_arm(agent, opponents, n, flag_on, python_exe, jobs=None):
        return _fake_result(0.70, 90.0) if flag_on else _fake_result(0.68, 100.0)

    monkeypatch.setattr(ab_mod, "_run_arm", fake_run_arm)
    result = run_ab("search", ["deck:aggro"], 200)

    assert result["win_rate_kept"] is True
    assert result["bank_spend_kept"] is True
    assert result["gate_passed"] is True


def test_run_ab_fails_when_win_rate_drops(monkeypatch):
    def fake_run_arm(agent, opponents, n, flag_on, python_exe, jobs=None):
        return _fake_result(0.60, 90.0) if flag_on else _fake_result(0.68, 100.0)

    monkeypatch.setattr(ab_mod, "_run_arm", fake_run_arm)
    result = run_ab("search", ["deck:aggro"], 200)

    assert result["win_rate_kept"] is False
    assert result["gate_passed"] is False


def test_run_ab_fails_when_bank_spend_increases(monkeypatch):
    def fake_run_arm(agent, opponents, n, flag_on, python_exe, jobs=None):
        return _fake_result(0.70, 120.0) if flag_on else _fake_result(0.68, 100.0)

    monkeypatch.setattr(ab_mod, "_run_arm", fake_run_arm)
    result = run_ab("search", ["deck:aggro"], 200)

    assert result["bank_spend_kept"] is False
    assert result["gate_passed"] is False


def test_run_ab_off_arm_runs_before_on_arm(monkeypatch):
    seen = []

    def fake_run_arm(agent, opponents, n, flag_on, python_exe, jobs=None):
        seen.append(flag_on)
        return _fake_result(0.68, 100.0)

    monkeypatch.setattr(ab_mod, "_run_arm", fake_run_arm)
    run_ab("search", ["deck:aggro"], 200)

    assert seen == [False, True]
