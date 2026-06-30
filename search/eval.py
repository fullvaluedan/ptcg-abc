"""Value of a rolled-out state, from our point of view.

The rating is margin independent (KTD5), so the primary signal is win, loss, or
draw. When a rollout does not reach a terminal result within the step budget, a
small prize differential breaks the tie: a state where we are closer to taking
our six prizes than the opponent is to theirs scores slightly higher. The shaping
is deliberately small so it never outweighs an actual win or loss.

Pure functions over the raw state dict (the shape cg.api returns once converted
with dataclasses.asdict), so this ships unchanged inside a submission.
"""
from __future__ import annotations

WIN = 1.0
LOSS = -1.0
DRAW = 0.0

# Engine result sentinel: the battle is still ongoing.
RESULT_ONGOING = -1
RESULT_DRAW = 2

PRIZE_TOTAL = 6
# Largest magnitude the prize shaping can reach. Kept well below 1 so a clear
# win always dominates a favorable but unfinished position.
PRIZE_SHAPING = 0.5


def terminal_value(result, your_index):
    """Map an engine result to our value, or None if the battle is ongoing.

    result is -1 while ongoing, 0 or 1 for the winning player index, 2 for a draw.
    """
    if result is None or result == RESULT_ONGOING:
        return None
    if result == RESULT_DRAW:
        return DRAW
    return WIN if result == your_index else LOSS


def _prizes_left(player) -> int:
    return len(player.get("prize") or [])


def shaped_value(state, your_index) -> float:
    """Terminal win/loss/draw if the battle is over, else a small prize estimate.

    Fewer of our prizes remaining means we are closer to winning, so the estimate
    rises as our prize count falls and the opponent's stays high.
    """
    tv = terminal_value(state.get("result", RESULT_ONGOING), your_index)
    if tv is not None:
        return tv
    players = state.get("players") or []
    if len(players) < 2:
        return 0.0
    me = players[your_index]
    opp = players[1 - your_index]
    diff = (_prizes_left(opp) - _prizes_left(me)) / PRIZE_TOTAL
    return diff * PRIZE_SHAPING
