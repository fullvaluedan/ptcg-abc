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
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.loss_classifier import BUCKETS, classify_batch  # noqa: E402
from analysis.proxy_calibration import calibrate  # noqa: E402
from tools.scout import digest_dir  # noqa: E402

STATE_DIR = _ROOT / "state"
CURRENT_PATH = STATE_DIR / "current.md"
HYPOTHESES_PATH = STATE_DIR / "hypotheses.md"

# Noise model v3 (tools/refit_noise_model.py statistical refit, 2026-07-04).
# The v2 estimate (M=150, basis a single eyeballed min/max range on ~6 reads)
# is superseded by a pooled-residual refit over the full ledger: 57 same-build
# reads across two families (heuristic+trolley n=30, heuristic+trolley-ability
# n=27), each family's own mean subtracted out before pooling so a real mean
# difference between two builds is never counted as noise. Pooled residual
# stdev is 52.0 and the single worst observed residual is 235.1; M=240 is the
# larger of a 2-sigma bound and that worst residual, rounded up to the nearest
# 10 (analysis/noise_model_refit.md). Per the L9 correction, the calibrated
# bracket ring (not a single ladder read) is still the actual lever decision
# gate; this default only matters if a future pre-registration still wants a
# ladder-side WIN/LOSS/BAND margin.
DEFAULT_MARGIN = 240

# Settlement needs at least this many rated episodes (the pre-committed episode
# floor N in every pre-registration must be >= this), per the loop protocol.
MIN_EPISODES = 30

# The two currently-live scored-slot refs (U107b): shadow-king heuristic+trolley-
# ability and reclaim-king heuristic+trolley, per state/current.md's Kings section
# and findings.md's "Board FROZEN: 2 scored slots occupied" note (2026-07-04); the
# same pair analysis/u107_per_build_loss_ledger.py already defaults to. Seeds
# current-state's live_refs array on the first write that has never carried the
# key at all, so per-build targeting has a default without a manual edit to the
# shared state file. A later shadow-king/reclaim-king swap updates live_refs the
# same way the kings themselves are updated: through the canonical writer.
DEFAULT_LIVE_REFS = ["54315802", "54315565"]

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
    """Write text to path atomically: a temp file in the same directory, then
    os.replace() into place.

    A plain path.write_text() truncates the destination before writing the new
    bytes, so a crash or exception mid-write (disk full, process killed) can leave
    current.md or hypotheses.md half-written. Writing to a sibling temp file first
    and only replacing the real path once that write is fully flushed means the
    destination is always either the old content or the new content in full, never
    a truncated in-between state. os.replace is atomic on both POSIX and Windows
    when source and destination are on the same filesystem, which a sibling temp
    file always is. On any failure the orphaned temp file is cleaned up and the
    exception re-raised; the destination is left untouched.
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_name, str(path))
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


class LockTimeout(RuntimeError):
    """Raised when a state-file lock could not be acquired within its bound."""


class _FileLock:
    """Cross-process advisory lock via an O_CREAT|O_EXCL lock file.

    Serializes read-modify-write access to a state file: the autoloop refreshes
    current.md from its own bash-driven schedule while this push's canonical
    writer also reads-mutates-writes the same file, and without serialization the
    later writer's write can clobber the earlier writer's update (a lost-update
    race). os.open with O_CREAT|O_EXCL is atomic on both POSIX and Windows, so the
    lock-file-exists check and its creation cannot race between two processes.
    Acquired with bounded retry, never a busy spin forever; a caller that cannot
    get the lock within the timeout raises LockTimeout rather than silently
    proceeding unlocked (which would defeat the whole point). Always release in a
    finally block (the context-manager form does this automatically).
    """

    def __init__(self, target: Path, timeout: float = 10.0, poll_s: float = 0.02):
        self._lock_path = Path(str(target) + ".lock")
        self._timeout = timeout
        self._poll_s = poll_s
        self._fd = None

    def acquire(self) -> None:
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self._timeout
        while True:
            try:
                self._fd = os.open(str(self._lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise LockTimeout(
                        f"could not acquire lock {self._lock_path} within {self._timeout}s "
                        "(another writer is holding it; retry later rather than write unlocked)"
                    )
                time.sleep(self._poll_s)

    def release(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        try:
            self._lock_path.unlink()
        except OSError:
            pass

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False


# --------------------------------------------------------------------------- #
# current.md: loss distribution, kings, candidates, ledger
# --------------------------------------------------------------------------- #
def read_current() -> dict:
    """Load the state block from current.md, or {} if it does not exist yet."""
    return parse_state_block(_read_file(CURRENT_PATH))


def write_current(data: dict) -> None:
    """Render current.md (prose view + json source of truth) from a state dict."""
    _write_file(CURRENT_PATH, _render_current_md(data))


def update_current(mutator) -> dict:
    """Locked read-modify-write on current.md's state dict; the concurrency-safe path.

    Acquires a lock on current.md (see _FileLock), reads the freshest state,
    hands it to mutator(data) (which mutates in place and/or returns the dict to
    write), writes the result back atomically, then releases the lock. Every
    caller that reads current-state, changes a few keys, and writes it back
    should route through this instead of a bare read_current()/write_current()
    pair: without the lock, two concurrent writers (the autoloop's bash-driven
    refresh and this push's canonical writes, or two of this push's own callers)
    can each read the same stale snapshot and the later write silently drops the
    earlier writer's change (a lost-update race). Returns the written dict.
    """
    with _FileLock(CURRENT_PATH):
        data = read_current()
        result = mutator(data)
        data = result if isinstance(result, dict) else data
        write_current(data)
        return data


def ensure_live_refs(data: dict) -> dict:
    """Seed data['live_refs'] with DEFAULT_LIVE_REFS if the key is absent entirely.

    Mutates and returns data. Only fires when live_refs has never been recorded
    at all: an operator (or a future unit) who intentionally sets live_refs to an
    empty list keeps that choice (it is read as "no live build known yet", which
    correctly forces the pool-wide fallback) until live_refs is explicitly set
    again. This is the "seeded once via the canonical writer" step U107b calls
    for; call it from inside an update_current mutator so the seed is written
    atomically with whatever else that write is doing.
    """
    if "live_refs" not in data:
        data["live_refs"] = list(DEFAULT_LIVE_REFS)
    return data


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
    targeting_mode = dist.get("targeting_mode")
    fallback_reason = dist.get("fallback_reason")
    if targeting_mode == "pool_fallback":
        # LOUD by design (U107b): a silent fallback here would look identical to
        # real per-build targeting and mask a lost-update regression back to the
        # audited-broken mixed-pool behavior.
        lines.append(
            f"**FALLBACK TO POOL-WIDE TARGETING** ({fallback_reason or 'live_refs unavailable'}). "
            "This is NOT per-build targeting: it mixes every historical build's "
            "losses together, the audited-broken behavior U107b closes. See "
            "tools/daily_refresh.py refresh_loss_distribution."
        )
        lines.append("")
    elif targeting_mode == "per_build":
        refs = dist.get("ref_filter") or []
        lines.append(f"_per-build targeting (U107b), live refs: {', '.join(str(r) for r in refs)}_")
        lines.append("")

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

    pool_wide = dist.get("pool_wide")
    if pool_wide and targeting_mode == "per_build":
        lines.append(
            f"_secondary, pool-wide (every build ever submitted): "
            f"{pool_wide.get('top_bucket', '?')} over {pool_wide.get('sample_size', 0)} "
            f"replays (W/D/L {pool_wide.get('wins', 0)}/{pool_wide.get('draws', 0)}/"
            f"{pool_wide.get('losses', 0)})._"
        )
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

    noise = data.get("noise_model") or {}
    if noise:
        lines.append("## Noise model (U22)")
        lines.append("")
        lines.append(f"- margin M = {noise.get('margin_M', DEFAULT_MARGIN)} "
                     f"(v{noise.get('version', 1)}): WIN >= king+M, LOSS <= king-M, else BAND.")
        if noise.get("basis"):
            lines.append(f"- basis: {noise['basis']}")
        if noise.get("refit_by"):
            lines.append(f"- re-fit by: {noise['refit_by']}")
        lines.append("")

    pregs = data.get("pre_registrations") or []
    lines.append("## Pre-registrations (machine-checked gate, U22)")
    lines.append("")
    lines.append("A build may not be submitted without a complete row here "
                 "(tools/loop_state.py check-submit --build <name>).")
    lines.append("")
    if pregs:
        lines.append("| build | hypothesis | dir | M | N | settle-by | complete |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for r in pregs:
            complete = "yes" if is_prereg_complete(r) else "NO"
            lines.append(
                f"| {r.get('build', '?')} | {r.get('hypothesis', '')} | "
                f"{r.get('direction', '')} | {r.get('margin', '')} | {r.get('n', '')} | "
                f"{r.get('settle_by', '')} | {complete} |"
            )
        lines.append("")
        for r in pregs:
            actions = r.get("actions") or {}
            lines.append(f"- **{r.get('build', '?')}** filters: {r.get('filters', '')}")
            lines.append(f"  - WIN: {actions.get('win', '')}")
            lines.append(f"  - LOSS: {actions.get('loss', '')}")
            lines.append(f"  - BAND: {actions.get('band', '')}")
        lines.append("")
    else:
        lines.append("_none_")
        lines.append("")

    drafts = data.get("draft_pre_registrations") or []
    if drafts:
        lines.append("## Draft pre-registrations (U10 pair package -- NOT a submission gate)")
        lines.append("")
        lines.append("Staged proposals awaiting Dan's confirmation. These do NOT allow any "
                     "submission (check-submit still BLOCKS); a human moves a row into "
                     "pre_registrations above to finalize it.")
        lines.append("")
        lines.append("| build | hypothesis | dir | M | N | settle-by | status | complete |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for r in drafts:
            complete = "yes" if is_prereg_complete(r) else "NO"
            lines.append(
                f"| {r.get('build', '?')} | {r.get('hypothesis', '')} | "
                f"{r.get('direction', '')} | {r.get('margin', '')} | {r.get('n', '')} | "
                f"{r.get('settle_by', '')} | {r.get('status', 'DRAFT')} | {complete} |"
            )
        lines.append("")
        for r in drafts:
            actions = r.get("actions") or {}
            lines.append(f"- **{r.get('build', '?')}** (DRAFT) filters: {r.get('filters', '')}")
            lines.append(f"  - WIN: {actions.get('win', '')}")
            lines.append(f"  - LOSS: {actions.get('loss', '')}")
            lines.append(f"  - BAND: {actions.get('band', '')}")
        lines.append("")

    proxies = data.get("calibrated_proxies") or []
    lines.append("## Calibrated proxies (U24 retrodiction gate)")
    lines.append("")
    lines.append("A proxy may BLOCK a slot (never promote) only after it retrodicts "
                 "the known five-build ordering (tools/loop_state.py check-gate --proxy <name>).")
    lines.append("")
    if proxies:
        lines.append("| proxy | tau | covered | passes | note |")
        lines.append("| --- | --- | --- | --- | --- |")
        for p in proxies:
            rep = p.get("report") or {}
            lines.append(
                f"| {p.get('proxy', '?')} | {rep.get('tau', '')} | "
                f"{rep.get('n_covered', '')}/{rep.get('n_known', '')} | "
                f"{'yes' if rep.get('passes') else 'NO'} | {p.get('note', '')} |"
            )
    else:
        lines.append("_none calibrated; every proxy gate is refused (default-deny)_")
    lines.append("")

    census = data.get("census") or {}
    if census:
        lines.append("## Expert census tier (U25)")
        lines.append("")
        lines.append(
            f"- cohort = {census.get('cohort', '?')}; dataset "
            f"{census.get('dataset', '?')}"
        )
        lines.append(
            f"- {census.get('episodes_scored', '?')} episodes scored, "
            f"{census.get('ranking_groups', '?')} ranking groups"
        )
        lines.append(
            f"- target family **{census.get('target_family', '?')}** -> tier "
            f"**{census.get('target_tier', '?')}** ({census.get('source', '')})"
        )
        lines.append("")

    branch = data.get("search_branch") or {}
    if branch:
        lines.append("## Search-branch verdict (U27)")
        lines.append("")
        lines.append(
            f"- PIMC diagnostic verdict: **{branch.get('verdict', '?')}** -> "
            f"**{branch.get('branch', '?')}** ({branch.get('source', '')})"
        )
        lines.append(
            f"- leaf correlation {branch.get('leaf_correlation', '?')}, "
            f"disambiguation slope {branch.get('disambig_slope', '?')}, "
            f"bias {branch.get('bias_abs', '?')} (decided {branch.get('decided', '?')}, "
            "not revisited per KD7)"
        )
        lines.append("")

    recon = data.get("reconciliation") or {}
    if recon:
        lines.append("## Contract reconciliation record (U28)")
        lines.append("")
        lines.append(
            f"- {recon.get('rulings', '?')} forked contracts each have one binding "
            f"ruling ({recon.get('source', '')}); recorded {recon.get('recorded', '?')} "
            "before any U40 code exists (KD4/KD5)."
        )
        lines.append(
            f"- W_generic ruling: {recon.get('w_generic', '?')} "
            f"(census tier {recon.get('census_tier', '?')} closes it by data)."
        )
        lines.append("")

    campaign = data.get("endgame_campaign") or {}
    if campaign:
        lines.append("## Endgame stopping rule (U48 prep)")
        lines.append("")
        lines.append(
            f"- stop target = {campaign.get('stop_target', '?')} "
            f"(king_true_estimate {campaign.get('king_true_estimate', '?')} + "
            f"bonus {campaign.get('bonus', '?')}, build {campaign.get('build', '?')})"
        )
        lines.append(f"- pair rule: {campaign.get('pair_rule', '?')}")
        lines.append(
            f"- no-roll buffer {campaign.get('no_roll_buffer', '?')}, "
            f"lock by {campaign.get('lock_by', '?')}"
        )
        if campaign.get("basis"):
            lines.append(f"- basis: {campaign['basis']}")
        lines.append("")

    scoring = data.get("final_scoring") or {}
    if scoring:
        lines.append("## Final scoring semantics (U29)")
        lines.append("")
        lines.append(
            f"- {scoring.get('model', '?')} ({scoring.get('source', '')}); "
            f"recorded {scoring.get('recorded', '?')}, gates U48."
        )
        lines.append(
            f"- deadline {scoring.get('deadline', '?')}, then "
            f"{scoring.get('final_window', '?')}; daily limit "
            f"{scoring.get('daily_limit', '?')}."
        )
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
# pre-registration: the machine-checked A/B gate (plan U22)
# --------------------------------------------------------------------------- #
def _valid_date(value) -> bool:
    """True only for a real YYYY-MM-DD date string (the settle-by field)."""
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.strptime(value.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_prereg(row: dict) -> list:
    """Return a list of human-readable problems that make a pre-registration
    row incomplete. An empty list means the row is complete and a submission for
    its build is allowed.

    This is the mechanical gate U22 adds: the loop may not spend a ladder slot on
    a hypothesis without a complete row. Every field the protocol names must be
    present and well-formed (hypothesis id, direction, margin M, episode floor N,
    settle-by date, offline filter values, and committed WIN/LOSS/BAND actions).
    An incomplete row is a hard block, not a warning, so the checks are strict:
    a missing OR malformed field both count as incomplete.
    """
    problems: list = []
    if not isinstance(row, dict):
        return ["pre-registration is not a mapping"]
    if not str(row.get("build", "")).strip():
        problems.append("missing build")
    if not str(row.get("hypothesis", "")).strip():
        problems.append("missing hypothesis")
    if str(row.get("direction", "")).strip().lower() not in ("up", "down"):
        problems.append("direction must be 'up' or 'down'")
    try:
        if int(row.get("margin")) <= 0:
            problems.append("margin must be a positive integer")
    except (TypeError, ValueError):
        problems.append("margin must be a positive integer")
    try:
        if int(row.get("n")) < MIN_EPISODES:
            problems.append(f"N (episode floor) must be >= {MIN_EPISODES}")
    except (TypeError, ValueError):
        problems.append(f"N (episode floor) must be >= {MIN_EPISODES}")
    if not _valid_date(row.get("settle_by")):
        problems.append("settle_by must be a YYYY-MM-DD date")
    filters = row.get("filters")
    if not filters or (isinstance(filters, str) and not filters.strip()):
        problems.append("missing offline filter values")
    actions = row.get("actions")
    if not isinstance(actions, dict):
        problems.append("missing WIN/LOSS/BAND actions")
    else:
        for key in ("win", "loss", "band"):
            if not str(actions.get(key, "")).strip():
                problems.append(f"missing committed {key.upper()} action")
    return problems


def is_prereg_complete(row: dict) -> bool:
    """True when the row carries every pre-registration field, well-formed."""
    return not validate_prereg(row)


def upsert_prereg(data: dict, row: dict) -> dict:
    """Add or replace (keyed by build) a pre-registration in a current-state dict.

    Raises ValueError if the row is incomplete: the gate refuses to record a
    partial pre-registration, so a row that survives to state/current.md is
    always submission-ready. Returns the mutated data for convenience.
    """
    problems = validate_prereg(row)
    if problems:
        raise ValueError("incomplete pre-registration: " + "; ".join(problems))
    rows = data.get("pre_registrations")
    if not isinstance(rows, list):
        rows = []
    build = row["build"]
    rows = [r for r in rows if r.get("build") != build]
    rows.append(row)
    data["pre_registrations"] = rows
    return data


def upsert_draft_prereg(data: dict, row: dict) -> dict:
    """Add or replace (keyed by build) a DRAFT pre-registration in a state dict.

    A draft is a fully-formed, validate_prereg-clean pre-registration row that is
    NOT yet a live submission gate: it is written to a separate
    ``draft_pre_registrations`` list and stamped ``status="DRAFT"``. It is
    deliberately kept out of ``pre_registrations`` so ``submission_allowed`` still
    BLOCKS the build -- only a human confirmation promotes a draft into the live
    ``pre_registrations`` list. This is the canonical writer the U10 pair package
    uses to stage a proposed final-pair row for Dan to sign, without ever flipping
    the submission gate open on an unsigned build.

    Raises ValueError if the row is incomplete, so a draft still has to be a
    complete, well-formed pre-registration (the same schema the live gate uses):
    a draft is "not yet signed", never "not yet finished". Returns the mutated
    data for convenience.
    """
    problems = validate_prereg(row)
    if problems:
        raise ValueError("incomplete pre-registration: " + "; ".join(problems))
    row = dict(row)
    row["status"] = "DRAFT"
    rows = data.get("draft_pre_registrations")
    if not isinstance(rows, list):
        rows = []
    build = row["build"]
    rows = [r for r in rows if r.get("build") != build]
    rows.append(row)
    data["draft_pre_registrations"] = rows
    return data


def submission_allowed(data: dict, build: str) -> tuple:
    """The dry-run submission gate: (allowed, reason) for a build.

    A submission is allowed only when current-state carries a complete
    pre-registration row for exactly that build. No row, or an incomplete row,
    blocks the slot. Callers (and the check-submit CLI) run this BEFORE any
    kaggle submit so an unpre-registered build can never reach the ladder.
    """
    for r in data.get("pre_registrations") or []:
        if r.get("build") == build:
            problems = validate_prereg(r)
            if problems:
                return False, "pre-registration incomplete: " + "; ".join(problems)
            return True, "pre-registration complete; submission allowed"
    return False, (f"no pre-registration row for build '{build}'; submission "
                   "blocked (U22: pre-register a complete row first)")


def settle_verdict(candidate_score, king_score, margin: int = DEFAULT_MARGIN) -> str:
    """WIN / LOSS / BAND from the noise-model margin arithmetic.

    WIN when the candidate clears the king by at least M, LOSS when it falls at
    least M below, BAND (inside the same-build noise band) otherwise. Ties and
    sub-margin gaps are BAND by construction, so noise is never promoted.
    """
    diff = float(candidate_score) - float(king_score)
    if diff >= margin:
        return "WIN"
    if diff <= -margin:
        return "LOSS"
    return "BAND"


def auto_settle(data: dict, build: str, candidate_score, king_score,
                margin: int | None = None) -> dict:
    """Mechanically settle a pre-registered build against the board: the verdict
    plus the EXACT committed action text for that verdict, with no prose
    interpretation.

    Looks up the build's own pre-registration row, computes WIN/LOSS/BAND via
    settle_verdict using the row's own margin (unless margin overrides it), and
    returns the row's already-committed action string for that verdict. This is
    the mandatory per-iteration auto-settlement step the L2 candidate-eviction
    note called for: a candidate reading clearly outside the band should be
    settled the instant it is observed, mechanically, rather than re-litigated
    in prose each time. Raises ValueError when no complete pre-registration row
    exists for the build, so nothing can be "settled" without one.
    """
    reg = None
    for r in data.get("pre_registrations") or []:
        if r.get("build") == build:
            reg = r
            break
    if reg is None:
        raise ValueError(f"no pre-registration row for build '{build}'")
    problems = validate_prereg(reg)
    if problems:
        raise ValueError("pre-registration incomplete: " + "; ".join(problems))
    m = margin if margin is not None else int(reg["margin"])
    verdict = settle_verdict(candidate_score, king_score, margin=m)
    action = (reg.get("actions") or {}).get(verdict.lower(), "")
    return {
        "build": build,
        "verdict": verdict,
        "margin": m,
        "candidate_score": candidate_score,
        "king_score": king_score,
        "action": action,
    }


# --------------------------------------------------------------------------- #
# proxy retrodiction gate: no uncalibrated proxy may block a slot (plan U24)
# --------------------------------------------------------------------------- #
def record_proxy_calibration(data: dict, proxy: str, proxy_scores: dict,
                             note: str | None = None) -> tuple:
    """Calibrate a proxy against the known five-build ordering and store the report.

    Runs analysis.proxy_calibration.calibrate over the proxy's per-build scores,
    records the report under current-state's calibrated_proxies (keyed by proxy
    name, replacing any prior report), and returns (data, report). A failing proxy
    is still recorded so the failure is visible and gate refusals can explain
    themselves; only a passing report unlocks gating.
    """
    report = calibrate(proxy_scores)
    rows = data.get("calibrated_proxies")
    if not isinstance(rows, list):
        rows = []
    rows = [r for r in rows if r.get("proxy") != proxy]
    entry = {"proxy": proxy, "report": report}
    if note:
        entry["note"] = note
    rows.append(entry)
    data["calibrated_proxies"] = rows
    return data, report


def proxy_may_gate(data: dict, proxy: str) -> tuple:
    """(allowed, reason): may this proxy BLOCK a slot?

    A proxy may gate only when current-state carries a calibration report for it
    whose retrodiction PASSED. No report, or a failing report, refuses the gate.
    This is the U24 default-deny: until a proxy proves it reproduces the known
    ladder ordering, loop_state will not let it kill a candidate. A passing proxy
    may only BLOCK, never promote; the ladder A/B stays the sole arbiter.
    """
    for r in data.get("calibrated_proxies") or []:
        if r.get("proxy") == proxy:
            report = r.get("report") or {}
            tau = report.get("tau")
            if report.get("passes"):
                return True, (f"proxy '{proxy}' calibrated (tau {tau}, covered "
                              f"{report.get('n_covered')}/{report.get('n_known')}); "
                              "may BLOCK a slot, never promote")
            return False, (f"proxy '{proxy}' failed retrodiction (tau {tau}, "
                           f"covered {report.get('n_covered')}/{report.get('n_known')}); "
                           "may not gate")
    return False, (f"proxy '{proxy}' has no calibration report; may not gate "
                   "(U24: calibrate against the known five-build ordering first)")


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


def classify_dirs_per_build(dirs, ref_filter: list[str] | None = None) -> dict:
    """Ranked loss-bucket report, optionally filtered by submission ref (U107).

    When ref_filter is provided (a list of submission refs), reads the
    episode-to-ref manifest from data/episode_to_ref.json and only classifies
    episodes belonging to the specified refs. Returns the full classify_batch
    report plus the filter applied and filtered episode count.

    Used for per-build loss ledger: segregate losses by submission so that
    targeting is attributed to the actual shipped agent, not a historical
    mix of all builds ever submitted.
    """
    import json
    from analysis.loss_classifier import parse_replay  # noqa: F401
    from tools import harvest_replays as hr
    from tools.scout import is_self_play, load_replay, our_index_from_replay

    digests = []
    used = []
    filtered_episodes = 0
    episode_to_ref = {}
    ref_filter_set = set(ref_filter) if ref_filter else set()

    # Load manifest if filtering is requested
    if ref_filter:
        episode_to_ref = hr._load_episode_to_ref_manifest()

    for d in dirs:
        path = Path(d)
        if not path.is_absolute():
            path = _ROOT / d
        if not path.is_dir():
            continue

        if ref_filter:
            # Iterate through files directly to filter by episode ref (U107)
            for fpath in sorted(path.glob("*.json")):
                try:
                    replay = load_replay(fpath)
                except (OSError, json.JSONDecodeError):
                    continue
                if is_self_play(replay):
                    continue

                # Extract episode_id from filename (format: <episode_id>.json)
                episode_id = fpath.stem
                ep_ref = episode_to_ref.get(str(episode_id))

                # Only include if ref is in filter (normalize to string for comparison)
                if ep_ref and str(ep_ref) in ref_filter_set:
                    seat = our_index_from_replay(replay)
                    digest = parse_replay(replay, our_index=seat if seat is not None else 0)
                    digests.append(digest)
                    filtered_episodes += 1
        else:
            # No filtering; use the standard digest_dir
            got = digest_dir(path)
            if got:
                digests.extend(got)
        used.append(str(d))

    report = classify_batch(digests)
    report["sources"] = used
    report["sample_size"] = report.get("games", 0)
    report["ref_filter"] = ref_filter or []
    report["filtered_episodes"] = filtered_episodes
    return report


def loss_distribution_from_dirs(dirs, ref_filter=None) -> dict:
    """Shape classify_dirs into the loss_distribution block current.md expects.

    When ref_filter is provided (a list of submission refs), filters the loss
    distribution to only episodes from those builds (U107 per-build ledger).
    Otherwise, uses the full union of all episodes across dirs.
    """
    if ref_filter:
        rep = classify_dirs_per_build(dirs, ref_filter=ref_filter)
    else:
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
        "ref_filter": ref_filter or [],
    }


# --------------------------------------------------------------------------- #
# CLI: refresh the loss distribution, or show the target bucket / re-test list
# --------------------------------------------------------------------------- #
def _cmd_refresh(args) -> None:
    ref_filter = None
    if args.ref_filter:
        ref_filter = args.ref_filter.split(",") if isinstance(args.ref_filter, str) else args.ref_filter
    dist = loss_distribution_from_dirs(args.dirs, ref_filter=ref_filter)

    def _mutate(data):
        data["loss_distribution"] = dist
        return data

    update_current(_mutate)
    if ref_filter:
        print(f"current.md updated (refs: {', '.join(ref_filter)}): "
              f"top bucket = {dist['top_bucket']} over {dist['sample_size']} replays "
              f"(W/D/L {dist['wins']}/{dist['draws']}/{dist['losses']})")
    else:
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


def _cmd_prereg(args) -> None:
    row = {
        "build": args.build,
        "hypothesis": args.hypothesis,
        "direction": args.direction,
        "margin": args.margin,
        "n": args.n,
        "settle_by": args.settle_by,
        "filters": args.filters,
        "actions": {"win": args.win, "loss": args.loss, "band": args.band},
    }
    problems_holder = {}

    def _mutate(data):
        try:
            upsert_prereg(data, row)
        except ValueError as exc:
            problems_holder["error"] = str(exc)
            raise
        return data

    try:
        update_current(_mutate)
    except ValueError:
        print(problems_holder["error"])
        raise SystemExit(2)
    print(f"pre-registered '{args.build}' (complete); submission now allowed")


def _cmd_prereg_draft(args) -> None:
    row = {
        "build": args.build,
        "hypothesis": args.hypothesis,
        "direction": args.direction,
        "margin": args.margin,
        "n": args.n,
        "settle_by": args.settle_by,
        "filters": args.filters,
        "actions": {"win": args.win, "loss": args.loss, "band": args.band},
    }
    data = read_current()
    try:
        upsert_draft_prereg(data, row)
    except ValueError as exc:
        print(str(exc))
        raise SystemExit(2)
    write_current(data)
    print(f"drafted pre-registration for '{args.build}' (DRAFT, complete); "
          "submission still BLOCKED until Dan promotes it to pre_registrations")


def _cmd_check_submit(args) -> None:
    ok, reason = submission_allowed(read_current(), args.build)
    print(("ALLOW: " if ok else "BLOCK: ") + reason)
    if not ok:
        raise SystemExit(1)


def _cmd_calibrate_proxy(args) -> None:
    try:
        scores = json.loads(args.scores)
    except ValueError as exc:
        print(f"invalid --scores JSON: {exc}")
        raise SystemExit(2)
    if not isinstance(scores, dict):
        print("--scores must be a JSON object mapping build -> score")
        raise SystemExit(2)
    report_holder = {}

    def _mutate(data):
        new_data, report = record_proxy_calibration(data, args.proxy, scores, note=args.note)
        report_holder["report"] = report
        return new_data

    update_current(_mutate)
    report = report_holder["report"]
    verdict = "PASS" if report["passes"] else "FAIL"
    print(f"calibrated '{args.proxy}': {verdict} (tau={report['tau']}, "
          f"covered {report['n_covered']}/{report['n_known']})")
    if not report["passes"]:
        raise SystemExit(2)


def _cmd_check_gate(args) -> None:
    ok, reason = proxy_may_gate(read_current(), args.proxy)
    print(("ALLOW: " if ok else "BLOCK: ") + reason)
    if not ok:
        raise SystemExit(1)


def _cmd_auto_settle(args) -> None:
    try:
        result = auto_settle(read_current(), args.build, args.candidate_score,
                             args.king_score, margin=args.margin)
    except ValueError as exc:
        print(str(exc))
        raise SystemExit(2)
    print(f"{result['verdict']} (margin {result['margin']}, "
          f"{result['candidate_score']} vs king {result['king_score']}): "
          f"{result['action']}")


def main() -> None:
    ap = argparse.ArgumentParser(description="stateful loop memory (plan U12)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    rf = sub.add_parser("refresh", help="re-classify replays and update current.md's loss distribution")
    rf.add_argument("dirs", nargs="+", help="replay directories to classify")
    rf.add_argument("--ref-filter", default=None,
                    help="comma-separated submission refs to filter by (U107 per-build ledger); "
                         "if provided, only episodes from these refs are classified")

    sub.add_parser("target", help="print the current top loss bucket from current.md")

    rt = sub.add_parser("retest", help="list refuted hypotheses whose re-test condition is now met")
    rt.add_argument("--sample", type=int, default=None, help="current replay sample size")
    rt.add_argument("--deck", default=None, help="current deck name")

    pr = sub.add_parser("prereg", help="add/replace a machine-checked pre-registration row (U22)")
    pr.add_argument("--build", required=True, help="the exact build/candidate name")
    pr.add_argument("--hypothesis", required=True, help="hypothesis id or claim under test")
    pr.add_argument("--direction", required=True, choices=["up", "down"],
                    help="expected direction of the metric")
    pr.add_argument("--margin", type=int, default=DEFAULT_MARGIN,
                    help=f"settlement margin M (default {DEFAULT_MARGIN})")
    pr.add_argument("--n", type=int, required=True,
                    help=f"pre-committed episode floor N (>= {MIN_EPISODES})")
    pr.add_argument("--settle-by", dest="settle_by", required=True, help="YYYY-MM-DD")
    pr.add_argument("--filters", required=True, help="offline filter values that were met")
    pr.add_argument("--win", required=True, help="committed WIN action")
    pr.add_argument("--loss", required=True, help="committed LOSS action")
    pr.add_argument("--band", required=True, help="committed BAND action")

    prd = sub.add_parser("prereg-draft",
                         help="stage a DRAFT pre-registration row (U10 pair package); "
                              "validated but kept out of the live submission gate")
    prd.add_argument("--build", required=True, help="the exact build/candidate name")
    prd.add_argument("--hypothesis", required=True, help="hypothesis id or claim under test")
    prd.add_argument("--direction", required=True, choices=["up", "down"],
                     help="expected direction of the metric")
    prd.add_argument("--margin", type=int, default=DEFAULT_MARGIN,
                     help=f"settlement margin M (default {DEFAULT_MARGIN})")
    prd.add_argument("--n", type=int, required=True,
                     help=f"pre-committed episode floor N (>= {MIN_EPISODES})")
    prd.add_argument("--settle-by", dest="settle_by", required=True, help="YYYY-MM-DD")
    prd.add_argument("--filters", required=True, help="offline filter values that were met")
    prd.add_argument("--win", required=True, help="committed WIN action")
    prd.add_argument("--loss", required=True, help="committed LOSS action")
    prd.add_argument("--band", required=True, help="committed BAND action")

    cs = sub.add_parser("check-submit", help="dry-run the U22 submission gate for a build")
    cs.add_argument("--build", required=True, help="the build about to be submitted")

    cp = sub.add_parser("calibrate-proxy",
                        help="retrodict a proxy vs the known five-build ordering (U24)")
    cp.add_argument("--proxy", required=True, help="proxy name")
    cp.add_argument("--scores", required=True,
                    help='JSON object {build: score} the proxy assigns each known build')
    cp.add_argument("--note", default=None, help="optional note stored with the report")

    cg = sub.add_parser("check-gate", help="dry-run the U24 proxy gate for a proxy")
    cg.add_argument("--proxy", required=True, help="the proxy about to gate a slot")

    ast = sub.add_parser("auto-settle",
                         help="mechanically settle a pre-registered build: WIN/LOSS/BAND "
                              "plus its exact committed action, no prose interpretation")
    ast.add_argument("--build", required=True, help="the exact build/candidate name")
    ast.add_argument("--candidate-score", type=float, required=True, dest="candidate_score",
                     help="the candidate's current board reading")
    ast.add_argument("--king-score", type=float, required=True, dest="king_score",
                     help="the king's current board reading")
    ast.add_argument("--margin", type=int, default=None,
                     help="override the row's own margin (defaults to the row's margin)")

    args = ap.parse_args()
    if args.cmd == "refresh":
        _cmd_refresh(args)
    elif args.cmd == "target":
        _cmd_target(args)
    elif args.cmd == "retest":
        _cmd_retest(args)
    elif args.cmd == "prereg":
        _cmd_prereg(args)
    elif args.cmd == "prereg-draft":
        _cmd_prereg_draft(args)
    elif args.cmd == "check-submit":
        _cmd_check_submit(args)
    elif args.cmd == "calibrate-proxy":
        _cmd_calibrate_proxy(args)
    elif args.cmd == "check-gate":
        _cmd_check_gate(args)
    elif args.cmd == "auto-settle":
        _cmd_auto_settle(args)


if __name__ == "__main__":
    main()
