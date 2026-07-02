"""The proxy retrodiction gate (plan U24): no uncalibrated proxy may block a slot.

analysis/proxy_calibration.py decides whether an offline proxy has earned the
right to gate a ladder slot by reproducing the rank order of the five builds whose
ladder scores we already know (569.6 > 554.5 > 514.7 > 510.1 > 382.5). These tests
pin the properties the loop relies on:

  1. a proxy that reproduces the ladder ordering PASSES; the ladder scores
     themselves are the trivial perfect proxy (tau 1.0),
  2. one inverted pair still passes (tau 0.8 == threshold); two inversions fail,
  3. a proxy covering too few of the known builds fails on coverage even when what
     it does cover is perfectly ordered,
  4. ties are dropped from the tau denominator rather than counted against a proxy,
  5. the verification the plan names: the ladder-score proxy retrodicts the
     recorded ordering.
"""
import pytest

from analysis import proxy_calibration as pc


def test_perfect_proxy_passes():
    """The ladder scores are the trivial perfect proxy: tau 1.0, passes."""
    report = pc.calibrate(dict(pc.KNOWN_LADDER))
    assert report["tau"] == 1.0
    assert report["n_covered"] == 5
    assert report["discordant"] == 0
    assert report["passes"] is True


def test_ladder_ordering_retrodicted():
    """Plan U24 verification: a monotone proxy retrodicts the known ordering."""
    # Any strictly-increasing transform of the ladder preserves every pair.
    scores = {b: v * 2.0 + 100 for b, v in pc.KNOWN_LADDER.items()}
    assert pc.is_calibrated(scores) is True


def test_one_inversion_at_threshold_passes():
    """Swapping the two closest builds inverts exactly one pair -> tau 0.8, passes."""
    scores = dict(pc.KNOWN_LADDER)
    # search+trolley (514.7) and meta_grimmsnarl (510.1) are adjacent; swap them.
    scores["search+trolley"], scores["meta_grimmsnarl"] = (
        pc.KNOWN_LADDER["meta_grimmsnarl"],
        pc.KNOWN_LADDER["search+trolley"],
    )
    report = pc.calibrate(scores)
    assert report["discordant"] == 1
    assert report["tau"] == pytest.approx(0.8)
    assert report["passes"] is True


def test_two_inversions_fail():
    """A proxy that flips two pairs drops below the threshold and fails."""
    # Reverse the whole ordering: every one of the ten pairs inverts, tau -1.0.
    scores = {b: -v for b, v in pc.KNOWN_LADDER.items()}
    report = pc.calibrate(scores)
    assert report["tau"] == -1.0
    assert report["passes"] is False


def test_low_coverage_fails_even_if_ordered():
    """Three perfectly-ordered builds still fail: coverage below MIN_COVERAGE."""
    scores = {
        "heuristic+trolley": 3,
        "heuristic+benchguard": 2,
        "search+trolley": 1,
    }
    report = pc.calibrate(scores)
    assert report["n_covered"] == 3
    assert report["tau"] == 1.0  # what it covers is perfectly ordered
    assert report["passes"] is False  # but coverage < MIN_COVERAGE (4)


def test_unknown_builds_ignored():
    """Scores for builds not in the known ladder do not count toward coverage."""
    scores = dict(pc.KNOWN_LADDER)
    scores["some-future-build"] = 999.0
    report = pc.calibrate(scores)
    assert report["n_covered"] == 5
    assert "some-future-build" not in report["covered"]


def test_kendall_tau_drops_ties():
    """A pair tied in either sequence is excluded from the tau denominator."""
    # b has a tie (1, 1); the (0.0, ...) pairs against it are dropped.
    a = [3.0, 2.0, 1.0]
    b = [1.0, 1.0, 0.0]
    # pairs: (3,2)vs(1,1) tie-in-b dropped; (3,1)vs(1,0) concordant;
    #        (2,1)vs(1,0) concordant. -> 2 concordant, 0 discordant, tau 1.0
    assert pc.kendall_tau(a, b) == 1.0


def test_kendall_tau_all_ties_is_none():
    """No rank information (all tied) returns None, not a divide-by-zero."""
    assert pc.kendall_tau([1, 1, 1], [5, 5, 5]) is None


def test_kendall_tau_length_mismatch_raises():
    with pytest.raises(ValueError):
        pc.kendall_tau([1, 2, 3], [1, 2])


def test_cli_pass_and_fail(capsys):
    """The module CLI exits 0 on a passing proxy and 2 on a failing one."""
    import json

    good = json.dumps(dict(pc.KNOWN_LADDER))
    assert pc._main(["--scores", good, "--proxy", "ladder"]) == 0

    bad = json.dumps({b: -v for b, v in pc.KNOWN_LADDER.items()})
    assert pc._main(["--scores", bad]) == 2

    assert pc._main(["--scores", "not json"]) == 2
