"""Tests for tools/oracle_ring_test.py (plan U109, the oracle bound test).

Mirrors tests/test_ring_calibrate.py's test boundary: the per-opponent oracle
decklist lookup and the win-rate bookkeeping are pure-logic and unit-tested
directly; a real ring run needs the local engine and card data, so that part
gets one small integration test gated by pytest.importorskip, matching
test_ring_calibrate.py's own test_ring_plays_a_real_tiny_ring pattern.
"""
from __future__ import annotations

import pytest

from tools import oracle_ring_test as ort


def test_opponent_true_decklist_reads_60_cards_from_disk():
    prior = ort._opponent_true_decklist("clone:bracket_1")
    assert len(prior) == 60
    assert all(isinstance(cid, int) for cid in prior)


def test_opponent_true_decklist_matches_the_opponent_it_pilots():
    """The oracle prior is read from the SAME csv the clone opponent itself
    plays, not a separately maintained copy that could drift out of sync."""
    from tools import opponents

    for name in ("clone:bracket_2", "clone:meta_archaludon"):
        family = name[len("clone:"):]
        expected = opponents._read_deck_csv(ort._ROOT / "decks" / f"{family}.csv")
        assert ort._opponent_true_decklist(name) == expected


def test_opponent_true_decklist_rejects_non_clone_names():
    with pytest.raises(ValueError):
        ort._opponent_true_decklist("deck:trolley")


def test_ring_win_rate_empty_inputs_return_zero():
    assert ort._ring_win_rate(lambda obs: [0], [], 10) == (0.0, 0, 0, 0, 0)
    assert ort._ring_win_rate(lambda obs: [0], ["clone:bracket_1"], 0) == (0.0, 0, 0, 0, 0)


def test_ring_win_rate_tallies_wins_draws_losses(monkeypatch):
    """Same bookkeeping contract as ring_calibrate._ring_win_rate: reward_a of
    1/-1/0 maps to a win/loss/draw, and win_rate is wins over total games."""
    from tools import ring_calibrate

    rewards = iter([1, -1, 0, 1])

    def fake_run_match(agent_fn, opp_fn, swap_first=False):
        return {"reward_a": next(rewards)}

    monkeypatch.setattr(ort, "run_match", fake_run_match)
    monkeypatch.setattr(ort.opponents, "get", lambda name: (lambda obs: [0]))

    win_rate, wins, draws, losses, n = ort._ring_win_rate(
        lambda obs: [0], ["clone:bracket_1"], 4
    )
    assert (wins, draws, losses, n) == (2, 1, 1, 4)
    assert win_rate == 0.5


def test_oracle_ring_win_rate_selects_a_fresh_oracle_prior_per_opponent(monkeypatch):
    """The round-robin loop must pick each matchup's oracle prior BEFORE the
    match starts (deliberately unfair information), not have a single static
    agent try to infer its opponent's identity from observations."""
    seen_priors = []

    def fake_factory(prior):
        seen_priors.append(prior)

        def factory():
            return lambda obs: [0]

        return factory

    monkeypatch.setattr(ort, "_oracle_search_agent_factory", fake_factory)
    monkeypatch.setattr(
        ort, "_opponent_true_decklist", lambda name: {"clone:bracket_1": [1], "clone:bracket_2": [2]}[name]
    )
    monkeypatch.setattr(ort.opponents, "get", lambda name: (lambda obs: [0]))
    monkeypatch.setattr(ort, "run_match", lambda a, o, swap_first=False: {"reward_a": 1})

    win_rate, wins, draws, losses, n = ort._oracle_ring_win_rate(
        ["clone:bracket_1", "clone:bracket_2"], 4
    )
    assert n == 4
    assert wins == 4
    # Each of the 4 games rebuilt the oracle agent with that game's opponent's
    # own true decklist, alternating bracket_1, bracket_2, bracket_1, bracket_2.
    assert seen_priors == [[1], [2], [1], [2]]


def test_oracle_ring_win_rate_empty_inputs_return_zero():
    assert ort._oracle_ring_win_rate([], 10) == (0.0, 0, 0, 0, 0)
    assert ort._oracle_ring_win_rate(["clone:bracket_1"], 0) == (0.0, 0, 0, 0, 0)


def test_run_oracle_bound_test_raises_without_ring_opponents(monkeypatch):
    monkeypatch.setattr(ort.ring_calibrate, "ring_names", lambda: [])
    with pytest.raises(RuntimeError):
        ort.run_oracle_bound_test(n_matches=2)


def test_main_gate_pass_and_fail(monkeypatch, capsys):
    pass_results = {
        "arm_a_stacked_incumbent": {"win_rate": 0.80, "wins": 32, "draws": 0, "losses": 8, "n": 40},
        "arm_b_oracle_search": {"win_rate": 0.90, "wins": 36, "draws": 0, "losses": 4, "n": 40},
    }
    monkeypatch.setattr(ort, "run_oracle_bound_test", lambda **kwargs: pass_results)
    assert ort._main([]) == 0
    out = capsys.readouterr().out
    assert "PASS" in out
    assert "+0.100" in out

    fail_results = {
        "arm_a_stacked_incumbent": {"win_rate": 0.86, "wins": 86, "draws": 0, "losses": 14, "n": 100},
        "arm_b_oracle_search": {"win_rate": 0.87, "wins": 87, "draws": 0, "losses": 13, "n": 100},
    }
    monkeypatch.setattr(ort, "run_oracle_bound_test", lambda **kwargs: fail_results)
    assert ort._main([]) == 2
    assert "FAIL" in capsys.readouterr().out


def test_ring_plays_a_real_tiny_ring():
    """Integration: both arms play two real games each against the real clone
    ring. Needs the local engine and card data, mirroring test_ring_calibrate.
    py's own test_ring_plays_a_real_tiny_ring."""
    pytest.importorskip("kaggle_environments")
    results = ort.run_oracle_bound_test(n_matches=2)
    assert set(results) == {"arm_a_stacked_incumbent", "arm_b_oracle_search"}
    for r in results.values():
        assert r["n"] == 2
        assert r["wins"] + r["draws"] + r["losses"] == 2
        assert 0.0 <= r["win_rate"] <= 1.0
