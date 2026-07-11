"""S1 (plan analysis/path_above_1000.md): the high-band ring baseline read.

"NO HIGH-BAND INSTRUMENT" is gap #1 in the path-above-1000 audit: the
calibrated bracket ring (tools/ring_calibrate.py) clones from OUR OWN 450-750
rating band, saturates at 0.875-0.91, and the live stack already reads 0.910
on it -- headroom on that instrument is worth roughly zero rating. This tool
is the near-free fix S1 describes: score the current live build against a
ring cloned from the top-50 LEADERBOARD's own decklists instead
(tools/top50_harvest.py, decks/top50/), via tools.opponents.top50_clone_names()
(plan S1's new, isolated registration path -- never mixed into the existing
calibrated ring, see tools/opponents.py).

Two arms, played same-run against the identical top50 ring so no cross-run
variance confounds the comparison (mirrors tools/threat_retreat_ring_check.py's
same-run design):

  STACK: heuristic + decks/candidate_yushin_ito.csv with both _ABILITY and
  _THREAT_RETREAT patched on -- the current live build. Built with
  tools.threat_retreat_ring_check._make_agent_factory exactly as that module's
  on-arm (ARM_ON) does it, reused rather than reimplemented.

  FLAGS_OFF: the same yushin deck with both flags patched off -- the shipped
  heuristic before either lever, a same-run comparison arm the task calls for
  (not the threat_retreat-only off-arm _make_agent_factory already measures
  in tools/threat_retreat_ring_check.py; this arm isolates ability's
  contribution too).

Reuses tools.threat_retreat_ring_check._ring_win_rate, hardest_clones, and
_merge_per_opponent as-is: both tools should agree on what "the current live
build" and "the hardest clones" mean, and a ring-scoring loop with per-
opponent bookkeeping is exactly what that module already built and tested.

Dev tool only; never shipped. Headline metric: how far below the saturated
0.910 calibrated-ring read (the S1 gate reference, analysis/path_above_1000.md)
the live stack sits against elite decks.
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

# Same import-order pin threat_retreat_ring_check.py documents and relies on:
# our agents/ package must be cached under the bare name "agents" before
# anything below can trigger kaggle_environments' own env-local agents.py.
from agents import heuristics as _heuristics  # noqa: E402,F401

from tools import opponents  # noqa: E402
from tools import threat_retreat_ring_check as trc  # noqa: E402

DEFAULT_MATCHES = 150
N_HARDEST = 3

# The S1 gate reference: the calibrated bracket ring's saturated read
# (analysis/path_above_1000.md verdict section), used only as a fixed
# comparison point here, never recomputed by this tool.
SATURATED_RING_WIN_RATE = 0.910

ARM_STACK = "heuristic+yushin+ability+threat_retreat"  # the current live build
ARM_FLAGS_OFF = "heuristic+yushin-flags_off"  # both PTCG_ABILITY and PTCG_THREAT_RETREAT off


def top50_ring_names() -> list:
    """`clone:<name>` for every decks/top50/*.csv on disk.

    A separate ring from tools.ring_calibrate.ring_names()'s calibrated
    bracket ring: reads tools.opponents.top50_clone_names() directly rather
    than clone_family_names(), which never includes top50 entries by design.
    """
    return [f"clone:{name}" for name in opponents.top50_clone_names()]


def run_baseline(n_matches=DEFAULT_MATCHES, opponent_names=None) -> dict:
    """Same-run STACK vs FLAGS_OFF read against the high-band (top50) ring.

    Returns a dict with per-arm {win_rate, wins, draws, losses, n, per_opponent}
    under ARM_STACK/ARM_FLAGS_OFF, ring_size, the hardest_clones list (pooled
    across both arms, tools.threat_retreat_ring_check.hardest_clones), and the
    headline gap_to_saturated_pp = (SATURATED_RING_WIN_RATE - stack win rate)
    in percentage points.
    """
    names = opponent_names if opponent_names is not None else top50_ring_names()
    if not names:
        raise RuntimeError(
            "no top50 clone: opponents available; run tools/top50_harvest.py "
            "or check decks/top50/"
        )

    factory_stack = trc._make_agent_factory(trc.YUSHIN_DECK, ability_on=True, threat_retreat_on=True)
    factory_flags_off = trc._make_agent_factory(trc.YUSHIN_DECK, ability_on=False, threat_retreat_on=False)

    stack_wr, stack_w, stack_d, stack_l, stack_n, stack_per_opp = trc._ring_win_rate(
        factory_stack(), names, n_matches
    )
    off_wr, off_w, off_d, off_l, off_n, off_per_opp = trc._ring_win_rate(
        factory_flags_off(), names, n_matches
    )

    hardest = trc.hardest_clones(
        trc._merge_per_opponent(stack_per_opp, off_per_opp), k=N_HARDEST
    )

    return {
        "ring_size": len(names),
        ARM_STACK: {
            "win_rate": stack_wr, "wins": stack_w, "draws": stack_d,
            "losses": stack_l, "n": stack_n, "per_opponent": stack_per_opp,
        },
        ARM_FLAGS_OFF: {
            "win_rate": off_wr, "wins": off_w, "draws": off_d,
            "losses": off_l, "n": off_n, "per_opponent": off_per_opp,
        },
        "hardest_clones": hardest,
        "saturated_ring_win_rate": SATURATED_RING_WIN_RATE,
        "gap_to_saturated_pp": (SATURATED_RING_WIN_RATE - stack_wr) * 100.0,
    }


def format_report(results: dict) -> str:
    """analysis/top50_ring_baseline.md body: per-opponent W/L, aggregate win
    rate per arm, and the S1 headline (gap to the saturated calibrated-ring
    read). Deterministic given `results` (opponent rows sorted by name).
    """
    stack = results[ARM_STACK]
    off = results[ARM_FLAGS_OFF]
    gap = results["gap_to_saturated_pp"]

    lines = [
        "# Top-50 high-band ring baseline (plan S1, analysis/path_above_1000.md)",
        "",
        f"Ring: {results['ring_size']} clone:top50_* opponents (decks/top50/, "
        "tools/top50_harvest.py). Same-run comparison, alternating seats, "
        f"n={stack['n']} games per arm.",
        "",
        "## Headline",
        "",
        f"Stack ({ARM_STACK}) reads **{stack['win_rate']:.3f}** "
        f"({stack['wins']}-{stack['draws']}-{stack['losses']}, n={stack['n']}) "
        f"against the high-band ring, **{gap:+.1f}pp** {'below' if gap > 0 else 'above'} "
        f"the saturated calibrated-ring read of {results['saturated_ring_win_rate']:.3f} "
        "(analysis/path_above_1000.md's S1 gate reference).",
        "",
        f"Flags-off ({ARM_FLAGS_OFF}) reads **{off['win_rate']:.3f}** "
        f"({off['wins']}-{off['draws']}-{off['losses']}, n={off['n']}); "
        f"the ability+threat_retreat lift on this ring is "
        f"{(stack['win_rate'] - off['win_rate']) * 100.0:+.1f}pp.",
        "",
        "Hardest three top50 clones this run (pooled across both arms, by loss rate): "
        + (", ".join(results["hardest_clones"]) if results["hardest_clones"] else "(none)"),
        "",
        "## Per-opponent W/L",
        "",
        "| opponent | stack W-D-L | stack win rate | flags-off W-D-L | flags-off win rate |",
        "|---|---|---|---|---|",
    ]
    for name in sorted(stack["per_opponent"]):
        s = stack["per_opponent"][name]
        o = off["per_opponent"].get(name, {"wins": 0, "draws": 0, "losses": 0, "n": 0})
        s_wr = s["wins"] / s["n"] if s["n"] else 0.0
        o_wr = o["wins"] / o["n"] if o["n"] else 0.0
        lines.append(
            f"| {name} | {s['wins']}-{s['draws']}-{s['losses']} | {s_wr:.3f} | "
            f"{o['wins']}-{o['draws']}-{o['losses']} | {o_wr:.3f} |"
        )

    lines += [
        "",
        "## Notes",
        "",
        "- STACK is the current live build: heuristic piloting "
        "decks/candidate_yushin_ito.csv with PTCG_ABILITY and PTCG_THREAT_RETREAT "
        "both patched on, built via "
        "tools.threat_retreat_ring_check._make_agent_factory (its on-arm pattern).",
        "- FLAGS_OFF is the same deck with both flags patched off (the shipped "
        "heuristic before either lever), a same-run comparison arm, not the "
        "threat_retreat-only off-arm tools/threat_retreat_ring_check.py already measures.",
        "- Ring opponents are `clone:top50_*` (tools.opponents.top50_clone_names()), "
        "a separate registration path from the existing calibrated bracket ring "
        "(clone_family_names()); this run never touches that ring.",
        "",
    ]
    return "\n".join(lines) + "\n"


def _main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", "--matches", type=int, default=DEFAULT_MATCHES,
                         help="games per arm (default %(default)s)")
    parser.add_argument("--out", default=str(_ROOT / "analysis" / "top50_ring_baseline.md"),
                         help="markdown report path (default %(default)s)")
    parser.add_argument("--json-out", default=None, help="optional JSON report path")
    args = parser.parse_args(argv)

    results = run_baseline(n_matches=args.matches)

    for name in (ARM_STACK, ARM_FLAGS_OFF):
        r = results[name]
        print(f"{name}: {r['win_rate']:.3f} ({r['wins']}-{r['draws']}-{r['losses']}, n={r['n']})")
    print(f"ring_size = {results['ring_size']}")
    print(f"gap to saturated ({results['saturated_ring_win_rate']:.3f}) = "
          f"{results['gap_to_saturated_pp']:+.1f}pp")
    print(f"hardest clones this run: {results['hardest_clones']}")

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
