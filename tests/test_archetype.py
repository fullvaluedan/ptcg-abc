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
def _clean_registry(monkeypatch):
    # Isolate the belief-mechanism tests from the shipped builtin field decks: with
    # PTCG_FIELD_PRIOR=0 the registry holds only what a test registers, so a shipped
    # archetype whose Pokemon happen to overlap a test signature cannot skew belief.
    monkeypatch.setenv("PTCG_FIELD_PRIOR", "0")
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


# --- Builtin field prior (the shipped registry models the real ladder field) ---


# Test scenario: the shipped builtin field decks are active by default, so a card
# distinctive to a meta archetype (here Archaludon ex, id 169) moves the belief to
# that archetype and makes its decklist the prior, with no manual registration.
def test_builtin_field_prior_recognizes_meta_deck(monkeypatch):
    monkeypatch.delenv("PTCG_FIELD_PRIOR", raising=False)  # default on
    deck = _deck()
    opp = _player(active=[_slot(169)])  # Archaludon ex, unique to the metal deck
    report = archetype.belief_report(_obs(opp), deck)
    assert report["map"] == "meta_archaludon"
    prior = archetype.opponent_prior(_obs(opp), deck)
    assert len(prior) == 60
    # The prior is now the field deck, not our mirror deck.
    assert Counter(prior) == Counter(archetype._BUILTIN_DECKLISTS["meta_archaludon"])
    assert Counter(prior) != Counter(deck)


# Test scenario: PTCG_FIELD_PRIOR=0 disables the builtin field decks, so the same
# reveal produces no belief and the prior falls back to the mirror deck. This is
# the A/B control the gauntlet uses to isolate the field prior's ladder effect.
def test_field_prior_disabled_falls_back_to_mirror(monkeypatch):
    monkeypatch.setenv("PTCG_FIELD_PRIOR", "0")
    deck = _deck()
    opp = _player(active=[_slot(169)])
    assert archetype.belief_report(_obs(opp), deck)["map"] is None
    prior = archetype.opponent_prior(_obs(opp), deck)
    # Base is the mirror deck (the reveal 169 is merged in over one basic energy),
    # NOT the Archaludon field deck: disabling the field prior removes it as a base.
    assert Counter(prior) != Counter(archetype._BUILTIN_DECKLISTS["meta_archaludon"])
    assert Counter(deck)[169] == 0 and Counter(prior)[169] == 1  # reveal forced in
    # Every non-revealed card still comes from the mirror deck.
    assert sum((Counter(prior) - Counter({169: 1})).values()) == 59


# Test scenario: the two Grimmsnarl variants stay distinct. A tell unique to the
# tonakaiiii list (Snorunt, id 860) picks it over the kazuki list even though a
# shared Grimmsnarl card (id 646) matches both, because tonakaiiii explains more.
def test_field_prior_distinguishes_grimmsnarl_variants(monkeypatch):
    monkeypatch.delenv("PTCG_FIELD_PRIOR", raising=False)
    deck = _deck()
    opp = _player(active=[_slot(646)], bench=[_slot(860)])
    report = archetype.belief_report(_obs(opp), deck)
    assert report["map"] == "meta_grimmsnarl_tonakaiiii"
    assert (report["belief"]["meta_grimmsnarl_tonakaiiii"]
            > report["belief"].get("meta_grimmsnarl", 0.0))


# Test scenario: signatures drop basic energy, so a bare basic-energy reveal is not
# a tell for any field deck (every deck runs energy) and produces no belief.
def test_field_prior_ignores_basic_energy_reveal(monkeypatch):
    monkeypatch.delenv("PTCG_FIELD_PRIOR", raising=False)
    deck = _deck()
    opp = _player(active=[_slot(8, energies=[8])])  # id 8 is a basic energy
    assert archetype.belief_report(_obs(opp), deck)["map"] is None


# --- No-reveal default: the field prior models the modal opponent, not the mirror ---


# Test scenario: with the field prior on and nothing revealed (every opening turn),
# the prior is the modal field archetype (Archaludon, the widest-adoption pillar),
# NOT a mirror of our own deck, so early rollouts face a realistic ladder opponent.
def test_no_reveal_defaults_to_modal_field_deck(monkeypatch):
    monkeypatch.delenv("PTCG_FIELD_PRIOR", raising=False)  # default on
    deck = _deck()
    opp = _player(active=[], bench=[], discard=[])  # nothing revealed
    assert archetype.belief_report(_obs(opp), deck)["map"] is None  # no belief
    prior = archetype.opponent_prior(_obs(opp), deck)
    assert len(prior) == 60
    assert Counter(prior) == Counter(archetype._BUILTIN_DECKLISTS["meta_archaludon"])
    assert Counter(prior) != Counter(deck)  # not the mirror


# Test scenario: PTCG_FIELD_PRIOR=0 removes the field default too, so a no-reveal
# prior falls back to the mirror deck exactly as before (the one-flag A/B control).
def test_no_reveal_field_prior_off_is_mirror(monkeypatch):
    monkeypatch.setenv("PTCG_FIELD_PRIOR", "0")
    deck = _deck()
    opp = _player(active=[], bench=[], discard=[])
    prior = archetype.opponent_prior(_obs(opp), deck)
    assert Counter(prior) == Counter(deck)


# Test scenario: a non-distinctive reveal (basic energy only) yields no belief, but
# the base is still the modal field deck with the reveal merged, so the prior carries
# the field's distinctive cards (Archaludon ex, id 169) our own deck never holds.
def test_no_belief_reveal_uses_field_default_base(monkeypatch):
    monkeypatch.delenv("PTCG_FIELD_PRIOR", raising=False)  # default on
    deck = _deck()
    opp = _player(active=[_slot(8, energies=[8])])  # basic energy, not a tell
    assert archetype.belief_report(_obs(opp), deck)["map"] is None
    prior = archetype.opponent_prior(_obs(opp), deck)
    assert len(prior) == 60
    field = archetype._BUILTIN_DECKLISTS["meta_archaludon"]
    assert Counter(prior)[169] == Counter(field)[169] > 0  # field's payoff Pokemon
    assert Counter(deck)[169] == 0  # which the mirror deck does not contain


# Test scenario: the explicit-archetypes path (tests and dev) never injects the
# builtin field default, so with no matching reveal the base stays the caller's
# mirror deck even while the field prior is on for production callers.
def test_explicit_archetypes_no_reveal_keeps_mirror(monkeypatch):
    monkeypatch.delenv("PTCG_FIELD_PRIOR", raising=False)  # on for production path
    deck = _deck()
    opp = _player(active=[], bench=[], discard=[])
    prior = archetype.opponent_prior(_obs(opp), deck, archetypes=[])
    assert Counter(prior) == Counter(deck)
