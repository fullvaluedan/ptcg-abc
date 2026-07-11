"""Tests for the S1 high-band (top50) ring baseline (tools/top50_ring.py)."""
import pytest

from tools import top50_ring as tr


def test_top50_ring_names_are_clone_prefixed_top50():
    names = tr.top50_ring_names()
    assert names, "top50 ring should be non-empty when decks/top50/ is harvested"
    assert all(n.startswith("clone:top50_") for n in names)


def test_top50_ring_names_uses_top50_clone_names_not_clone_family_names():
    from tools import opponents

    names = set(tr.top50_ring_names())
    family_names = {f"clone:{f}" for f in opponents.clone_family_names()}
    # The high-band ring must stay disjoint from the existing calibrated
    # bracket ring (plan S1: never touch that instrument).
    assert names.isdisjoint(family_names)


def test_run_baseline_raises_with_no_opponents():
    with pytest.raises(RuntimeError):
        tr.run_baseline(n_matches=2, opponent_names=[])


# --- integration: real tiny ring run ----------------------------------------

def test_run_baseline_plays_a_real_tiny_ring_and_reconciles_totals():
    pytest.importorskip("kaggle_environments")
    results = tr.run_baseline(n_matches=2)
    assert set(results) >= {
        "ring_size", tr.ARM_STACK, tr.ARM_FLAGS_OFF, "hardest_clones",
        "saturated_ring_win_rate", "gap_to_saturated_pp",
    }
    assert results["ring_size"] == len(tr.top50_ring_names())
    for name in (tr.ARM_STACK, tr.ARM_FLAGS_OFF):
        r = results[name]
        assert r["n"] == 2
        assert r["wins"] + r["draws"] + r["losses"] == r["n"]
        assert sum(o["n"] for o in r["per_opponent"].values()) == r["n"]
    assert isinstance(results["gap_to_saturated_pp"], float)
    assert results["saturated_ring_win_rate"] == tr.SATURATED_RING_WIN_RATE


def test_run_baseline_stack_arm_uses_ability_and_threat_retreat_on(monkeypatch):
    # STACK must be built exactly like threat_retreat_ring_check's on-arm
    # factory (ability_on=True, threat_retreat_on=True); FLAGS_OFF both off.
    pytest.importorskip("kaggle_environments")
    from agents import heuristics as H

    seen = {"stack": [], "flags_off": []}

    def fake_inner(obs):
        return "ok"

    from tools import opponents as opp_mod
    monkeypatch.setattr(opp_mod, "get", lambda name: fake_inner)

    orig_ability = H._ABILITY
    orig_threat = H._THREAT_RETREAT

    factory_stack = tr.trc._make_agent_factory(tr.trc.YUSHIN_DECK, ability_on=True, threat_retreat_on=True)
    factory_off = tr.trc._make_agent_factory(tr.trc.YUSHIN_DECK, ability_on=False, threat_retreat_on=False)

    def probe(factory, bucket):
        def wrapped(obs):
            bucket.append((H._ABILITY, H._THREAT_RETREAT))
            return fake_inner(obs)

        monkeypatch.setattr(opp_mod, "get", lambda name: wrapped)
        agent = factory()
        agent({"select": None})

    probe(factory_stack, seen["stack"])
    probe(factory_off, seen["flags_off"])

    assert seen["stack"] == [(True, True)]
    assert seen["flags_off"] == [(False, False)]
    assert H._ABILITY == orig_ability
    assert H._THREAT_RETREAT == orig_threat


# --- report formatting -------------------------------------------------------

def _fake_results():
    return {
        "ring_size": 2,
        tr.ARM_STACK: {
            "win_rate": 0.75, "wins": 3, "draws": 0, "losses": 1, "n": 4,
            "per_opponent": {
                "clone:top50_01_a": {"wins": 2, "draws": 0, "losses": 0, "n": 2},
                "clone:top50_02_b": {"wins": 1, "draws": 0, "losses": 1, "n": 2},
            },
        },
        tr.ARM_FLAGS_OFF: {
            "win_rate": 0.5, "wins": 2, "draws": 0, "losses": 2, "n": 4,
            "per_opponent": {
                "clone:top50_01_a": {"wins": 1, "draws": 0, "losses": 1, "n": 2},
                "clone:top50_02_b": {"wins": 1, "draws": 0, "losses": 1, "n": 2},
            },
        },
        "hardest_clones": ["clone:top50_02_b", "clone:top50_01_a"],
        "saturated_ring_win_rate": 0.910,
        "gap_to_saturated_pp": (0.910 - 0.75) * 100.0,
    }


def test_format_report_includes_headline_and_per_opponent_rows():
    report = tr.format_report(_fake_results())
    assert "0.750" in report
    assert "16.0pp" in report  # gap_to_saturated_pp
    assert "clone:top50_01_a" in report
    assert "clone:top50_02_b" in report
    assert "0.910" in report


def test_format_report_handles_empty_hardest_clones():
    results = _fake_results()
    results["hardest_clones"] = []
    report = tr.format_report(results)
    assert "Hardest three top50 clones this run" in report
    assert "(none)" in report


def test_main_writes_report_and_prints_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(tr, "run_baseline", lambda **kwargs: _fake_results())
    out_path = tmp_path / "baseline.md"
    rc = tr._main(["--out", str(out_path)])
    assert rc == 0
    assert out_path.exists()
    out = capsys.readouterr().out
    assert tr.ARM_STACK in out
    assert tr.ARM_FLAGS_OFF in out
    assert "ring_size = 2" in out
