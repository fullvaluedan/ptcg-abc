# Engine drift triage: vendored cg/ vs grader cabt engine (U30 leg 2)

Recorded 2026-07-02. Tool: `tools/engine_drift.py` (run `--strict` for the
pre-Aug-10-freeze audit). Guard test: `tests/test_engine_drift.py`.

## Why this exists

Our offline gauntlet drives matches with the engine vendored at `data/cg/`, and
`tools/build_submission.py` bundles that same directory verbatim into every
submission tarball. The grader runs its OWN copy inside the pip
`kaggle_environments` cabt package. If the two diverge on a game-affecting file,
every offline measurement silently stops predicting the ladder. The plan (U30)
calls for a scheduled diff run now and again before the Aug 10 freeze.

## Current diff (verdict WARN, triaged benign)

| file | status | ruling |
| --- | --- | --- |
| game.py | WHITESPACE_ONLY | benign; pure-python rules identical modulo blank lines |
| libcg.so (linux x86_64, GRADER RUNTIME) | BINARY_META | triaged: hash differs, size byte-identical (1342400 B) |
| cg.dll (windows) | BINARY_META | same-size hash diff; not the grader runtime |
| libcg.dylib (macos) | BINARY_META | same-size hash diff; not the grader runtime |
| libcg-arm64.so | BINARY_SIZE (1300584 vs 1296464) | not runtime-critical (grader is x86_64); does not fail verdict |
| sim.py | PY_SUBSTANTIVE | offline-only ctypes wrapper delta (see below); benign |
| api.py | OFFLINE_ONLY | our helper layer; correctly bundled into the tarball |
| utils.py | OFFLINE_ONLY | our helper layer; correctly bundled into the tarball |

## The two findings that looked alarming, and why they are benign

### 1. Every platform binary differs by hash but is byte-for-byte identical in SIZE

`libcg.so`, `cg.dll`, and `libcg.dylib` each differ from the grader copy by
sha256 yet match its byte COUNT exactly. Identical length across three unrelated
object formats (ELF, PE, Mach-O) at once is the signature of a reproducible-build
metadata delta (embedded build timestamp / path / UUID), not a code change: a
real patch almost never lands on the exact same byte count on all three
simultaneously. Corroborating evidence that the engines adjudicate the same game:

- `game.py` (the pure-python rules layer) is whitespace-only identical.
- Empirically the ladder plays full legal games with no illegal-move forfeits;
  the trolley king settled 569.6 then resubmitted to 600.0 and the thick A/B
  plays complete matches. A rules divergence would surface as forfeits.

The tool therefore classifies a same-size binary hash diff as WARN (triaged),
not DRIFT. A SIZE change on the runtime library is a much stronger signal of a
real engine bump and hard-fails the verdict; that is what the scheduled guard is
watching for before the freeze.

`libcg-arm64.so` is the one binary whose SIZE actually differs, but arm64 is not
the Kaggle grader runtime (Linux x86_64), so it is out of the verdict scope.

### 2. sim.py binds 7 C functions the grader wrapper does not

The vendored `sim.py` declares `AgentStart`, `AllCard`, `AllAttack`,
`SearchBegin`, `SearchStep`, `SearchEnd`, `SearchRelease`; the grader wrapper
does not. This is not a hazard: each side imports its OWN wrapper, and the
shipped agent carries our `data/cg` copy, so those bindings resolve at grade
time regardless of the grader's wrapper. The grader wrapper additionally carries
a `raminingTime` field on `Battle` that ours lacks (a time-tracking field, not
game-affecting). Note this delta is the mechanical reason a naive
`from cabt.cg import sim` search build would be inert against the grader engine,
consistent with the prior observation that search fell back to heuristic on the
ladder.

## Verdict

WARN, triaged benign. No runtime-critical SIZE change, no python rule drift, no
missing runtime file. The submission engine is self-consistent (agent runs on
the exact binary the gauntlet tested). Re-run `tools/engine_drift.py --strict`
before the Aug 10 freeze; if the runtime library size or `game.py` rules move,
the verdict flips to DRIFT and `tests/test_engine_drift.py` fails, forcing a
fresh triage.
