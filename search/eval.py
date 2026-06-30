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
# Board-strength terms break ties between positions with equal prizes. Each is
# bounded and their sum stays under PRIZE_SHAPING, so prize progress always
# outranks raw board state and a terminal result always outranks any estimate.
HP_SHAPING = 0.15
BOARD_SHAPING = 0.05
# cabt allows one active plus five bench Pokemon per player.
BENCH_MAX = 5


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


def _in_play(player) -> list:
    """Every Pokemon a player currently has on the board: active plus bench."""
    pokes = []
    for zone in ("active", "bench"):
        for p in player.get(zone) or []:
            if p:
                pokes.append(p)
    return pokes


def _hp_fraction(pokes) -> float:
    """Mean current-HP fraction across in-play Pokemon, 0 when none are in play.

    A Pokemon with no maxHp recorded is skipped rather than guessed, so a missing
    field never invents board health.
    """
    fracs = []
    for p in pokes:
        mx = p.get("maxHp") or 0
        if mx > 0:
            fracs.append(max(0.0, min(1.0, p.get("hp", 0) / mx)))
    return sum(fracs) / len(fracs) if fracs else 0.0


def board_value(state, your_index) -> float:
    """Card-data-aware estimate of a non-terminal position, from our point of view.

    Prize differential dominates (it is the win condition). Board health and board
    presence then break ties between positions with equal prizes: a healthier,
    wider board is worth more. Every term is bounded and their sum stays under a
    terminal win or loss, so a real result always outranks any estimate.
    """
    players = state.get("players") or []
    if len(players) < 2:
        return 0.0
    me = players[your_index]
    opp = players[1 - your_index]
    prize = (_prizes_left(opp) - _prizes_left(me)) / PRIZE_TOTAL * PRIZE_SHAPING
    mine = _in_play(me)
    theirs = _in_play(opp)
    hp = (_hp_fraction(mine) - _hp_fraction(theirs)) * HP_SHAPING
    board = (len(mine) - len(theirs)) / (BENCH_MAX + 1) * BOARD_SHAPING
    return prize + hp + board


def shaped_value(state, your_index) -> float:
    """Terminal win/loss/draw if the battle is over, else the board estimate.

    The estimate rises as we take prizes and keep a healthier, wider board than
    the opponent.
    """
    tv = terminal_value(state.get("result", RESULT_ONGOING), your_index)
    if tv is not None:
        return tv
    return board_value(state, your_index)
