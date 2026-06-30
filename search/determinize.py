"""Sample a hidden game state consistent with what the agent can observe.

The engine's forward model (cg.api.search_begin) needs the cards in every hidden
zone supplied as card IDs: our own deck and prize (face-down to us), and the
opponent's deck, prize, hand, and face-down active. It validates that each list
has at least as many cards as the observed count, that every ID is a real card,
and that a predicted face-down active is a Pokemon. This module produces those
lists so that validation always passes.

What we know exactly versus sample:
- Our own side is fully determined. We submitted the 60 card deck, so the cards
  hidden from us (deck plus prize) are our decklist minus everything currently
  visible in our hand, discard, and board. We only sample the split between deck
  and prize, which does not matter for the engine and barely for value.
- The opponent side is genuinely hidden. We start from a prior decklist (the
  mirror assumption by default; U8 will sharpen this with archetype priors),
  subtract the opponent cards we have already seen, and deal the remainder into
  their deck, prize, and hand to match the observed counts.

Pure functions over the raw observation dict, no ptcg_agent import, so this ships
unchanged inside a submission next to main.py.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# CardType values (api.py CardType enum) used to pick safe fillers and a legal
# face-down active prediction.
CARD_TYPE_POKEMON = 0
CARD_TYPE_BASIC_ENERGY = 5


def _ensure_cg_on_path() -> None:
    try:
        import cg.api  # noqa: F401

        return
    except ImportError:
        pass
    here = Path(__file__).resolve()
    for parent in here.parents:
        for sub in ("data", "vendor"):
            if (parent / sub / "cg" / "api.py").exists():
                p = str(parent / sub)
                if p not in sys.path:
                    sys.path.insert(0, p)
                return


@lru_cache(maxsize=1)
def _card_index() -> dict:
    _ensure_cg_on_path()
    from cg.api import all_card_data

    return {c.cardId: c for c in all_card_data()}


@lru_cache(maxsize=1)
def _filler_energy_id() -> int:
    """A guaranteed-legal basic energy ID, used to pad a short hidden zone."""
    for cid, card in _card_index().items():
        if int(card.cardType) == CARD_TYPE_BASIC_ENERGY:
            return cid
    # Basic {W} Energy is ID 3 in the shipped database; a final safety net.
    return 3


@lru_cache(maxsize=1)
def _any_basic_pokemon_id() -> int:
    for cid, card in _card_index().items():
        if card.basic and int(card.cardType) == CARD_TYPE_POKEMON:
            return cid
    raise RuntimeError("No basic Pokemon found in the card database.")


@dataclass
class Determinization:
    """Predicted hidden-zone card IDs, as cg.api.search_begin expects them."""

    your_deck: list
    your_prize: list
    opponent_deck: list
    opponent_prize: list
    opponent_hand: list
    opponent_active: list

    def as_search_begin_kwargs(self) -> dict:
        return {
            "your_deck": self.your_deck,
            "your_prize": self.your_prize,
            "opponent_deck": self.opponent_deck,
            "opponent_prize": self.opponent_prize,
            "opponent_hand": self.opponent_hand,
            "opponent_active": self.opponent_active,
        }


def _slot_card_ids(slot) -> list:
    """Every card ID physically present on one in-play Pokemon."""
    ids = [slot["id"]]
    for energy in slot.get("energyCards") or []:
        ids.append(energy["id"])
    for tool in slot.get("tools") or []:
        ids.append(tool["id"])
    for pre in slot.get("preEvolution") or []:
        ids.append(pre["id"])
    return ids


def _board_card_ids(player) -> list:
    ids = []
    for slot in (player.get("active") or []) + (player.get("bench") or []):
        if slot is not None:
            ids.extend(_slot_card_ids(slot))
    return ids


def _own_visible_ids(player) -> list:
    """Our cards the engine has already revealed to us: hand, discard, board.

    Deck and prize are excluded on purpose: those are exactly the zones we are
    about to predict. Stadium is excluded because either player may own it.
    """
    ids = list(_board_card_ids(player))
    for card in player.get("discard") or []:
        ids.append(card["id"])
    for card in player.get("hand") or []:
        ids.append(card["id"])
    return ids


def _opponent_visible_ids(player) -> list:
    """Opponent cards we have seen in their visible zones (board, discard).

    Their hand is None, and prize and face-down cards are hidden, so those never
    appear here. These are subtracted from the prior so we never predict more
    copies of a card than the prior decklist actually contains.
    """
    ids = list(_board_card_ids(player))
    for card in player.get("discard") or []:
        ids.append(card["id"])
    return ids


def _multiset_remove(pool, to_remove) -> list:
    """Return pool with each element of to_remove deleted at most once."""
    remaining = list(pool)
    for cid in to_remove:
        try:
            remaining.remove(cid)
        except ValueError:
            # The card is not in the prior (opponent ran something off-prior).
            # Leaving the pool unchanged keeps counts sane; the fit step trims.
            pass
    return remaining


def _fit(cards, n, rng) -> list:
    """Shuffle cards and force the list to exactly n entries.

    Pads a short list with basic energy (always a legal card ID) and trims a long
    one. The engine validates count and legality, not provenance, so this keeps
    search_begin happy even when the prior and the truth disagree.
    """
    out = list(cards)
    rng.shuffle(out)
    if len(out) > n:
        return out[:n]
    if len(out) < n:
        out.extend([_filler_energy_id()] * (n - len(out)))
    return out


def determinize(obs, your_full_deck, rng, opponent_prior=None) -> Determinization:
    """Sample a hidden state consistent with the observation.

    Args:
        obs: the raw observation dict passed to the agent.
        your_full_deck: the 60 card IDs we submitted as our deck.
        rng: a random.Random for reproducible sampling.
        opponent_prior: a 60 card decklist to model the opponent. Defaults to the
            mirror assumption (our own deck).

    Returns a Determinization whose lists match the observed zone counts.
    """
    state = obs["current"]
    yi = state["yourIndex"]
    me = state["players"][yi]
    opp = state["players"][1 - yi]

    # Our side: decklist minus everything we can already see, split deck/prize.
    own_hidden = _multiset_remove(your_full_deck, _own_visible_ids(me))
    deck_n = me["deckCount"]
    prize_n = len(me["prize"])
    own_hidden = _fit(own_hidden, deck_n + prize_n, rng)
    your_deck = own_hidden[:deck_n]
    your_prize = own_hidden[deck_n:deck_n + prize_n]

    # Opponent side: prior minus what they have shown, dealt into the hidden zones.
    prior = list(opponent_prior) if opponent_prior is not None else list(your_full_deck)
    opp_hidden = _multiset_remove(prior, _opponent_visible_ids(opp))
    opp_deck_n = opp["deckCount"]
    opp_prize_n = len(opp["prize"])
    opp_hand_n = opp["handCount"]
    opp_hidden = _fit(opp_hidden, opp_deck_n + opp_prize_n + opp_hand_n, rng)
    opponent_deck = opp_hidden[:opp_deck_n]
    opponent_prize = opp_hidden[opp_deck_n:opp_deck_n + opp_prize_n]
    opponent_hand = opp_hidden[opp_deck_n + opp_prize_n:opp_deck_n + opp_prize_n + opp_hand_n]

    # Face-down opponent active must be predicted as a basic Pokemon ID.
    opp_active = opp.get("active") or []
    if opp_active and opp_active[0] is None:
        cards = _card_index()
        basic = next(
            (cid for cid in prior
             if (c := cards.get(cid)) is not None
             and c.basic
             and int(c.cardType) == CARD_TYPE_POKEMON),
            _any_basic_pokemon_id(),
        )
        opponent_active = [basic]
    else:
        opponent_active = []

    return Determinization(
        your_deck=your_deck,
        your_prize=your_prize,
        opponent_deck=opponent_deck,
        opponent_prize=opponent_prize,
        opponent_hand=opponent_hand,
        opponent_active=opponent_active,
    )
