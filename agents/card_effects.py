"""Card-knowledge layer: a fixed effect-tag vocabulary over card text (U33).

Pure stdlib. No cg import, no card lookup, no package import: every function here
takes the already-fetched effect text (a string or None) and returns a frozenset
of tags drawn from TAG_VOCAB, so the module bundles next to main.py in a
submission and is trivially testable without the native engine. The callers
(agents/heuristics.py, tools/tag_coverage.py) own the card lookup and pass the
text in; this keeps the layer one-directional (heuristics imports card_effects,
never the reverse) and free of the sys.path/cg concerns heuristics carries.

Why a tag layer at all: the heuristic's card-aware branches used to each re-scan
the raw effect text with their own substring/regex checks (does this trainer mill
the deck, does it bench a Basic, is this ability once-per-turn). That knowledge is
now named once here, so a later deck-aware pilot (seeds, ranker) reads the same
tags instead of re-deriving them, and a coverage meter (tools/tag_coverage.py) can
audit which cards in a deck the layer actually understands.

Behavior contract: the tag predicates reproduce the exact boolean the old inline
heuristics checks returned, card-for-card over the whole pool. tests/
test_card_effects.py pins that equivalence against a frozen copy of the legacy
inline logic, so the delegation in heuristics.py is behavior-frozen: any drift in
a tag definition breaks the golden test before it can change ladder behavior.

Three-state degradation (resolve): a card is EMPTY (no effect text: a vanilla
Pokemon or a basic energy), TAGGED (text we recognize), UNTAGGED_EFFECT (text we
do not recognize yet: the coverage gap the meter ratchets down), or UNKNOWN_CARD
(the id is not in the pool at all). Only EMPTY and TAGGED count as covered.

TAGS_VERSION is bumped whenever TAG_VOCAB or any tag's definition changes; a drift
test pins it so a silent vocabulary edit cannot pass unnoticed (mirrors the
engine-drift STATE LOCK).
"""
from __future__ import annotations

import re

# Bump on ANY change to TAG_VOCAB or a tag definition below. A drift test
# (tests/test_card_effects.py) pins this so a vocabulary edit is never silent.
TAGS_VERSION = "1"

# Effect tags. Each names one atomic signal read from a card's lowercased effect
# text. The four consumed by the frozen heuristic predicates (DRAW, SEARCH_TO_HAND,
# RECOVERS_FROM_DISCARD, DISCARDS_FROM_DECK, BENCH_BASIC_FROM_DECK,
# RARE_CANDY_EVOLVE, ONCE_PER_TURN) reproduce those predicates exactly; ENERGY_ACCEL
# is knowledge-only (no frozen predicate reads it) and exists so an energy-attach
# trainer such as Waitress resolves to TAGGED instead of an UNTAGGED_EFFECT gap.
DRAW = "DRAW"
SEARCH_TO_HAND = "SEARCH_TO_HAND"
RECOVERS_FROM_DISCARD = "RECOVERS_FROM_DISCARD"
DISCARDS_FROM_DECK = "DISCARDS_FROM_DECK"
BENCH_BASIC_FROM_DECK = "BENCH_BASIC_FROM_DECK"
RARE_CANDY_EVOLVE = "RARE_CANDY_EVOLVE"
ONCE_PER_TURN = "ONCE_PER_TURN"
ENERGY_ACCEL = "ENERGY_ACCEL"

TAG_VOCAB = frozenset({
    DRAW,
    SEARCH_TO_HAND,
    RECOVERS_FROM_DISCARD,
    DISCARDS_FROM_DECK,
    BENCH_BASIC_FROM_DECK,
    RARE_CANDY_EVOLVE,
    ENERGY_ACCEL,
    ONCE_PER_TURN,
})

# Degradation states returned by resolve().
UNKNOWN_CARD = "UNKNOWN_CARD"
UNTAGGED_EFFECT = "UNTAGGED_EFFECT"
EMPTY = "EMPTY"
TAGGED = "TAGGED"

# \bdraw matches "draw"/"draws"/"drawn" but not "withdraw" (a switch effect that
# never drills the deck); reused so the DRAW tag and the legacy inline check agree.
_DRAW_RE = re.compile(r"\bdraw")


def tag_text(text) -> frozenset:
    """Tags for a card's effect text (a string or None), a frozenset over TAG_VOCAB.

    Pure and total: None or empty text yields the empty frozenset (a vanilla card
    carries no effect), and any text that matches no signal also yields empty (an
    UNTAGGED_EFFECT gap the coverage meter surfaces). Never raises. Each clause
    mirrors the exact substring/regex the corresponding legacy heuristic check
    used, so the derived predicates stay byte-for-byte equivalent card-wide.
    """
    if not text:
        return frozenset()
    t = text.lower()
    tags = set()
    if _DRAW_RE.search(t):
        tags.add(DRAW)
    if "into your hand" in t:
        tags.add(SEARCH_TO_HAND)
    # A discard-pile-to-hand recovery (Night Stretcher) that does NOT touch the
    # deck is resource recovery, not a mill; the "your deck" guard keeps a card
    # that also searches/draws the deck out of this tag (so it stays a driller).
    if (
        "from your discard pile" in t
        and "into your hand" in t
        and "your deck" not in t
    ):
        tags.add(RECOVERS_FROM_DISCARD)
    # A discard that names the deck as the source destroys deck cards; a
    # discard-pile recycler ("into your deck") only grows it and is excluded by
    # requiring the deck-source phrasing.
    if "discard" in t and ("of your deck" in t or "your deck for" in t):
        tags.add(DISCARDS_FROM_DECK)
    if (
        "search your deck" in t
        and "onto your bench" in t
        and "basic" in t
        and "pok" in t
    ):
        tags.add(BENCH_BASIC_FROM_DECK)
    if "stage 2" in t and "skipping the stage 1" in t:
        tags.add(RARE_CANDY_EVOLVE)
    if "attach" in t and "energy" in t:
        tags.add(ENERGY_ACCEL)
    if "once during your turn" in t:
        tags.add(ONCE_PER_TURN)
    return frozenset(tags)


def resolve(card_present: bool, text):
    """Classify a card into (state, tags): the three-state degradation model.

    card_present is whether the id resolved to a card in the pool (the caller owns
    that lookup). The states: UNKNOWN_CARD (id not in the pool), EMPTY (in the pool
    with no effect text: a vanilla Pokemon or basic energy), TAGGED (recognized
    effect), UNTAGGED_EFFECT (effect text we do not recognize yet). Only EMPTY and
    TAGGED are "covered"; the coverage meter ratchets UNTAGGED_EFFECT down. Pure,
    never raises.
    """
    if not card_present:
        return (UNKNOWN_CARD, frozenset())
    tags = tag_text(text)
    if tags:
        return (TAGGED, tags)
    if text:
        return (UNTAGGED_EFFECT, frozenset())
    return (EMPTY, frozenset())


def is_covered(state) -> bool:
    """True when a resolve() state means the layer understands the card."""
    return state in (EMPTY, TAGGED)
