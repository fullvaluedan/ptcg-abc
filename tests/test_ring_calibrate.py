"""Tests for the top-player clone ring calibration gate (plan U73).

The math tests exercise calibrate_from_results directly on planted win-rate
orderings (no engine, no card data), pinning the same properties
tests/test_proxy_calibration.py already pins for the underlying Kendall-tau
math, since this module reuses it rather than re-deriving it: a perfectly
retrodicted ordering passes, one inversion at the threshold still passes, two
inversions fail, ties are dropped rather than counted against the ring, and a
build set smaller than MIN_COVERAGE refuses to conclude even if what it does
cover is perfectly ordered. A final integration test actually plays a tiny
real ring (needs the local engine + card data, skipped otherwise) to prove the
build factories and ring wiring produce a playable match.
"""
import pytest

from tools import ring_calibrate as rc


def _results_from_scores(scores):
    """A run_ring-shaped results dict from a plain {build: win_rate} mapping."""
    return {name: {"win_rate": wr, "wins": 0, "draws": 0, "losses": 0, "n": 0}
            for name, wr in scores.items()}


def test_perfect_ordering_passes():
    # Any strictly-increasing transform of the known ladder scores preserves
    # every pair, so it retrodicts the ladder ordering perfectly.
    scores = {b: v / 1000.0 for b, v in rc.KNOWN_LADDER.items()}
    report = rc.calibrate_from_results(_results_from_scores(scores))
    assert report["tau"] == 1.0
    assert report["n_covered"] == 6
    assert report["passes"] is True


def test_one_inversion_at_threshold_passes():
    # search+trolley (514.7) and meta_grimmsnarl (510.1) are adjacent; swapping
    # their win rates inverts exactly one of the fifteen pairs.
    scores = dict(rc.KNOWN_LADDER)
    scores["search+trolley"], scores["meta_grimmsnarl"] = (
        rc.KNOWN_LADDER["meta_grimmsnarl"], rc.KNOWN_LADDER["search+trolley"],
    )
    report = rc.calibrate_from_results(_results_from_scores(scores))
    assert report["discordant"] == 1
    assert report["tau"] == pytest.approx((14 - 1) / 15)
    assert report["tau"] >= rc.CORRELATION_THRESHOLD
    assert report["passes"] is True


def test_reversed_ordering_fails():
    scores = {b: -v for b, v in rc.KNOWN_LADDER.items()}
    report = rc.calibrate_from_results(_results_from_scores(scores))
    assert report["tau"] == -1.0
    assert report["passes"] is False


def test_low_coverage_refuses_to_conclude():
    scores = {
        "heuristic+trolley": 0.9,
        "heuristic+benchguard": 0.6,
        "search+trolley": 0.3,
    }
    report = rc.calibrate_from_results(_results_from_scores(scores))
    assert report["n_covered"] == 3
    assert report["tau"] == 1.0  # what it covers is perfectly ordered
    assert report["passes"] is False  # but below MIN_COVERAGE (4)


def test_unknown_build_ignored():
    scores = dict(rc.KNOWN_LADDER)
    scores["some-future-build"] = 999.0
    report = rc.calibrate_from_results(_results_from_scores(scores))
    assert report["n_covered"] == 6
    assert "some-future-build" not in report["covered"]


def test_calibrate_from_results_preserves_ring_results():
    scores = _results_from_scores(dict(rc.KNOWN_LADDER))
    scores["heuristic+trolley"]["wins"] = 12
    report = rc.calibrate_from_results(scores)
    assert report["ring_results"] == scores


def test_ring_names_matches_clone_family_names():
    from tools import opponents

    assert rc.ring_names() == [f"clone:{fam}" for fam in opponents.clone_family_names()]


def test_run_ring_raises_without_ring_opponents(monkeypatch):
    monkeypatch.setattr(rc, "ring_names", lambda: [])
    with pytest.raises(RuntimeError):
        rc.run_ring(n_matches=2)


def test_main_pass_and_fail(monkeypatch, capsys):
    good = {
        "tau": 1.0, "n_covered": 6, "n_known": 6, "concordant": 15, "discordant": 0,
        "min_coverage": rc.MIN_COVERAGE, "threshold": rc.CORRELATION_THRESHOLD,
        "passes": True, "covered": sorted(rc.KNOWN_LADDER), "ring_results": {},
    }
    monkeypatch.setattr(rc, "calibrate", lambda **kwargs: good)
    assert rc._main([]) == 0
    assert "PASS" in capsys.readouterr().out

    bad = dict(good, tau=-1.0, passes=False)
    monkeypatch.setattr(rc, "calibrate", lambda **kwargs: bad)
    assert rc._main([]) == 2
    assert "FAIL" in capsys.readouterr().out


def test_ring_plays_a_real_tiny_ring():
    # Integration: two of the fast (non-search) historical builds play two
    # games each against the real clone ring, with zero-length runs excluded.
    # Needs the local engine + card data, matching test_opponents.py's own
    # integration tests; excludes search+trolley to keep this test fast.
    pytest.importorskip("kaggle_environments")
    builds = {
        "heuristic+benchguard": rc.BUILD_FACTORIES["heuristic+benchguard"],
        "trolley_thick": rc.BUILD_FACTORIES["trolley_thick"],
    }
    results = rc.run_ring(n_matches=2, builds=builds)
    assert set(results) == set(builds)
    for r in results.values():
        assert r["n"] == 2
        assert r["wins"] + r["draws"] + r["losses"] == 2
        assert 0.0 <= r["win_rate"] <= 1.0


def test_no_benchguard_agent_restores_thin_bench_after_use():
    pytest.importorskip("kaggle_environments")
    from agents import heuristics as H

    orig = H.THIN_BENCH
    agent = rc._no_benchguard_trolley_agent()
    agent({"select": None})  # deck-selection step: no THIN_BENCH read on this path
    assert H.THIN_BENCH == orig
