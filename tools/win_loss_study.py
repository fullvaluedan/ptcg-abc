"""How the best teams win vs lose (plan U63).

Reads the two corpora plan U62 built (tools/top_player_tracker.py's win corpus,
source=top_player, and loss corpus, source=top_player_loss) plus, when
available, our own loss-bucket measurement (tools/measure_loss_modes.py's
JSON output) and contrasts them three ways:

  (a) loss-bucket distribution: which failure modes (analysis/loss_classifier
      buckets) dominate the top teams' losses, versus ours.
  (b) discriminative feature deltas at matched turn ranges: which feature
      (bench width, deck count, prize tempo, energy, ...) differs most
      between the top teams' wins and their losses.
  (c) who beats them: the opponents the top teams lose to most often. The
      loss corpus carries only the opponent's team name, not their decklist,
      so archetype-level attribution is out of scope here; team name is the
      strongest signal available at this row-level granularity.

Emits a human-readable analysis/top_player_win_loss_study.md and a
machine-usable analysis/top_player_win_loss_study.json a retrain can load
without re-parsing the corpora.

Every comparison degrades to a stated "insufficient data" note instead of
raising or dividing by zero when a group (a team with no losses, a turn range
with rows on only one side) is too thin to compare.

Dev tool only, never shipped. Reads only data/training/*.csv corpora already
produced by tools/top_player_tracker.py; touches no network or replay data
directly.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ptcg_agent.features import FEATURE_NAMES  # noqa: E402

DEFAULT_TRAIN_DIR = _ROOT / "data" / "training"
DEFAULT_REPORT_PATH = _ROOT / "analysis" / "top_player_win_loss_study.md"
DEFAULT_SUMMARY_PATH = _ROOT / "analysis" / "top_player_win_loss_study.json"
DEFAULT_OURS_JSON = DEFAULT_TRAIN_DIR / "loss_modes_on.json"

# (name, low turn, high turn or None for open-ended). Ranges are inclusive so
# win and loss rows are compared only within the same stage of the game;
# comparing an early-game win row against a late-game loss row would confound
# "what wins" with "games just look different early vs late".
TURN_BINS = (("early", 0, 3), ("mid", 4, 8), ("late", 9, None))
TOP_K_FEATURES = 8
INSUFFICIENT = "insufficient data"


def load_rows(csv_path) -> list:
    """Read a top-player win or loss corpus CSV (tools/top_player_tracker.py's
    schema) into typed dict rows.

    Numeric columns (seat, turn, every FEATURE_NAMES entry, label) are cast to
    float; game_id, source, team, and (loss corpus only) loss_bucket/opponent
    stay strings. A malformed numeric cell falls back to 0.0 rather than
    raising: this is a best-effort study over real scraped data, not a gate.
    Returns [] when csv_path does not exist.
    """
    path = Path(csv_path)
    if not path.exists():
        return []
    numeric_cols = {"seat", "turn", "label", *FEATURE_NAMES}
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            row = dict(raw)
            for col in numeric_cols:
                if col in row:
                    try:
                        row[col] = float(row[col])
                    except (TypeError, ValueError):
                        row[col] = 0.0
            rows.append(row)
    return rows


def distinct_games(rows) -> set:
    """Unique (game_id, team) pairs a row list covers (one per game, not per decision)."""
    return {(r.get("game_id"), r.get("team")) for r in rows}


def bucket_distribution(loss_rows) -> Counter:
    """Loss-bucket counts, one per distinct (game_id, team) loss, not per row.

    A game contributes many decision rows all carrying the same loss_bucket;
    counting rows would weight long games over short ones for no reason.
    """
    seen = set()
    counts = Counter()
    for r in loss_rows:
        key = (r.get("game_id"), r.get("team"))
        if key in seen:
            continue
        seen.add(key)
        counts[r.get("loss_bucket") or "unclassified"] += 1
    return counts


def opponent_distribution(loss_rows) -> Counter:
    """Opponent team-name counts, one per distinct (game_id, team) loss."""
    seen = set()
    counts = Counter()
    for r in loss_rows:
        key = (r.get("game_id"), r.get("team"))
        if key in seen:
            continue
        seen.add(key)
        counts[r.get("opponent") or "unknown"] += 1
    return counts


def load_ours_buckets(path) -> dict | None:
    """Load an "ours" loss-mode measurement (tools/measure_loss_modes.py's
    measure_agent() JSON output: a "buckets" dict plus a "losses" total).

    Returns None (never raises) when the file is missing, unreadable, or does
    not carry the expected shape, so the caller degrades to an insufficient
    data note instead.
    """
    path = Path(path)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    buckets = data.get("buckets")
    losses = data.get("losses")
    if not isinstance(buckets, dict) or not isinstance(losses, int):
        return None
    return {"buckets": buckets, "losses": losses}


def compare_bucket_distributions(top_loss_buckets: Counter, ours: dict | None) -> dict:
    """Rate-of-losses per bucket for top-team losses vs ours, with the delta.

    Ranked by the top teams' own rate (their dominant failure mode first).
    Degrades to a "note" (no divide by zero) when either side has zero
    losses to bucket.
    """
    top_total = sum(top_loss_buckets.values())
    our_buckets = (ours or {}).get("buckets") or {}
    our_total = (ours or {}).get("losses") or 0
    all_buckets = sorted(set(top_loss_buckets) | set(our_buckets))
    rows = []
    for b in all_buckets:
        top_rate = (top_loss_buckets.get(b, 0) / top_total) if top_total else None
        our_rate = (our_buckets.get(b, 0) / our_total) if our_total else None
        delta = (top_rate - our_rate) if top_rate is not None and our_rate is not None else None
        rows.append({
            "bucket": b,
            "top_count": top_loss_buckets.get(b, 0),
            "top_rate": top_rate,
            "our_count": our_buckets.get(b, 0),
            "our_rate": our_rate,
            "delta": delta,
        })
    rows.sort(key=lambda r: (r["top_rate"] if r["top_rate"] is not None else -1), reverse=True)
    note = None
    if top_total == 0:
        note = "no top-team losses in this corpus; bucket comparison is insufficient data"
    elif not our_total:
        note = "no our-side loss-mode measurement found; run tools/measure_loss_modes.py to compare"
    return {"rows": rows, "top_total": top_total, "our_total": our_total, "note": note}


def _turn_bin(turn) -> str | None:
    for name, lo, hi in TURN_BINS:
        if turn >= lo and (hi is None or turn <= hi):
            return name
    return None


def feature_means(rows, features=FEATURE_NAMES) -> dict:
    """Mean of each feature over rows, or {} for an empty row list."""
    if not rows:
        return {}
    sums = {f: 0.0 for f in features}
    for r in rows:
        for f in features:
            sums[f] += r.get(f, 0.0)
    n = len(rows)
    return {f: sums[f] / n for f in features}


def feature_deltas_by_bin(win_rows, loss_rows, features=FEATURE_NAMES) -> dict:
    """Per turn-bin, per-feature mean(win) - mean(loss).

    A bin with rows on only one side (or neither) is omitted entirely rather
    than compared against an empty group.
    """
    out = {}
    for name, lo, hi in TURN_BINS:
        w = [r for r in win_rows if _turn_bin(r.get("turn", 0)) == name]
        losses = [r for r in loss_rows if _turn_bin(r.get("turn", 0)) == name]
        if not w or not losses:
            continue
        wm = feature_means(w, features)
        lm = feature_means(losses, features)
        out[name] = {
            f: {"win_mean": wm[f], "loss_mean": lm[f], "delta": wm[f] - lm[f]}
            for f in features
        }
    return out


def top_discriminative_features(bin_deltas: dict, k: int = TOP_K_FEATURES) -> list:
    """Flatten per-bin feature deltas and rank by |delta| descending.

    Iteration follows TURN_BINS then FEATURE_NAMES order, both fixed, so the
    ranking (and any tie-break) is deterministic across runs on the same data.
    """
    flat = []
    for bin_name, feats in bin_deltas.items():
        for feat, vals in feats.items():
            flat.append({"turn_bin": bin_name, "feature": feat, **vals})
    flat.sort(key=lambda d: abs(d["delta"]), reverse=True)
    return flat[:k]


def study(win_rows, loss_rows, ours: dict | None = None) -> dict:
    """Run the full U63 comparison and return a JSON-serializable summary."""
    bucket_cmp = compare_bucket_distributions(bucket_distribution(loss_rows), ours)
    bin_deltas = feature_deltas_by_bin(win_rows, loss_rows)
    notes = []
    if bucket_cmp["note"]:
        notes.append(bucket_cmp["note"])
    if not bin_deltas:
        notes.append(
            "no matched turn range had both win and loss rows; feature-delta comparison is "
            + INSUFFICIENT
        )
    return {
        "win_games": len(distinct_games(win_rows)),
        "loss_games": len(distinct_games(loss_rows)),
        "win_rows": len(win_rows),
        "loss_rows": len(loss_rows),
        "bucket_comparison": bucket_cmp,
        "feature_deltas_by_bin": bin_deltas,
        "top_discriminative_features": top_discriminative_features(bin_deltas),
        "opponents": opponent_distribution(loss_rows).most_common(),
        "notes": notes,
    }


def _fmt_rate(x) -> str:
    return f"{x:.1%}" if x is not None else "n/a"


def format_report(result: dict, win_csv=None, loss_csv=None, ours_json=None) -> str:
    """Render analysis/top_player_win_loss_study.md's content."""
    lines = [
        "# How the best teams win vs lose",
        "",
        "Plan U63 (docs/plans/2026-07-02-003-feat-offline-match-scale-topplayer-mining-plan.md).",
        "Contrasts the top-N leaderboard teams' wins against their losses (plan U62's win",
        "and loss corpora) and, where available, our own loss-bucket measurement",
        "(tools/measure_loss_modes.py), to name what makes the difference.",
        "",
    ]
    if win_csv or loss_csv or ours_json:
        lines += [f"Sources: win corpus `{win_csv}`, loss corpus `{loss_csv}`, ours `{ours_json}`.", ""]
    lines += [
        f"- Top-team win games: {result['win_games']} ({result['win_rows']} decision rows)",
        f"- Top-team loss games: {result['loss_games']} ({result['loss_rows']} decision rows)",
        "",
        "## How the top teams lose, versus how we lose",
        "",
    ]
    bc = result["bucket_comparison"]
    if bc["rows"]:
        lines.append("| loss bucket | top-team rate | top-team count | our rate | our count |")
        lines.append("|---|---|---|---|---|")
        for r in bc["rows"]:
            lines.append(
                f"| {r['bucket']} | {_fmt_rate(r['top_rate'])} | {r['top_count']} | "
                f"{_fmt_rate(r['our_rate'])} | {r['our_count']} |"
            )
    else:
        lines.append(f"- {INSUFFICIENT}: no loss rows to bucket")
    if bc["note"]:
        lines += ["", f"Note: {bc['note']}"]

    lines += ["", "## What separates their wins from their losses", ""]
    feats = result["top_discriminative_features"]
    if feats:
        lines.append("| turn range | feature | win mean | loss mean | delta (win minus loss) |")
        lines.append("|---|---|---|---|---|")
        for f in feats:
            lines.append(
                f"| {f['turn_bin']} | {f['feature']} | {f['win_mean']:.3f} | "
                f"{f['loss_mean']:.3f} | {f['delta']:+.3f} |"
            )
    else:
        lines.append(f"- {INSUFFICIENT}: no turn range had both win and loss rows to compare")

    lines += ["", "## Who beats them", ""]
    if result["opponents"]:
        lines.append(
            "Opponent is the team name only; the loss corpus carries no decklist, so "
            "archetype-level attribution is not available at this granularity."
        )
        lines.append("")
        lines.append("| opponent | top-team losses to them |")
        lines.append("|---|---|")
        for name, n in result["opponents"][:15]:
            lines.append(f"| {name} | {n} |")
    else:
        lines.append(f"- {INSUFFICIENT}: no loss rows to attribute to an opponent")

    if result["notes"]:
        lines += ["", "## Data notes", ""]
        for n in result["notes"]:
            lines.append(f"- {n}")

    lines.append("")
    return "\n".join(lines)


def _default_csv(prefix: str):
    files = sorted(DEFAULT_TRAIN_DIR.glob(f"{prefix}_*.csv"))
    return files[-1] if files else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--win-csv", default=None, help="top_player win corpus CSV (default: newest under data/training)")
    ap.add_argument("--loss-csv", default=None, help="top_player loss corpus CSV (default: newest under data/training)")
    ap.add_argument("--ours-json", default=str(DEFAULT_OURS_JSON),
                     help="tools/measure_loss_modes.py JSON output for our own loss buckets")
    ap.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    ap.add_argument("--summary", default=str(DEFAULT_SUMMARY_PATH))
    args = ap.parse_args(argv)

    win_csv = Path(args.win_csv) if args.win_csv else _default_csv("top_player_corpus")
    loss_csv = Path(args.loss_csv) if args.loss_csv else _default_csv("top_player_loss_corpus")
    if win_csv is None or loss_csv is None:
        print("no top-player corpus CSVs found under data/training; run tools/top_player_tracker.py first")
        return 1

    win_rows = load_rows(win_csv)
    loss_rows = load_rows(loss_csv)
    ours = load_ours_buckets(args.ours_json)

    result = study(win_rows, loss_rows, ours)
    report = format_report(result, win_csv, loss_csv, args.ours_json)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(report, encoding="utf-8")
    Path(args.summary).write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"wrote {args.report}")
    print(f"wrote {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
