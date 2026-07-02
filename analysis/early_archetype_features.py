"""Early-turn opponent feature extractor for archetype detection (plan U9a).

analysis/opponent_archetype.py's archetype_label() already gives a proven
ground-truth label, but only once a WHOLE finished replay has been read (it
needs the deck's headline attacker to have shown up somewhere across the whole
game). This module extracts the much smaller signal actually available BEFORE
that point: what the opponent has revealed by their first few turns. U9b trains
a classifier to predict archetype_label's own answer from this early-turn
vector alone (a distillation task), and U9c (behind a flag, gated on a
gauntlet A/B) uses that prediction to sharpen analysis/archetype.py's static
pre-reveal decklist guess.

Pure over an injected is_pokemon/energy_type_of predicate pair, the same
dependency-injection shape as opponent_archetype.py, so this unit-tests without
the card engine. Bench and active-spot Pokemon are face-up information in this
game (not hidden), so, like revealed_opponent_pokemon, this reads every step's
observation regardless of which seat recorded it; only the turn number (capped
at cutoff_turn) bounds how far into the game a feature may look.

Never raises: a missing or malformed replay returns a zero vector of the
correct length, same discipline as ptcg_agent/features.py and
agents/imitation_features.py.
"""
from __future__ import annotations

# Bump on ANY change to FEATURE_NAMES or the extractor below (mirrors
# ptcg_agent/features.py's FEATURE_VERSION discipline). A trained model
# (U9b's analysis/archetype_prior.json) records the version it was fit
# against, and its scorer (U9c) refuses to score with a stale-version model.
FEATURE_VERSION = "1"

# "Cutoff turn 6" is each seat's first three turns (turn 1 = seat A's turn 1,
# turn 2 = seat B's turn 1, turn 3 = seat A's turn 2, ... turn 6 = seat B's
# turn 3), matching how the plan's addendum frames the early-game window.
DEFAULT_CUTOFF_TURN = 6

FEATURE_NAMES = (
    "opp_bench_count",
    "opp_revealed_pokemon_count",
    "opp_energy_type_count",
    "opp_is_first_player",
    "first_pokemon_reveal_turn",
    "first_energy_reveal_turn",
)
N_FEATURES = len(FEATURE_NAMES)

_POKEMON_AREAS = ("active", "bench")


def feature_version() -> str:
    """The FEATURE_VERSION a trained model should be pinned against. Pure."""
    return FEATURE_VERSION


def _zero_vector() -> list:
    return [0.0] * N_FEATURES


def _area_slots(player, area) -> list:
    return [p for p in (player.get(area) or []) if p]


def _extract(replay, opp_seat, is_pokemon, energy_type_of, cutoff_turn) -> list:
    if not isinstance(replay, dict) or not isinstance(opp_seat, int) or not (0 <= opp_seat < 2):
        return _zero_vector()

    pokemon_ids: set = set()
    energy_types: set = set()
    max_bench = 0
    first_player = None
    first_pokemon_turn = cutoff_turn
    first_energy_turn = cutoff_turn
    seen_pokemon = False
    seen_energy = False

    for step in replay.get("steps") or []:
        if not isinstance(step, (list, tuple)):
            continue
        for rec in step:
            if not isinstance(rec, dict):
                continue
            obs = rec.get("observation") or {}
            current = obs.get("current") or {}
            turn = current.get("turn")
            if not isinstance(turn, int) or turn < 1 or turn > cutoff_turn:
                continue
            if first_player is None and isinstance(current.get("firstPlayer"), int):
                first_player = current.get("firstPlayer")
            players = current.get("players") or []
            if not (0 <= opp_seat < len(players)):
                continue
            opp = players[opp_seat] or {}

            bench = _area_slots(opp, "bench")
            if len(bench) > max_bench:
                max_bench = len(bench)

            for entry in _area_slots(opp, "active") + bench:
                cid = entry.get("id")
                if cid is not None and is_pokemon(cid):
                    pokemon_ids.add(cid)
                    if not seen_pokemon:
                        seen_pokemon = True
                        first_pokemon_turn = turn
                for ecard in (entry.get("energyCards") or []):
                    if not ecard:
                        continue
                    eid = ecard.get("id")
                    etype = energy_type_of(eid) if eid is not None else None
                    if etype is not None:
                        energy_types.add(etype)
                        if not seen_energy:
                            seen_energy = True
                            first_energy_turn = turn

    return [
        float(max_bench),
        float(len(pokemon_ids)),
        float(len(energy_types)),
        1.0 if first_player == opp_seat else 0.0,
        float(min(first_pokemon_turn, cutoff_turn)),
        float(min(first_energy_turn, cutoff_turn)),
    ]


def early_archetype_features(replay, opp_seat, is_pokemon, energy_type_of,
                              cutoff_turn: int = DEFAULT_CUTOFF_TURN) -> list:
    """Fixed-order early-turn feature vector (FEATURE_NAMES) for `opp_seat`.

    `replay` is a whole replay dict (as saved by tools/harvest_replays.py);
    `opp_seat` is the opponent's absolute seat (0 or 1); `is_pokemon(cid)` and
    `energy_type_of(cid)` are injected card lookups (energy_type_of returns
    None for a non-basic-energy card id, matching the real wiring in
    tools/replays_to_archetype_rows.py). Only steps at turn <= cutoff_turn
    contribute, so this never sees more of the game than a real early-turn
    decision would have. Returns a list of N_FEATURES floats; any malformed
    input returns a zero vector of the correct length rather than raising.
    """
    try:
        return _extract(replay, opp_seat, is_pokemon, energy_type_of, cutoff_turn)
    except Exception:
        return _zero_vector()
