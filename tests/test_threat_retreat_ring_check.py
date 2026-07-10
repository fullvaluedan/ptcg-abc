"""Tests for the U105b threat-retreat ring check (tools/threat_retreat_ring_check.py)."""
import pytest

from tools import threat_retreat_ring_check as trc


def test_agent_restores_flags_after_use():
    pytest.importorskip("kaggle_environments")
    from agents import heuristics as H

    orig_ability = H._ABILITY
    orig_threat = H._THREAT_RETREAT
    factory = trc._make_agent_factory(trc.YUSHIN_DECK, ability_on=not orig_ability,
                                       threat_retreat_on=not orig_threat)
    agent = factory()
    agent({"select": None})  # deck-selection step: no flag reads on this path
    assert H._ABILITY == orig_ability
    assert H._THREAT_RETREAT == orig_threat


def test_agent_actually_toggles_both_flags_during_a_call(monkeypatch):
    pytest.importorskip("kaggle_environments")
    from agents import heuristics as H

    seen = {}

    def fake_inner(obs):
        seen["ability"] = H._ABILITY
        seen["threat_retreat"] = H._THREAT_RETREAT
        return "ok"

    monkeypatch.setattr(trc.opponents, "get", lambda name: fake_inner)
    orig_ability = H._ABILITY
    orig_threat = H._THREAT_RETREAT
    factory = trc._make_agent_factory(trc.YUSHIN_DECK, ability_on=True, threat_retreat_on=True)
    agent = factory()
    agent({"select": None})
    assert seen["ability"] is True
    assert seen["threat_retreat"] is True
    assert H._ABILITY == orig_ability
    assert H._THREAT_RETREAT == orig_threat


def test_off_arm_agent_never_sees_threat_retreat_true(monkeypatch):
    """The off-arm factory (threat_retreat_on=False) must never let the wrapped
    call observe _THREAT_RETREAT as True, across repeated calls, distinct from
    the on-arm factory built from the same YUSHIN_DECK.
    """
    pytest.importorskip("kaggle_environments")
    from agents import heuristics as H

    seen = []

    def fake_inner(obs):
        seen.append(H._THREAT_RETREAT)
        return "ok"

    monkeypatch.setattr(trc.opponents, "get", lambda name: fake_inner)

    off_factory = trc._make_agent_factory(trc.YUSHIN_DECK, ability_on=True, threat_retreat_on=False)
    on_factory = trc._make_agent_factory(trc.YUSHIN_DECK, ability_on=True, threat_retreat_on=True)

    off_agent = off_factory()
    on_agent = on_factory()

    for _ in range(3):
        off_agent({"select": None})
        on_agent({"select": None})

    # Six calls total, alternating off/on: the off-arm calls are at even indices.
    off_seen = seen[0::2]
    on_seen = seen[1::2]
    assert all(v is False for v in off_seen)
    assert all(v is True for v in on_seen)

    # The two factories are also genuinely distinct agent objects, not aliases.
    assert off_agent is not on_agent


def test_off_and_on_factories_are_distinct_agents():
    pytest.importorskip("kaggle_environments")
    off_factory = trc._make_agent_factory(trc.YUSHIN_DECK, ability_on=True, threat_retreat_on=False)
    on_factory = trc._make_agent_factory(trc.YUSHIN_DECK, ability_on=True, threat_retreat_on=True)
    assert off_factory() is not on_factory()


# --- gate math -------------------------------------------------------------

def test_gate_diff_exactly_at_margin_is_fail():
    # off-arm below saturation, so the margin boundary decides it, not routing.
    assert trc.compute_verdict(off_win_rate=0.5, diff_pp=5.0) == "FAIL"


def test_gate_diff_just_above_margin_is_pass():
    assert trc.compute_verdict(off_win_rate=0.5, diff_pp=5.1) == "PASS"


def test_gate_below_margin_and_below_saturation_is_fail():
    assert trc.compute_verdict(off_win_rate=0.80, diff_pp=2.0) == "FAIL"


def test_gate_below_margin_and_saturated_routes_to_hard_ring():
    assert trc.compute_verdict(off_win_rate=0.85, diff_pp=2.0) == "NEEDS_U5_HARD_RING"
    assert trc.compute_verdict(off_win_rate=0.90, diff_pp=4.9) == "NEEDS_U5_HARD_RING"


def test_gate_pass_overrides_saturation():
    # A delta that actually clears the margin is a PASS even if the off-arm
    # happens to read at or above the saturation threshold too.
    assert trc.compute_verdict(off_win_rate=0.90, diff_pp=5.1) == "PASS"


# --- secondary hardest-clone metric -----------------------------------------

def test_hardest_clones_ranks_by_loss_rate_with_alphabetical_tiebreak():
    per_opponent = {
        "clone:bracket_1": {"wins": 8, "draws": 0, "losses": 2, "n": 10},   # 0.2
        "clone:bracket_2": {"wins": 5, "draws": 0, "losses": 5, "n": 10},   # 0.5
        "clone:bracket_3": {"wins": 5, "draws": 0, "losses": 5, "n": 10},   # 0.5 tie
        "clone:meta_archaludon": {"wins": 9, "draws": 0, "losses": 1, "n": 10},  # 0.1
        "clone:meta_grimmsnarl": {"wins": 0, "draws": 0, "losses": 0, "n": 0},   # excluded, n=0
    }
    hardest = trc.hardest_clones(per_opponent, k=3)
    assert hardest == ["clone:bracket_2", "clone:bracket_3", "clone:bracket_1"]


def test_hardest_clones_excludes_zero_n_opponents():
    per_opponent = {
        "clone:a": {"wins": 0, "draws": 0, "losses": 0, "n": 0},
        "clone:b": {"wins": 1, "draws": 0, "losses": 1, "n": 2},
    }
    assert trc.hardest_clones(per_opponent, k=3) == ["clone:b"]


def test_loss_rate_vs_clones_counts_only_named_clones():
    per_opponent = {
        "clone:hard_1": {"wins": 0, "draws": 0, "losses": 10, "n": 10},   # 1.0
        "clone:hard_2": {"wins": 0, "draws": 0, "losses": 5, "n": 10},    # 0.5
        "clone:easy": {"wins": 10, "draws": 0, "losses": 0, "n": 10},     # 0.0, must be ignored
    }
    rate, losses, n = trc.loss_rate_vs_clones(per_opponent, ["clone:hard_1", "clone:hard_2"])
    assert losses == 15
    assert n == 20
    assert rate == pytest.approx(0.75)


def test_loss_rate_vs_clones_ignores_unknown_names():
    per_opponent = {"clone:a": {"wins": 1, "draws": 0, "losses": 1, "n": 2}}
    rate, losses, n = trc.loss_rate_vs_clones(per_opponent, ["clone:a", "clone:does_not_exist"])
    assert losses == 1
    assert n == 2
    assert rate == pytest.approx(0.5)


def test_loss_rate_vs_clones_empty_list_is_zero():
    per_opponent = {"clone:a": {"wins": 1, "draws": 0, "losses": 1, "n": 2}}
    rate, losses, n = trc.loss_rate_vs_clones(per_opponent, [])
    assert (rate, losses, n) == (0.0, 0, 0)


def test_merge_per_opponent_sums_across_arms():
    a = {"clone:x": {"wins": 1, "draws": 0, "losses": 1, "n": 2}}
    b = {"clone:x": {"wins": 0, "draws": 1, "losses": 1, "n": 2},
         "clone:y": {"wins": 2, "draws": 0, "losses": 0, "n": 2}}
    merged = trc._merge_per_opponent(a, b)
    assert merged["clone:x"] == {"wins": 1, "draws": 1, "losses": 2, "n": 4}
    assert merged["clone:y"] == {"wins": 2, "draws": 0, "losses": 0, "n": 2}


# --- integration: real tiny ring run ----------------------------------------

def test_run_check_plays_a_real_tiny_ring_and_reconciles_totals():
    pytest.importorskip("kaggle_environments")
    results = trc.run_check(n_matches=2)
    assert set(results) >= {
        trc.ARM_OFF, trc.ARM_ON, "diff_pp", "verdict", "hardest_clones",
        "hardest_clone_loss_rate", "hardest_clone_losses", "hardest_clone_n",
    }
    for name in (trc.ARM_OFF, trc.ARM_ON):
        r = results[name]
        assert r["n"] == 2
        assert r["wins"] + r["draws"] + r["losses"] == r["n"]
    assert isinstance(results["diff_pp"], float)
    assert results["verdict"] in ("PASS", "FAIL", "NEEDS_U5_HARD_RING")
    # secondary metric n never exceeds each arm's total n.
    for name in (trc.ARM_OFF, trc.ARM_ON):
        assert results["hardest_clone_n"][name] <= results[name]["n"]


# --- CLI ---------------------------------------------------------------------

def test_main_prints_both_arms_diff_and_verdict(monkeypatch, capsys):
    fake_results = {
        trc.ARM_OFF: {"win_rate": 0.5, "wins": 1, "draws": 0, "losses": 1, "n": 2},
        trc.ARM_ON: {"win_rate": 1.0, "wins": 2, "draws": 0, "losses": 0, "n": 2},
        "diff_pp": 50.0,
        "verdict": "PASS",
        "hardest_clones": ["clone:bracket_1"],
        "hardest_clone_loss_rate": {trc.ARM_OFF: 0.5, trc.ARM_ON: 0.0},
        "hardest_clone_losses": {trc.ARM_OFF: 1, trc.ARM_ON: 0},
        "hardest_clone_n": {trc.ARM_OFF: 2, trc.ARM_ON: 2},
    }
    monkeypatch.setattr(trc, "run_check", lambda **kwargs: fake_results)
    assert trc._main([]) == 0
    out = capsys.readouterr().out
    assert trc.ARM_OFF in out
    assert trc.ARM_ON in out
    assert "+50.0" in out
    assert "PASS" in out
    assert "clone:bracket_1" in out


def test_main_notes_saturation_when_routed(monkeypatch, capsys):
    fake_results = {
        trc.ARM_OFF: {"win_rate": 0.90, "wins": 18, "draws": 0, "losses": 2, "n": 20},
        trc.ARM_ON: {"win_rate": 0.92, "wins": 18, "draws": 1, "losses": 1, "n": 20},
        "diff_pp": 2.0,
        "verdict": "NEEDS_U5_HARD_RING",
        "hardest_clones": ["clone:bracket_1"],
        "hardest_clone_loss_rate": {trc.ARM_OFF: 0.5, trc.ARM_ON: 0.5},
        "hardest_clone_losses": {trc.ARM_OFF: 1, trc.ARM_ON: 1},
        "hardest_clone_n": {trc.ARM_OFF: 2, trc.ARM_ON: 2},
    }
    monkeypatch.setattr(trc, "run_check", lambda **kwargs: fake_results)
    assert trc._main([]) == 0
    out = capsys.readouterr().out
    assert "NEEDS_U5_HARD_RING" in out
    assert "saturation" in out
