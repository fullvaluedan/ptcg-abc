"""tools/endgame_stopping.py: the U48 final-pair optimal-stopping rule.

Pins three properties: (1) king_true_estimate reuses refit_noise_model's own
family stats so the two tools never disagree on what counts as "the same
build"; (2) stopping_threshold/should_stop implement the plan's exact rule
(stop once the best draw clears mean + bonus, default bonus 40); (3) --write
lands a complete endgame_campaign block into state/current.md without
touching anything else in that state dict.
"""
import pytest

from tools import loop_state as ls
from tools import endgame_stopping as es


def test_king_true_estimate_matches_family_mean():
    ledger = [{"build": "heuristic+trolley (reclaim)", "ladder": v} for v in (450.0, 460.0, 440.0, 470.0)]
    stats = es.king_true_estimate(ledger, "heuristic+trolley (king-copy revert, 2026-07-04)")
    assert stats["n"] == 4
    assert stats["mean"] == pytest.approx(455.0)


def test_king_true_estimate_none_when_build_absent():
    ledger = [{"build": "meta_grimmsnarl", "ladder": 510.1}]
    assert es.king_true_estimate(ledger, "heuristic+trolley") is None


def test_stopping_threshold_adds_bonus():
    assert es.stopping_threshold(560.0, bonus=40) == pytest.approx(600.0)
    assert es.stopping_threshold(560.0) == pytest.approx(600.0)  # default bonus 40


def test_should_stop_boundary():
    assert es.should_stop(600.0, king_estimate=560.0, bonus=40) is True
    assert es.should_stop(599.9, king_estimate=560.0, bonus=40) is False
    assert es.should_stop(560.0, king_estimate=560.0) is False  # bare mean, no edge, never stop


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    monkeypatch.setattr(ls, "STATE_DIR", state_dir)
    monkeypatch.setattr(ls, "CURRENT_PATH", state_dir / "current.md")
    monkeypatch.setattr(ls, "HYPOTHESES_PATH", state_dir / "hypotheses.md")
    return state_dir


def test_main_write_updates_only_endgame_campaign(tmp_state):
    ledger = [{"build": "heuristic+trolley-ability", "ladder": v} for v in (560.0, 580.0, 600.0)]
    data = {
        "ledger": ledger,
        "shadow_king": {"build": "heuristic+trolley-ability", "ref": "1", "ladder": 600.0},
        "noise_model": {"margin_M": 240, "version": 3},
    }
    ls.write_current(data)

    rc = es.main(["--write", "--recorded", "2026-07-04"])
    assert rc == 0

    written = ls.read_current()
    campaign = written["endgame_campaign"]
    assert campaign["build"] == "heuristic+trolley-ability"
    assert campaign["king_true_estimate"] == pytest.approx(580.0)
    assert campaign["stop_target"] == pytest.approx(620.0)
    assert campaign["bonus"] == 40
    assert campaign["recorded"] == "2026-07-04"
    assert "endgame_stopping.py" in campaign["basis"]
    # everything else in the state dict is untouched
    assert written["shadow_king"] == data["shadow_king"]
    assert written["noise_model"] == data["noise_model"]
    assert written["ledger"] == ledger


def test_main_defaults_build_to_shadow_king(tmp_state):
    ledger = [{"build": "heuristic+trolley-ability", "ladder": v} for v in (560.0, 580.0)]
    data = {
        "ledger": ledger,
        "shadow_king": {"build": "heuristic+trolley-ability", "ref": "1", "ladder": 580.0},
    }
    ls.write_current(data)

    rc = es.main([])
    assert rc == 0
    # no --write, so nothing persisted; just confirms it resolved the default build without error
    assert ls.read_current().get("endgame_campaign") is None


def test_main_no_shadow_king_and_no_build_fails(tmp_state):
    ls.write_current({"ledger": []})
    rc = es.main([])
    assert rc == 1
