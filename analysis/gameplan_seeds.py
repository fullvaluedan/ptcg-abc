"""Game-plan seeds emitter (plan U36, piece 3 of 3).

The miner (piece 2, analysis/gameplan_mine) distills a target family's real
expert episodes into six stat blocks, each contrasting the family's WINNING
appearances with its LOSING ones and each carrying a resolution_rate. A block
whose WINNING split resolved below the miner's 0.90 bar is already marked
`barred`. This emitter is the second half of the gate: it reads the mined
blocks and turns only the blocks whose winning signal is BOTH observable (not
barred) AND concentrated enough into a small seeds JSON that the U37 consumer
bakes as build-time dict constants (attach target, bench / play targets, evolve
priority, opening commitment, first-attack / first-evolve timing).

Three emission bars, one per block shape, exactly as the plan names them
(0.70 share / 0.80 timing / 0.95 unanimity):

  categorical target blocks (attach_target, play_target, evolve_target):
      emit when the winning modal card's SHARE of resolved decisions >= 0.70.
  the opening commitment (opening_category):
      a stronger bar -- baking "always open this way" is a hard commitment, so
      the winning modal opening must be near-UNANIMOUS (share >= 0.95).
  timing blocks (first_attack_ordinal, first_evolve_ordinal):
      emit when the winning modal ordinal's CONSISTENCY (its share of the
      episodes that saw the event) >= 0.80.

A block that is barred, has no resolved mode, or falls under its bar emits no
seed, and its reason is recorded in the decision log -- a skipped block is never
silently dropped. The emitted seed carries the winning value and the metric that
cleared the bar; the losing-split mode is rendered alongside in the human doc so
the writeup shows the win-vs-loss contrast the miner measured.

Pure and cg-free at import, like the selector and the miner: emit_seeds and
render_gameplan_doc operate on the miner's already-computed blocks dict, touching
no engine, replay, or card data. The CLI reads the miner's blocks JSON (isolated
under data/derived/gameplans/), writes the machine seeds JSON back through
tools.isolation (competition-derived, gitignored), and writes the human game-plan
doc -- aggregates only, never raw episodes -- to the committed analysis/gameplans/
tree for the writeup.

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

from tools.isolation import derived_path  # noqa: E402

# Emission bars (the plan's 0.70 share / 0.80 timing / 0.95 unanimity). The
# miner's 0.90 resolution bar is separate and already applied upstream as
# block["barred"]; these bars gate on how CONCENTRATED the winning signal is.
SHARE_BAR = 0.70
UNANIMITY_BAR = 0.95
TIMING_BAR = 0.80

# Which bar governs each block. The opening commitment gets the unanimity bar
# because baking a fixed opening is a hard commitment; the three target blocks
# share the 0.70 bar; the two timing blocks share the 0.80 consistency bar.
EMISSION_BAR = {
    "opening_category": UNANIMITY_BAR,
    "attach_target": SHARE_BAR,
    "play_target": SHARE_BAR,
    "evolve_target": SHARE_BAR,
    "first_attack_ordinal": TIMING_BAR,
    "first_evolve_ordinal": TIMING_BAR,
}


def _metric_and_value(block: dict):
    """(metric, value) the emitter thresholds against, from the WINNING split.

    Categorical blocks are gated on the modal card's mode_share and emit the
    mode; timing blocks are gated on the modal ordinal's consistency and emit the
    mode_ordinal. Pure, never raises on a well-formed block.
    """
    win = block["win"]
    if block["kind"] == "categorical":
        return win["mode_share"], win["mode"]
    return win["consistency"], win["mode_ordinal"]


def evaluate_block(name: str, block: dict) -> dict:
    """Decide whether one block emits a seed, recording the reason either way.

    A block is skipped when it is barred (winning split under the miner's 0.90
    resolution bar), when nothing resolved (no mode to read), or when the winning
    metric falls under this block's emission bar. Otherwise it is emitted. Pure,
    never raises on a well-formed block.
    """
    bar = EMISSION_BAR[name]
    metric, value = _metric_and_value(block)
    if block.get("barred"):
        emitted, reason = False, "barred"
    elif value is None:
        emitted, reason = False, "no_mode"
    elif metric < bar:
        emitted, reason = False, "below_bar"
    else:
        emitted, reason = True, "ok"
    return {
        "block": name,
        "kind": block["kind"],
        "emitted": emitted,
        "reason": reason,
        "value": value,
        "metric": metric,
        "bar": bar,
        "loss_value": _loss_value(block),
    }


def _loss_value(block: dict):
    """The LOSING split's modal value, kept for the win-vs-loss contrast in the doc."""
    loss = block["loss"]
    return loss["mode"] if block["kind"] == "categorical" else loss["mode_ordinal"]


def emit_seeds(mined: dict) -> dict:
    """Turn a mined blocks result (gameplan_mine.mine output) into seeds.

    Evaluates each known block against its emission bar and keeps only the blocks
    that clear it. Returns the emitted seeds keyed by block name plus the full
    per-block decision log (so every skip carries its reason) and the episode
    counts the miner measured. Blocks the miner did not produce are simply absent.
    Pure, never raises on well-formed input.
    """
    blocks = mined.get("blocks", {})
    decisions = {
        name: evaluate_block(name, blocks[name])
        for name in EMISSION_BAR
        if name in blocks
    }
    seeds = {
        name: {"value": d["value"], "metric": d["metric"], "kind": d["kind"]}
        for name, d in decisions.items()
        if d["emitted"]
    }
    return {
        "episodes_win": mined.get("episodes_win"),
        "episodes_loss": mined.get("episodes_loss"),
        "seeds": seeds,
        "decisions": decisions,
    }


def render_gameplan_doc(result: dict) -> str:
    """Render the human game-plan markdown from an emit result (aggregates only).

    Carries the target family, the episode counts, the emission bars, and one row
    per block: its winning seed value and metric, the losing-split modal value for
    contrast, and whether it seeded (or why it did not). No raw episodes, so the
    doc is safe to commit under analysis/gameplans/. Pure, never raises.
    """
    fam = result.get("target_family") or "?"
    lines = [
        f"# Game plan: {fam}",
        "",
        "Machine seeds emitted by analysis/gameplan_seeds.py (plan U36 piece 3) from",
        "the miner's win-vs-loss stat blocks. Aggregates only; no raw episodes.",
        "",
        f"- appearances mined: {result.get('episodes_win')} winning, "
        f"{result.get('episodes_loss')} losing",
        f"- emission bars: share {SHARE_BAR:.2f}, unanimity {UNANIMITY_BAR:.2f}, "
        f"timing {TIMING_BAR:.2f} (miner resolution bar {result.get('bar_resolution')})",
        f"- source blocks: {result.get('source_blocks')}",
        "",
        "| block | kind | winning value | metric | bar | losing value | status |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, d in result.get("decisions", {}).items():
        status = "SEEDED" if d["emitted"] else d["reason"]
        lines.append(
            f"| {name} | {d['kind']} | {d['value']} | {d['metric']:.3f} | "
            f"{d['bar']:.2f} | {d['loss_value']} | {status} |"
        )
    seeded = [n for n, d in result.get("decisions", {}).items() if d["emitted"]]
    lines += ["", f"Seeded blocks: {', '.join(seeded) if seeded else 'none'}."]
    return "\n".join(lines) + "\n"


def run_emit(blocks_path) -> dict:
    """Read a mined blocks JSON (written by gameplan_mine) and emit seeds + provenance."""
    payload = json.loads(Path(blocks_path).read_text(encoding="utf-8"))
    result = emit_seeds(payload)
    result["target_family"] = payload.get("target_family")
    result["source_blocks"] = str(blocks_path)
    result["thresholds"] = {
        "share": SHARE_BAR,
        "unanimity": UNANIMITY_BAR,
        "timing": TIMING_BAR,
    }
    result["bar_resolution"] = payload.get("bar_resolution")
    return result


def _print_summary(result: dict) -> None:
    print(f"target family: {result.get('target_family')}")
    print(
        f"appearances: {result.get('episodes_win')} winning, "
        f"{result.get('episodes_loss')} losing"
    )
    print(
        f"\nblocks (bars: share {SHARE_BAR:.2f} / timing {TIMING_BAR:.2f} / "
        f"unanimity {UNANIMITY_BAR:.2f}):"
    )
    for name, d in result.get("decisions", {}).items():
        status = "SEEDED" if d["emitted"] else d["reason"]
        print(
            f"  {name:<20} metric={d['metric']:.3f} bar={d['bar']:.2f} "
            f"value={d['value']} -> {status}"
        )
    print(f"\nseeds emitted: {len(result.get('seeds', {}))}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--blocks",
        default=str(derived_path("gameplans", "gameplan_blocks.json")),
        help="mined blocks JSON (gameplan_mine --out), under data/derived/gameplans/",
    )
    ap.add_argument(
        "--out",
        default="gameplan_seeds.json",
        help="seeds JSON filename under data/derived/gameplans/ (isolated)",
    )
    ap.add_argument(
        "--doc",
        default=None,
        help="path for the committed human game-plan markdown "
        "(default analysis/gameplans/<family>_gameplan.md)",
    )
    args = ap.parse_args(argv)

    result = run_emit(args.blocks)
    _print_summary(result)

    payload = {
        "target_family": result.get("target_family"),
        "source_blocks": result.get("source_blocks"),
        "thresholds": result.get("thresholds"),
        "bar_resolution": result.get("bar_resolution"),
        "episodes_win": result.get("episodes_win"),
        "episodes_loss": result.get("episodes_loss"),
        "seeds": result.get("seeds"),
        "decisions": result.get("decisions"),
    }
    out = derived_path("gameplans", args.out)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nseeds written (isolated): {out}")

    fam = result.get("target_family") or "target"
    doc_path = Path(args.doc) if args.doc else _ROOT / "analysis" / "gameplans" / f"{fam}_gameplan.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(render_gameplan_doc(result), encoding="utf-8")
    print(f"game-plan doc written (committed, aggregates only): {doc_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
