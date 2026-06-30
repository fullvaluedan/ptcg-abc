"""Endgame solver: search harder when the state space is small (U9).

Late in a match, when prizes are low and our remaining resources (hand plus deck)
are few, the hidden information is small and each decision is pivotal: one misplay
loses or wins outright. The endgame solver detects this regime from the
observation and tells the search agent to enumerate the option tree more
exhaustively, spending a larger slice of the thinking bank (a higher per-move soft
cap) and more determinizations on the decision.

It never overrides the hard time guard. The boosted soft cap still passes through
TimeBudget.allot, which bounds any single decision to a fraction of the remaining
bank, so an endgame decision can never approach a timeout. Pure over the raw
observation dict, no cg import, so it ships next to main.py.
"""
from __future__ import annotations

# Endgame triggers only when prizes are low for at least one player AND our own
# hand plus deck is small, so the regime is genuinely a near-decided position and
# not merely an aggressive board with a full deck still behind it.
PRIZE_THRESHOLD = 2
RESOURCE_THRESHOLD = 12

# Boosted thinking for a pivotal endgame decision. The soft cap is the per-move
# time ceiling handed to TimeBudget.allot (still bounded by the remaining-bank
# reserve fraction), and the determinization multiplier widens the search when a
# hard determinization cap is set; both are inert in non-endgame play.
ENDGAME_SOFT_CAP = 4.0
ENDGAME_DET_MULTIPLIER = 4


def _prizes_left(player):
    prize = player.get("prize")
    return len(prize) if isinstance(prize, list) else None


def is_endgame(obs, prize_threshold=PRIZE_THRESHOLD,
               resource_threshold=RESOURCE_THRESHOLD) -> bool:
    """True when the position is small and near-decided, worth deeper search.

    Fires when at least one player is at or below prize_threshold prizes left and
    our own hand plus deck is at or below resource_threshold cards. Returns False
    (the safe default) whenever the observation lacks the fields to judge, so a
    malformed state never forces an expensive boosted search.
    """
    try:
        state = obs.get("current") or {}
        yi = state.get("yourIndex", 0)
        players = state.get("players") or []
        if yi not in (0, 1) or len(players) < 2 or len(players) <= yi:
            return False
        me = players[yi]
        opp = players[1 - yi]
        prizes = [p for p in (_prizes_left(me), _prizes_left(opp)) if p is not None]
        if not prizes or min(prizes) > prize_threshold:
            return False
        deck_n = me.get("deckCount")
        if deck_n is None:
            return False
        hand_n = len(me.get("hand") or [])
        return (deck_n + hand_n) <= resource_threshold
    except Exception:
        return False


def endgame_soft_cap(base_soft_cap, soft_cap=ENDGAME_SOFT_CAP) -> float:
    """Per-move soft cap for an endgame decision; never below normal play."""
    return max(base_soft_cap, soft_cap)


def endgame_dets(max_dets, multiplier=ENDGAME_DET_MULTIPLIER):
    """Widen a hard determinization cap for the endgame; None stays time-bounded."""
    if max_dets is None:
        return None
    return max_dets * multiplier
