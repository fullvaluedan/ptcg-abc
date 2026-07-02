import sys

import tools.run_ab as run_ab_mod
from tools.run_ab import GATE_MARGIN_PP, run_ab


def test_run_ab_runs_both_arms_and_computes_diff():
    logged = []
    result = run_ab("random", ["first"], n=2, python_exe=sys.executable, log=logged.append)

    assert result["off"]["matches"] == 2
    assert result["on"]["matches"] == 2
    assert result["diff_pp"] == round(
        (result["on"]["win_rate"] - result["off"]["win_rate"]) * 100, 2
    )
    assert result["gate_margin_pp"] == GATE_MARGIN_PP
    assert result["verdict"] in ("flip default on", "keep default off")
    assert len(logged) == 2


def _fake_arm(win_rate):
    return {"win_rate": win_rate, "matches": 400, "wins": int(win_rate * 400)}


def test_run_ab_verdict_at_exact_margin_does_not_flip(monkeypatch):
    def fake_run_arm(agent, opponents, n, learned_eval, python_exe):
        return _fake_arm(0.50 + GATE_MARGIN_PP / 100) if learned_eval else _fake_arm(0.50)

    monkeypatch.setattr(run_ab_mod, "_run_arm", fake_run_arm)
    result = run_ab("search", ["deck:aggro"], n=400)
    assert result["diff_pp"] == GATE_MARGIN_PP
    assert result["verdict"] == "keep default off"


def test_run_ab_verdict_above_margin_flips(monkeypatch):
    def fake_run_arm(agent, opponents, n, learned_eval, python_exe):
        return _fake_arm(0.55) if learned_eval else _fake_arm(0.50)

    monkeypatch.setattr(run_ab_mod, "_run_arm", fake_run_arm)
    result = run_ab("search", ["deck:aggro"], n=400)
    assert result["diff_pp"] > GATE_MARGIN_PP
    assert result["verdict"] == "flip default on"
