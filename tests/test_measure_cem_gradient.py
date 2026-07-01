"""Tests for the CEM-gradient diagnostic (analysis/measure_cem_gradient.py).

Engine- and dataset-free: the subprocess scorer is replaced by a canned callable,
so these pin the orchestration (one row per genome dim, correct low/high env per
dim, the inert-dim delta) without loading the native engine or the replay data.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis import measure_cem_gradient as mg  # noqa: E402
from tools import weight_space as ws  # noqa: E402


def test_sweep_has_one_row_per_genome_dim():
    """Every PARAM_SPACE dim gets exactly one leverage row, in order."""
    res = mg.sweep("ignored", score=lambda env: (0.5, 10))
    assert [r["dim"] for r in res["rows"]] == ws.keys()
    assert res["baseline"] == {"agreement": 0.5, "n": 10}


def test_sweep_passes_low_and_high_env_per_dim():
    """Each dim is scored with its own low then high override, others empty.

    The canned scorer records the env map it was handed, so the sequence of calls
    is (baseline {}, dim0 low, dim0 high, dim1 low, dim1 high, ...). For a dim whose
    bound differs from the default the override names that one key; a bound equal to
    the default yields an empty map (a byte-identical build).
    """
    seen = []

    def score(env):
        seen.append(dict(env))
        return (0.2, 5)

    mg.sweep("ignored", score=score)
    assert seen[0] == {}  # baseline
    # The first genome dim is PTCG_W_THIN_BENCH default 2, bounds 1..4: both bounds
    # differ from the default, so both are non-empty single-key overrides.
    key0, default0, low0, high0, cast0 = ws.PARAM_SPACE[0]
    assert seen[1] == {key0: str(cast0(low0))}
    assert seen[2] == {key0: str(cast0(high0))}


def test_inert_dim_reports_zero_delta():
    """A scorer that ignores the env yields delta 0.0 for every dim (all inert)."""
    res = mg.sweep("ignored", score=lambda env: (0.3, 7))
    assert all(r["delta"] == 0.0 for r in res["rows"])


def test_delta_is_absolute_difference():
    """delta = abs(agr_high - agr_low), computed from the two bound scores.

    The scorer returns a higher agreement whenever the override sets THIN_BENCH to
    its low bound, so that dim shows a positive delta and the rest stay flat.
    """
    key0 = ws.PARAM_SPACE[0][0]

    def score(env):
        return (0.9 if env.get(key0) == "1" else 0.4, 3)

    res = mg.sweep("ignored", score=score)
    row0 = next(r for r in res["rows"] if r["dim"] == key0)
    assert abs(row0["delta"] - 0.5) < 1e-9
    assert all(r["delta"] == 0.0 for r in res["rows"] if r["dim"] != key0)


def test_none_agreement_yields_none_delta():
    """A scorer that returns no agreement (None) propagates a None delta, not a crash."""
    res = mg.sweep("ignored", score=lambda env: (None, 0))
    assert all(r["delta"] is None for r in res["rows"])
