"""Card-effect tag coverage meter and gate (U33 / MSR-3).

Answers one question for a deck: does the card-knowledge layer
(agents/card_effects.py) understand every card in it? A card is covered when it
resolves to EMPTY (no effect text: a vanilla Pokemon or a basic energy) or TAGGED
(a recognized effect); it is a gap when it is UNTAGGED_EFFECT (effect text no tag
matches yet) or UNKNOWN_CARD (id not in the pool).

Two uses:

1. The 100% target-deck gate. Before any deck-AWARE pilot build (the seeds
   consumer U37, the learned ranker U40/U41) may spend a scarce ladder slot, every
   card in the target deck must be covered: a pilot that keys on card tags must not
   be blind to any card it will actually play. deck_covered_100pct() is that gate;
   it is advisory here (no build reads it yet) and consumed when the aware pilot
   lands.

2. The ratcheting pool audit. pool_untagged_fraction() is the share of
   effect-bearing pool cards the layer does not yet recognize. It only falls as the
   vocabulary grows, so analysis/tag_coverage_baseline.json records it and a test
   asserts the live value never rises (a vocabulary regression is caught).

This is a development tool. It uses the same card lookup the pilot uses
(agents/heuristics: card_index, _card_text, _card_type) but is never shipped.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agents import card_effects  # noqa: E402
from agents import heuristics  # noqa: E402
from tools.deck_validate import read_deck  # noqa: E402

TARGET_DECK = "trolley_thick"
BASELINE_PATH = _ROOT / "analysis" / "tag_coverage_baseline.json"


def card_state(card_id):
    """Resolve one card id to its (state, tags) via the knowledge layer.

    Owns the card lookup the layer deliberately does not: a missing card is
    UNKNOWN_CARD, otherwise the card's effect text drives resolve(). Never raises.
    """
    try:
        present = heuristics.card_index().get(card_id) is not None
    except Exception:
        present = False
    text = heuristics._card_text(card_id) if present else None
    return card_effects.resolve(present, text)


def deck_coverage(deck_ids) -> dict:
    """Coverage report for a deck (a list of card ids), over its DISTINCT cards.

    Counting distinct cards (not all 60) keeps the copy count of a basic energy
    from dominating the fraction. Returns the per-state counts, the covered
    fraction, and the specific uncovered card ids so a gap is actionable.
    """
    distinct = sorted(set(deck_ids))
    states = {}
    counts = Counter()
    uncovered = []
    for cid in distinct:
        state, tags = card_state(cid)
        states[cid] = (state, sorted(tags))
        counts[state] += 1
        if not card_effects.is_covered(state):
            uncovered.append(cid)
    total = len(distinct)
    covered = total - len(uncovered)
    return {
        "distinct_cards": total,
        "covered": covered,
        "coverage": (covered / total) if total else 1.0,
        "counts": dict(counts),
        "uncovered": uncovered,
        "states": states,
    }


def deck_covered_100pct(deck_ids) -> bool:
    """The gate: True only when every distinct card in the deck is covered."""
    return not deck_coverage(deck_ids)["uncovered"]


def pool_untagged_fraction() -> dict:
    """Share of effect-bearing pool cards the layer does not recognize (the ratchet).

    Denominator is every pool card that carries effect text (EMPTY vanilla cards
    are excluded: they have nothing to tag). Numerator is the UNTAGGED_EFFECT
    cards. Falls monotonically as tags are added, so it is a safe ratchet metric.
    Never raises; an empty pool reports 0.0.
    """
    try:
        ids = list(heuristics.card_index().keys())
    except Exception:
        ids = []
    with_text = 0
    untagged = 0
    for cid in ids:
        state, _ = card_state(cid)
        if state == card_effects.UNTAGGED_EFFECT:
            with_text += 1
            untagged += 1
        elif state == card_effects.TAGGED:
            with_text += 1
    return {
        "effect_cards": with_text,
        "untagged": untagged,
        "fraction": (untagged / with_text) if with_text else 0.0,
    }


def _deck_path(name) -> Path:
    return _ROOT / "decks" / f"{name}.csv"


def load_baseline() -> dict:
    return json.loads(BASELINE_PATH.read_text()) if BASELINE_PATH.exists() else {}


def build_baseline() -> dict:
    """The committed audit record: tags version, target-deck coverage, pool ratchet."""
    cov = deck_coverage(read_deck(_deck_path(TARGET_DECK)))
    pool = pool_untagged_fraction()
    return {
        "tags_version": card_effects.TAGS_VERSION,
        "target_deck": TARGET_DECK,
        "target_deck_coverage": cov["coverage"],
        "target_deck_uncovered": cov["uncovered"],
        "pool_effect_cards": pool["effect_cards"],
        "pool_untagged": pool["untagged"],
        "pool_untagged_fraction": pool["fraction"],
    }


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="card-effect tag coverage meter")
    ap.add_argument("deck", nargs="?", default=TARGET_DECK,
                    help="deck name under decks/ (default: the target deck)")
    ap.add_argument("--write-baseline", action="store_true",
                    help="regenerate analysis/tag_coverage_baseline.json")
    args = ap.parse_args()

    if args.write_baseline:
        rec = build_baseline()
        BASELINE_PATH.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
        print(f"wrote {BASELINE_PATH}")
        print(json.dumps(rec, indent=2, sort_keys=True))
        return

    cov = deck_coverage(read_deck(_deck_path(args.deck)))
    pool = pool_untagged_fraction()
    print(f"deck {args.deck}: coverage {cov['coverage']:.3f} "
          f"({cov['covered']}/{cov['distinct_cards']} distinct cards)")
    print(f"  counts: {cov['counts']}")
    if cov["uncovered"]:
        print(f"  UNCOVERED ids: {cov['uncovered']}")
        for cid in cov["uncovered"]:
            state, _ = cov["states"][cid]
            name = None
            c = heuristics.card_index().get(cid)
            if c is not None:
                name = getattr(c, "name", None)
            print(f"    {cid} ({name}): {state}")
    print(f"pool untagged fraction: {pool['fraction']:.4f} "
          f"({pool['untagged']}/{pool['effect_cards']} effect cards)")


if __name__ == "__main__":
    main()
