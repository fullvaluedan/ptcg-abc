"""Ladder replay -> early-turn archetype silver-label rows (plan U9a).

Pairs analysis/early_archetype_features.py's early-turn-only feature vector
with analysis/opponent_archetype.py's archetype_label(), computed over the
SAME replay's WHOLE game. That label always looks further into the future
than the features it is paired with, so this is a legitimate distillation
target (predict what the whole game eventually reveals, from only the first
few turns), not a leak: U9b trains a classifier on these rows, and U9c wires
its prediction into analysis/archetype.py's pre-reveal fallback behind a flag.

Any label seen fewer than MIN_LABEL_GAMES times is collapsed into OTHER,
mirroring tools/archetype_select.py's own MIN_GAMES/OTHER pattern: the real
ladder replay pool is long-tailed across 20+ archetypes at n=140 usable games
(docs/plans/2026-07-03-addendum-u9-archetype-detection-v1.md), so most raw
labels have too few examples to be a trustworthy classifier class on their own.

Dev tool only; never shipped. Ladder replay JSON is gitignored competition
data, never committed or redistributed.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.early_archetype_features import (  # noqa: E402
    DEFAULT_CUTOFF_TURN,
    FEATURE_NAMES,
    early_archetype_features,
)
from analysis.opponent_archetype import archetype_label, revealed_opponent_pokemon  # noqa: E402
from analysis.replay_trace import episode_id_of  # noqa: E402
from tools.scout import OUR_TEAM, is_self_play, load_replay, our_index_from_replay  # noqa: E402

DEFAULT_SRC_DIR = _ROOT / "data" / "replays"
DEFAULT_OUT_DIR = _ROOT / "data" / "training"
SOURCE = "ladder"

# A label with fewer appearances than this collapses into OTHER: too few
# examples to train a trustworthy per-class decision on (see module docstring).
MIN_LABEL_GAMES = 5
OTHER = "other"


def real_predicates():
    """Real card-engine name_of/is_pokemon/energy_type_of, lazily wired.

    Local import so this tool only touches the native engine when actually
    converting replays, mirroring analysis.opponent_archetype.scan_dir's own
    local-import wiring.
    """
    from agents.heuristics import CARD_BASIC_ENERGY, CARD_POKEMON, card_index

    cards = card_index()

    def name_of(cid):
        c = cards.get(cid)
        return getattr(c, "name", None) if c is not None else None

    def is_pokemon(cid):
        c = cards.get(cid)
        return c is not None and getattr(c, "cardType", None) == CARD_POKEMON

    def energy_type_of(cid):
        c = cards.get(cid)
        if c is None or getattr(c, "cardType", None) != CARD_BASIC_ENERGY:
            return None
        return getattr(c, "energyType", None)

    return name_of, is_pokemon, energy_type_of


def row_from_replay(replay, predicates, our_index_fallback=0,
                     cutoff_turn=DEFAULT_CUTOFF_TURN, team=None):
    """(label, feature_vector) for one replay, or None for self-play/unreadable.

    `predicates` is a (name_of, is_pokemon, energy_type_of) tuple, normally
    from real_predicates(). label is the WHOLE-game silver label; the feature
    vector is early_archetype_features over the same replay capped at
    cutoff_turn. Returns None for self-play episodes (not real ladder
    opponents, mirrors analysis.opponent_archetype.scan_dir).
    """
    if not isinstance(replay, dict) or is_self_play(replay):
        return None
    name_of, is_pokemon, energy_type_of = predicates
    team = team or OUR_TEAM
    seat = our_index_from_replay(replay, team)
    our_index = seat if seat is not None else our_index_fallback
    opp_seat = 1 - our_index

    revealed = revealed_opponent_pokemon(replay, opp_seat, is_pokemon)
    label = archetype_label(revealed, name_of)
    feats = early_archetype_features(replay, opp_seat, is_pokemon, energy_type_of, cutoff_turn)
    return label, feats


def collapse_rare_labels(labeled_rows, min_games=MIN_LABEL_GAMES) -> list:
    """Collapse any label with fewer than min_games appearances into OTHER.

    `labeled_rows` is an iterable of (label, feats) pairs; returns a new list,
    input is left unmodified. Pure.
    """
    counts: dict = {}
    for label, _feats in labeled_rows:
        counts[label] = counts.get(label, 0) + 1
    return [
        (label if counts[label] >= min_games else OTHER, feats)
        for label, feats in labeled_rows
    ]


def convert_dir(src_dir=None, cutoff_turn=DEFAULT_CUTOFF_TURN, team=None,
                 min_games=MIN_LABEL_GAMES, predicates=None) -> list:
    """(game_id, label, *FEATURE_NAMES) rows for every replay under src_dir.

    Rare raw labels are folded into OTHER (collapse_rare_labels) before this
    returns. Malformed or unreadable replay files, and self-play episodes, are
    skipped rather than aborting the whole batch.
    """
    src_dir = Path(src_dir) if src_dir else DEFAULT_SRC_DIR
    predicates = predicates or real_predicates()

    game_ids = []
    labeled = []
    for path in sorted(Path(src_dir).glob("*.json")):
        try:
            replay = load_replay(path)
        except (OSError, ValueError):
            continue
        try:
            result = row_from_replay(replay, predicates, cutoff_turn=cutoff_turn, team=team)
        except (AttributeError, TypeError, KeyError):
            continue
        if result is None:
            continue
        game_ids.append(episode_id_of(path.name))
        labeled.append(result)

    collapsed = collapse_rare_labels(labeled, min_games=min_games)
    return [[game_id, label, *feats] for game_id, (label, feats) in zip(game_ids, collapsed)]


def label_counts(rows) -> dict:
    """{label: row count} over convert_dir's output, for the companion report."""
    counts: dict = {}
    for row in rows:
        label = row[1]
        counts[label] = counts.get(label, 0) + 1
    return counts


def write_csv(rows, out_path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["game_id", "label", *FEATURE_NAMES, "source"])
        for row in rows:
            writer.writerow([*row, SOURCE])
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default=str(DEFAULT_SRC_DIR),
                     help="directory of replay JSON files (default data/replays)")
    ap.add_argument("--out", default=None,
                     help="output CSV path (default data/training/archetype_rows_<timestamp>.csv)")
    ap.add_argument("--cutoff-turn", type=int, default=DEFAULT_CUTOFF_TURN,
                     help="max turn number to read early-turn features from")
    ap.add_argument("--min-label-games", type=int, default=MIN_LABEL_GAMES,
                     help="labels seen fewer than this many times collapse into 'other'")
    args = ap.parse_args()

    rows = convert_dir(args.dir, cutoff_turn=args.cutoff_turn, min_games=args.min_label_games)
    out_path = Path(args.out) if args.out else DEFAULT_OUT_DIR / f"archetype_rows_{int(time.time())}.csv"
    write_csv(rows, out_path)

    counts = label_counts(rows)
    other = counts.get(OTHER, 0)
    print(f"wrote {len(rows)} archetype rows ({len(counts)} labels after collapse) to {out_path}")
    for label, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {label:<28} {n}")
    if other:
        print(f"collapsed-to-other: {other} rows")


if __name__ == "__main__":
    main()
