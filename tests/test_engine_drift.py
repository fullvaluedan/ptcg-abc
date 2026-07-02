"""U30 leg 2: engine-drift diff between the vendored cg/ and the grader engine.

The vendored engine at data/cg/ drives the offline gauntlet and is bundled into
every submission tarball; the grader ships its own copy inside the pip cabt
package. tools/engine_drift.py guards against a game-affecting divergence. These
tests lock two things: (1) the classifier and verdict reducer behave as designed
on synthetic inputs, and (2) the CURRENT real engine pair reads exactly as
triaged (game.py whitespace-only, sim.py an offline-only search-API wrapper
delta, libcg.so a same-size reproducible-build metadata WARN). If a future pip
bump changes the runtime library SIZE or the python game rules, verdict flips to
DRIFT and the real-state test fails, forcing a fresh triage before the freeze.
"""

from tools import engine_drift


# --- classifier unit tests (synthetic files via tmp_path) ---

def _write(p, data):
    if isinstance(data, str):
        p.write_text(data, encoding="utf-8")
    else:
        p.write_bytes(data)
    return p


def test_identical_bytes(tmp_path):
    v = _write(tmp_path / "a.py", "x = 1\n")
    g = _write(tmp_path / "b.py", "x = 1\n")
    assert engine_drift.classify("a.py", v, g)["status"] == "IDENTICAL"


def test_whitespace_only_py(tmp_path):
    v = _write(tmp_path / "v.py", "x = 1\n\n\ny = 2\n")
    g = _write(tmp_path / "g.py", "x = 1\ny = 2   \n")
    assert engine_drift.classify("game.py", v, g)["status"] == "WHITESPACE_ONLY"


def test_py_substantive(tmp_path):
    v = _write(tmp_path / "v.py", "x = 1\n")
    g = _write(tmp_path / "g.py", "x = 2\n")
    assert engine_drift.classify("game.py", v, g)["status"] == "PY_SUBSTANTIVE"


def test_binary_meta_same_size(tmp_path):
    v = _write(tmp_path / "v.so", b"\x00\x01\x02\x03")
    g = _write(tmp_path / "g.so", b"\x03\x02\x01\x00")
    r = engine_drift.classify("libcg.so", v, g)
    assert r["status"] == "BINARY_META"
    assert "metadata" in r["detail"]


def test_binary_size_change(tmp_path):
    v = _write(tmp_path / "v.so", b"\x00\x01\x02\x03")
    g = _write(tmp_path / "g.so", b"\x00\x01\x02")
    assert engine_drift.classify("libcg.so", v, g)["status"] == "BINARY_SIZE"


def test_offline_only_when_grader_missing(tmp_path):
    v = _write(tmp_path / "v.py", "x = 1\n")
    assert engine_drift.classify("api.py", v, tmp_path / "nope.py")["status"] == "OFFLINE_ONLY"


def test_sim_py_detail_names_offline_bindings(tmp_path):
    v = _write(tmp_path / "v.py", "lib.Select\nlib.SearchBegin\nlib.SearchStep\n")
    g = _write(tmp_path / "g.py", "lib.Select\n")
    r = engine_drift.classify("sim.py", v, g)
    assert r["status"] == "PY_SUBSTANTIVE"
    assert "SearchBegin" in r["detail"] and "SearchStep" in r["detail"]
    assert "Select" not in r["detail"]  # shared binding is not reported as a delta


# --- helper unit tests ---

def test_strip_ws_drops_blank_and_trailing():
    assert engine_drift._strip_ws("a\n\n  \nb   \n") == "a\nb"


def test_lib_bindings_extracts_names():
    got = engine_drift._lib_bindings("lib.BattleStart.restype = x\nlib.Select(y)\n")
    assert got == {"BattleStart", "Select"}


# --- verdict reducer unit tests (the dangerous cases the real engines lack) ---

def test_verdict_clean_when_runtime_identical():
    files = [
        {"file": "libcg.so", "status": "IDENTICAL", "detail": ""},
        {"file": "game.py", "status": "WHITESPACE_ONLY", "detail": ""},
        {"file": "sim.py", "status": "PY_SUBSTANTIVE", "detail": ""},  # not runtime-critical
    ]
    verdict, _, warnings = engine_drift.verdict_for(files)
    assert verdict == "CLEAN"
    assert warnings == []


def test_verdict_warn_on_runtime_binary_meta():
    files = [{"file": "libcg.so", "status": "BINARY_META", "detail": ""}]
    verdict, _, warnings = engine_drift.verdict_for(files)
    assert verdict == "WARN"
    assert warnings and warnings[0]["file"] == "libcg.so"


def test_verdict_drift_on_runtime_size_change():
    files = [{"file": "libcg.so", "status": "BINARY_SIZE", "detail": ""}]
    assert engine_drift.verdict_for(files)[0] == "DRIFT"


def test_verdict_drift_on_runtime_py_rule_change():
    files = [{"file": "game.py", "status": "PY_SUBSTANTIVE", "detail": ""}]
    assert engine_drift.verdict_for(files)[0] == "DRIFT"


def test_non_runtime_drift_does_not_fail_verdict():
    # arm64 lib is not the grader runtime; a size change there is not DRIFT.
    files = [{"file": "libcg-arm64.so", "status": "BINARY_SIZE", "detail": ""}]
    assert engine_drift.verdict_for(files)[0] == "CLEAN"


# --- real-engine state lock (the actual guard) ---

def test_real_engine_state_is_the_triaged_baseline():
    """The current vendored-vs-grader pair must read exactly as triaged.

    Skips only if the pip cabt engine is absent (verdict UNKNOWN). Otherwise it
    pins: game.py whitespace-only, sim.py the offline search-API wrapper delta,
    libcg.so a same-size metadata WARN, api.py/utils.py offline-only. A real
    engine bump breaks this and forces re-triage.
    """
    report = engine_drift.diff_engines()
    if report["verdict"] == "UNKNOWN":
        import pytest
        pytest.skip("grader cabt engine not installed")

    by = {f["file"]: f["status"] for f in report["files"]}
    assert report["verdict"] == "WARN"
    assert by["game.py"] == "WHITESPACE_ONLY"
    assert by["sim.py"] == "PY_SUBSTANTIVE"
    assert by["libcg.so"] == "BINARY_META"
    assert by["api.py"] == "OFFLINE_ONLY"
    assert by["utils.py"] == "OFFLINE_ONLY"

    sim = next(f for f in report["files"] if f["file"] == "sim.py")
    assert "SearchBegin" in sim["detail"]  # offline-only search API, absent from grader wrapper
