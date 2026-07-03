"""Value of a rolled-out state, from our point of view.

The rating is margin independent (KTD5), so the primary signal is win, loss, or
draw. When a rollout does not reach a terminal result within the step budget, a
small prize differential breaks the tie: a state where we are closer to taking
our six prizes than the opponent is to theirs scores slightly higher. Board
health, board presence, and attached energy break any remaining tie. The shaping
is deliberately small so it never outweighs an actual win or loss.

Pure functions over the raw state dict (the shape cg.api returns once converted
with dataclasses.asdict), so this ships unchanged inside a submission.
"""
from __future__ import annotations

import os

try:
    from search import learned_eval
except ImportError:  # inside a submission, support modules sit at the top level
    import learned_eval


def _env_num(name, default, cast):
    """Read a tunable leaf-eval constant from the environment, else the default.

    The CEM optimizer (tools/weight_space.py, offline) searches the leaf shaping
    weights alongside the pilot knobs by baking PTCG_W_* overrides into a build;
    each is read here like the PTCG_BENCH_FLOOR lever below. Unset (every shipped
    build unless a tuned vector is baked) returns the default unchanged, so the
    build stays byte-identical, and a malformed value falls back to the default
    rather than raising. `cast` is int or float; the default mirrors the entry in
    tools/weight_space.PARAM_SPACE (a drift test guards the pairing).
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return cast(raw)
    except (TypeError, ValueError):
        return default


WIN = 1.0
LOSS = -1.0
DRAW = 0.0

# Engine result sentinel: the battle is still ongoing.
RESULT_ONGOING = -1
RESULT_DRAW = 2

PRIZE_TOTAL = 6
# Largest magnitude the prize shaping can reach. Kept well below 1 so a clear
# win always dominates a favorable but unfinished position.
PRIZE_SHAPING = _env_num("PTCG_W_PRIZE_SHAPING", 0.5, float)
# Board-strength terms break ties between positions with equal prizes. Each is
# bounded and their sum stays under PRIZE_SHAPING, so prize progress always
# outranks raw board state and a terminal result always outranks any estimate.
HP_SHAPING = _env_num("PTCG_W_HP_SHAPING", 0.15, float)
# The active Pokemon is on the front line: it is the one being attacked, the one
# that gets knocked out for a prize, and the one that attacks back. Its health
# therefore matters more than a benched Pokemon's, so weight it above the bench
# rather than averaging the whole board flat: a dying active behind a healthy
# bench is in real danger, which a flat mean would hide by letting the bench pull
# the score up. The active carries this fraction of the health term; the bench
# shares the rest.
ACTIVE_HP_WEIGHT = _env_num("PTCG_W_ACTIVE_HP_WEIGHT", 0.6, float)
BOARD_SHAPING = _env_num("PTCG_W_BOARD_SHAPING", 0.05, float)
# Attached energy is the fuel for attacks: a board with more energy in play is
# closer to executing its game plan and taking prizes, so it breaks ties between
# positions that are otherwise equal on prizes, health, and width. Kept small so
# the sum of the board terms (0.15 + 0.05 + 0.05 = 0.25) stays well under
# PRIZE_SHAPING and a terminal result always outranks any estimate.
ENERGY_SHAPING = _env_num("PTCG_W_ENERGY_SHAPING", 0.05, float)
# The attached-energy differential is normalized by the energy a well-developed
# full board carries and clamped to it, so a single over-loaded Pokemon saturates
# the term rather than letting it grow without bound.
ENERGY_NORM = 12
# cabt allows one active plus five bench Pokemon per player.
BENCH_MAX = 5

# Empty-bench floor (PTCG_BENCH_FLOOR, default off). The linear board-presence
# term above values width as a flat differential: it treats losing one benched
# Pokemon the same whether we drop from five to four or from one to zero. But
# self-collapse (our active is knocked out with no Basic to promote) is the
# dominant loss mode, and it is a CLIFF, not a linear cost: the FIRST benched
# Pokemon is the one that keeps us alive through a knockout, so its marginal
# value dwarfs the fifth's. This term adds a convex bench cushion whose gain is
# largest going from zero to one and saturates by BENCH_TARGET, so the search
# steers away from trading into a knockout that empties our own bench. It is a
# differential of our cushion against the opponent's, so it stays antisymmetric
# and equal boards net to zero. Kept bounded so the four board terms
# (0.15 + 0.05 + 0.05 + 0.08 = 0.33) still sum below PRIZE_SHAPING and a terminal
# result always outranks any estimate.
BENCH_FLOOR_SHAPING = _env_num("PTCG_W_BENCH_FLOOR_SHAPING", 0.08, float)
# A bench of this width is a "reasonably full" cushion: beyond it the marginal
# survival value of another Basic is negligible, so the cushion saturates here
# rather than rewarding a maxed bench over an adequate one.
BENCH_TARGET = _env_num("PTCG_W_BENCH_TARGET", 3, int)
_BENCH_FLOOR = os.environ.get("PTCG_BENCH_FLOOR", "0") != "0"
# Route non-terminal scoring through the learned evaluator (plan U4/U5) instead
# of the hand-tuned shaping below. Off by default: keep as an A/B lever until
# a gauntlet run shows it beats the hand-tuned eval by a clear margin.
_LEARNED_EVAL = os.environ.get("PTCG_LEARNED_EVAL", "0") != "0"


def _parse_blend(raw, fallback):
    """Parse PTCG_EVAL_BLEND's raw string to a weight in [0, 1], clamped.

    None (unset) or a malformed value returns fallback unchanged, mirroring
    _env_num's fallback-on-malformed-input contract, so a bad env value never
    crashes eval scoring or silently picks an unintended blend.
    """
    if raw is None:
        return fallback
    try:
        return max(0.0, min(1.0, float(raw)))
    except (TypeError, ValueError):
        return fallback


# Weighted blend between the hand-tuned board_value and the learned evaluator
# (plan U11), generalizing the on/off PTCG_LEARNED_EVAL switch into a sweepable
# weight: 0.0 is hand-tuned only, 1.0 is learned only. None (the default, when
# PTCG_EVAL_BLEND is unset or malformed) means "defer to PTCG_LEARNED_EVAL",
# read fresh each call in _effective_blend so existing PTCG_LEARNED_EVAL
# behavior and tests are unchanged when no explicit blend weight is set. Set
# PTCG_EVAL_BLEND to sweep an in-between weight (tools/eval_blend_sweep.py,
# analysis/eval_blend_sweep.md).
_EVAL_BLEND = _parse_blend(os.environ.get("PTCG_EVAL_BLEND"), None)


def _effective_blend() -> float:
    if _EVAL_BLEND is not None:
        return _EVAL_BLEND
    return 1.0 if _LEARNED_EVAL else 0.0


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


def _slot_hp_fraction(slot):
    """Current-HP fraction of one Pokemon in [0, 1], or None when maxHp is missing.

    A slot with no maxHp recorded is skipped rather than guessed, so a missing
    field never invents board health.
    """
    mx = slot.get("maxHp") or 0
    if mx <= 0:
        return None
    return max(0.0, min(1.0, slot.get("hp", 0) / mx))


def _mean_hp_fraction(slots):
    """Mean HP fraction across slots, or None when none report a maxHp."""
    fracs = [f for f in (_slot_hp_fraction(s) for s in slots) if f is not None]
    return sum(fracs) / len(fracs) if fracs else None


def _hp_fraction(player) -> float:
    """Board-health score in [0, 1], weighting the active above the bench.

    The active Pokemon's health is worth ACTIVE_HP_WEIGHT of the term and the
    bench shares the rest, because the active is the one being attacked and taking
    prizes: a board with a dying active but a healthy bench is in real danger,
    which a flat mean over every Pokemon would hide. Falls back to whichever part
    is present, so a knocked-out active awaiting a promote or an empty bench never
    invents or drops health. Returns 0 when neither part reports a maxHp.
    """
    active = player.get("active") or []
    active_frac = _slot_hp_fraction(active[0]) if active and active[0] else None
    bench_frac = _mean_hp_fraction([p for p in (player.get("bench") or []) if p])
    if active_frac is None and bench_frac is None:
        return 0.0
    if active_frac is None:
        return bench_frac
    if bench_frac is None:
        return active_frac
    return ACTIVE_HP_WEIGHT * active_frac + (1 - ACTIVE_HP_WEIGHT) * bench_frac


def _attached_energy(pokes) -> int:
    """Total energy cards attached across a list of in-play Pokemon.

    Read directly from each slot's energyCards, so the value function stays pure
    over the state dict with no card-data lookup and ships unchanged inside a
    submission. A slot with no energyCards field contributes nothing rather than
    guessing.
    """
    return sum(len(p.get("energyCards") or []) for p in pokes)


def _bench_count(player) -> int:
    """Number of Pokemon on a player's bench (the active is not counted).

    The bench is the promote pool: an empty bench means one knockout ends the
    game, so this count, not the whole board width, is what the floor term reads.
    """
    return sum(1 for p in (player.get("bench") or []) if p)


def _bench_cushion(count) -> float:
    """Convex survival cushion of a bench of `count` Pokemon, in [0, 1].

    Concave and saturating: sqrt gives the first benched Pokemon the largest
    marginal value (0 -> 1 is the jump off the self-collapse cliff) and flattens
    by BENCH_TARGET, past which another Basic barely changes our survival odds.
    """
    capped = min(count, BENCH_TARGET)
    return (capped / BENCH_TARGET) ** 0.5


def _bench_floor_term(me, opp) -> float:
    """Differential convex bench-cushion term, our board against the opponent's.

    A differential (not a one-sided penalty) so equal boards net to zero and the
    whole estimate stays antisymmetric, while convexity still makes emptying our
    own bench cost more than any single step higher up.
    """
    cushion = _bench_cushion(_bench_count(me)) - _bench_cushion(_bench_count(opp))
    return cushion * BENCH_FLOOR_SHAPING


def board_value(state, your_index) -> float:
    """Card-data-aware estimate of a non-terminal position, from our point of view.

    Prize differential dominates (it is the win condition). Board health, board
    presence, and attached energy then break ties between positions with equal
    prizes: a healthier, wider, better-powered board is worth more. Every term is
    bounded and their sum stays under a terminal win or loss, so a real result
    always outranks any estimate.
    """
    players = state.get("players") or []
    if len(players) < 2:
        return 0.0
    me = players[your_index]
    opp = players[1 - your_index]
    prize = (_prizes_left(opp) - _prizes_left(me)) / PRIZE_TOTAL * PRIZE_SHAPING
    mine = _in_play(me)
    theirs = _in_play(opp)
    hp = (_hp_fraction(me) - _hp_fraction(opp)) * HP_SHAPING
    board = (len(mine) - len(theirs)) / (BENCH_MAX + 1) * BOARD_SHAPING
    energy_raw = (_attached_energy(mine) - _attached_energy(theirs)) / ENERGY_NORM
    energy = max(-1.0, min(1.0, energy_raw)) * ENERGY_SHAPING
    bench_floor = _bench_floor_term(me, opp) if _BENCH_FLOOR else 0.0
    return prize + hp + board + energy + bench_floor


def shaped_value(state, your_index) -> float:
    """Terminal win/loss/draw if the battle is over, else a blended board estimate.

    The blend weight (_effective_blend) picks between the hand-tuned board_value
    and the learned evaluator: 0.0 is hand-tuned only, 1.0 is learned only, and
    anything in between is a weighted average of both (plan U11). The estimate
    rises as we take prizes and keep a healthier, wider board than the opponent.
    """
    tv = terminal_value(state.get("result", RESULT_ONGOING), your_index)
    if tv is not None:
        return tv
    blend = _effective_blend()
    if blend <= 0.0:
        return board_value(state, your_index)
    if blend >= 1.0:
        return learned_eval.predict_value(state, your_index)
    board = board_value(state, your_index)
    learned = learned_eval.predict_value(state, your_index)
    return blend * learned + (1.0 - blend) * board
