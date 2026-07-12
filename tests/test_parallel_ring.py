import json

import pytest

from tools import parallel_ring as pr


# ---------------------------------------------------------------------------
# Shard math (no real engine)
# ---------------------------------------------------------------------------

def test_shard_offsets_covers_range_with_cumulative_offsets():
    shards = pr._shard_offsets(17, 5)
    assert sum(size for _, size in shards) == 17
    assert all(size > 0 for _, size in shards)
    offsets = [offset for offset, _ in shards]
    assert offsets[0] == 0
    # every shard's offset is the running sum of prior sizes, so the union of
    # [offset, offset+size) ranges is exactly [0, 17) with no gap or overlap.
    cum = 0
    for offset, size in shards:
        assert offset == cum
        cum += size
    assert cum == 17


def test_shard_offsets_zero_matches():
    assert pr._shard_offsets(0, 5) == []


def test_shard_offsets_caps_jobs_at_match_count():
    shards = pr._shard_offsets(3, 10)
    assert len(shards) == 3
    assert sum(size for _, size in shards) == 3


def test_make_arm_rejects_unknown_flag():
    with pytest.raises(ValueError):
        pr.make_arm("bad", "candidate_yushin_ito", not_a_real_flag=True)


def test_make_arm_shape():
    arm = pr.make_arm("plain", "candidate_yushin_ito", ability=False, threat_retreat=True)
    assert arm == {
        "key": "plain",
        "deck": "candidate_yushin_ito",
        "flags": {"ability": False, "threat_retreat": True},
    }


def test_flag_attr_supports_ranker():
    # PTCG_RANKER (analysis/ranker_outcome_model.md) reuses the same
    # same-run-safe module-attribute patching as ability/threat_retreat, so
    # the powered gate (task B part 2) can toggle it via make_arm.
    assert pr.FLAG_ATTR["ranker"] == "_RANKER"
    arm = pr.make_arm("ranker_on", "candidate_yushin_ito", ranker=True)
    assert arm["flags"] == {"ranker": True}


# ---------------------------------------------------------------------------
# Merge logic (no real engine)
# ---------------------------------------------------------------------------

def test_merge_arm_results_sums_across_shards():
    arm_specs = [pr.make_arm("plain", "d"), pr.make_arm("both", "d", ability=True)]
    shard_results = [
        {"plain": {"wins": 3, "draws": 0, "losses": 2, "n": 5},
         "both": {"wins": 4, "draws": 0, "losses": 1, "n": 5}},
        {"plain": {"wins": 2, "draws": 1, "losses": 2, "n": 5},
         "both": {"wins": 1, "draws": 0, "losses": 4, "n": 5}},
    ]
    merged = pr._merge_arm_results(arm_specs, shard_results)
    assert merged["plain"] == {"wins": 5, "draws": 1, "losses": 4, "n": 10}
    assert merged["both"] == {"wins": 5, "draws": 0, "losses": 5, "n": 10}


def test_merge_arm_results_empty_shards_keeps_zeroed_arms():
    arm_specs = [pr.make_arm("plain", "d")]
    merged = pr._merge_arm_results(arm_specs, [])
    assert merged == {"plain": {"wins": 0, "draws": 0, "losses": 0, "n": 0}}


# ---------------------------------------------------------------------------
# Win-rate / SE / same-run delta math (no real engine)
# ---------------------------------------------------------------------------

def test_binomial_se_known_value():
    # p=0.5, n=100 -> se = sqrt(0.25/100) = 0.05
    assert pr._binomial_se(0.5, 100) == pytest.approx(0.05)


def test_binomial_se_zero_n_is_zero():
    assert pr._binomial_se(0.7, 0) == 0.0


def test_arm_stats_computes_win_rate_and_se():
    merged = {"plain": {"wins": 85, "draws": 0, "losses": 15, "n": 100}}
    stats = pr._arm_stats(merged)
    assert stats["plain"]["win_rate"] == pytest.approx(0.85)
    assert stats["plain"]["se"] == pytest.approx((0.85 * 0.15 / 100) ** 0.5)


def test_same_run_deltas_baseline_is_zero():
    arm_stats = {
        "plain": {"wins": 85, "draws": 0, "losses": 15, "n": 100, "win_rate": 0.85, "se": 0.0357},
        "ability": {"wins": 69, "draws": 0, "losses": 31, "n": 100, "win_rate": 0.69, "se": 0.0463},
    }
    deltas = pr.same_run_deltas(arm_stats, "plain")
    assert deltas["plain"]["delta_pp"] == pytest.approx(0.0)
    assert deltas["ability"]["delta_pp"] == pytest.approx(-16.0)
    se_pp = deltas["ability"]["se_pp"]
    assert se_pp == pytest.approx(100.0 * (0.0357 ** 2 + 0.0463 ** 2) ** 0.5, rel=1e-3)
    lo, hi = deltas["ability"]["ci95_pp"]
    assert lo < deltas["ability"]["delta_pp"] < hi


# ---------------------------------------------------------------------------
# run_parallel_ring orchestration with a stubbed _run_shard (no real engine,
# no real subprocess) -- mirrors test_parallel_gauntlet.py's monkeypatch style.
# ---------------------------------------------------------------------------

def test_run_parallel_ring_merges_stubbed_shards(monkeypatch):
    arm_specs = [pr.make_arm("plain", "d"), pr.make_arm("both", "d", ability=True, threat_retreat=True)]

    def fake_run_shard(shard_idx, specs, opponent_names, offset, size, seed, python_exe, timeout=None):
        # deterministic canned per-shard result, keyed by real arm keys
        return (
            {"plain": {"wins": size, "draws": 0, "losses": 0, "n": size},
             "both": {"wins": 0, "draws": 0, "losses": size, "n": size}},
            None,
        )

    monkeypatch.setattr(pr, "_run_shard", fake_run_shard)
    result = pr.run_parallel_ring(arm_specs, ["clone:a", "clone:b"], 10, jobs=3, seed=0)

    assert result["arms"]["plain"]["n"] == 10
    assert result["arms"]["plain"]["wins"] == 10
    assert result["arms"]["plain"]["win_rate"] == pytest.approx(1.0)
    assert result["arms"]["both"]["win_rate"] == pytest.approx(0.0)
    assert result["same_run_deltas_pp"]["both"]["delta_pp"] == pytest.approx(-100.0)
    assert result["shard_errors"] == []
    assert result["shortfall_per_arm"] == 0
    assert result["baseline_key"] == "plain"


def test_run_parallel_ring_reports_shortfall_on_shard_error(monkeypatch):
    arm_specs = [pr.make_arm("plain", "d")]

    def fake_run_shard(shard_idx, specs, opponent_names, offset, size, seed, python_exe, timeout=None):
        if shard_idx == 1:
            return None, f"shard {shard_idx}: boom"
        return {"plain": {"wins": size, "draws": 0, "losses": 0, "n": size}}, None

    monkeypatch.setattr(pr, "_run_shard", fake_run_shard)
    result = pr.run_parallel_ring(arm_specs, ["clone:a"], 10, jobs=2, seed=0)

    assert result["shard_errors"] == ["shard 1: boom"]
    assert result["shortfall_per_arm"] > 0
    assert result["arms"]["plain"]["n"] == result["requested_n_per_arm"] - result["shortfall_per_arm"]


def test_run_parallel_ring_rejects_empty_arms():
    with pytest.raises(ValueError):
        pr.run_parallel_ring([], ["clone:a"], 10)


def test_run_parallel_ring_rejects_empty_ring():
    with pytest.raises(RuntimeError):
        pr.run_parallel_ring([pr.make_arm("plain", "d")], [], 10)


# ---------------------------------------------------------------------------
# _run_shard subprocess plumbing (subprocess.Popen stubbed, no real engine)
# ---------------------------------------------------------------------------

class _FakePopen:
    """Stand-in for subprocess.Popen with a scripted .communicate()."""

    def __init__(self, args, cwd=None, stdout=None, stderr=None, text=None,
                 pid=4242, returncode=0, out="", err="", raise_timeout=False):
        self.args = args
        self.pid = pid
        self.returncode = returncode
        self._out = out
        self._err = err
        self._raise_timeout = raise_timeout
        self._raised_once = False

    def communicate(self, timeout=None):
        if self._raise_timeout and not self._raised_once:
            self._raised_once = True
            raise pr.subprocess.TimeoutExpired(self.args, timeout)
        return self._out, self._err


def test_run_shard_parses_subprocess_stdout(monkeypatch):
    captured = {}
    out = json.dumps({"plain": {"wins": 1, "draws": 0, "losses": 0, "n": 1}}) + "\n"

    def fake_popen(args, **kwargs):
        captured["args"] = args
        return _FakePopen(args, returncode=0, out=out, err="")

    monkeypatch.setattr(pr.subprocess, "Popen", fake_popen)
    result, err = pr._run_shard(0, [pr.make_arm("plain", "d")], ["clone:a"], 0, 1, 0, "python")
    assert err is None
    assert result == {"plain": {"wins": 1, "draws": 0, "losses": 0, "n": 1}}
    assert captured["args"][0] == "python"


def test_run_shard_reports_nonzero_exit(monkeypatch):
    monkeypatch.setattr(
        pr.subprocess, "Popen",
        lambda args, **kwargs: _FakePopen(args, returncode=1, out="", err="Traceback...\nRuntimeError: boom\n"),
    )
    result, err = pr._run_shard(2, [pr.make_arm("plain", "d")], ["clone:a"], 0, 1, 0, "python")
    assert result is None
    assert "shard 2" in err
    assert "RuntimeError: boom" in err


def test_run_shard_kills_process_tree_on_timeout(monkeypatch):
    # Reproduces the real failure this guards against (analysis/ranker_gate.md):
    # a shard that never returns must be killed (whole tree, see
    # _kill_process_tree's docstring) and reported as a shard error, not
    # block the run forever.
    killed = {}
    monkeypatch.setattr(pr, "_kill_process_tree", lambda pid: killed.setdefault("pid", pid))
    monkeypatch.setattr(
        pr.subprocess, "Popen",
        lambda args, **kwargs: _FakePopen(args, pid=9999, raise_timeout=True),
    )
    result, err = pr._run_shard(5, [pr.make_arm("plain", "d")], ["clone:a"], 0, 1, 0, "python", timeout=30)
    assert result is None
    assert "timed out" in err
    assert "shard 5" in err
    assert killed["pid"] == 9999
