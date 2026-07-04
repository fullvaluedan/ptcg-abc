"""tools/refit_noise_model.py: family grouping, pooled residual refit, and the
state/current.md write path.

Pins three properties: (1) build names are grouped into families by stripping
the trailing parenthetical, so resubmission notes never fragment one tarball
into many single-read "families"; (2) small families (below MIN_FAMILY_N) are
reported but never pollute the pooled residual used to size M; (3) --write
lands the recommended M and a fresh basis string into state/current.md's
noise_model block without touching anything else in that state dict.
"""
import pytest

from tools import loop_state as ls
from tools import refit_noise_model as rnm


def test_family_key_strips_parenthetical():
    assert rnm.family_key("heuristic+trolley (king-copy revert, 2026-07-04)") == "heuristic+trolley"
    assert rnm.family_key("heuristic+trolley (reclaim)") == "heuristic+trolley"
    assert rnm.family_key("heuristic+trolley-ability (floor restoration)") == "heuristic+trolley-ability"
    assert rnm.family_key("heuristic+trolley-ability") == "heuristic+trolley-ability"


def test_family_reads_groups_and_skips_non_numeric():
    ledger = [
        {"build": "heuristic+trolley (reclaim)", "ladder": 600.0},
        {"build": "heuristic+trolley (king-copy revert)", "ladder": 500.0},
        {"build": "heuristic+trolley-ability", "ladder": "PENDING"},
        {"build": "heuristic+trolley-ability (ERRORed, superseded)", "ladder": "ERROR"},
        {"build": "meta_grimmsnarl", "ladder": 510.1},
    ]
    families = rnm.family_reads(ledger)
    assert families["heuristic+trolley"] == [600.0, 500.0]
    assert families["meta_grimmsnarl"] == [510.1]
    assert "heuristic+trolley-ability" not in families


def test_refit_excludes_small_families_from_pooled_residual():
    ledger = (
        [{"build": "heuristic+trolley", "ladder": v} for v in (450.0, 460.0, 440.0, 450.0)]
        + [{"build": "meta_grimmsnarl", "ladder": 510.1}]
    )
    report = rnm.refit(ledger)
    assert report["per_family"]["heuristic+trolley"]["n"] == 4
    assert report["per_family"]["meta_grimmsnarl"]["n"] == 1
    # only the qualifying family (n=4 >= MIN_FAMILY_N) feeds the pooled residual
    assert report["pooled_n"] == 4
    assert report["recommended_M"] is not None


def test_refit_recommends_worst_residual_when_it_exceeds_sigma_bound():
    # a tight cluster plus one big outlier: 2-sigma stays small, but the single
    # worst residual must still set the floor for M so it is never averaged away.
    values = [500.0, 500.0, 500.0, 500.0, 500.0, 800.0]
    ledger = [{"build": "heuristic+trolley", "ladder": v} for v in values]
    report = rnm.refit(ledger)
    mean = sum(values) / len(values)
    worst_residual = max(abs(v - mean) for v in values)
    assert report["max_abs_residual"] == pytest.approx(worst_residual)
    assert report["recommended_M"] >= worst_residual


def test_refit_reports_none_when_no_family_qualifies():
    ledger = [{"build": "meta_grimmsnarl", "ladder": 510.1}, {"build": "meta_archaludon", "ladder": 382.5}]
    report = rnm.refit(ledger)
    assert report["recommended_M"] is None
    assert report["pooled_stdev"] is None


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    monkeypatch.setattr(ls, "STATE_DIR", state_dir)
    monkeypatch.setattr(ls, "CURRENT_PATH", state_dir / "current.md")
    monkeypatch.setattr(ls, "HYPOTHESES_PATH", state_dir / "hypotheses.md")
    return state_dir


def test_main_write_updates_only_noise_model(tmp_state):
    ledger = [{"build": "heuristic+trolley", "ladder": v} for v in (450.0, 460.0, 440.0, 470.0)]
    data = {
        "ledger": ledger,
        "noise_model": {"margin_M": 150, "version": 2, "basis": "stale", "refit_by": "2026-07-15"},
        "shadow_king": {"build": "heuristic+trolley", "ref": "1", "ladder": 460.0},
    }
    ls.write_current(data)

    rc = rnm.main(["--write", "--refit-by", "2026-08-01"])
    assert rc == 0

    written = ls.read_current()
    assert written["noise_model"]["version"] == 3
    assert written["noise_model"]["margin_M"] != 150
    assert written["noise_model"]["refit_by"] == "2026-08-01"
    assert "refit_noise_model.py" in written["noise_model"]["basis"]
    # everything else in the state dict is untouched
    assert written["shadow_king"] == data["shadow_king"]
    assert written["ledger"] == ledger
