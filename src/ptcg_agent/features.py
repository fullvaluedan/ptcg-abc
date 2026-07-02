"""Pure feature extractor for the learned state evaluator (plan U2).

extract_features(state, your_index) turns a raw engine state dict (the
dataclasses.asdict shape cg.api returns, the same shape search/eval.py reads)
into a fixed-order, fixed-length numeric vector from our seat's point of view.
FEATURE_NAMES documents that order for the training CSV header, the exported
model JSON, and the writeup.

Dependency-free by design (stdlib only, no sibling-module imports), unlike
heuristics.py which imports card_effects: there is nothing to import-fallback
here, so this file already satisfies the "ships flat next to main.py" contract
that pattern exists for. tools/gauntlet.py (U1), tools/train_eval.py (U4), and
search/learned_eval.py (U4, at match time) all import this SAME function, so
the feature layout can never drift between training and inference.

Never raises: a missing or malformed field falls back to a neutral default, and
any unexpected failure returns a zero vector of the correct length rather than
propagating, so one odd state can never abort a batch of thousands or crash a
live decision.
"""
from __future__ import annotations

# Fixed feature order. Do not reorder once a model is trained on it; append new
# features at the end instead, and bump a version marker alongside FEATURE_NAMES
# if the layout ever changes (mirrors the discipline in agents/imitation_features.py).
FEATURE_NAMES = (
    "prize_diff",
    "our_prizes_left",
    "their_prizes_left",
    "our_deck_count",
    "their_deck_count",
    "deck_diff",
    "our_hand_count",
    "their_hand_count",
    "our_bench_size",
    "their_bench_size",
    "our_bench_nonempty",
    "our_active_hp_frac",
    "their_active_hp_frac",
    "our_bench_hp_frac",
    "their_bench_hp_frac",
    "our_energy",
    "their_energy",
    "turn_number",
    "is_our_turn",
    "our_supporter_played",
    "our_energy_attached",
)
N_FEATURES = len(FEATURE_NAMES)

PRIZE_TOTAL = 6
# Same normalization constants as search/eval.py, so a raw feature value and the
# hand-tuned shaping it replaces stay on comparable scales.
ENERGY_NORM = 12
TURN_NORM = 40


def _prizes_left(player) -> int:
    return len(player.get("prize") or [])


def _active_slot(player):
    active = player.get("active") or []
    return active[0] if active and active[0] else None


def _bench_slots(player) -> list:
    return [p for p in (player.get("bench") or []) if p]


def _in_play(player) -> list:
    active = _active_slot(player)
    slots = _bench_slots(player)
    return ([active] if active else []) + slots


def _slot_hp_fraction(slot):
    if not slot:
        return None
    mx = slot.get("maxHp") or 0
    if mx <= 0:
        return None
    return max(0.0, min(1.0, slot.get("hp", 0) / mx))


def _mean_hp_fraction(slots):
    fracs = [f for f in (_slot_hp_fraction(s) for s in slots) if f is not None]
    return sum(fracs) / len(fracs) if fracs else None


def _attached_energy(slots) -> int:
    return sum(len(p.get("energyCards") or []) for p in slots)


def _is_our_turn(turn, first_player, your_index) -> bool:
    """Whether `turn` belongs to our seat, derived from turn/firstPlayer parity.

    Per the engine docs, turn 1 is the starting player's first turn, turn 2 the
    second player's first turn, turn 3 the starting player's second turn, and so
    on, so parity plus firstPlayer identifies the owner. Falls back to True (most
    decisions are on-turn) when firstPlayer is not yet decided (-1) or turn is 0,
    rather than guessing an owner from no information.
    """
    if not isinstance(first_player, int) or first_player not in (0, 1) or turn < 1:
        return True
    owner = first_player if (turn - 1) % 2 == 0 else (1 - first_player)
    return owner == your_index


def _zero_vector() -> list:
    return [0.0] * N_FEATURES


def _extract(state, your_index) -> list:
    players = state.get("players") or []
    if not isinstance(your_index, int) or not (0 <= your_index < len(players)) or len(players) < 2:
        return _zero_vector()
    me = players[your_index] or {}
    opp = players[1 - your_index] or {}

    our_prizes = _prizes_left(me)
    their_prizes = _prizes_left(opp)
    our_deck = int(me.get("deckCount") or 0)
    their_deck = int(opp.get("deckCount") or 0)
    our_hand = int(me.get("handCount") or 0)
    their_hand = int(opp.get("handCount") or 0)
    our_bench = _bench_slots(me)
    their_bench = _bench_slots(opp)
    our_active = _active_slot(me)
    their_active = _active_slot(opp)

    turn = min(max(int(state.get("turn") or 0), 0), TURN_NORM)
    is_our_turn = _is_our_turn(turn, state.get("firstPlayer"), your_index)

    our_energy = min(_attached_energy(_in_play(me)), ENERGY_NORM)
    their_energy = min(_attached_energy(_in_play(opp)), ENERGY_NORM)

    return [
        (their_prizes - our_prizes) / PRIZE_TOTAL,
        float(our_prizes),
        float(their_prizes),
        float(our_deck),
        float(their_deck),
        float(our_deck - their_deck),
        float(our_hand),
        float(their_hand),
        float(len(our_bench)),
        float(len(their_bench)),
        1.0 if our_bench else 0.0,
        _slot_hp_fraction(our_active) or 0.0,
        _slot_hp_fraction(their_active) or 0.0,
        _mean_hp_fraction(our_bench) or 0.0,
        _mean_hp_fraction(their_bench) or 0.0,
        float(our_energy),
        float(their_energy),
        float(turn),
        1.0 if is_our_turn else 0.0,
        1.0 if bool(state.get("supporterPlayed")) else 0.0,
        1.0 if bool(state.get("energyAttached")) else 0.0,
    ]


def extract_features(state, your_index) -> list:
    """Fixed-order feature vector (FEATURE_NAMES) for `state` from our seat.

    `state` is the raw engine state dict (obs["current"] / dataclasses.asdict of
    the search Observation's current state); `your_index` is our seat, 0 or 1.
    Returns a list of N_FEATURES floats. Any malformed input, including a state
    that is not a dict or an out-of-range your_index, returns a zero vector of
    the correct length rather than raising.
    """
    try:
        return _extract(state or {}, your_index)
    except Exception:
        return _zero_vector()
