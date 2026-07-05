"""Tests for tools/score_candidate_decks.py (plan U39 step 2 correction).

Pure-logic tests for promote_verdicts (no engine, no real games) plus a
filesystem test for candidate_deck_names. score_candidates itself plays real
matches through ring_calibrate's _ring_win_rate and is exercised indirectly
via the CLI in a real ring run, not unit-tested here (mirrors
tools/ring_calibrate.py's own test boundary: run_ring is real-engine,
calibrate_from_results is the pure-logic seam that gets unit tests).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools import score_candidate_decks as scd  # noqa: E402


def test_candidate_deck_names_lists_only_candidate_prefix(tmp_path):
    (tmp_path / "candidate_alpha.csv").write_text("1\n", encoding="utf-8")
    (tmp_path / "candidate_beta.csv").write_text("2\n", encoding="utf-8")
    (tmp_path / "trolley.csv").write_text("3\n", encoding="utf-8")
    (tmp_path / "meta_archaludon.csv").write_text("4\n", encoding="utf-8")

    names = scd.candidate_deck_names(tmp_path)

    assert names == ["candidate_alpha", "candidate_beta"]


def test_candidate_deck_names_empty_when_dir_missing(tmp_path):
    assert scd.candidate_deck_names(tmp_path / "nope") == []


def test_promote_verdicts_flags_material_beats_baseline():
    results = {
        "trolley": {"win_rate": 0.60, "wins": 12, "draws": 0, "losses": 8, "n": 20},
        "candidate_strong": {"win_rate": 0.80, "wins": 16, "draws": 0, "losses": 4, "n": 20},
        "candidate_weak": {"win_rate": 0.55, "wins": 11, "draws": 0, "losses": 9, "n": 20},
        "candidate_tie": {"win_rate": 0.65, "wins": 13, "draws": 0, "losses": 7, "n": 20},
    }

    verdicts = scd.promote_verdicts(results, margin=0.10)

    assert "trolley" not in verdicts
    assert verdicts["candidate_strong"]["promote"] is True
    assert verdicts["candidate_strong"]["delta"] == 0.20000000000000007 or abs(
        verdicts["candidate_strong"]["delta"] - 0.20
    ) < 1e-9
    assert verdicts["candidate_weak"]["promote"] is False
    assert verdicts["candidate_tie"]["promote"] is False  # +0.05 delta, under the 0.10 margin


def test_promote_verdicts_exact_margin_boundary_promotes():
    results = {
        "trolley": {"win_rate": 0.50},
        "candidate_exact": {"win_rate": 0.60},
    }
    verdicts = scd.promote_verdicts(results, margin=0.10)
    assert verdicts["candidate_exact"]["promote"] is True


def test_promote_verdicts_empty_without_baseline():
    results = {"candidate_only": {"win_rate": 0.70}}
    assert scd.promote_verdicts(results, baseline="trolley") == {}


def test_promote_verdicts_negative_delta_when_candidate_worse():
    results = {
        "trolley": {"win_rate": 0.80},
        "candidate_bad": {"win_rate": 0.40},
    }
    verdicts = scd.promote_verdicts(results)
    assert verdicts["candidate_bad"]["delta"] < 0
    assert verdicts["candidate_bad"]["promote"] is False
