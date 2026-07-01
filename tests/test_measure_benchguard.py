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


def test_sweep_runs_each_value_and_restores_guard():
    # Two THIN_BENCH values, 2 games each: game 0 our seat 0 boards out, game 1 our
    # seat 1 boards out, so every setting sees a 100% our-seat early_collapse rate.
    # The point of the test is the plumbing: one result per swept value, the games
    # split correctly per seat, and the global is restored afterward.
    saved = heuristics.THIN_BENCH
    g0 = _game(rewards=[-1, 1], turn=3, prizes=(6, 6), decks=(42, 41), benches=(0, 2))
    g1 = _game(rewards=[1, -1], turn=3, prizes=(6, 6), decks=(41, 42), benches=(2, 0))
    try:
        heuristics.THIN_BENCH = sentinel = 2
        res = mb.sweep(str(_ROOT / "decks" / "trolley.csv"), [1, 3], n_games=2,
                       env_factory=_factory([g0, g1, g0, g1]))
        assert heuristics.THIN_BENCH == sentinel
        assert res["opp_thin_bench"] == sentinel
        assert [v for v, _ in res["settings"]] == [1, 3]
        for _, r in res["settings"]:
            assert r["decided"] == 2
            assert r["early_collapse"] == 2
    finally:
        heuristics.THIN_BENCH = saved


def test_format_sweep_flags_a_candidate_lever_only_on_separated_cis():
    # The shipped THIN_BENCH=2 boards out every game; raising OUR seat to 3 clears it
    # (all draws). At n=10 the two Wilson intervals are disjoint, so the formatter is
    # allowed to name 3 as a candidate next lever. Our seat alternates by parity, so a
    # collapse game is seeded for whichever seat is ours that round.
    g0 = _game(rewards=[-1, 1], turn=3, prizes=(6, 6), decks=(42, 41), benches=(0, 2))
    g1 = _game(rewards=[1, -1], turn=3, prizes=(6, 6), decks=(41, 42), benches=(2, 0))
    draw = _game(rewards=[0, 0])
    n = 10
    collapse_run = [g0 if i % 2 == 0 else g1 for i in range(n)]
    draw_run = [draw] * n
    saved = heuristics.THIN_BENCH
    try:
        heuristics.THIN_BENCH = 2
        res = mb.sweep(str(_ROOT / "decks" / "trolley.csv"), [2, 3], n_games=n,
                       env_factory=_factory(collapse_run + draw_run))
        text = mb._format_sweep(res)
        assert "lowest board-out at THIN_BENCH=3" in text
        assert "candidate next lever" in text
    finally:
        heuristics.THIN_BENCH = saved


def test_format_sweep_calls_overlapping_difference_noise():
    # Same directional signal but only n=2 per setting: the Wilson intervals overlap,
    # so the formatter must NOT claim a lever and must flag the result as within noise.
    g0 = _game(rewards=[-1, 1], turn=3, prizes=(6, 6), decks=(42, 41), benches=(0, 2))
    g1 = _game(rewards=[1, -1], turn=3, prizes=(6, 6), decks=(41, 42), benches=(2, 0))
    draw = _game(rewards=[0, 0])
    saved = heuristics.THIN_BENCH
    try:
        heuristics.THIN_BENCH = 2
        res = mb.sweep(str(_ROOT / "decks" / "trolley.csv"), [2, 3], n_games=2,
                       env_factory=_factory([g0, g1, draw, draw]))
        text = mb._format_sweep(res)
        assert "within noise" in text
        assert "candidate next lever" not in text
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
