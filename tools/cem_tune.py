"""CEM self-improvement optimizer over the pilot+eval weight vector (plan U6).

OFFLINE ONLY. Never bundled into a submission. This is the engine's first real
gear: it searches the weight vector named in tools/weight_space.py with the
Cross-Entropy Method, scoring each candidate by how well it BEATS THE DIVERSE
POOL (tools/opponents.pool, plan U4) and MATCHES THE TOP PLAYERS' MOVES
(analysis/move_ranking_validator, plan U5), never by beating itself. Its output
is a small env-override map (weight_space.vector_to_env) staged for the sole
arbiter, the live ladder A/B via tools/build_submission.py --env (KTD1, KTD4).
Offline win rate is a FILTER; the ladder decides.

Why CEM (KTD3). The genome is 11 numbers (weight_space.PARAM_SPACE); CEM is the
reliable, tiny-to-ship optimizer for a vector this size, is derivative-free, and
is embarrassingly parallel across the existing gauntlet. A learned value net (P4)
has more headroom but only earns its keep after CEM plateaus.

Injected-variance regularization is NON-NEGOTIABLE (KTD3, R2). Plain CEM shrinks
the sampling std toward zero as the elite set agrees, and collapses onto whatever
the first few iterations favored, the textbook premature-convergence failure. So
every iteration re-inflates the std by a fixed floor (`injected_variance`) after
fitting the elites, keeping exploration alive for the whole run. With the floor at
zero the distribution provably collapses (tests/test_cem_tune.py pins both the
prevented collapse and the collapse-without-it, documenting why the trick is
mandatory).

Scale invariance. PARAM_SPACE mixes an int bench width (range 1 to 4) with float
eval weights (range 0 to 0.4), so a single scalar std cannot mean the same thing
across dims. The CEM math runs in NORMALIZED [0, 1] space (each dim mapped through
its bounds), so `init_std` and `injected_variance` are one meaningful fraction for
every knob; fitness always receives the DENORMALIZED real vector.

Ship-faithful evaluation. A candidate's weights reach the pilot exactly the way a
baked build does: the parent sets the PTCG_W_* env from vector_to_env and spawns a
fresh subprocess that imports agents/heuristics.py and search/eval.py, which read
those keys at import (the same clean-runtime contract the grader uses). No
in-process module reload, so a candidate can never leak its constants into the
next candidate's evaluation.

Honest limitation. The subprocess sets one process-global env, so both seats in
the offline gauntlet share the candidate's weights; the anti-self-beater guard is
the DECK diversity of the pool (U4) plus the expert-move validator (U5), not a
per-seat weight split. The ladder A/B remains the only decision.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools import weight_space as ws  # noqa: E402


# --- CEM core (pure, scale-invariant in normalized [0, 1] space) -----------

@dataclass
class CEMConfig:
    """CEM hyperparameters. Defaults follow KTD3 (population ~50, elite ~10)."""

    population: int = 50
    elite: int = 10
    iterations: int = 20
    init_std: float = 0.25
    # NON-NEGOTIABLE exploration floor re-added to the std every iteration; the
    # module docstring and tests explain why zero here collapses the search.
    injected_variance: float = 0.05
    seed: int = 0


def _bounds_arrays():
    """(low, high) float arrays in PARAM_SPACE order, for normalize/denormalize."""
    b = ws.bounds()
    low = np.array([lo for lo, _ in b], dtype=float)
    high = np.array([hi for _, hi in b], dtype=float)
    return low, high


def normalize(vector) -> np.ndarray:
    """Map a real weight vector into the unit box using the PARAM_SPACE bounds.

    A degenerate dim (high == low) maps to 0; every result is clipped to [0, 1] so
    an out-of-bounds input never escapes the box the sampler works in.
    """
    low, high = _bounds_arrays()
    span = np.where(high > low, high - low, 1.0)
    return np.clip((np.asarray(vector, dtype=float) - low) / span, 0.0, 1.0)


def denormalize(unit) -> np.ndarray:
    """Map a unit-box point back to the real weight space (inverse of normalize).

    The unit input is clipped first, so a sample just outside the box lands on the
    bound rather than past it; casting to the constant's int/float type is left to
    weight_space.vector_to_env at the apply step.
    """
    low, high = _bounds_arrays()
    span = high - low
    return low + np.clip(np.asarray(unit, dtype=float), 0.0, 1.0) * span


def sample_population(mean, std, size, rng) -> np.ndarray:
    """`size` Gaussian samples in normalized space, clipped to the unit box.

    Each row is one candidate in [0, 1]^d; the caller denormalizes before scoring.
    """
    mean = np.asarray(mean, dtype=float)
    draws = rng.normal(loc=mean, scale=std, size=(size, mean.shape[0]))
    return np.clip(draws, 0.0, 1.0)


def update_distribution(elite_units, injected_variance):
    """Refit the sampling distribution to the elites, then re-inject exploration.

    mean = elite mean; std = elite std PLUS the injected-variance floor. The
    additive floor is the whole anti-collapse mechanism: because elite std is
    non-negative, the returned std is always at least `injected_variance`, so the
    search can never freeze (set it to zero only to demonstrate the collapse).
    """
    elite_units = np.asarray(elite_units, dtype=float)
    mean = elite_units.mean(axis=0)
    std = elite_units.std(axis=0) + injected_variance
    return mean, std


def cem_optimize(fitness, config=None, mean0=None, callback=None):
    """Run CEM over the weight vector; return the best candidate and history.

    `fitness(real_vector) -> float` is any scalar objective; it receives the
    DENORMALIZED real vector so callers never touch normalized space. A non-finite
    score is treated as the worst possible, so a candidate that errors out (the
    subprocess fitness returns -inf) is simply never selected. The result carries
    the best real vector, its ready-to-bake env map (vector_to_env), the per
    iteration history (best/elite-mean fitness and mean std, so a run can be seen
    to keep exploring), and the final distribution.
    """
    config = config or CEMConfig()
    rng = np.random.default_rng(config.seed)
    dim = len(ws.PARAM_SPACE)
    mean = normalize(ws.defaults() if mean0 is None else mean0)
    std = np.full(dim, config.init_std, dtype=float)
    best = {"fitness": float("-inf"), "vector": list(ws.defaults())}
    history = []

    for iteration in range(config.iterations):
        pop = sample_population(mean, std, config.population, rng)
        vectors = [denormalize(u) for u in pop]
        raw = np.array([fitness(list(v)) for v in vectors], dtype=float)
        scores = np.where(np.isfinite(raw), raw, -np.inf)

        order = np.argsort(scores)[::-1]
        elite_idx = order[: config.elite]
        top = order[0]
        if scores[top] > best["fitness"]:
            best = {"fitness": float(scores[top]), "vector": list(vectors[top])}

        mean, std = update_distribution(pop[elite_idx], config.injected_variance)
        elite_scores = scores[elite_idx]
        finite_elite = elite_scores[np.isfinite(elite_scores)]
        history.append(
            {
                "iteration": iteration,
                "best_fitness": best["fitness"],
                "elite_mean_fitness": (
                    float(finite_elite.mean()) if finite_elite.size else None
                ),
                "std_mean": float(std.mean()),
            }
        )
        if callback is not None:
            callback(history[-1])

    best["env"] = ws.vector_to_env(best["vector"])
    return {
        "best": best,
        "history": history,
        "final_mean": list(denormalize(mean)),
        "final_std": [float(s) for s in std],
    }


# --- fitness: beat the diverse pool AND match the top players' moves --------

def aggregate_fitness(win_rate, agreement, w_pool=0.5, w_val=0.5):
    """One scalar from the two offline filters; a missing component drops out.

    The pool win rate (U4) and the held-out expert move agreement (U5) are the two
    signals; either may be None when its half was not requested (e.g. no replay
    source), in which case only the present component counts. With BOTH missing the
    candidate has no evidence and scores -inf so CEM never selects it on nothing.
    Both signals are in [0, 1], so with the default equal weights fitness is a
    simple average, comparable across candidates on a fixed evaluation.
    """
    parts = []
    if win_rate is not None:
        parts.append(w_pool * win_rate)
    if agreement is not None:
        parts.append(w_val * agreement)
    if not parts:
        return float("-inf")
    return float(sum(parts))


def _run_evaluator(env, payload, python):
    """Spawn the internal --evaluate subprocess with `env` set; return its stdout.

    The candidate's PTCG_W_* keys are already in `env`; the child reads them at
    import, exactly like a baked build. Kept as a seam so tests can substitute a
    canned runner and exercise the env-building and parsing without the engine.
    """
    proc = subprocess.run(
        [python, "-m", "tools.cem_tune", "--evaluate"],
        input=payload,
        env=env,
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _parse_evaluator_output(out):
    """Extract the {win_rate, agreement} JSON payload from evaluator stdout.

    Some transitively-imported modules (kaggle_environments' OpenSpiel loader,
    among others) log INFO/WARNING lines to stdout on import, ahead of
    `_internal_evaluate`'s own print, so stdout is not guaranteed to be pure
    JSON. That print is always the last line written, so scan from the end and
    parse the first line that decodes rather than assuming line 1 is the
    payload (a real pooled CEM run silently scored every candidate -inf this
    way: every subprocess raised JSONDecodeError, which subprocess_fitness maps
    to the worst score).
    """
    for line in reversed(out.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise ValueError("evaluator produced no parseable JSON output")


def evaluate_vector(vector, spec, python=None, runner=None):
    """Score one real weight vector by spawning a fresh, env-baked evaluator.

    Builds the child env from the current environment plus vector_to_env(vector)
    (so an un-tuned default vector adds nothing), hands the child the evaluation
    spec as JSON on stdin, and folds its reported win rate and agreement into one
    number via aggregate_fitness. `runner` defaults to the real subprocess and is
    injectable for tests.
    """
    env = dict(os.environ)
    env.update(ws.vector_to_env(vector))
    runner = runner or _run_evaluator
    out = runner(env, json.dumps(spec), python or sys.executable)
    data = _parse_evaluator_output(out)
    return aggregate_fitness(
        data.get("win_rate"),
        data.get("agreement"),
        spec.get("w_pool", 0.5),
        spec.get("w_val", 0.5),
    )


def subprocess_fitness(spec, python=None):
    """A fitness closure over `spec` for cem_optimize; errors score -inf.

    A candidate whose evaluation subprocess fails (a bad state, a crashed match)
    must not abort the whole CEM run, so any exception maps to the worst score and
    the candidate is dropped.
    """

    def fitness(vector):
        try:
            return evaluate_vector(vector, spec, python=python)
        except Exception:
            return float("-inf")

    return fitness


def _internal_evaluate(spec):
    """Run the requested offline filters in THIS (env-baked) process, return dict.

    `pool_matches` > 0 runs the gauntlet as the heuristic pilot against the U4
    diverse pool (falling back to the built-in heuristic if the pool is empty).
    `replays` runs the U5 move-ranking validator over that dataset for the pilot;
    if `replays` is absent, `teacher_labels` (a U83 self-play JSONL file or dir)
    is scored instead via `analysis.teacher_labels.agreement`, the same {"n",
    "agree", "agreement"} shape, so a run can fit against the much larger
    teacher-self-play sample when the real-ladder replay sample is not given.
    Both are optional; a caller can score on one signal alone. Defensive: a
    component that raises reports None rather than aborting.
    """
    win_rate = None
    n = int(spec.get("pool_matches", 0) or 0)
    if n > 0:
        try:
            from tools.gauntlet import run_gauntlet
            from tools import opponents

            pool = opponents.pool() or ["heuristic"]
            win_rate = run_gauntlet("heuristic", pool, n)["win_rate"]
        except Exception:
            win_rate = None

    agreement = None
    replays = spec.get("replays")
    if replays:
        try:
            from analysis import move_ranking_validator as mrv
            from agents.heuristics import choose

            teams = spec.get("teams") or list(mrv.DEFAULT_EXPERT_TEAMS)
            pairs = mrv.load_replays(replays, limit=spec.get("limit"))
            # Tune on one canonical md5 bucket only (KD4). Without this the CEM
            # would fit train+test together and its held-out validation would not
            # be held out; "train" is the correct bucket for a tuning run, leaving
            # "test" clean for the pre-registered offline filter. The same
            # split_of rule every other held-out unit uses (analysis/replay_trace,
            # tools/per_archetype_baseline) so membership never drifts.
            split = spec.get("split")
            if split in ("train", "test"):
                from analysis import replay_trace

                pairs = [
                    (rep, label)
                    for rep, label in pairs
                    if replay_trace.split_of(label) == split
                ]
            result = mrv.score_replays(pairs, choose, teams)
            agreement = result["agreement"]
        except Exception:
            agreement = None

    teacher_labels_path = spec.get("teacher_labels")
    if agreement is None and teacher_labels_path:
        try:
            from analysis import teacher_labels as tl
            from agents.heuristics import choose

            records = list(tl.load_records(teacher_labels_path, limit=spec.get("limit")))
            # Same KD4 held-out discipline as the replays branch above, just
            # keyed on the self-play game identity (tl.match_key) instead of a
            # ladder episode label.
            split = spec.get("split")
            if split in ("train", "test"):
                records = [rec for rec in records if tl.split_of(rec) == split]
            result = tl.agreement(records, choose)
            agreement = result["agreement"]
        except Exception:
            agreement = None

    return {"win_rate": win_rate, "agreement": agreement}


# --- CLI -------------------------------------------------------------------

def _run_cem(args) -> int:
    spec = {
        "pool_matches": args.pool_matches,
        "replays": args.replays,
        "teacher_labels": args.teacher_labels,
        "limit": args.limit,
        "split": args.split,
        "teams": args.teams,
        "w_pool": args.w_pool,
        "w_val": args.w_val,
    }
    config = CEMConfig(
        population=args.population,
        elite=args.elite,
        iterations=args.iterations,
        init_std=args.init_std,
        injected_variance=args.injected_variance,
        seed=args.seed,
    )

    def report(rec):
        em = rec["elite_mean_fitness"]
        em = f"{em:.4f}" if em is not None else "n/a"
        print(
            f"  iter {rec['iteration']:>3}  best={rec['best_fitness']:.4f}  "
            f"elite_mean={em}  std={rec['std_mean']:.4f}"
        )

    result = cem_optimize(subprocess_fitness(spec), config=config, callback=report)
    best = result["best"]
    print(f"\nbest fitness: {best['fitness']:.4f}")
    print("staged env overrides (bake via build_submission.py --env):")
    if best["env"]:
        for k in ws.keys():
            if k in best["env"]:
                print(f"  {k}={best['env'][k]}")
    else:
        print("  (none: the default vector won; ship stays byte-identical)")
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nfull result written to {args.out}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--evaluate",
        action="store_true",
        help="internal mode: read an eval spec on stdin, print {win_rate, "
        "agreement} JSON using the PTCG_W_* env already set by the parent",
    )
    ap.add_argument("--population", type=int, default=50)
    ap.add_argument("--elite", type=int, default=10)
    ap.add_argument("--iterations", type=int, default=20)
    ap.add_argument("--init-std", dest="init_std", type=float, default=0.25)
    ap.add_argument(
        "--injected-variance",
        dest="injected_variance",
        type=float,
        default=0.05,
        help="the NON-NEGOTIABLE exploration floor; do not set to 0 for a real run",
    )
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--pool-matches",
        dest="pool_matches",
        type=int,
        default=40,
        help="gauntlet matches vs the U4 diverse pool per candidate (0 to skip)",
    )
    ap.add_argument(
        "--replays",
        default=None,
        help="a .zip or dir of episode JSONs for the U5 move-ranking validator",
    )
    ap.add_argument(
        "--teacher-labels",
        dest="teacher_labels",
        default=None,
        help="a .jsonl file or dir from tools/teacher_selfplay.py (U83); scored "
        "only when --replays is not given",
    )
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument(
        "--split",
        choices=("train", "test", "all"),
        default="train",
        help="md5 bucket to score the agreement channel on; 'train' keeps the "
        "held-out 'test' bucket clean for the pre-registered offline filter",
    )
    ap.add_argument("--teams", nargs="+", default=None)
    ap.add_argument("--w-pool", dest="w_pool", type=float, default=0.5)
    ap.add_argument("--w-val", dest="w_val", type=float, default=0.5)
    ap.add_argument("--out", default=None, help="write the full result JSON here")
    args = ap.parse_args(argv)

    if args.evaluate:
        spec = json.loads(sys.stdin.read() or "{}")
        print(json.dumps(_internal_evaluate(spec)))
        return 0
    return _run_cem(args)


if __name__ == "__main__":
    raise SystemExit(main())
