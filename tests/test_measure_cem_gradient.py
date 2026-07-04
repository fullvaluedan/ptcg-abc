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


# --- teacher-labels source (condition (c), LOOP_BRIEF L7/U83) ---------------

def test_teacher_labels_source_needs_no_replays_argument(monkeypatch):
    """`replays` is optional now; teacher_labels alone must build a working scorer."""
    calls = []

    def fake_score_env_teacher(env_overrides, teacher_labels, split, limit, python):
        calls.append((dict(env_overrides), teacher_labels, split, limit))
        return (0.5, 100)

    monkeypatch.setattr(mg, "_score_env_teacher", fake_score_env_teacher)
    res = mg.sweep(teacher_labels="data/training", split="test", limit=999)
    assert res["baseline"] == {"agreement": 0.5, "n": 100}
    assert calls[0] == ({}, "data/training", "test", 999)
    # one baseline call plus low+high per genome dim
    assert len(calls) == 1 + 2 * len(ws.PARAM_SPACE)


def test_teacher_labels_takes_priority_over_replays_when_both_given(monkeypatch):
    def fake_score_env_teacher(env_overrides, teacher_labels, split, limit, python):
        return (0.7, 10)

    def fail_score_env(*a, **k):
        raise AssertionError("replay scorer must not run when teacher_labels is set")

    monkeypatch.setattr(mg, "_score_env_teacher", fake_score_env_teacher)
    monkeypatch.setattr(mg, "_score_env", fail_score_env)
    res = mg.sweep("some_replays_dir", teacher_labels="data/training")
    assert res["baseline"]["agreement"] == 0.7


def test_replays_only_path_still_uses_the_replay_scorer(monkeypatch):
    """Regression guard: the original real-replay path must survive the refactor."""
    calls = []

    def fake_score_env(env_overrides, replays, teams, limit, python):
        calls.append((dict(env_overrides), replays))
        return (0.4, 8)

    monkeypatch.setattr(mg, "_score_env", fake_score_env)
    res = mg.sweep("some_replays_dir")
    assert res["baseline"] == {"agreement": 0.4, "n": 8}
    assert calls[0] == ({}, "some_replays_dir")
