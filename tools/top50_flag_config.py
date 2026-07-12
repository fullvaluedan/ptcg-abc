"""Flag-configuration experiment on the elite ring (docs task: flag-config sweep).

The live submission 54555716 runs the full stack (PTCG_ABILITY and
PTCG_THREAT_RETREAT both on, decks/candidate_yushin_ito.csv). The only same-run
read on the high-band (top50) ring so far (analysis/top50_ring_baseline.md,
n=150) found that stack at 0.693 against 0.753 for flags-off -- a -6.0pp read
that only ever compared two arms (all flags on vs all flags off) and never
isolated which lever, if either, is responsible for the gap. This tool settles
that properly: four arms, factorized by lever, n=100 each, played SAME RUN
against the identical top50 elite ring (round-robin, alternating seats, exactly
tools/top50_ring.py's runner), plus a second same-run pass at n=50 each against
the OLD calibrated bracket ring (tools/ring_calibrate.py) as a regression guard
(does a config that looks best on the elite ring still hold up on the
instrument every prior lever gate was measured against).

Arms (all piloting decks/candidate_yushin_ito.csv via
tools.threat_retreat_ring_check._make_agent_factory, reused as-is rather than
reimplemented, exactly as tools/top50_ring.py and tools/stacked_ring_u104.py
already do):

  plain           ability=off  threat_retreat=off   (config 1)
  ability         ability=on   threat_retreat=off   (config 2)
  threat_retreat  ability=off  threat_retreat=on    (config 3)
  stack           ability=on   threat_retreat=on    (config 4, = live submission)

Reuses tools.threat_retreat_ring_check._ring_win_rate, hardest_clones, and
_merge_per_opponent as-is (the same round-robin-with-per-opponent-bookkeeping
loop tools/top50_ring.py already reuses), and tools.top50_ring.top50_ring_names
/ tools.ring_calibrate.ring_names for the two ring opponent pools, so this tool
never re-derives what "the elite ring" or "the calibrated ring" means.

Dev tool only; never shipped.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Same import-order pin threat_retreat_ring_check.py and top50_ring.py document
# and rely on: our agents/ package must be cached under the bare name "agents"
# before anything below can trigger kaggle_environments' own env-local agents.py.
from agents import heuristics as _heuristics  # noqa: E402,F401

from tools import ring_calibrate as rc  # noqa: E402
from tools import threat_retreat_ring_check as trc  # noqa: E402
from tools import top50_ring as t50  # noqa: E402

DEFAULT_ELITE_MATCHES = 100
DEFAULT_CALIBRATED_MATCHES = 50
N_HARDEST = 3

YUSHIN_DECK = trc.YUSHIN_DECK

# config key -> (display arm name, ability_on, threat_retreat_on). Order fixed
# so every report iterates configs 1-4 in the task's own numbering.
CONFIG_ORDER = ["plain", "ability", "threat_retreat", "stack"]
CONFIG_FLAGS = {
    "plain": (False, False),
    "ability": (True, False),
    "threat_retreat": (False, True),
    "stack": (True, True),
}
ARM_NAMES = {
    "plain": "heuristic+yushin-plain",
    "ability": "heuristic+yushin+ability",
    "threat_retreat": "heuristic+yushin+threat_retreat",
    "stack": "heuristic+yushin+ability+threat_retreat",
}

# Prior same-run read this experiment is meant to settle properly (n=100 same-run
# vs analysis/top50_ring_baseline.md's n=150 two-arm read), cited verbatim in the
# report, never recomputed here.
PRIOR_ELITE_READ = {"stack": 0.693, "plain": 0.753}
LIVE_SUBMISSION_REF = "54555716"
LIVE_SUBMISSION_CONFIG = "stack"


def run_configs_on_ring(opponent_names, n_matches, configs=CONFIG_ORDER) -> dict:
    """Run every config in `configs` sequentially against the same ring.

    Same-run in this codebase's established sense (tools/top50_ring.py,
    tools/threat_retreat_ring_check.py): one script execution, the identical
    ring opponent list and round-robin order for every arm, so no cross-run
    variance (different clone-selection noise, different engine seed state)
    can confound the comparison between arms. Returns
    {config_key: {win_rate, wins, draws, losses, n, per_opponent}}.
    """
    if not opponent_names:
        raise RuntimeError(
            "no clone: opponents available for this ring; run the relevant "
            "harvest tool or check decks/"
        )
    results = {}
    for key in configs:
        ability_on, threat_retreat_on = CONFIG_FLAGS[key]
        factory = trc._make_agent_factory(YUSHIN_DECK, ability_on=ability_on,
                                           threat_retreat_on=threat_retreat_on)
        wr, w, d, l, n, per_opp = trc._ring_win_rate(factory(), opponent_names, n_matches)
        results[key] = {
            "win_rate": wr, "wins": w, "draws": d, "losses": l, "n": n,
            "per_opponent": per_opp,
        }
    return results


def best_worst_configs(elite_results: dict, configs=CONFIG_ORDER) -> tuple:
    """(best_key, worst_key) by elite win_rate; ties break by CONFIG_ORDER."""
    ranked = sorted(configs, key=lambda k: (-elite_results[k]["win_rate"], configs.index(k)))
    return ranked[0], ranked[-1]


def same_run_deltas(elite_results: dict, configs=CONFIG_ORDER, baseline="plain") -> dict:
    """{config_key: win_rate_pp_vs_baseline} for every config, this run only.

    Positive means the config beat the `baseline` config (default "plain",
    all flags off) in THIS run's same-ring same-seat-order comparison.
    """
    base_wr = elite_results[baseline]["win_rate"]
    return {
        key: (elite_results[key]["win_rate"] - base_wr) * 100.0
        for key in configs
    }


def run_experiment(n_elite=DEFAULT_ELITE_MATCHES, n_calibrated=DEFAULT_CALIBRATED_MATCHES,
                    elite_names=None, calibrated_names=None) -> dict:
    """Full four-arm experiment: elite ring (n_elite/arm) + calibrated ring
    regression guard (n_calibrated/arm), same-run within each ring.

    Returns a dict with "elite" and "calibrated" sub-results (each
    {config_key: {win_rate, wins, draws, losses, n, per_opponent}}), the pooled
    hardest_clones on the elite ring, per-opponent breakdowns for the best and
    worst elite configs, same-run deltas (vs "plain") on both rings, and the
    best/worst config keys on the elite ring.
    """
    e_names = elite_names if elite_names is not None else t50.top50_ring_names()
    c_names = calibrated_names if calibrated_names is not None else rc.ring_names()

    elite = run_configs_on_ring(e_names, n_elite)
    calibrated = run_configs_on_ring(c_names, n_calibrated)

    pooled_per_opp = trc._merge_per_opponent(*(elite[k]["per_opponent"] for k in CONFIG_ORDER))
    hardest = trc.hardest_clones(pooled_per_opp, k=N_HARDEST)

    best_key, worst_key = best_worst_configs(elite)

    return {
        "elite": elite,
        "calibrated": calibrated,
        "elite_ring_size": len(e_names),
        "calibrated_ring_size": len(c_names),
        "hardest_clones_elite": hardest,
        "best_elite_config": best_key,
        "worst_elite_config": worst_key,
        "elite_same_run_deltas_pp": same_run_deltas(elite),
        "calibrated_same_run_deltas_pp": same_run_deltas(calibrated),
    }


def format_report(results: dict) -> str:
    """analysis/top50_flag_config.md body. Deterministic given `results`."""
    elite = results["elite"]
    calibrated = results["calibrated"]
    best_key = results["best_elite_config"]
    worst_key = results["worst_elite_config"]
    e_deltas = results["elite_same_run_deltas_pp"]
    c_deltas = results["calibrated_same_run_deltas_pp"]

    lines = [
        "# Flag-configuration experiment on the elite ring",
        "",
        "Four arms, all piloting decks/candidate_yushin_ito.csv, factorized by "
        "PTCG_ABILITY x PTCG_THREAT_RETREAT: plain (config 1, both off), "
        "+ability (config 2), +threat_retreat (config 3), and "
        "+ability+threat_retreat (config 4, the live submission's stack). Each "
        "pass is same-run: one script execution, round-robin across the full "
        "ring, alternating seats, identical opponent order for every arm "
        "(mirrors tools/top50_ring.py and tools/stacked_ring_u104.py).",
        "",
        "## Context",
        "",
        f"The live submission ref {LIVE_SUBMISSION_REF} runs config 4 "
        "(+ability+threat_retreat). The only prior same-run elite-ring read "
        f"(analysis/top50_ring_baseline.md, n=150) found config 4 at "
        f"{PRIOR_ELITE_READ['stack']:.3f} against {PRIOR_ELITE_READ['plain']:.3f} "
        "for config 1 (plain) -- a same-run deficit that only ever compared "
        "those two arms and never isolated which lever, if either, causes it. "
        "This experiment settles that comparison properly at n=100 same-run, "
        "with the two middle configs (ability-only, threat_retreat-only) "
        "isolating each lever's individual contribution.",
        "",
        "## Headline",
        "",
        f"Elite ring ({results['elite_ring_size']} clone:top50_* opponents, "
        f"n={elite[CONFIG_ORDER[0]]['n']} games/arm):",
        "",
        "| config | arm | W-D-L | win rate | delta vs plain (pp, same run) |",
        "|---|---|---|---|---|",
    ]
    for i, key in enumerate(CONFIG_ORDER, start=1):
        r = elite[key]
        lines.append(
            f"| {i} | {ARM_NAMES[key]} | {r['wins']}-{r['draws']}-{r['losses']} | "
            f"{r['win_rate']:.3f} | {e_deltas[key]:+.1f} |"
        )
    lines += [
        "",
        f"Best against elite play: **{ARM_NAMES[best_key]}** (config "
        f"{CONFIG_ORDER.index(best_key) + 1}) at {elite[best_key]['win_rate']:.3f}. "
        f"Worst: **{ARM_NAMES[worst_key]}** (config "
        f"{CONFIG_ORDER.index(worst_key) + 1}) at {elite[worst_key]['win_rate']:.3f}.",
        "",
        f"Calibrated (old) ring regression guard "
        f"({results['calibrated_ring_size']} clone:<family> opponents, "
        f"n={calibrated[CONFIG_ORDER[0]]['n']} games/arm):",
        "",
        "| config | arm | W-D-L | win rate | delta vs plain (pp, same run) |",
        "|---|---|---|---|---|",
    ]
    for i, key in enumerate(CONFIG_ORDER, start=1):
        r = calibrated[key]
        lines.append(
            f"| {i} | {ARM_NAMES[key]} | {r['wins']}-{r['draws']}-{r['losses']} | "
            f"{r['win_rate']:.3f} | {c_deltas[key]:+.1f} |"
        )

    lines += [
        "",
        "Hardest three top50 clones this run (pooled across all four elite-ring "
        "arms, by loss rate): "
        + (", ".join(results["hardest_clones_elite"]) if results["hardest_clones_elite"] else "(none)"),
        "",
        "## Per-opponent breakdown, elite ring: best vs worst config",
        "",
        f"| opponent | {ARM_NAMES[best_key]} W-D-L | win rate | "
        f"{ARM_NAMES[worst_key]} W-D-L | win rate |",
        "|---|---|---|---|---|",
    ]
    best_opp = elite[best_key]["per_opponent"]
    worst_opp = elite[worst_key]["per_opponent"]
    for name in sorted(best_opp):
        b = best_opp[name]
        w = worst_opp.get(name, {"wins": 0, "draws": 0, "losses": 0, "n": 0})
        b_wr = b["wins"] / b["n"] if b["n"] else 0.0
        w_wr = w["wins"] / w["n"] if w["n"] else 0.0
        lines.append(
            f"| {name} | {b['wins']}-{b['draws']}-{b['losses']} | {b_wr:.3f} | "
            f"{w['wins']}-{w['draws']}-{w['losses']} | {w_wr:.3f} |"
        )

    verdict_best_is_stack = best_key == "stack"
    if best_key == "plain":
        best_line = (
            f"Best config against elite play this run: **{ARM_NAMES[best_key]}** "
            f"(config {CONFIG_ORDER.index(best_key) + 1}), {elite[best_key]['win_rate']:.3f}. "
        )
    else:
        best_line = (
            f"Best config against elite play this run: **{ARM_NAMES[best_key]}** "
            f"(config {CONFIG_ORDER.index(best_key) + 1}), "
            f"{elite[best_key]['win_rate']:.3f} vs plain's {elite['plain']['win_rate']:.3f} "
            f"({e_deltas[best_key]:+.1f}pp same-run delta). "
        )
    lines += [
        "",
        "## Verdict",
        "",
        best_line
        + (
            "This confirms config 4 (the live submission's stack) as the best "
            "elite-ring read in this n=100 same-run experiment."
            if verdict_best_is_stack else
            f"This is NOT config 4 (the live submission's stack, which reads "
            f"{elite['stack']['win_rate']:.3f} here, {e_deltas['stack']:+.1f}pp vs "
            "plain) -- the live submission is not the best-reading config on "
            "this elite-ring pass."
        ),
        "",
        "## Recommendation (for the second ladder slot; submission is Dan's call)",
        "",
        f"Recommend **{ARM_NAMES[best_key]}** (config {CONFIG_ORDER.index(best_key) + 1}) "
        "for the second ladder slot: it is the best same-run elite-ring reader "
        f"in this experiment ({elite[best_key]['win_rate']:.3f}, n={elite[best_key]['n']}), "
        f"and its calibrated-ring read ({calibrated[best_key]['win_rate']:.3f}, "
        f"n={calibrated[best_key]['n']}) is provided above as the regression check. "
        "This is a recommendation only; the actual second-slot submission remains "
        "Dan's call.",
        "",
        "## Notes",
        "",
        "- Every arm pilots decks/candidate_yushin_ito.csv, built via "
        "tools.threat_retreat_ring_check._make_agent_factory (its flag-patching "
        "pattern, reused as-is), so only PTCG_ABILITY and PTCG_THREAT_RETREAT vary "
        "between arms.",
        "- Elite ring = tools.top50_ring.top50_ring_names() (clone:top50_*, "
        "decks/top50/). Calibrated ring = tools.ring_calibrate.ring_names() "
        "(clone:<family>, the old 9-clone calibrated ring); the calibrated pass "
        "is a regression guard only, not the primary read.",
        "- Each ring's four-arm pass is same-run: sequential within one script "
        "execution against the identical ring opponent list and round-robin "
        "seat-alternation order, so arm-to-arm deltas within a ring are not "
        "confounded by cross-run variance. The elite pass and the calibrated "
        "pass are two separate same-run experiments, not one shared run.",
        f"- Prior context: live submission ref {LIVE_SUBMISSION_REF} runs config 4 "
        f"(+ability+threat_retreat). The prior same-run elite-ring read "
        "(analysis/top50_ring_baseline.md, n=150, two arms only) found config 4 at "
        f"{PRIOR_ELITE_READ['stack']:.3f} against {PRIOR_ELITE_READ['plain']:.3f} "
        "for config 1.",
        "",
    ]
    return "\n".join(lines) + "\n"


def _main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elite-matches", type=int, default=DEFAULT_ELITE_MATCHES,
                         help="games per arm on the elite ring (default %(default)s)")
    parser.add_argument("--calibrated-matches", type=int, default=DEFAULT_CALIBRATED_MATCHES,
                         help="games per arm on the calibrated regression-guard ring "
                              "(default %(default)s)")
    parser.add_argument("--out", default=str(_ROOT / "analysis" / "top50_flag_config.md"),
                         help="markdown report path (default %(default)s)")
    parser.add_argument("--json-out", default=None, help="optional JSON report path")
    args = parser.parse_args(argv)

    results = run_experiment(n_elite=args.elite_matches, n_calibrated=args.calibrated_matches)

    print("Elite ring:")
    for key in CONFIG_ORDER:
        r = results["elite"][key]
        print(f"  {ARM_NAMES[key]}: {r['win_rate']:.3f} ({r['wins']}-{r['draws']}-{r['losses']}, n={r['n']})")
    print("Calibrated ring (regression guard):")
    for key in CONFIG_ORDER:
        r = results["calibrated"][key]
        print(f"  {ARM_NAMES[key]}: {r['win_rate']:.3f} ({r['wins']}-{r['draws']}-{r['losses']}, n={r['n']})")
    print(f"best_elite_config = {ARM_NAMES[results['best_elite_config']]}")
    print(f"worst_elite_config = {ARM_NAMES[results['worst_elite_config']]}")
    print(f"hardest clones this run: {results['hardest_clones_elite']}")

    report = format_report(results)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"wrote {out_path}")

    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"wrote {json_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
