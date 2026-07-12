"""Worker-sharded ring A/B runner (ml_expert_review.md prescription item 1).

Every ring gate in this repo (tools/top50_ring.py, tools/threat_retreat_ring_check.py,
tools/stacked_ring_u104.py, tools/top50_flag_config.py) runs single-process at
1.7-1.9 games/s, so a properly powered n=700/arm elite-ring read costs ~13
minutes per arm sequentially. tools/parallel_gauntlet.py already solved this for
single-arm gauntlet runs (subprocess-sharded, merged in the parent); this module
reuses that exact subprocess pattern for multi-arm same-run ring A/Bs instead of
reimplementing it.

The one subtlety single-arm sharding does not have: "same-run" here means every
arm's win-rate delta must come from playing the SAME opponent-and-seat sequence
as every other arm, so ring-order noise cancels out of the comparison (the
convention every ring tool above already uses, single-process). Splitting the
n games of an arm across workers is fine (parallel_gauntlet already does that
for one arm); splitting DIFFERENT ARMS across DIFFERENT workers would not be,
since then arm A's games and arm B's games would face different opponent/seat
draws by construction. So each worker is handed one shard of the GAME-INDEX
range and plays that shard for every arm in turn (agents.heuristics imported
once, each arm's agent built once, reused for every game in the shard), using
the global game index (not a shard-local 0..size-1 index) to pick the opponent
and seat -- so the merged result is numerically identical in structure to what
one sequential process would have produced for the same total n, just computed
in parallel.

Flags are patched as module attributes on agents.heuristics (PTCG_ABILITY and
PTCG_THREAT_RETREAT are read once at import time, so env-var flipping post-import
is a no-op -- the same reason tools/stacked_ring_u104.py and
tools/threat_retreat_ring_check.py patch H._ABILITY / H._THREAT_RETREAT directly
instead of using tools/run_ab.py's env-baked-into-subprocess-env approach, which
only works when one subprocess runs exactly one arm).

Dev tool only; never shipped.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.parallel_gauntlet import _chunk_matches, default_jobs  # noqa: E402

# arm flag name -> agents.heuristics module attribute it patches. Extend this
# map (never add an env-var branch) when a future lever needs the same
# same-run-safe treatment PTCG_ABILITY and PTCG_THREAT_RETREAT get here.
FLAG_ATTR = {
    "ability": "_ABILITY",
    "threat_retreat": "_THREAT_RETREAT",
    "ranker": "_RANKER",
}


def elite_ring_names() -> list:
    """clone:top50_* opponent names (tools.top50_ring.top50_ring_names)."""
    from tools import top50_ring as t50

    return t50.top50_ring_names()


def calibrated_ring_names() -> list:
    """clone:<family> opponent names, the old 9-clone ring (tools.ring_calibrate.ring_names)."""
    from tools import ring_calibrate as rc

    return rc.ring_names()


def make_arm(key, deck, **flags) -> dict:
    """One arm spec: {"key": ..., "deck": ..., "flags": {...}}.

    flags keys must be in FLAG_ATTR (e.g. make_arm("plain", "candidate_yushin_ito",
    ability=False, threat_retreat=False)).
    """
    unknown = set(flags) - set(FLAG_ATTR)
    if unknown:
        raise ValueError(f"unknown flag(s) {sorted(unknown)}; known: {sorted(FLAG_ATTR)}")
    return {"key": key, "deck": deck, "flags": dict(flags)}


def _shard_offsets(n, jobs):
    """[(offset, size), ...] covering [0, n) in up to `jobs` near-equal shards.

    offset is the GLOBAL game index the shard starts at (cumulative sum of
    prior shard sizes), which is what makes a parallel run's per-arm merge
    numerically equivalent to a single sequential same-run pass over the same
    n (module docstring). Reuses parallel_gauntlet._chunk_matches for the
    size split so the two runners agree on how n is divided among jobs.
    """
    sizes = _chunk_matches(n, jobs)
    offsets = []
    cum = 0
    for s in sizes:
        offsets.append(cum)
        cum += s
    return list(zip(offsets, sizes))


def _make_agent(deck_name, flags):
    """Agent callable piloting deck_name with the given flags patched on agents.heuristics.

    Built once per arm per worker and reused for every game in that worker's
    shard (mirrors every existing ring tool's _make_agent_factory pattern,
    generalized from a fixed ability/threat_retreat pair to an arbitrary
    FLAG_ATTR-keyed dict so future levers need no new factory function).
    """
    from agents import heuristics as H
    from tools import opponents

    base_agent = opponents.get(f"deck:{deck_name}")
    attr_values = {FLAG_ATTR[name]: val for name, val in flags.items()}

    def agent(obs):
        orig = {attr: getattr(H, attr) for attr in attr_values}
        for attr, val in attr_values.items():
            setattr(H, attr, val)
        try:
            return base_agent(obs)
        finally:
            for attr, val in orig.items():
                setattr(H, attr, val)

    return agent


def _play_shard(arm_specs, opponent_names, offset, size, seed):
    """Play games [offset, offset+size) of EVERY arm in arm_specs, same worker.

    Returns {arm_key: {"wins", "draws", "losses", "n"}}. Each arm's agent is
    built once (not per game). Game index i (global, not shard-local) picks
    the opponent (opponent_names[i % len(opponent_names)]) and the seat
    (swap_first=(i % 2 == 1)), identical to every existing single-process ring
    tool's round-robin convention -- so every arm in this shard, and every arm
    across other shards at the same global index, faces the same opponent/seat
    draw, which is the property "same-run" depends on.
    """
    import random

    from ptcg_agent.engine import run_match
    from tools import opponents as _opponents

    random.seed(seed)
    n_ring = len(opponent_names)
    if n_ring == 0 or size <= 0:
        return {spec["key"]: {"wins": 0, "draws": 0, "losses": 0, "n": 0} for spec in arm_specs}

    results = {}
    for spec in arm_specs:
        agent_fn = _make_agent(spec["deck"], spec.get("flags", {}))
        wins = draws = losses = 0
        for i in range(offset, offset + size):
            opp_fn = _opponents.get(opponent_names[i % n_ring])
            res = run_match(agent_fn, opp_fn, swap_first=(i % 2 == 1))
            r = res["reward_a"]
            if r == 1:
                wins += 1
            elif r == -1:
                losses += 1
            else:
                draws += 1
        results[spec["key"]] = {"wins": wins, "draws": draws, "losses": losses, "n": size}
    return results


def _kill_process_tree(pid):
    """Best-effort kill of pid and every descendant.

    Discovered live during the task B part 2 powered gate (analysis/
    ranker_gate.md): on this Windows box, python_exe (a venv Scripts/
    python.exe) is itself a thin redirector that spawns the real interpreter
    as a CHILD process rather than exec-replacing its own image (Windows has
    no exec()). subprocess's own timeout handling only kills the process it
    directly spawned (the redirector); the real worker underneath -- where
    the game loop actually runs -- is orphaned and keeps burning CPU
    indefinitely. taskkill /T kills the whole tree by PID. POSIX venvs don't
    have this redirector split (real exec via symlink), but a process-group
    kill is included for parity in case a future opponent/engine call ever
    forks.
    """
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
        )
    else:
        import signal

        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                pass


def _run_shard(shard_idx, arm_specs, opponent_names, offset, size, seed, python_exe, timeout=None):
    """Run one shard (every arm, games [offset, offset+size)) in a subprocess.

    Mirrors tools.parallel_gauntlet._run_shard's inline `python -c` invocation:
    the native engine is a per-process singleton, so each shard gets its own
    subprocess. Returns (per_arm_dict, error_str), exactly one of which is None.

    timeout (seconds, None = wait forever) guards against a single
    pathological game hanging the whole run: the elite-ring PTCG_RANKER
    powered gate (analysis/ranker_gate.md) hit exactly this, two shards out
    of sixteen still running after 15+ minutes against a ~1-minute normal
    shard, apparently a specific seeded game trajectory rather than any one
    opponent (an unseeded 140-game per-opponent replay of both arms found no
    reproduction). A timed-out shard is reported as a shard_errors entry and
    excluded from the merge (the same degrade-gracefully contract
    tools.parallel_gauntlet already uses for a failed shard), not silently
    retried and not allowed to block the other shards' results.
    """
    code = (
        "import json, sys; "
        f"sys.path.insert(0, {str(_ROOT)!r}); sys.path.insert(0, {str(_ROOT / 'src')!r}); "
        # Import-order pin (see tools/threat_retreat_ring_check.py docstring):
        # our agents/ package must be cached under the bare name "agents" before
        # anything can trigger kaggle_environments' own env-local agents.py.
        "from agents import heuristics as _heuristics; "
        "from tools.parallel_ring import _play_shard; "
        f"r = _play_shard({arm_specs!r}, {opponent_names!r}, {offset!r}, {size!r}, {seed!r}); "
        "print(json.dumps(r))"
    )
    proc = subprocess.Popen(
        [python_exe, "-c", code], cwd=str(_ROOT),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        returncode = proc.returncode
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc.pid)
        try:
            proc.communicate(timeout=10)
        except Exception:
            pass
        return None, f"shard {shard_idx}: timed out after {timeout}s (killed)"
    if returncode != 0:
        tail = stderr.strip().splitlines()
        detail = tail[-1] if tail else f"exit code {returncode}"
        return None, f"shard {shard_idx}: {detail}"
    lines = stdout.strip().splitlines()
    if not lines:
        return None, f"shard {shard_idx}: no output"
    try:
        return json.loads(lines[-1]), None
    except ValueError as exc:
        return None, f"shard {shard_idx}: unparseable output ({exc})"


def _merge_arm_results(arm_specs, shard_results):
    """Sum wins/draws/losses/n per arm key across every shard's per-arm dict."""
    merged = {spec["key"]: {"wins": 0, "draws": 0, "losses": 0, "n": 0} for spec in arm_specs}
    for shard in shard_results:
        for key, counts in shard.items():
            m = merged[key]
            m["wins"] += counts["wins"]
            m["draws"] += counts["draws"]
            m["losses"] += counts["losses"]
            m["n"] += counts["n"]
    return merged


def _binomial_se(p, n):
    """Standard binomial SE of a win-rate proportion; 0.0 when n == 0."""
    return math.sqrt(p * (1 - p) / n) if n else 0.0


def _arm_stats(merged):
    """{arm_key: {..counts.., win_rate, se}} from _merge_arm_results's output."""
    stats = {}
    for key, c in merged.items():
        n = c["n"]
        wr = c["wins"] / n if n else 0.0
        stats[key] = {**c, "win_rate": wr, "se": _binomial_se(wr, n)}
    return stats


def same_run_deltas(arm_stats, baseline_key, z=1.96):
    """{arm_key: {delta_pp, se_pp, ci95_pp}} vs baseline_key, this run only.

    delta_pp is (arm win rate - baseline win rate) * 100. se_pp treats the two
    arms as independent binomial samples (true within a shard: they are
    different games, drawn from the engine's own internal entropy, even though
    they share the opponent/seat schedule) and pools shard-summed n, so
    se_pp = 100 * sqrt(se_arm^2 + se_baseline^2); ci95_pp is
    (delta_pp - z*se_pp, delta_pp + z*se_pp).
    """
    base = arm_stats[baseline_key]
    out = {}
    for key, s in arm_stats.items():
        delta_pp = (s["win_rate"] - base["win_rate"]) * 100.0
        se_pp = 100.0 * math.sqrt(s["se"] ** 2 + base["se"] ** 2)
        out[key] = {
            "delta_pp": delta_pp,
            "se_pp": se_pp,
            "ci95_pp": (delta_pp - z * se_pp, delta_pp + z * se_pp),
        }
    return out


def run_parallel_ring(arm_specs, opponent_names, n_per_arm, jobs=None, seed=0,
                       python_exe=None, baseline_key=None, shard_timeout=None) -> dict:
    """Shard n_per_arm games across up to `jobs` worker subprocesses.

    Every worker plays its shard of the global game-index range for EVERY arm
    (module docstring), so the merged per-arm W-D-L is what one sequential
    same-run pass over n_per_arm would have produced, computed in parallel.
    baseline_key defaults to the first arm in arm_specs. shard_timeout
    (seconds, None = wait forever) is passed to _run_shard: a shard that
    outlives it is killed (whole process tree) and counted as a shard error
    rather than blocking every other shard's already-finished result
    (analysis/ranker_gate.md hit exactly this against the real engine).
    Returns per-arm win_rate/se, same-run deltas vs baseline (pp, with 95%
    CI), jobs used, and any shard_errors (a shard that failed is excluded
    from the merge and reflected in a shortfall, mirroring
    tools.parallel_gauntlet's contract).
    """
    if not arm_specs:
        raise ValueError("arm_specs must be non-empty")
    if not opponent_names:
        raise RuntimeError("opponent_names must be non-empty (ring has no opponents)")
    jobs = jobs or default_jobs()
    python_exe = python_exe or sys.executable
    baseline_key = baseline_key or arm_specs[0]["key"]

    shards = _shard_offsets(n_per_arm, jobs)
    shard_results = []
    errors = []
    with ThreadPoolExecutor(max_workers=max(1, len(shards))) as ex:
        futures = [
            ex.submit(_run_shard, i, arm_specs, opponent_names, offset, size, seed + i,
                      python_exe, shard_timeout)
            for i, (offset, size) in enumerate(shards)
        ]
        for i, fut in enumerate(futures):
            result, err = fut.result()
            if err is not None:
                errors.append(err)
            else:
                shard_results.append(result)

    merged = _merge_arm_results(arm_specs, shard_results)
    arm_stats = _arm_stats(merged)
    deltas = same_run_deltas(arm_stats, baseline_key)

    completed_shards = len(shards) - len(errors)
    shortfall = n_per_arm - (merged[baseline_key]["n"] if arm_specs else 0)

    return {
        "arm_keys": [spec["key"] for spec in arm_specs],
        "baseline_key": baseline_key,
        "opponent_ring_size": len(opponent_names),
        "requested_n_per_arm": n_per_arm,
        "jobs": len(shards),
        "completed_shards": completed_shards,
        "shard_errors": errors,
        "shortfall_per_arm": shortfall,
        "arms": arm_stats,
        "same_run_deltas_pp": deltas,
    }


# ---------------------------------------------------------------------------
# CLI: the four-config elite/calibrated flag experiment (task A.3), plus a
# plain 2-arm smoke mode for the timing probe (task A.2).
# ---------------------------------------------------------------------------

FOUR_CONFIG_ARMS = [
    make_arm("plain", "candidate_yushin_ito", ability=False, threat_retreat=False),
    make_arm("ability", "candidate_yushin_ito", ability=True, threat_retreat=False),
    make_arm("threat_retreat", "candidate_yushin_ito", ability=False, threat_retreat=True),
    make_arm("both", "candidate_yushin_ito", ability=True, threat_retreat=True),
]


def _main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ring", choices=("elite", "calibrated"), default="elite")
    ap.add_argument("-n", "--matches", type=int, default=100, help="games per arm")
    ap.add_argument("--jobs", type=int, default=None, help="worker subprocesses (default: min(cores-2, 16))")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--shard-timeout", type=float, default=None,
                     help="seconds before a hung shard is killed and counted as a shard error (default: no timeout)")
    ap.add_argument("--smoke", action="store_true",
                     help="2-arm (plain vs both) smoke run instead of the full 4-config sweep")
    ap.add_argument("-o", "--out", help="write the JSON result to this path")
    args = ap.parse_args(argv)

    names = elite_ring_names() if args.ring == "elite" else calibrated_ring_names()
    arms = [FOUR_CONFIG_ARMS[0], FOUR_CONFIG_ARMS[-1]] if args.smoke else FOUR_CONFIG_ARMS

    t0 = time.time()
    result = run_parallel_ring(arms, names, args.matches, jobs=args.jobs, seed=args.seed,
                                shard_timeout=args.shard_timeout)
    elapsed = time.time() - t0
    total_games = sum(a["n"] for a in result["arms"].values())

    print(f"ring={args.ring} ({result['opponent_ring_size']} opponents), "
          f"{result['jobs']} jobs, n={args.matches}/arm, {elapsed:.1f}s")
    for key in result["arm_keys"]:
        a = result["arms"][key]
        d = result["same_run_deltas_pp"][key]
        print(f"  {key}: {a['win_rate']:.3f} +/- {a['se']:.3f} SE "
              f"({a['wins']}-{a['draws']}-{a['losses']}, n={a['n']}) "
              f"delta {d['delta_pp']:+.1f}pp (95% CI {d['ci95_pp'][0]:+.1f} to {d['ci95_pp'][1]:+.1f})")
    print(f"total games: {total_games}, wall clock: {elapsed:.1f}s, "
          f"effective {total_games / elapsed:.2f} games/s" if elapsed > 0 else "")
    if result["shard_errors"]:
        print(f"shard errors: {result['shard_errors']}")

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2))
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
