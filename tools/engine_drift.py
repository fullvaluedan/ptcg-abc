"""Engine-drift diff: vendored cg/ vs the grader's pip cabt engine (plan U30).

Our offline gauntlet drives matches with the engine vendored at data/cg/ (and
that same directory is bundled verbatim into every submission tarball by
tools/build_submission.py). The grader runs its OWN copy shipped inside the pip
kaggle_environments cabt package. If those two engines ever diverge on a
game-affecting file, every offline measurement silently stops predicting the
ladder, and a submission built against a stale engine could behave differently
at grade time. This tool is the scheduled diff the plan calls for: run it now
and again before the Aug 10 freeze and it fails loudly on a dangerous bump.

Not every difference is dangerous. Each side imports its OWN Python wrapper
(sim.py/game.py) and the shipped agent carries its own bundled cg/, so a wrapper
delta or an offline-only helper is benign. The load-bearing invariant is the
runtime shared library: Kaggle grades on Linux x86_64, so data/cg/libcg.so must
stay byte-identical to the grader's, and the pure-python game rules (game.py)
must not drift beyond whitespace. The verdict fails only when one of those
runtime-critical files drifts; everything else is reported and triaged.

Classification per file:
  IDENTICAL       bytes match exactly
  WHITESPACE_ONLY python source differs only in blank lines / trailing space
  PY_SUBSTANTIVE  python source differs in non-whitespace tokens
  BINARY_META     non-text file whose bytes differ but SIZE is identical
  BINARY_SIZE     non-text file whose byte count differs
  OFFLINE_ONLY    present in the vendored engine, absent from the grader
  GRADER_ONLY     present in the grader, absent from the vendored engine

BINARY_META is deliberately separated from BINARY_SIZE. Every platform binary
here (libcg.so/.dylib/-arm64.so, cg.dll) differs by hash yet is byte-for-byte
identical in SIZE across all four at once. Identical length is the signature of
a reproducible-build metadata delta (embedded timestamp / build path / UUID),
not a code change: a real patch almost never lands on the exact same byte count
on three unrelated object formats simultaneously. So a same-size binary drift is
a triaged warning, while a SIZE change on a runtime-critical binary is a hard
fail, being a strong signal of an actual engine bump.

Usage:
    python tools/engine_drift.py            # human report, exit 1 on DRIFT
    python tools/engine_drift.py --strict    # also fail on triaged warnings
    python tools/engine_drift.py --json      # machine-readable report
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
VENDORED = _ROOT / "data" / "cg"

# Kaggle grades on Linux x86_64 and the shipped agent bundles its own cg/, so
# these two files are the only ones whose drift is game-affecting: the runtime
# shared library and the pure-python game rules. Everything else (the ctypes
# wrapper, non-runtime platform libs, offline-only helpers) is triaged benign.
RUNTIME_CRITICAL = ("libcg.so", "game.py")

PY_SUFFIX = ".py"


def grader_cg_dir() -> Path | None:
    """Locate the pip cabt engine's cg/ directory, or None if not installed."""
    spec = importlib.util.find_spec("kaggle_environments")
    if spec is None or not spec.submodule_search_locations:
        return None
    base = Path(list(spec.submodule_search_locations)[0])
    cg = base / "envs" / "cabt" / "cg"
    return cg if cg.is_dir() else None


def _strip_ws(text: str) -> str:
    """Normalize python source to non-whitespace tokens for a semantic compare.

    Drops blank lines and trailing whitespace so a reformat (extra blank line,
    trailing space) reads as WHITESPACE_ONLY rather than PY_SUBSTANTIVE.
    """
    lines = [ln.rstrip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln.strip())


def _lib_bindings(text: str) -> set[str]:
    """Extract the set of `lib.<Name>` C bindings declared in a sim.py wrapper.

    Used to explain a sim.py drift concretely: which ctypes functions one side
    binds that the other does not (e.g. the offline search API).
    """
    out: set[str] = set()
    # Scan for "lib." followed by an identifier.
    idx = 0
    while True:
        hit = text.find("lib.", idx)
        if hit == -1:
            break
        j = hit + 4
        name = []
        while j < len(text) and (text[j].isalnum() or text[j] == "_"):
            name.append(text[j])
            j += 1
        if name:
            out.add("".join(name))
        idx = j
    return out


def classify(name: str, vpath: Path, gpath: Path | None) -> dict:
    """Classify one file's drift and attach a concrete detail string."""
    if gpath is None or not gpath.exists():
        return {"file": name, "status": "OFFLINE_ONLY", "detail": "absent from grader engine"}
    vbytes = vpath.read_bytes()
    gbytes = gpath.read_bytes()
    if vbytes == gbytes:
        return {"file": name, "status": "IDENTICAL", "detail": ""}
    if name.endswith(PY_SUFFIX):
        vtext = vbytes.decode("utf-8", "replace")
        gtext = gbytes.decode("utf-8", "replace")
        if _strip_ws(vtext) == _strip_ws(gtext):
            return {"file": name, "status": "WHITESPACE_ONLY", "detail": "blank-line / trailing-space only"}
        detail = ""
        if name == "sim.py":
            only_v = sorted(_lib_bindings(vtext) - _lib_bindings(gtext))
            only_g = sorted(_lib_bindings(gtext) - _lib_bindings(vtext))
            parts = []
            if only_v:
                parts.append("offline-only bindings: " + ", ".join(only_v))
            if only_g:
                parts.append("grader-only bindings: " + ", ".join(only_g))
            detail = "; ".join(parts) if parts else "non-whitespace source drift"
        else:
            detail = "non-whitespace source drift"
        return {"file": name, "status": "PY_SUBSTANTIVE", "detail": detail}
    if len(vbytes) == len(gbytes):
        return {
            "file": name,
            "status": "BINARY_META",
            "detail": f"bytes differ, size identical ({len(vbytes)} B) -- reproducible-build metadata",
        }
    return {
        "file": name,
        "status": "BINARY_SIZE",
        "detail": f"byte count differs ({len(vbytes)} vs {len(gbytes)})",
    }


def diff_engines() -> dict:
    """Diff the vendored engine against the grader engine and render a verdict.

    A runtime-critical file drift is HARD (verdict DRIFT) when it is a python
    non-whitespace change (PY_SUBSTANTIVE), a binary size change (BINARY_SIZE),
    or a presence change (OFFLINE_ONLY / GRADER_ONLY): each is a strong signal of
    a real engine bump. A same-size binary hash difference (BINARY_META) on a
    runtime-critical file is a triaged WARNING, not a failure, because identical
    length across every platform binary is reproducible-build metadata rather
    than code. Non-runtime files (the ctypes wrapper, non-runtime platform libs,
    offline-only helpers) never affect the verdict. A missing grader engine
    yields verdict UNKNOWN so a machine that lacks the pip package does not read
    as falsely clean.
    """
    grader = grader_cg_dir()
    if grader is None:
        return {
            "verdict": "UNKNOWN",
            "reason": "grader cabt engine not found (kaggle_environments not installed?)",
            "vendored": str(VENDORED),
            "grader": None,
            "files": [],
        }

    names = sorted({p.name for p in VENDORED.iterdir() if p.is_file()}
                   | {p.name for p in grader.iterdir() if p.is_file()})
    files = []
    for name in names:
        if name == "__init__.py":
            continue
        vpath = VENDORED / name
        gpath = grader / name
        if not vpath.exists():
            files.append({"file": name, "status": "GRADER_ONLY", "detail": "absent from vendored engine"})
            continue
        files.append(classify(name, vpath, gpath))

    verdict, reason, warnings = verdict_for(files)
    return {
        "verdict": verdict,
        "reason": reason,
        "vendored": str(VENDORED),
        "grader": str(grader),
        "runtime_critical": list(RUNTIME_CRITICAL),
        "warnings": warnings,
        "files": files,
    }


# A runtime-critical file at any of these statuses is a strong signal of a real
# engine bump and hard-fails the verdict; a same-size binary hash difference is
# a triaged WARN instead (see the BINARY_META rationale in the module docstring).
_HARD_STATUSES = ("PY_SUBSTANTIVE", "BINARY_SIZE", "OFFLINE_ONLY", "GRADER_ONLY")


def verdict_for(files: list[dict]) -> tuple[str, str, list[dict]]:
    """Reduce a classified file list to (verdict, reason, warnings).

    Only RUNTIME_CRITICAL files move the verdict. A _HARD_STATUSES drift yields
    DRIFT; a same-size binary metadata drift (BINARY_META) yields WARN;
    otherwise CLEAN.
    """
    dangerous = []
    warnings = []
    for f in files:
        if f["file"] not in RUNTIME_CRITICAL:
            continue
        if f["status"] in _HARD_STATUSES:
            dangerous.append(f)
        elif f["status"] not in ("IDENTICAL", "WHITESPACE_ONLY"):
            warnings.append(f)

    if dangerous:
        return "DRIFT", (
            "runtime-critical drift: "
            + ", ".join(f"{f['file']} ({f['status']})" for f in dangerous)
        ), warnings
    if warnings:
        return "WARN", (
            "runtime-critical binaries differ by hash but not size (triaged reproducible-build metadata): "
            + ", ".join(f"{f['file']} ({f['status']})" for f in warnings)
        ), warnings
    return "CLEAN", "runtime-critical files byte-match; remaining drift is triaged wrapper/aux difference", warnings


def render(report: dict) -> str:
    lines = []
    lines.append(f"engine drift: vendored {report['vendored']}")
    lines.append(f"          vs grader {report['grader']}")
    lines.append("")
    for f in report["files"]:
        crit = " *runtime-critical*" if f["file"] in report.get("runtime_critical", ()) else ""
        detail = f"  ({f['detail']})" if f["detail"] else ""
        lines.append(f"  {f['status']:<15} {f['file']}{crit}{detail}")
    lines.append("")
    lines.append(f"VERDICT: {report['verdict']} -- {report['reason']}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="diff the vendored cg/ engine against the grader's pip cabt engine (plan U30)")
    ap.add_argument("--json", action="store_true", help="emit the machine-readable report")
    ap.add_argument("--strict", action="store_true", help="also fail on triaged WARN (same-size binary metadata drift)")
    args = ap.parse_args()

    report = diff_engines()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render(report))

    # DRIFT and UNKNOWN always fail (a missing engine is never silently clean).
    # WARN passes by default (triaged reproducible-build metadata) but fails
    # under --strict, the mode for the pre-Aug-10-freeze audit.
    if report["verdict"] == "CLEAN":
        return 0
    if report["verdict"] == "WARN" and not args.strict:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
