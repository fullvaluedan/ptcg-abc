"""Teacher self-play label store: teacher-agreement fitness data (plan U83 prep).

`analysis/cem_run_prio_pooled.md` recorded the PRIO genome's second consecutive
non-WIN CEM candidate (a flat, zero held-out transfer against the real-ladder
expert-move sample) and named its own re-open conditions: (a) a materially
larger expert-move sample, or (c) a genome region with an observed non-flat
held-out gradient. `L6` (U82 category mining v2) mined the rule-flag space and
found no new lever, so condition (c) is unavailable. This module targets
condition (a): the real dataset gives 116 train / 30 held-out test MAIN
decisions; self-play against the calibrated L5 bracket ring
(`tools.ring_calibrate`, tau 0.857) can generate thousands, at the cost of the
labels being teacher-quality (a full search-stack agent's own choices) rather
than human-top-player-quality.

Deliberately shaped like `analysis.move_ranking_validator`: `agreement()` takes
the same {"n", "agree", "agreement"} shape as that module's `agreement()`, so a
caller (or a future `tools/cem_tune.py` fitness channel) can swap one label
source for the other without touching any downstream code. The difference is
the record source: a Kaggle replay's per-seat steps there, a self-play JSONL
log here.
"""
from __future__ import annotations

import json
from pathlib import Path

SEL_MAIN = 0


def is_scorable_main(obs):
    """(sel, options) if `obs` is a scorable single-pick MAIN decision, else None.

    Mirrors `analysis.replay_trace._scorable_main`'s definition (SEL_MAIN,
    exactly one pick, more than one option) so teacher-agreement numbers stay
    comparable to the existing real-ladder expert-move agreement filter (U5).
    Pure, never raises on a malformed obs.
    """
    sel = (obs or {}).get("select")
    if not isinstance(sel, dict) or sel.get("type") != SEL_MAIN:
        return None
    if sel.get("minCount", 1) != 1 or sel.get("maxCount", 1) != 1:
        return None
    options = sel.get("option") or []
    if len(options) <= 1:
        return None
    return sel, options


def played_index(move):
    """The single option index `move` names, or None when not a single pick."""
    if isinstance(move, (list, tuple)) and len(move) == 1:
        idx = move[0]
        if isinstance(idx, int) and not isinstance(idx, bool) and idx >= 0:
            return idx
    return None


class TeacherLogger:
    """Buffers one JSONL row per scorable MAIN decision the teacher seat makes.

    Unlike `tools.gauntlet`'s winner-only move logging, EVERY decision is kept
    regardless of who wins the game: the teacher's own choice is the label, not
    a proxy for skill, so a loss carries just as much signal as a win. Rows are
    buffered per game and flushed at `flush_game`, mirroring the gauntlet
    logger's per-game buffering so a multi-thousand-game harvest stays memory
    bounded. Opens in append mode so repeated runs against the same path grow
    one accumulating label set across loop iterations instead of overwriting it.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "a", encoding="utf-8")

    def wrap(self, agent_fn, game_id, seat, rows):
        """Wrap `agent_fn` so every scorable decision it makes appends to `rows`."""

        def wrapped(obs):
            move = agent_fn(obs)
            got = is_scorable_main(obs)
            if got is not None:
                idx = played_index(move)
                _sel, options = got
                if idx is not None and idx < len(options):
                    rows.append(
                        {
                            "game_id": game_id,
                            "seat": seat,
                            "decision_id": len(rows),
                            "obs": obs,
                            "played": idx,
                        }
                    )
            return move

        return wrapped

    def flush_game(self, rows):
        for row in rows:
            self._fh.write(json.dumps(row) + "\n")
        self._fh.flush()

    def close(self):
        self._fh.close()


def load_records(source, limit=None):
    """Yield teacher-decision dicts from a `.jsonl` file or a directory of them.

    A directory is read as every `*.jsonl` member, sorted, mirroring
    `move_ranking_validator.load_replays`'s dir-of-files shape. A malformed line
    is skipped rather than aborting the batch. `limit` caps how many records are
    yielded so a CLI run stays bounded.
    """
    src = Path(source)
    paths = sorted(src.glob("*.jsonl")) if src.is_dir() else [src]
    count = 0
    for path in paths:
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                if limit is not None and count >= limit:
                    return
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                count += 1
                yield rec


def agreement(records, pilot_choose):
    """Top-1 agreement of a candidate pilot with the logged teacher decisions.

    Mirrors `analysis.move_ranking_validator.agreement`'s contract exactly (same
    {"n", "agree", "agreement"} shape) so `cem_tune.aggregate_fitness` and any
    downstream reporting work unchanged against either label source. A pilot
    that raises or answers with something other than a single index counts as a
    non-match, never aborts the batch.
    """
    n = 0
    agree = 0
    for rec in records:
        n += 1
        try:
            choice = pilot_choose(rec["obs"])
        except Exception:
            continue
        if isinstance(choice, (list, tuple)) and len(choice) == 1 and choice[0] == rec["played"]:
            agree += 1
    return {"n": n, "agree": agree, "agreement": (agree / n) if n else None}
