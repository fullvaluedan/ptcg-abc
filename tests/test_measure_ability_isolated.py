"""Tests for tools/measure_ability_isolated.py.

The native engine is a per-process singleton, so these cover the pure logic
without running real matches: _seat_wrap pins agents.heuristics._ABILITY to a
fixed value right before delegating to the wrapped callable (not a value
captured once at wrap time), and run_arm restores the shipped default (False)
after it finishes, whether it completes normally or a match raises.
"""
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agents import heuristics as h  # noqa: E402
from tools import measure_ability_isolated as mai  # noqa: E402


def test_seat_wrap_sets_ability_before_delegating():
    saved = h._ABILITY
    try:
        h._ABILITY = None
        seen = []

        def fn(obs):
            seen.append((h._ABILITY, obs))
            return [0]

        wrapped_on = mai._seat_wrap(fn, True)
        wrapped_on({"select": "x"})
        assert seen[-1] == (True, {"select": "x"})

        wrapped_off = mai._seat_wrap(fn, False)
        wrapped_off({"select": "y"})
        assert seen[-1] == (False, {"select": "y"})
    finally:
        h._ABILITY = saved


def test_run_arm_tallies_results_and_restores_default_ability(monkeypatch):
    saved = h._ABILITY
    h._ABILITY = True  # a stale non-default value the run must clear afterward

    monkeypatch.setattr(mai.opponents, "get", lambda name: (lambda obs: [0]))

    results = iter([
        {"reward_a": 1},
        {"reward_a": -1},
        {"reward_a": 0},
    ])
    monkeypatch.setattr(mai, "run_match", lambda a, b, swap_first: next(results))

    try:
        stats = mai.run_arm(True, False, pool=("deck:x",), n_matches=3, seed=0)
        assert stats == {
            "pilot_ability": True,
            "opponent_ability": False,
            "matches": 3,
            "wins": 1,
            "draws": 1,
            "losses": 1,
            "win_rate": pytest.approx(1 / 3),
            "wilson_lo": stats["wilson_lo"],
            "wilson_hi": stats["wilson_hi"],
        }
        assert h._ABILITY is False
    finally:
        h._ABILITY = saved


def test_run_arm_restores_default_ability_after_exception(monkeypatch):
    saved = h._ABILITY
    h._ABILITY = True

    monkeypatch.setattr(mai.opponents, "get", lambda name: (lambda obs: [0]))

    def boom(a, b, swap_first):
        raise RuntimeError("engine blew up mid-run")

    monkeypatch.setattr(mai, "run_match", boom)

    try:
        with pytest.raises(RuntimeError):
            mai.run_arm(True, True, pool=("deck:x",), n_matches=2, seed=0)
        assert h._ABILITY is False
    finally:
        h._ABILITY = saved
