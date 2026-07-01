"""Tests for tools/measure_benchguard.py.

The native engine is a per process singleton, so these cover the pure logic: the
per-seat tally classifies OUR seat (not whichever seat lost) across alternating
first-player games through an injected fake env, and the shared THIN_BENCH global is
restored after measure() even when a game raises. No native engine, no network.
"""
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agents import heuristics  # noqa: E402
from tests.test_collapse_rate import _FakeEnv, _game  # noqa: E402
from tools import measure_benchguard as mb  # noqa: E402


def _factory(games):
    seq = iter(games)

    def factory():
        return _FakeEnv(next(seq))

    return factory


def test_run_setting_counts_only_our_seat_across_alternation():
    # Game 0 (even i): our seat is index 0, and seat 0 lost with an empty bench.
    # Game 1 (odd i): our seat is index 1, and seat 1 lost with an empty bench.
    # Both must count as OUR early_collapse; a naive whichever-seat tally would
    # still pass, so game 1 pins the seat by making seat 0 the WINNER there.
    g0 = _game(rewards=[-1, 1], turn=3, prizes=(6, 6), decks=(42, 41), benches=(0, 2))
    g1 = _game(rewards=[1, -1], turn=3, prizes=(6, 6), decks=(41, 42), benches=(2, 0))
    r = mb._run_setting([1, 2, 3], 0, 2, n_games=2, env_factory=_factory([g0, g1]))
    assert r["decided"] == 2
    assert r["our_losses"] == 2
    assert r["early_collapse"] == 2
    assert abs(r["early_collapse_rate"] - 1.0) < 1e-9


def test_run_setting_our_win_and_draw_not_counted_as_collapse():
    # i=0 our seat is index 0 and we WIN; i=1 our seat is index 1 and it is a draw.
    win = _game(rewards=[1, -1], turn=6, prizes=(3, 6), decks=(40, 30), benches=(3, 0))
    draw = _game(rewards=[0, 0])
    r = mb._run_setting([1, 2, 3], 2, 2, n_games=2, env_factory=_factory([win, draw]))
    assert r["decided"] == 1           # the draw is not a decided result for us
    assert r["our_losses"] == 0
    assert r["early_collapse"] == 0
    assert r["early_collapse_rate"] == 0.0


def test_thin_bench_restored_after_measure():
    sentinel = 7
    saved = heuristics.THIN_BENCH
    heuristics.THIN_BENCH = sentinel
    try:
        draws = [_game(rewards=[0, 0]) for _ in range(4)]
        mb.measure(str(_ROOT / "decks" / "trolley.csv"), 2,
                   env_factory=_factory(draws))
        assert heuristics.THIN_BENCH == sentinel
    finally:
        heuristics.THIN_BENCH = saved


def test_thin_bench_restored_after_exception():
    sentinel = 9
    saved = heuristics.THIN_BENCH
    heuristics.THIN_BENCH = sentinel

    def boom():
        raise RuntimeError("engine blew up mid-run")

    try:
        with pytest.raises(RuntimeError):
            mb.measure(str(_ROOT / "decks" / "trolley.csv"), 2, env_factory=boom)
        assert heuristics.THIN_BENCH == sentinel
    finally:
        heuristics.THIN_BENCH = saved


def test_seat_returns_deck_on_deck_selection_and_pins_guard():
    saved = heuristics.THIN_BENCH
    try:
        seat = mb._seat([5, 6, 7], 3)
        # Deck-selection step: the fixed deck, guard untouched.
        assert seat({"select": None}) == [5, 6, 7]
        # A live (benign sub-select) decision pins THIN_BENCH before choosing.
        heuristics.THIN_BENCH = 999
        move = seat({"select": {"type": 99, "option": [0], "minCount": 1, "maxCount": 1}})
        assert heuristics.THIN_BENCH == 3
        assert move == [0]
    finally:
        heuristics.THIN_BENCH = saved
