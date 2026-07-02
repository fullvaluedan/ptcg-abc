import json
import sys

import tools.run_ab as run_ab_mod
from tools.run_ab import GATE_MARGIN_PP, run_ab, run_ab_resumable


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


def _fake_batch(win_rate, n):
    wins = int(win_rate * n)
    return {"wins": wins, "draws": 0, "losses": n - wins, "matches": n}


def test_run_ab_resumable_runs_to_completion_in_batches(tmp_path, monkeypatch):
    checkpoint = tmp_path / "progress.json"
    calls = []

    def fake_run_arm(agent, opponents, n, learned_eval, python_exe):
        calls.append((learned_eval, n))
        return _fake_batch(0.6 if learned_eval else 0.5, n)

    monkeypatch.setattr(run_ab_mod, "_run_arm", fake_run_arm)
    result = run_ab_resumable("search", ["deck:aggro"], n=20, checkpoint_path=checkpoint, batch_size=10)

    assert result["done"] is True
    assert result["off"]["matches"] == 20
    assert result["on"]["matches"] == 20
    assert result["diff_pp"] == round((0.6 - 0.5) * 100, 2)
    assert [n for _, n in calls] == [10, 10, 10, 10]
    saved = json.loads(checkpoint.read_text())
    assert saved["off"]["matches"] == 20
    assert saved["on"]["matches"] == 20


def test_run_ab_resumable_picks_up_from_existing_checkpoint(tmp_path, monkeypatch):
    checkpoint = tmp_path / "progress.json"
    checkpoint.write_text(json.dumps({
        "off": {"wins": 15, "draws": 0, "losses": 10, "matches": 25},
        "on": {"wins": 0, "draws": 0, "losses": 0, "matches": 0},
    }))
    calls = []

    def fake_run_arm(agent, opponents, n, learned_eval, python_exe):
        calls.append((learned_eval, n))
        return _fake_batch(0.6, n)

    monkeypatch.setattr(run_ab_mod, "_run_arm", fake_run_arm)
    result = run_ab_resumable("search", ["deck:aggro"], n=25, checkpoint_path=checkpoint, batch_size=10)

    assert result["done"] is True
    assert all(learned_eval for learned_eval, _ in calls)  # off arm never re-run
    assert result["off"]["matches"] == 25
    assert result["off"]["wins"] == 15  # preserved from the checkpoint, not re-simulated


def test_run_ab_resumable_stops_at_time_budget(tmp_path, monkeypatch):
    checkpoint = tmp_path / "progress.json"
    calls = []

    def fake_run_arm(agent, opponents, n, learned_eval, python_exe):
        calls.append((learned_eval, n))
        return _fake_batch(0.5, n)

    times = iter([0, 0, 1000])  # start, first budget check (pass), second check (over budget)

    monkeypatch.setattr(run_ab_mod, "_run_arm", fake_run_arm)
    monkeypatch.setattr(run_ab_mod.time, "time", lambda: next(times))
    result = run_ab_resumable(
        "search", ["deck:aggro"], n=25, checkpoint_path=checkpoint, batch_size=10, time_budget_s=5,
    )

    assert result["done"] is False
    assert len(calls) == 1
    assert result["off"]["matches"] == 10
    saved = json.loads(checkpoint.read_text())
    assert saved["off"]["matches"] == 10
