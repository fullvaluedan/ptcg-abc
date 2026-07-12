"""Tests for the four-arm flag-configuration experiment (tools/top50_flag_config.py)."""
import pytest

from tools import top50_flag_config as fc


def test_config_flags_cover_all_four_lever_combinations():
    combos = set(fc.CONFIG_FLAGS[k] for k in fc.CONFIG_ORDER)
    assert combos == {(False, False), (True, False), (False, True), (True, True)}


def test_config_flags_match_task_numbering():
    # config 1 plain, 2 +ability, 3 +threat_retreat, 4 +ability+threat_retreat
    assert fc.CONFIG_FLAGS["plain"] == (False, False)
    assert fc.CONFIG_FLAGS["ability"] == (True, False)
    assert fc.CONFIG_FLAGS["threat_retreat"] == (False, True)
    assert fc.CONFIG_FLAGS["stack"] == (True, True)


def test_arm_names_keyed_for_every_config():
    assert set(fc.ARM_NAMES) == set(fc.CONFIG_ORDER)


def test_live_submission_config_is_stack():
    assert fc.LIVE_SUBMISSION_CONFIG == "stack"
    assert fc.CONFIG_FLAGS[fc.LIVE_SUBMISSION_CONFIG] == (True, True)


def test_run_configs_on_ring_raises_with_no_opponents():
    with pytest.raises(RuntimeError):
        fc.run_configs_on_ring([], n_matches=2)


# --- arm-flag wiring (mirrors test_top50_ring.py's monkeypatch probe) -------

def test_all_four_arms_see_the_flags_their_config_declares(monkeypatch):
    pytest.importorskip("kaggle_environments")
    from agents import heuristics as H
    from tools import opponents as opp_mod

    orig_ability = H._ABILITY
    orig_threat = H._THREAT_RETREAT

    seen = {}

    def probe(key):
        def wrapped(obs):
            seen[key] = (H._ABILITY, H._THREAT_RETREAT)
            return "ok"
        monkeypatch.setattr(opp_mod, "get", lambda name: wrapped)
        ability_on, threat_on = fc.CONFIG_FLAGS[key]
        factory = fc.trc._make_agent_factory(fc.YUSHIN_DECK, ability_on=ability_on,
                                              threat_retreat_on=threat_on)
        agent = factory()
        agent({"select": None})

    for key in fc.CONFIG_ORDER:
        probe(key)

    for key in fc.CONFIG_ORDER:
        assert seen[key] == fc.CONFIG_FLAGS[key]
    # flags restored after every call
    assert H._ABILITY == orig_ability
    assert H._THREAT_RETREAT == orig_threat


# --- best/worst + same-run delta math ---------------------------------------

def _fake_elite_results():
    return {
        "plain": {"win_rate": 0.60, "wins": 6, "draws": 0, "losses": 4, "n": 10,
                   "per_opponent": {"clone:a": {"wins": 3, "draws": 0, "losses": 2, "n": 5},
                                     "clone:b": {"wins": 3, "draws": 0, "losses": 2, "n": 5}}},
        "ability": {"win_rate": 0.70, "wins": 7, "draws": 0, "losses": 3, "n": 10,
                     "per_opponent": {"clone:a": {"wins": 4, "draws": 0, "losses": 1, "n": 5},
                                       "clone:b": {"wins": 3, "draws": 0, "losses": 2, "n": 5}}},
        "threat_retreat": {"win_rate": 0.50, "wins": 5, "draws": 0, "losses": 5, "n": 10,
                             "per_opponent": {"clone:a": {"wins": 2, "draws": 0, "losses": 3, "n": 5},
                                               "clone:b": {"wins": 3, "draws": 0, "losses": 2, "n": 5}}},
        "stack": {"win_rate": 0.40, "wins": 4, "draws": 0, "losses": 6, "n": 10,
                   "per_opponent": {"clone:a": {"wins": 1, "draws": 0, "losses": 4, "n": 5},
                                     "clone:b": {"wins": 3, "draws": 0, "losses": 2, "n": 5}}},
    }


def test_best_worst_configs_picks_highest_and_lowest_win_rate():
    best, worst = fc.best_worst_configs(_fake_elite_results())
    assert best == "ability"
    assert worst == "stack"


def test_best_worst_configs_ties_break_by_config_order():
    results = _fake_elite_results()
    # tie the two lowest arms at 0.40; plain (index 0) sorts before
    # threat_retreat (index 2) among the tied group, so threat_retreat lands
    # last overall and is picked as "worst".
    results["plain"]["win_rate"] = 0.40
    results["threat_retreat"]["win_rate"] = 0.40
    results["stack"]["win_rate"] = 0.50
    best, worst = fc.best_worst_configs(results)
    assert best == "ability"
    assert worst == "threat_retreat"


def test_same_run_deltas_vs_plain_are_zero_for_plain_itself():
    deltas = fc.same_run_deltas(_fake_elite_results())
    assert deltas["plain"] == pytest.approx(0.0)
    assert deltas["ability"] == pytest.approx(10.0)
    assert deltas["stack"] == pytest.approx(-20.0)


# --- report formatting -------------------------------------------------------

def _fake_full_results():
    elite = _fake_elite_results()
    calibrated = {
        k: {"win_rate": 0.8, "wins": 4, "draws": 0, "losses": 1, "n": 5,
            "per_opponent": {"clone:x": {"wins": 4, "draws": 0, "losses": 1, "n": 5}}}
        for k in fc.CONFIG_ORDER
    }
    return {
        "elite": elite,
        "calibrated": calibrated,
        "elite_ring_size": 2,
        "calibrated_ring_size": 1,
        "hardest_clones_elite": ["clone:a", "clone:b"],
        "best_elite_config": "ability",
        "worst_elite_config": "stack",
        "elite_same_run_deltas_pp": fc.same_run_deltas(elite),
        "calibrated_same_run_deltas_pp": fc.same_run_deltas(calibrated),
    }


def test_format_report_includes_all_four_arms_and_headline():
    report = fc.format_report(_fake_full_results())
    for key in fc.CONFIG_ORDER:
        assert fc.ARM_NAMES[key] in report
    assert "0.700" in report  # ability win rate
    assert "Best against elite play" in report
    assert "Recommendation" in report
    assert "54555716" in report


def test_format_report_notes_when_best_is_not_the_live_stack():
    report = fc.format_report(_fake_full_results())
    assert "NOT config 4" in report


def test_format_report_confirms_stack_when_stack_is_best():
    results = _fake_full_results()
    results["best_elite_config"] = "stack"
    report = fc.format_report(results)
    assert "confirms config 4" in report


# --- integration: real tiny ring run ----------------------------------------

def test_run_experiment_plays_real_tiny_rings_and_reconciles_totals():
    pytest.importorskip("kaggle_environments")
    results = fc.run_experiment(n_elite=2, n_calibrated=2)
    assert set(results) >= {
        "elite", "calibrated", "elite_ring_size", "calibrated_ring_size",
        "hardest_clones_elite", "best_elite_config", "worst_elite_config",
        "elite_same_run_deltas_pp", "calibrated_same_run_deltas_pp",
    }
    for ring_key, expected_n in (("elite", 2), ("calibrated", 2)):
        for cfg_key in fc.CONFIG_ORDER:
            r = results[ring_key][cfg_key]
            assert r["n"] == expected_n
            assert r["wins"] + r["draws"] + r["losses"] == r["n"]
            assert sum(o["n"] for o in r["per_opponent"].values()) == r["n"]
    assert results["best_elite_config"] in fc.CONFIG_ORDER
    assert results["worst_elite_config"] in fc.CONFIG_ORDER


# --- CLI ---------------------------------------------------------------------

def test_main_writes_report_and_prints_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fc, "run_experiment", lambda **kwargs: _fake_full_results())
    out_path = tmp_path / "flag_config.md"
    rc = fc._main(["--out", str(out_path)])
    assert rc == 0
    assert out_path.exists()
    out = capsys.readouterr().out
    for key in fc.CONFIG_ORDER:
        assert fc.ARM_NAMES[key] in out
    assert "best_elite_config" in out
