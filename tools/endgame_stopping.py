"""Pre-compute the U48 final-pair optimal-stopping rule ahead of the Aug 10-16
endgame campaign (docs/plans/2026-07-02-001-feat-unified-number-one-plan.md,
Phase 4). The plan fixes the design already: re-roll the strongest settled
build, stop the first time the live pair's best draw clears the build's own
true-skill estimate by a fixed bonus (so a lucky high draw is banked, not
rolled away), and lock the final pair with a day of slack before the deadline.
What was missing was turning "king-true-estimate" into an actual number: this
module reuses tools/refit_noise_model.py's per-build family stats (the same
pooled same-build reads that just refit M to 240) to estimate it as that
build's own mean ladder read, so the stop target is data-driven rather than
guessed the week of the campaign.

SUPERSEDED (2026-07-05 item 9): The prior stop_target 611.6 hard-stop regime is
retired per P3 (POSTURE INVERSION, 2026-07-05). The new endgame strategy is
LOCK-THE-STRONGEST-PAIR EARLY (by Aug 12-13): two copies of the genuinely
strongest ring-gated build. This tool remains available for computing the
threshold, but no fixed stop_target is enforced as a gate. The endgame campaign
uses the ring as the decision authority, not a static ladder-read threshold.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.loop_state import read_current, write_current  # noqa: E402
from tools.refit_noise_model import family_key, refit  # noqa: E402

DEFAULT_BONUS = 40
DEFAULT_PAIR_RULE = (
    "two copies of the strongest settled build; a diverse hedge only if the "
    "runner-up settled within M and is mechanically different"
)


def king_true_estimate(ledger: list, build: str) -> dict | None:
    """The named build's own pooled mean/n from the ledger, or None if absent."""
    report = refit(ledger, min_family_n=1)
    return report["per_family"].get(family_key(build))


def stopping_threshold(king_estimate: float, bonus: int = DEFAULT_BONUS) -> float:
    return king_estimate + bonus


def should_stop(best_draw: float, king_estimate: float, bonus: int = DEFAULT_BONUS) -> bool:
    """True once the live pair's best draw clears the stop target: bank it, stop rolling."""
    return best_draw >= stopping_threshold(king_estimate, bonus)


def _format_report(build: str, stats: dict | None, bonus: int) -> str:
    if stats is None:
        return f"No ladder reads found for build family '{family_key(build)}'; cannot set a stop target."
    threshold = stopping_threshold(stats["mean"], bonus)
    return (
        f"King true-estimate for {family_key(build)}: mean={stats['mean']:.1f} "
        f"(n={stats['n']}, stdev={stats['stdev']:.1f})\n"
        f"Stop target = mean + {bonus} = {threshold:.1f}\n"
        "Rule: re-roll the king; every re-roll evicts the older submission; stop "
        "the first time the live pair's best draw >= stop target."
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", default=None,
                         help="build family to base the stop target on "
                              "(defaults to the current shadow-king's build)")
    parser.add_argument("--bonus", type=int, default=DEFAULT_BONUS,
                         help="points the best draw must clear the mean by (U48 default 40)")
    parser.add_argument("--write", action="store_true",
                         help="write the stop target and pair rule into "
                              "state/current.md's endgame_campaign block")
    parser.add_argument("--recorded", default=None,
                         help="date to stamp the written block with, e.g. 2026-07-04")
    args = parser.parse_args(argv)

    data = read_current()
    ledger = data.get("ledger") or []
    build = args.build or (data.get("shadow_king") or {}).get("build")
    if not build:
        print("No --build given and no shadow_king recorded; nothing to compute.")
        return 1

    stats = king_true_estimate(ledger, build)
    print(_format_report(build, stats, args.bonus))

    if args.write and stats is not None:
        campaign = data.get("endgame_campaign") or {}
        campaign["build"] = family_key(build)
        campaign["king_true_estimate"] = round(stats["mean"], 1)
        campaign["bonus"] = args.bonus
        campaign["stop_target"] = round(stopping_threshold(stats["mean"], args.bonus), 1)
        campaign["pair_rule"] = DEFAULT_PAIR_RULE
        campaign["no_roll_buffer"] = "2026-08-14 12:00 UTC"
        campaign["lock_by"] = "2026-08-15"
        campaign["basis"] = (
            f"tools/endgame_stopping.py, king_true_estimate = mean of {stats['n']} pooled "
            f"same-build reads for {family_key(build)} (tools/refit_noise_model.py family "
            f"stats, stdev={stats['stdev']:.1f}); stop_target = mean + bonus ({args.bonus}), "
            "per U48 (docs/plans/2026-07-02-001-feat-unified-number-one-plan.md)."
        )
        if args.recorded:
            campaign["recorded"] = args.recorded
        data["endgame_campaign"] = campaign
        write_current(data)
        print(f"Wrote endgame_campaign stop_target={campaign['stop_target']:.1f} to state/current.md")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
