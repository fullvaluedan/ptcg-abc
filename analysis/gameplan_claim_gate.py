"""Claim / prediction gates for the U91 comprehension-track blocks (plan U91).

The miner (analysis/gameplan_mine) distills a target family's within-turn
sequencing, energy-banking, and win-condition-timing blocks (attach_before_attack,
energy_banking, game_length_turns) into win-vs-loss aggregates. That is enough to
notice a pattern but not enough to trust it: a small-sample win/loss gap can be
noise, and a pattern that only describes the mined data (rather than predicting
top-player play the miner never looked at) is not a real game-plan lesson. This
module is the two-gate discipline the loop brief names for this track:

  CLAIM GATE:  both the winning and losing splits carry >= MIN_CLAIM_N qualifying
               observations, and a bootstrap CI (default 90%) on
               mean(win) - mean(loss) excludes zero. Establishes the win-vs-loss
               gap is real, not sampling noise, on the data it was mined from.
  PREDICTION GATE: the SAME pattern, mined only on the KD4 train split, is
               checked against the KD4 held-out test split: the test split's own
               winning-side estimate must fall inside a bootstrap CI built from
               the train split alone. A pattern that only claim-gates on its own
               data but fails to predict held-out play is cut, not shipped.

Both gates need the miner's PRE-FOLD values, so callers must mine with
keep_raw=True (mine()'s block["raw"] = {"win": [...], "loss": [...]}); the
committed aggregate docs never carry those raw lists, only this gate's summary
numbers (n, means, CI bounds, pass/fail).

Bootstrapping is a fixed-seed, pure-Python percentile bootstrap (no numpy/scipy
dependency): reproducible across runs, cg-free, dev tool only, never shipped.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.gameplan_mine import episode_family_streams, mine  # noqa: E402
from analysis.move_ranking_validator import load_replays  # noqa: E402
from analysis.replay_trace import episode_id_of, split_of  # noqa: E402
from tools.expert_census import build_signatures  # noqa: E402
from tools.isolation import derived_path  # noqa: E402

# The three U91 comprehension-track blocks these gates apply to (the original six
# target/timing blocks already have their own emission bars in gameplan_seeds).
CLAIM_BLOCKS = ("attach_before_attack", "energy_banking", "game_length_turns")

MIN_CLAIM_N = 200
CLAIM_CI = 0.90
N_RESAMPLES = 2000
SEED = 0


# --- bootstrap ---------------------------------------------------------------

def _percentile_bounds(values, ci: float, n_resamples: int):
    lo_i = int((1 - ci) / 2 * n_resamples)
    hi_i = int((1 + ci) / 2 * n_resamples) - 1
    return values[lo_i], values[max(hi_i, lo_i)]


def bootstrap_mean_ci(values, ci: float = CLAIM_CI, n_resamples: int = N_RESAMPLES, seed: int = SEED):
    """Percentile bootstrap CI for the mean of `values`, or (None, None) if empty.

    A fixed `seed` makes the interval reproducible across runs on the same data.
    Pure given a fixed seed.
    """
    if not values:
        return None, None
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_resamples):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return _percentile_bounds(means, ci, n_resamples)


def bootstrap_diff_ci(
    win_values, loss_values, ci: float = CLAIM_CI, n_resamples: int = N_RESAMPLES, seed: int = SEED
):
    """Percentile bootstrap CI for mean(win_values) - mean(loss_values).

    Resamples each side independently (same rng, same draw count) so the
    interval is over the win-vs-loss GAP the claim gate tests against zero.
    (None, None) if either side is empty. Pure given a fixed seed.
    """
    if not win_values or not loss_values:
        return None, None
    rng = random.Random(seed)
    nw, nl = len(win_values), len(loss_values)
    diffs = []
    for _ in range(n_resamples):
        w = sum(win_values[rng.randrange(nw)] for _ in range(nw)) / nw
        l = sum(loss_values[rng.randrange(nl)] for _ in range(nl)) / nl
        diffs.append(w - l)
    diffs.sort()
    return _percentile_bounds(diffs, ci, n_resamples)


# --- gates ---------------------------------------------------------------

def _clean_values(block: dict, side: str) -> list:
    """block["raw"][side] as clean floats: True/False -> 1.0/0.0, None dropped."""
    raw = block["raw"][side]
    if block["kind"] == "categorical":
        return [1.0 if v else 0.0 for v in raw if v is not None]
    return [float(v) for v in raw if v is not None]


def claim_gate(
    block: dict,
    min_n: int = MIN_CLAIM_N,
    ci: float = CLAIM_CI,
    n_resamples: int = N_RESAMPLES,
    seed: int = SEED,
) -> dict:
    """Whether a mined block's win-vs-loss gap is real, not sampling noise.

    Requires both the winning and losing splits to carry >= `min_n` qualifying
    observations (turns for the two per-turn blocks, episodes for
    game_length_turns) AND a bootstrap `ci` CI on mean(win) - mean(loss) that
    excludes zero. `block` must come from mine(..., keep_raw=True). Pure given a
    fixed seed.
    """
    win = _clean_values(block, "win")
    loss = _clean_values(block, "loss")
    n_win, n_loss = len(win), len(loss)
    lo, hi = bootstrap_diff_ci(win, loss, ci=ci, n_resamples=n_resamples, seed=seed)
    enough_n = n_win >= min_n and n_loss >= min_n
    excludes_zero = lo is not None and (lo > 0 or hi < 0)
    return {
        "n_win": n_win,
        "n_loss": n_loss,
        "win_mean": (sum(win) / n_win) if n_win else None,
        "loss_mean": (sum(loss) / n_loss) if n_loss else None,
        "ci_lo": lo,
        "ci_hi": hi,
        "min_n": min_n,
        "ci": ci,
        "passes": bool(enough_n and excludes_zero),
    }


def prediction_gate(
    train_block: dict,
    test_block: dict,
    ci: float = CLAIM_CI,
    n_resamples: int = N_RESAMPLES,
    seed: int = SEED,
) -> dict:
    """Whether the train-mined winning-side pattern replicates on held-out data.

    Bootstraps a CI for the TRAIN split's winning-side mean, then checks the
    TEST split's own winning-side point estimate falls inside it: the pattern
    must predict how top players actually play in games the miner never
    touched when it read off the claim, not just describe the training slice.
    `train_block`/`test_block` must come from mine(..., keep_raw=True) over the
    KD4 train/test partition. Pure given a fixed seed.
    """
    train_win = _clean_values(train_block, "win")
    test_win = _clean_values(test_block, "win")
    if not train_win or not test_win:
        return {
            "train_n": len(train_win),
            "test_n": len(test_win),
            "test_mean": None,
            "train_ci_lo": None,
            "train_ci_hi": None,
            "passes": False,
        }
    lo, hi = bootstrap_mean_ci(train_win, ci=ci, n_resamples=n_resamples, seed=seed)
    test_mean = sum(test_win) / len(test_win)
    return {
        "train_n": len(train_win),
        "test_n": len(test_win),
        "test_mean": test_mean,
        "train_ci_lo": lo,
        "train_ci_hi": hi,
        "passes": bool(lo is not None and lo <= test_mean <= hi),
    }


# --- live wrapper: mine train/test separately, then gate --------------------

def run_split_mine(source, signatures, target, threshold: float = 0.35, limit=None) -> dict:
    """Mine `target`'s blocks separately over the KD4 train and test splits.

    Both splits are folded with keep_raw=True (needed by claim_gate /
    prediction_gate). The split is read off the episode label (its filename
    stem) via replay_trace's canonical md5 partition, so it matches every other
    unit that reports a held-out number.
    """
    train_streams, test_streams = [], []
    for replay, label in load_replays(source, limit=limit):
        split = split_of(episode_id_of(label))
        bucket = train_streams if split == "train" else test_streams
        for won, decisions in episode_family_streams(replay, signatures, target, threshold):
            bucket.append((won, decisions))
    return {
        "train": mine(train_streams, keep_raw=True),
        "test": mine(test_streams, keep_raw=True),
    }


def run_gates(source, signatures, target, threshold: float = 0.35, limit=None, **gate_kwargs) -> dict:
    """Mine `target` (train/test split) and gate every CLAIM_BLOCKS entry.

    Returns {"target_family", "blocks": {name: {"claim_gate", "prediction_gate",
    "verdict"}}}. verdict is CONFIRMED only when both gates pass; otherwise CUT.
    """
    mined = run_split_mine(source, signatures, target, threshold, limit=limit)
    blocks = {}
    for name in CLAIM_BLOCKS:
        train_block = mined["train"]["blocks"][name]
        test_block = mined["test"]["blocks"][name]
        claim = claim_gate(train_block, **gate_kwargs)
        pred = prediction_gate(train_block, test_block, **{
            k: v for k, v in gate_kwargs.items() if k != "min_n"
        })
        blocks[name] = {
            "claim_gate": claim,
            "prediction_gate": pred,
            "verdict": "CONFIRMED" if claim["passes"] and pred["passes"] else "CUT",
        }
    return {
        "target_family": target,
        "train_episodes": {
            "win": mined["train"]["episodes_win"],
            "loss": mined["train"]["episodes_loss"],
        },
        "test_episodes": {
            "win": mined["test"]["episodes_win"],
            "loss": mined["test"]["episodes_loss"],
        },
        "blocks": blocks,
    }


def _print_summary(report: dict) -> None:
    print(f"target family: {report['target_family']}")
    print(
        f"train appearances: {report['train_episodes']['win']} winning, "
        f"{report['train_episodes']['loss']} losing"
    )
    print(
        f"test appearances:  {report['test_episodes']['win']} winning, "
        f"{report['test_episodes']['loss']} losing"
    )
    for name, row in report["blocks"].items():
        c, p = row["claim_gate"], row["prediction_gate"]
        print(f"\n{name}: {row['verdict']}")
        print(
            f"  claim_gate n_win={c['n_win']} n_loss={c['n_loss']} "
            f"win_mean={c['win_mean']} loss_mean={c['loss_mean']} "
            f"ci=({c['ci_lo']}, {c['ci_hi']}) passes={c['passes']}"
        )
        print(
            f"  prediction_gate train_n={p['train_n']} test_n={p['test_n']} "
            f"test_mean={p['test_mean']} train_ci=({p['train_ci_lo']}, {p['train_ci_hi']}) "
            f"passes={p['passes']}"
        )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", help="a .zip of episode JSONs or a directory of *.json replays")
    ap.add_argument("target", help="the archetype family to mine (e.g. bracket_4)")
    ap.add_argument("--decks-dir", default=None)
    ap.add_argument("--threshold", type=float, default=0.35)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--min-n", type=int, default=MIN_CLAIM_N)
    ap.add_argument("--ci", type=float, default=CLAIM_CI)
    ap.add_argument("--resamples", type=int, default=N_RESAMPLES)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default="gameplan_claims.json")
    args = ap.parse_args(argv)

    signatures = build_signatures(args.decks_dir)
    report = run_gates(
        args.source,
        signatures,
        args.target,
        args.threshold,
        limit=args.limit,
        min_n=args.min_n,
        ci=args.ci,
        n_resamples=args.resamples,
        seed=args.seed,
    )
    _print_summary(report)

    out = derived_path("gameplans", args.out)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nclaims written (isolated): {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
