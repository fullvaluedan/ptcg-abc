"""Stateful, loss-bucket-driven loop memory (plan U12).

The self-improvement loop is stateful: each iteration re-classifies the latest
replays, targets the top loss bucket, and must not re-litigate a lever a prior
iteration already refuted (yet must be able to re-test one once its recorded
condition is met, since a refutation is stateful, not permanent: bench-dig's
direction flipped at a larger sample). This module is that memory.

Two files under state/ hold it:

  state/current.md      the live loss distribution, the shadow-king (best live
                        build) and reclaim-king (safe floor), candidates awaiting
                        the ladder, and a per-build ledger (oracle result,
                        move-agreement delta, ladder score, sample size).
  state/hypotheses.md   the falsified-hypothesis registry: each lever tried, its
                        verdict, the evidence, the sample size it was refuted at,
                        and the re-test condition (a larger sample or a different
                        deck) that would license trying it again.

Both files carry a fenced ```json STATE block as the machine-readable source of
truth; the markdown around that block is a rendered, human-readable view
regenerated from the same data on every write. Reading parses only the json
block, so a hand-edit to the prose never corrupts the state, and a missing or
malformed block degrades to an empty state rather than raising. Nothing here
touches the network: it reads saved replay JSON through tools.scout and writes
local markdown only. A missing state/ is created on first write.
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

from analysis.loss_classifier import BUCKETS, classify_batch  # noqa: E402
from tools.scout import digest_dir  # noqa: E402

STATE_DIR = _ROOT / "state"
CURRENT_PATH = STATE_DIR / "current.md"
HYPOTHESES_PATH = STATE_DIR / "hypotheses.md"

# The fenced json block that carries the machine-readable state. Kept explicit so
# both the writer and the reader agree on the exact fence, and a human editing the
# prose around it can see it is the source of truth.
_BLOCK_OPEN = "```json STATE"
_BLOCK_CLOSE = "```"


# --------------------------------------------------------------------------- #
# json-block round trip (the source of truth inside each markdown file)
# --------------------------------------------------------------------------- #
def parse_state_block(text: str) -> dict:
    """Extract the fenced ```json STATE block from a markdown string.

    Returns the parsed dict, or {} when the block is absent or malformed. Never
    raises: a hand-edited or truncated file reads as an empty state, which the
    callers treat as "nothing recorded yet" rather than an error.

    Anchors to the LAST fence that stands alone on its own line. The writers emit
    the real block on its own lines and always append it after the prose, while a
    value quoting the fence string appears only inline (inside a prose sentence or
    a JSON string), never as a bare line. Both the un-escaped prose view and the
    JSON body can therefore contain the fence text without fooling the parser: a
    plain find/rfind on the bare marker would otherwise latch onto a decoy and
    silently drop the state.
    """
    if not text:
        return {}
    open_marker = "\n" + _BLOCK_OPEN + "\n"
    idx = text.rfind(open_marker)
    if idx < 0:
        return {}
    body_start = idx + len(open_marker)
    end = text.find("\n" + _BLOCK_CLOSE, body_start)
    if end < 0:
        return {}
    raw = text[body_start:end].strip()
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _render_block(data: dict) -> str:
    """Render a state dict as the fenced json block, sorted for stable diffs."""
    body = json.dumps(data, indent=2, sort_keys=True)
    return f"{_BLOCK_OPEN}\n{body}\n{_BLOCK_CLOSE}\n"


def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _write_file(path: Path, text: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
# current.md: loss distribution, kings, candidates, ledger
# --------------------------------------------------------------------------- #
def read_current() -> dict:
    """Load the state block from current.md, or {} if it does not exist yet."""
    return parse_state_block(_read_file(CURRENT_PATH))


def write_current(data: dict) -> None:
    """Render current.md (prose view + json source of truth) from a state dict."""
    _write_file(CURRENT_PATH, _render_current_md(data))


def _render_current_md(data: dict) -> str:
    dist = data.get("loss_distribution") or {}
    lines = [
        "# Loop state: current",
        "",
        "Machine-readable source of truth is the fenced `json STATE` block at the",
        "bottom; the prose above is a rendered view regenerated on every write.",
        "Update this every iteration (loss distribution, kings, candidates, ledger).",
        "",
        "## Top loss bucket (what this iteration targets)",
        "",
    ]
    top = dist.get("top_bucket")
    if top:
        lines.append(f"**{top}** over {dist.get('sample_size', 0)} classified replays "
                     f"(W/D/L {dist.get('wins', 0)}/{dist.get('draws', 0)}/{dist.get('losses', 0)}).")
    else:
        lines.append("_no replays classified yet_")
    lines.append("")
    buckets = dist.get("buckets") or {}
    if buckets:
        lines.append("| bucket | losses |")
        lines.append("| --- | --- |")
        for name, count in sorted(buckets.items(), key=lambda kv: kv[1] or 0, reverse=True):
            if count:
                lines.append(f"| {name} | {count} |")
        lines.append("")

    lines.append("## Kings")
    lines.append("")
    king = data.get("shadow_king") or {}
    reclaim = data.get("reclaim_king") or {}
    lines.append(f"- **shadow-king** (best live build): {king.get('build', '?')} "
                 f"(ref {king.get('ref', '?')}, ladder {king.get('ladder', '?')})")
    lines.append(f"- **reclaim-king** (safe floor): {reclaim.get('build', '?')} "
                 f"(ref {reclaim.get('ref', '?')}, ladder {reclaim.get('ladder', '?')})")
    lines.append("")

    candidates = data.get("active_candidates") or []
    lines.append("## Candidates awaiting a ladder slot")
    lines.append("")
    if candidates:
        for c in candidates:
            lines.append(f"- {c.get('build', '?')}: {c.get('note', '')}")
    else:
        lines.append("_none_")
    lines.append("")

    ledger = data.get("ledger") or []
    lines.append("## Per-build ledger")
    lines.append("")
    if ledger:
        lines.append("| build | oracle | move-agree delta | ladder | sample | note |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for e in ledger:
            lines.append(
                f"| {e.get('build', '?')} | {e.get('oracle', '')} | "
                f"{e.get('move_agreement_delta', '')} | {e.get('ladder', '')} | "
                f"{e.get('sample_size', '')} | {e.get('note', '')} |"
            )
    else:
        lines.append("_empty_")
    lines.append("")

    return "\n".join(lines) + "\n" + _render_block(data)


# --------------------------------------------------------------------------- #
# hypotheses.md: the falsified-lever registry with re-test conditions
# --------------------------------------------------------------------------- #
def read_hypotheses() -> dict:
    """Load the state block from hypotheses.md, or {} if it does not exist yet."""
    return parse_state_block(_read_file(HYPOTHESES_PATH))


def write_hypotheses(data: dict) -> None:
    """Render hypotheses.md (prose view + json source of truth) from a state dict."""
    _write_file(HYPOTHESES_PATH, _render_hypotheses_md(data))


def _render_hypotheses_md(data: dict) -> str:
    hyps = data.get("hypotheses") or []
    lines = [
        "# Loop state: hypotheses",
        "",
        "The falsified-lever registry. Read this BEFORE proposing a fix: do not",
        "re-walk a refuted lever unless its recorded re-test condition is met (a",
        "larger sample or a different deck). A refutation is stateful, not",
        "permanent. Machine-readable source of truth is the fenced `json STATE`",
        "block at the bottom.",
        "",
        "| lever | verdict | sample | deck | re-test when | source |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for h in hyps:
        lines.append(
            f"| {h.get('name', '?')} | {h.get('verdict', '?')} | "
            f"{h.get('sample_size', '')} | {h.get('deck', '')} | "
            f"{h.get('retest_condition', '')} | {h.get('source', '')} |"
        )
    lines.append("")
    lines.append("## Detail")
    lines.append("")
    for h in hyps:
        lines.append(f"### {h.get('name', '?')} ({h.get('verdict', '?')})")
        if h.get("claim"):
            lines.append(f"- claim: {h['claim']}")
        if h.get("evidence"):
            lines.append(f"- evidence: {h['evidence']}")
        if h.get("retest_sample"):
            lines.append(f"- re-test at sample >= {h['retest_sample']}")
        lines.append("")
    return "\n".join(lines) + "\n" + _render_block(data)


def needs_retest(hyp: dict, current_sample: int | None = None,
                 current_deck: str | None = None) -> bool:
    """Should a refuted hypothesis be re-tested given the current situation.

    A refutation is stateful: it holds only under the conditions it was measured
    in. A hypothesis is flagged for re-test when it is refuted AND either

      - the current replay sample has reached the recorded retest_sample (the
        bench-dig case: its direction flipped at a larger sample), or
      - it opted into deck-change re-testing (retest_on_deck_change) AND the
        current deck differs from the deck it was refuted on (the thin-bench case:
        the board-out floor is deck-set, so a higher-basic deck genuinely re-opens
        the lever).

    Deck-change re-testing is opt-in rather than automatic on any deck mismatch:
    a lever refuted ON the meta decks is not re-licensed just because we are now
    on trolley. Confirmed/active/resolved hypotheses never flag. Missing
    conditions are treated as "not met" so the default is to leave a refutation
    standing.
    """
    if hyp.get("verdict") != "refuted":
        return False
    retest_sample = hyp.get("retest_sample")
    if retest_sample is not None and current_sample is not None:
        try:
            if int(current_sample) >= int(retest_sample):
                return True
        except (TypeError, ValueError):
            pass
    if hyp.get("retest_on_deck_change"):
        deck = hyp.get("deck")
        if current_deck and deck and current_deck != deck:
            return True
    return False


def retest_candidates(data: dict, current_sample: int | None = None,
                      current_deck: str | None = None) -> list:
    """The names of refuted hypotheses whose re-test condition is now met."""
    return [
        h.get("name")
        for h in (data.get("hypotheses") or [])
        if needs_retest(h, current_sample=current_sample, current_deck=current_deck)
    ]


# --------------------------------------------------------------------------- #
# loss-bucket classification over one or more replay dirs (the MEASURE step)
# --------------------------------------------------------------------------- #
def classify_dirs(dirs) -> dict:
    """Ranked loss-bucket report over the union of several replay directories.

    Each iteration classifies the latest replays to find the top bucket. Real
    replays are split across per-build dirs (replays_*/), so this concatenates
    their digests before ranking. A missing dir contributes nothing rather than
    raising. Returns the classify_batch report plus the sources and a sample_size
    (total games) convenient for seeding current.md's loss_distribution. Seat
    detection is per-replay inside scout.digest_dir (from info.TeamNames), so no
    our_index is threaded here.
    """
    digests = []
    used = []
    for d in dirs:
        path = Path(d)
        if not path.is_absolute():
            path = _ROOT / d
        if not path.is_dir():
            continue
        got = digest_dir(path)
        if got:
            digests.extend(got)
            used.append(str(d))
    report = classify_batch(digests)
    report["sources"] = used
    report["sample_size"] = report.get("games", 0)
    return report


def loss_distribution_from_dirs(dirs) -> dict:
    """Shape classify_dirs into the loss_distribution block current.md expects."""
    rep = classify_dirs(dirs)
    return {
        "games": rep.get("games", 0),
        "wins": rep.get("wins", 0),
        "draws": rep.get("draws", 0),
        "losses": rep.get("losses", 0),
        "buckets": {b: rep.get("buckets", {}).get(b, 0) for b in BUCKETS},
        "top_bucket": rep.get("top_bucket"),
        "sample_size": rep.get("sample_size", 0),
        "sources": rep.get("sources", []),
    }


# --------------------------------------------------------------------------- #
# CLI: refresh the loss distribution, or show the target bucket / re-test list
# --------------------------------------------------------------------------- #
def _cmd_refresh(args) -> None:
    dist = loss_distribution_from_dirs(args.dirs)
    data = read_current()
    data["loss_distribution"] = dist
    write_current(data)
    print(f"current.md updated: top bucket = {dist['top_bucket']} "
          f"over {dist['sample_size']} replays "
          f"(W/D/L {dist['wins']}/{dist['draws']}/{dist['losses']})")


def _cmd_target(args) -> None:
    dist = read_current().get("loss_distribution") or {}
    top = dist.get("top_bucket")
    print(top if top else "no loss distribution recorded; run 'refresh' first")


def _cmd_retest(args) -> None:
    names = retest_candidates(read_hypotheses(),
                              current_sample=args.sample, current_deck=args.deck)
    if names:
        print("re-test now licensed for: " + ", ".join(str(n) for n in names))
    else:
        print("no refuted hypothesis meets its re-test condition")


def main() -> None:
    ap = argparse.ArgumentParser(description="stateful loop memory (plan U12)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    rf = sub.add_parser("refresh", help="re-classify replays and update current.md's loss distribution")
    rf.add_argument("dirs", nargs="+", help="replay directories to classify")

    sub.add_parser("target", help="print the current top loss bucket from current.md")

    rt = sub.add_parser("retest", help="list refuted hypotheses whose re-test condition is now met")
    rt.add_argument("--sample", type=int, default=None, help="current replay sample size")
    rt.add_argument("--deck", default=None, help="current deck name")

    args = ap.parse_args()
    if args.cmd == "refresh":
        _cmd_refresh(args)
    elif args.cmd == "target":
        _cmd_target(args)
    elif args.cmd == "retest":
        _cmd_retest(args)


if __name__ == "__main__":
    main()
