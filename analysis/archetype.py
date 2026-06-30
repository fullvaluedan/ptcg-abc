"""Infer the opponent's deck archetype from revealed cards and bias the
determinization prior toward a consistent decklist (U8).

Two layers sit here:

1. A registry of known archetypes. Each archetype is a name plus a representative
   60 card decklist; its signature is the set of distinctive (non basic energy)
   card IDs in that list. The registry is empty by default and is filled at
   development time from the decks directory, or later from scouted opponent
   decklists. Basic energy is shared by every deck, so it is never a tell and is
   excluded from signatures.

2. Belief inference. The cards the opponent has revealed (everything visible in
   their board and discard) are scored against each archetype signature and
   normalized into a belief. The most likely archetype's decklist becomes the
   determinization prior. When nothing matches (or the registry is empty) the
   belief is empty and we fall back to a broad prior: the mirror decklist with
   the revealed opponent cards merged in, so the prior is always consistent with
   what we have actually seen on the board.

The submitted agent calls opponent_prior() each decision and hands the result to
the determinizer. This module is self contained over cg.api (it reuses the
determinizer's card index, which locates cg lazily), so it ships next to main.py
inside a submission. With no archetypes registered the practical effect is the
mirror prior guaranteed to contain the revealed cards; the archetype layer
activates once scouted decklists are registered.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

try:  # package layout in the repo
    from search.determinize import (
        CARD_TYPE_BASIC_ENERGY,
        _card_index,
        _filler_energy_id,
        _opponent_visible_ids,
    )
except ImportError:  # flat layout inside a built submission
    from determinize import (  # type: ignore
        CARD_TYPE_BASIC_ENERGY,
        _card_index,
        _filler_energy_id,
        _opponent_visible_ids,
    )

DECK_SIZE = 60


def _is_basic_energy(card_id: int) -> bool:
    card = _card_index().get(card_id)
    return card is not None and int(card.cardType) == CARD_TYPE_BASIC_ENERGY


def signature_of(decklist) -> frozenset:
    """The distinctive card IDs of a decklist: everything but basic energy."""
    return frozenset(cid for cid in set(decklist) if not _is_basic_energy(cid))


@dataclass(frozen=True)
class Archetype:
    name: str
    decklist: tuple
    signature: frozenset


# Built in archetypes ship with the submission. Empty until scouted decklists are
# embedded here (a U6 follow up); register_archetype/load_decks_dir feed the
# registry at development and test time without touching this list.
_BUILTIN_ARCHETYPES: list = []
_REGISTERED: list = []


def _archetypes(explicit=None) -> list:
    if explicit is not None:
        return list(explicit)
    return list(_BUILTIN_ARCHETYPES) + list(_REGISTERED)


def register_archetype(name: str, decklist) -> Archetype:
    """Add an archetype (name plus 60 card decklist) to the registry.

    Re-registering a name replaces the prior entry, so a name maps to exactly one
    decklist; otherwise infer_belief would sum two signatures under one name while
    map_archetype could only return one of the decklists.
    """
    deck = tuple(decklist)
    arch = Archetype(name=name, decklist=deck, signature=signature_of(deck))
    _REGISTERED[:] = [a for a in _REGISTERED if a.name != name]
    _REGISTERED.append(arch)
    return arch


def clear_archetypes() -> None:
    """Drop every registered archetype (test and dev hygiene)."""
    _REGISTERED.clear()


def load_decks_dir(path) -> list:
    """Register one archetype per .csv decklist in a directory (dev time only)."""
    from pathlib import Path

    out = []
    for csv in sorted(Path(path).glob("*.csv")):
        ids = [int(line) for line in csv.read_text().split("\n") if line.strip()]
        if len(ids) >= DECK_SIZE:
            out.append(register_archetype(csv.stem, ids[:DECK_SIZE]))
    return out


def revealed_opponent_ids(obs) -> list:
    """Every opponent card we have seen face up: their board and discard.

    These are the cards we know the opponent's 60 contains. Their hand is hidden,
    and prize and face down cards are None, so none of those leak in here.
    """
    state = obs["current"]
    yi = state["yourIndex"]
    opp = state["players"][1 - yi]
    return list(_opponent_visible_ids(opp))


def infer_belief(revealed_ids, archetypes=None) -> dict:
    """Score revealed cards against each archetype signature, normalized.

    Returns a name to weight mapping that sums to one, or an empty dict when no
    archetype shares a distinctive card with the reveal (no information: the
    caller falls back to a broad prior). Weight is the count of distinct revealed
    signature cards an archetype matches, so a deck that explains more of what we
    have seen earns more belief.
    """
    revealed = set(revealed_ids)
    scores = {}
    for arch in _archetypes(archetypes):
        overlap = len(revealed & arch.signature)
        if overlap:
            scores[arch.name] = scores.get(arch.name, 0) + overlap
    total = sum(scores.values())
    if not total:
        return {}
    return {name: score / total for name, score in scores.items()}


def map_archetype(belief: dict, archetypes=None):
    """The most likely archetype given a belief, or None when the belief is empty.

    Ties break on name so selection is deterministic under a fixed registry.
    """
    if not belief:
        return None
    best = max(belief.items(), key=lambda kv: (kv[1], kv[0]))[0]
    for arch in _archetypes(archetypes):
        if arch.name == best:
            return arch
    return None


def _merge_revealed(base, revealed) -> list:
    """A 60 card prior that keeps the base decklist but guarantees the reveals.

    Start from the base (the archetype or mirror decklist), add only the deficit
    where the opponent has shown more copies of a card than the base holds, then
    remove an equal number of other cards so the total stays at 60. Removals are
    drawn basic energy first and never below a card's revealed count, so the
    archetype's distinctive cards (its Pokemon and trainers) survive even a heavy
    reveal. Prepending the whole reveal instead would crowd those cards out and
    leave the determinized opponent deck full of already played energy. Since the
    revealed total can never exceed 60, the deficit can always be absorbed.
    """
    base_ct = Counter(base)
    rev_ct = Counter(revealed)
    final = Counter(base_ct)
    deficit = 0
    for cid, c in rev_ct.items():
        short = c - base_ct.get(cid, 0)
        if short > 0:
            final[cid] += short
            deficit += short
    if deficit:
        spare = []
        for cid, c in final.items():
            extra = c - rev_ct.get(cid, 0)
            if extra > 0:
                spare.extend([cid] * extra)
        spare.sort(key=lambda cid: (not _is_basic_energy(cid), cid))
        for cid in spare[:deficit]:
            final[cid] -= 1
    out = list(final.elements())
    while len(out) < DECK_SIZE:  # defensive: base shorter than 60
        out.append(_filler_energy_id())
    return out[:DECK_SIZE]


def opponent_prior(obs, your_deck, archetypes=None) -> list:
    """A 60 card prior decklist for the opponent, biased by revealed cards.

    Picks the most likely archetype's decklist as the base when belief is non
    empty, else mirrors our own deck, then merges in every revealed opponent card
    so the prior stays consistent with the visible board. Pass the result to the
    determinizer as opponent_prior.
    """
    revealed = revealed_opponent_ids(obs)
    belief = infer_belief(revealed, archetypes)
    arch = map_archetype(belief, archetypes)
    base = list(arch.decklist) if arch is not None else list(your_deck)
    return _merge_revealed(base, revealed)


def belief_report(obs, your_deck=None, archetypes=None) -> dict:
    """A debug digest of the archetype belief for scouting and tests."""
    revealed = revealed_opponent_ids(obs)
    belief = infer_belief(revealed, archetypes)
    arch = map_archetype(belief, archetypes)
    return {
        "revealed": revealed,
        "belief": belief,
        "map": arch.name if arch is not None else None,
    }
