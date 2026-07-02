"""Tests for the PIMC diagnostic (plan U27).

Cg-free: only the pure metric functions (leaf_correlation, bias,
disambiguation_slope, verdict, and their helpers) are exercised, on synthetic
value matrices and (turn, revealed) point lists. The native capture/rollout path
is never touched, so the card engine does not load.
"""
import pytest

from analysis import pimc_diagnostic as P


# --- _argmax / _modal_share --------------------------------------------------

def test_argmax_breaks_ties_to_lower_index():
    assert P._argmax([0.5, 0.5, 0.5]) == 0
    assert P._argmax([0.1, 0.9, 0.2]) == 1
    assert P._argmax([-1.0, -1.0, -0.5]) == 2


def test_modal_share_all_agree_is_one():
    assert P._modal_share([2, 2, 2, 2]) == 1.0


def test_modal_share_even_split():
    assert P._modal_share([0, 1, 2, 3]) == pytest.approx(0.25)
    assert P._modal_share([0, 0, 1, 1]) == pytest.approx(0.5)


def test_modal_share_empty_is_zero():
    assert P._modal_share([]) == 0.0


# --- _pearson ----------------------------------------------------------------

def test_pearson_constant_vector_is_none():
    assert P._pearson([1.0, 1.0, 1.0], [0.0, 1.0, 2.0]) is None
    assert P._pearson([0.0, 1.0, 2.0], [5.0, 5.0, 5.0]) is None


def test_pearson_perfect_positive():
    assert P._pearson([0.0, 1.0, 2.0], [1.0, 3.0, 5.0]) == pytest.approx(1.0)


def test_pearson_perfect_negative():
    assert P._pearson([0.0, 1.0, 2.0], [2.0, 1.0, 0.0]) == pytest.approx(-1.0)


# --- leaf_correlation --------------------------------------------------------

def test_leaf_correlation_worlds_agree_high():
    # Every world ranks candidate 1 best -> modal share 1.0, strong correlation.
    matrix = [[0.0, 1.0, -1.0], [-0.5, 0.9, -1.0], [0.1, 1.0, -0.8]]
    lc = P.leaf_correlation(matrix)
    assert lc["modal_share"] == 1.0
    assert lc["pairwise_corr"] is not None
    assert lc["n_worlds"] == 3


def test_leaf_correlation_worlds_disagree_low():
    # Each world prefers a different candidate -> modal share 1/3.
    matrix = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    lc = P.leaf_correlation(matrix)
    assert lc["modal_share"] == pytest.approx(1 / 3)


def test_leaf_correlation_single_candidate_cannot_fuse():
    # One option per world cannot suffer strategy fusion; share defaults to 1.0.
    lc = P.leaf_correlation([[1.0], [1.0]])
    assert lc["modal_share"] == 1.0
    assert lc["pairwise_corr"] is None


def test_leaf_correlation_all_saturated_skips_pairwise():
    # Every world is a flat win: modal share is a degenerate 1.0 and every value
    # vector is constant, so no pairwise correlation is defined.
    matrix = [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0]]
    lc = P.leaf_correlation(matrix)
    assert lc["modal_share"] == 1.0
    assert lc["pairwise_corr"] is None


# --- bias --------------------------------------------------------------------

def test_bias_signed_mean():
    assert P.bias([[1.0, 1.0], [1.0, 1.0]]) == pytest.approx(1.0)
    assert P.bias([[1.0, -1.0], [1.0, -1.0]]) == pytest.approx(0.0)
    assert P.bias([[-1.0, -0.5]]) == pytest.approx(-0.75)


# --- disambiguation_slope ----------------------------------------------------

def test_disambiguation_slope_positive_when_revealed_climbs():
    points = [(1, 0.05), (2, 0.10), (3, 0.15), (4, 0.20)]
    assert P.disambiguation_slope(points) == pytest.approx(0.05)


def test_disambiguation_slope_flat_is_zero():
    points = [(1, 0.3), (2, 0.3), (3, 0.3)]
    assert P.disambiguation_slope(points) == pytest.approx(0.0)


def test_disambiguation_slope_single_point_no_divide_by_zero():
    assert P.disambiguation_slope([(5, 0.9)]) == 0.0
    assert P.disambiguation_slope([]) == 0.0


def test_disambiguation_slope_all_same_turn_no_divide_by_zero():
    # Fully-observed / degenerate: identical x values would divide by zero.
    assert P.disambiguation_slope([(3, 0.2), (3, 0.8)]) == 0.0


# --- verdict -----------------------------------------------------------------

def test_verdict_favorable_when_all_pass():
    v = P.verdict(leaf_corr=0.8, disambig_slope=0.05, bias_abs=0.5)
    assert v["favorable"] is True
    assert v["branch"] == "U45 belief-weighted search"
    assert v["leaf_ok"] and v["disambig_ok"] and v["bias_ok"]


def test_verdict_unfavorable_on_low_leaf_correlation():
    v = P.verdict(leaf_corr=0.4, disambig_slope=0.05, bias_abs=0.5)
    assert v["favorable"] is False
    assert v["branch"] == "U46 doubled deck-aware breadth"
    assert v["leaf_ok"] is False


def test_verdict_unfavorable_on_low_disambiguation():
    v = P.verdict(leaf_corr=0.8, disambig_slope=0.005, bias_abs=0.5)
    assert v["favorable"] is False
    assert v["disambig_ok"] is False


def test_verdict_unfavorable_on_extreme_bias():
    v = P.verdict(leaf_corr=0.8, disambig_slope=0.05, bias_abs=0.99)
    assert v["favorable"] is False
    assert v["bias_ok"] is False


def test_thresholds_are_the_registered_values():
    assert P.LEAF_CORR_MIN == 0.55
    assert P.DISAMBIG_SLOPE_MIN == 0.02
    assert P.BIAS_ABS_MAX == 0.9
