"""Tests for the U74 ability-lever ring check (tools/ability_ring_check.py)."""
import pytest

from tools import ability_ring_check as arc


def test_ability_agent_restores_flag_after_use():
    pytest.importorskip("kaggle_environments")
    from agents import heuristics as H

    orig = H._ABILITY
    agent = arc._ability_trolley_agent(not orig)
    agent({"select": None})  # deck-selection step: no _ABILITY read on this path
    assert H._ABILITY == orig


def test_ability_agent_actually_toggles_the_flag_during_a_call(monkeypatch):
    pytest.importorskip("kaggle_environments")
    from agents import heuristics as H
    from tools import opponents

    seen = {}

    def fake_inner(obs):
        seen["ability"] = H._ABILITY
        return "ok"

    monkeypatch.setattr(opponents, "get", lambda name: fake_inner)
    orig = H._ABILITY
    agent = arc._ability_trolley_agent(True)
    agent({"select": None})
    assert seen["ability"] is True
    assert H._ABILITY == orig


def test_run_check_plays_a_real_tiny_ring_and_reports_diff():
    pytest.importorskip("kaggle_environments")
    results = arc.run_check(n_matches=2)
    assert set(results) == {
        "heuristic+trolley-ability-off", "heuristic+trolley-ability-on", "diff_pp",
    }
    for name in ("heuristic+trolley-ability-off", "heuristic+trolley-ability-on"):
        r = results[name]
        assert r["n"] == 2
        assert r["wins"] + r["draws"] + r["losses"] == 2
    assert isinstance(results["diff_pp"], float)


def test_main_prints_both_builds_and_diff(monkeypatch, capsys):
    fake_results = {
        "heuristic+trolley-ability-off": {"win_rate": 0.5, "wins": 1, "draws": 0, "losses": 1, "n": 2},
        "heuristic+trolley-ability-on": {"win_rate": 1.0, "wins": 2, "draws": 0, "losses": 0, "n": 2},
        "diff_pp": 50.0,
    }
    monkeypatch.setattr(arc, "run_check", lambda **kwargs: fake_results)
    assert arc._main([]) == 0
    out = capsys.readouterr().out
    assert "heuristic+trolley-ability-off" in out
    assert "heuristic+trolley-ability-on" in out
    assert "+50.0" in out
