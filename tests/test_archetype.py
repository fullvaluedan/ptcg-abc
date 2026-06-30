"""U8: opponent archetype identification and prior weighting.

Covers the unit's test scenarios: revealed cards move the belief toward the
matching archetype; the opponent prior always contains the revealed cards (so a
determinization can never contradict the visible board); an unrecognized opening
falls back to the broad mirror prior; and the determinizer's short zone padding
draws from the prior (archetype consistent) before basic energy.
"""
import random
from collections import Counter
from pathlib import Path

import pytest

from analysis import archetype
from search.determinize import _card_index, _filler_energy_id, _fit

ROOT = Path(__file__).resolve().parents[1]


def _deck():
    ids = [int(x) for x in (ROOT / "decks" / "baseline.csv").read_text().split("\n") if x.strip()]
    return ids[:60]


def _pokemon_ids(n, skip=()):
    """n distinct basic Pokemon card IDs from the database, for signatures."""
    out = []
    for cid, card in _card_index().items():
        if cid in skip:
            continue
        if card.basic and int(card.cardType) == 0:  # CardType.POKEMON
            out.append(cid)
        if len(out) >= n:
            break
    return out


def _decklist(signature_ids):
    """A 60 card list: the signature cards padded out with basic {W} energy (id 3)."""
    return list(signature_ids) + [3] * (60 - len(signature_ids))


def _slot(card_id, energies=()):
    return {"id": card_id, "energyCards": [{"id": e} for e in energies],
            "tools": [], "preEvolution": []}


def _player(deck_count=40, prize_count=6, hand_count=3, active=None, bench=None,
            discard=None):
    return {
        "active": active if active is not None else [],
        "bench": bench or [],
        "deckCount": deck_count,
        "discard": discard or [],
        "prize": [None] * prize_count,
        "handCount": hand_count,
        "hand": None,
    }


def _obs(opp, your_index=0):
    me = _player()
    players = [me, opp] if your_index == 0 else [opp, me]
    return {"current": {"yourIndex": your_index, "players": players}}


@pytest.fixture(autouse=True)
def _clean_registry():
    archetype.clear_archetypes()
    yield
    archetype.clear_archetypes()


# Test scenario: revealed cards move the belief toward the matching archetype.
def test_belief_points_at_matching_archetype():
    pokes = _pokemon_ids(6)
    a_sig, b_sig = pokes[:3], pokes[3:6]
    archetype.register_archetype("alpha", _decklist(a_sig))
    archetype.register_archetype("beta", _decklist(b_sig))

    opp = _player(active=[_slot(a_sig[0])], bench=[_slot(a_sig[1])])
    report = archetype.belief_report(_obs(opp))
    assert report["map"] == "alpha"
    assert report["belief"]["alpha"] > report["belief"].get("beta", 0.0)


# Test scenario: signatures ignore basic energy (it is shared by every deck).
def test_signature_excludes_basic_energy():
    pokes = _pokemon_ids(2)
    sig = archetype.signature_of(_decklist(pokes))
    assert set(pokes) <= sig
    assert 3 not in sig  # basic {W} energy is not a tell


# Test scenario: an unrecognized opening falls back to the broad mirror prior.
def test_unknown_opening_falls_back_to_mirror():
    pokes = _pokemon_ids(3)
    archetype.register_archetype("alpha", _decklist(pokes))
    deck = _deck()

    # Opponent has shown nothing distinctive (empty board and discard).
    opp = _player(active=[], bench=[], discard=[])
    assert archetype.infer_belief(set(archetype.revealed_opponent_ids(_obs(opp)))) == {}
    prior = archetype.opponent_prior(_obs(opp), deck)
    assert len(prior) == 60
    # With no belief the base is the mirror deck, so the prior is our own cards.
    assert Counter(prior) == Counter(deck)


# Test scenario: the prior never contradicts the visible board: every revealed
# opponent card appears in the prior (at least as many copies as we have seen).
def test_prior_contains_revealed_cards():
    pokes = _pokemon_ids(4)
    archetype.register_archetype("alpha", _decklist(pokes[:3]))
    deck = _deck()
    # Reveal a Pokemon that is NOT in our mirror deck nor the alpha decklist's
    # padding, to prove the merge forces it in regardless of the base.
    off_deck = pokes[3]
    opp = _player(active=[_slot(off_deck, energies=[3])], bench=[_slot(pokes[0])])
    prior = archetype.opponent_prior(_obs(opp), deck)
    assert len(prior) == 60
    revealed = Counter(archetype.revealed_opponent_ids(_obs(opp)))
    prior_ct = Counter(prior)
    for cid, c in revealed.items():
        assert prior_ct[cid] >= c


# Test scenario: a determinization built from the archetype prior keeps the
# opponent's hidden zones consistent with that prior, and never contradicts the
# board (revealed board cards are not duplicated into the hidden zones).
def test_determinization_uses_archetype_prior():
    from search.determinize import determinize

    pokes = _pokemon_ids(3)
    archetype.register_archetype("alpha", _decklist(pokes))
    deck = _deck()
    opp = _player(deck_count=45, prize_count=6, hand_count=5,
                  active=[_slot(pokes[0])])
    obs = _obs(opp)
    prior = archetype.opponent_prior(obs, deck)
    det = determinize(obs, deck, random.Random(3), opponent_prior=prior)
    allowed = set(prior) | {_filler_energy_id()}
    hidden = det.opponent_deck + det.opponent_prize + det.opponent_hand
    assert all(cid in allowed for cid in hidden)
    # The revealed active is on the board (engine side), so it is not also dealt
    # into a hidden zone beyond the copies the prior holds for the hand/deck/prize.
    assert hidden.count(pokes[0]) <= Counter(prior)[pokes[0]] - 1


# Test scenario: a heavy reveal does not crowd the archetype's Pokemon out of the
# prior (the merge removes basic energy first, keeping distinctive cards).
def test_heavy_reveal_keeps_base_pokemon():
    pokes = _pokemon_ids(4)
    sig, off_deck = pokes[:3], pokes[3]
    # Base has energy first and its Pokemon last, so a naive prepend-the-reveal
    # merge would truncate the Pokemon away once the reveal is large enough.
    base = [3] * 57 + sig
    archetype.register_archetype("alpha", base)
    deck = _deck()
    # Reveal 58 copies of an off-deck non-energy card in the opponent discard.
    opp = _player(active=[_slot(sig[0])], discard=[{"id": off_deck}] * 58)
    prior = archetype.opponent_prior(_obs(opp), deck)
    assert len(prior) == 60
    prior_ct = Counter(prior)
    assert prior_ct[off_deck] >= 58            # the reveal is honored
    assert any(prior_ct[p] >= 1 for p in sig)  # the archetype Pokemon survive


# Test scenario: short hidden zones pad from the prior pool before basic energy.
def test_fit_pads_from_pool_then_energy():
    rng = random.Random(0)
    pool = [101, 102, 103]
    out = _fit([], 3, rng, pad_pool=pool)
    assert sorted(out) == sorted(pool)
    # With no pool, padding falls back to basic energy.
    out2 = _fit([], 2, random.Random(0))
    assert out2 == [_filler_energy_id(), _filler_energy_id()]
