"""Card database access, backed by the engine's all_card_data().

Loaded lazily and cached so importing this module does not load the native
library until a card is actually looked up.
"""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _index() -> dict:
    from ptcg_agent.engine import ensure_official_cg

    ensure_official_cg()
    from cg.api import all_card_data

    return {c.cardId: c for c in all_card_data()}


def get_card(card_id: int):
    """Return the CardData for a card id, or None if unknown."""
    return _index().get(card_id)


def all_cards() -> list:
    return list(_index().values())
