"""Tests for the early-turn archetype feature extractor (plan U9a).

Pins FEATURE_NAMES/N_FEATURES, checks feature_version() for U9b/U9c's
stale-model guard, checks the extractor never raises on malformed/short
replays, and checks the cutoff_turn boundary: steps beyond cutoff_turn must
not change the output versus omitting those steps entirely (the whole point of
an EARLY-turn feature is that it cannot see the rest of the game).
"""
from analysis import early_archetype_features as EAF

# Small stand-in card world: id -> is_pokemon / basic-energy type. No card DB
# needed, same dependency-injection shape as tests/test_scout.py's opponent
# archetype fixtures.
_POKEMON_IDS = {100, 101, 102}
_ENERGY_TYPES = {300: 3, 301: 1, 302: 3}  # 300/302 same type, 301 a different one


def _is_pokemon(cid):
    return cid in _POKEMON_IDS


def _energy_type_of(cid):
    return _ENERGY_TYPES.get(cid)


def _mon(cid, energy_ids=None):
    return {"id": cid, "energyCards": [{"id": e} for e in (energy_ids or [])]}


def _board_step(turn, opp_seat, active=None, bench=None, first_player=0):
    """A replay step revealing opp_seat's board (active/bench) at `turn`."""
    current = {
        "turn": turn,
        "firstPlayer": first_player,
        "yourIndex": opp_seat,
        "players": [None, None],
    }
    current["players"][opp_seat] = {"active": active or [], "bench": bench or []}
    current["players"][1 - opp_seat] = {"active": [], "bench": []}
    rec = {"status": "ACTIVE", "observation": {"current": current}}
    return [rec]


def test_feature_names_pinned():
    assert EAF.N_FEATURES == len(EAF.FEATURE_NAMES) == 6
    assert EAF.FEATURE_NAMES == (
        "opp_bench_count",
        "opp_revealed_pokemon_count",
        "opp_energy_type_count",
        "opp_is_first_player",
        "first_pokemon_reveal_turn",
        "first_energy_reveal_turn",
    )
    assert len(set(EAF.FEATURE_NAMES)) == EAF.N_FEATURES


def test_feature_version_is_pinned_string():
    assert EAF.feature_version() == EAF.FEATURE_VERSION
    assert isinstance(EAF.FEATURE_VERSION, str)


def test_never_raises_on_malformed_replay():
    assert EAF.early_archetype_features(None, 1, _is_pokemon, _energy_type_of) == [0.0] * EAF.N_FEATURES
    assert EAF.early_archetype_features("not-a-dict", 1, _is_pokemon, _energy_type_of) == [0.0] * EAF.N_FEATURES
    assert EAF.early_archetype_features({}, 5, _is_pokemon, _energy_type_of) == [0.0] * EAF.N_FEATURES
    assert EAF.early_archetype_features({}, -1, _is_pokemon, _energy_type_of) == [0.0] * EAF.N_FEATURES
    result = EAF.early_archetype_features({"steps": "not-a-list"}, 1, _is_pokemon, _energy_type_of)
    assert len(result) == EAF.N_FEATURES


def test_short_replay_returns_no_reveal_defaults():
    result = EAF.early_archetype_features({}, 1, _is_pokemon, _energy_type_of)
    assert len(result) == EAF.N_FEATURES
    names = dict(zip(EAF.FEATURE_NAMES, result))
    assert names["opp_bench_count"] == 0.0
    assert names["opp_revealed_pokemon_count"] == 0.0
    assert names["opp_energy_type_count"] == 0.0
    # No firstPlayer info at all -> the flag defaults false.
    assert names["opp_is_first_player"] == 0.0
    # No reveal at all -> clamped to the cutoff, not left unset.
    assert names["first_pokemon_reveal_turn"] == EAF.DEFAULT_CUTOFF_TURN
    assert names["first_energy_reveal_turn"] == EAF.DEFAULT_CUTOFF_TURN


def test_reveals_accumulate_across_steps():
    replay = {"steps": [
        _board_step(1, opp_seat=1, active=[_mon(100)], bench=[]),
        _board_step(3, opp_seat=1, active=[_mon(100, [300])], bench=[_mon(101)]),
        _board_step(5, opp_seat=1, active=[_mon(100, [300])], bench=[_mon(101), _mon(102, [301])]),
    ]}
    result = EAF.early_archetype_features(replay, opp_seat=1, is_pokemon=_is_pokemon,
                                           energy_type_of=_energy_type_of)
    names = dict(zip(EAF.FEATURE_NAMES, result))
    assert names["opp_bench_count"] == 2.0  # max bench seen (turn 5)
    assert names["opp_revealed_pokemon_count"] == 3.0  # 100, 101, 102
    assert names["opp_energy_type_count"] == 2.0  # energy types 3 (id 300) and 1 (id 301)
    assert names["first_pokemon_reveal_turn"] == 1.0
    assert names["first_energy_reveal_turn"] == 3.0


def test_wrong_seat_sees_nothing():
    replay = {"steps": [_board_step(1, opp_seat=1, active=[_mon(100, [300])], bench=[_mon(101)])]}
    result = EAF.early_archetype_features(replay, opp_seat=0, is_pokemon=_is_pokemon,
                                           energy_type_of=_energy_type_of)
    names = dict(zip(EAF.FEATURE_NAMES, result))
    assert names["opp_bench_count"] == 0.0
    assert names["opp_revealed_pokemon_count"] == 0.0
    assert names["opp_energy_type_count"] == 0.0


def test_opp_is_first_player_flag():
    replay_first = {"steps": [_board_step(1, opp_seat=1, active=[_mon(100)], first_player=1)]}
    replay_second = {"steps": [_board_step(1, opp_seat=1, active=[_mon(100)], first_player=0)]}
    r1 = EAF.early_archetype_features(replay_first, 1, _is_pokemon, _energy_type_of)
    r2 = EAF.early_archetype_features(replay_second, 1, _is_pokemon, _energy_type_of)
    idx = EAF.FEATURE_NAMES.index("opp_is_first_player")
    assert r1[idx] == 1.0
    assert r2[idx] == 0.0


def test_cutoff_turn_excludes_later_steps():
    early_steps = [
        _board_step(1, opp_seat=1, active=[_mon(100, [300])], bench=[]),
        _board_step(3, opp_seat=1, active=[_mon(100, [300])], bench=[_mon(101)]),
    ]
    late_steps = [
        _board_step(9, opp_seat=1, active=[_mon(100, [300])],
                    bench=[_mon(101), _mon(102, [301])]),
    ]
    replay_without_late = {"steps": early_steps}
    replay_with_late = {"steps": early_steps + late_steps}

    r_without = EAF.early_archetype_features(replay_without_late, 1, _is_pokemon, _energy_type_of,
                                               cutoff_turn=EAF.DEFAULT_CUTOFF_TURN)
    r_with = EAF.early_archetype_features(replay_with_late, 1, _is_pokemon, _energy_type_of,
                                           cutoff_turn=EAF.DEFAULT_CUTOFF_TURN)
    assert r_with == r_without


def test_custom_cutoff_turn_is_respected():
    replay = {"steps": [
        _board_step(1, opp_seat=1, active=[_mon(100)], bench=[]),
        _board_step(4, opp_seat=1, active=[_mon(100)], bench=[_mon(101)]),
    ]}
    result = EAF.early_archetype_features(replay, 1, _is_pokemon, _energy_type_of, cutoff_turn=2)
    names = dict(zip(EAF.FEATURE_NAMES, result))
    assert names["opp_bench_count"] == 0.0  # the turn-4 bench reveal is past cutoff_turn=2
    assert names["opp_revealed_pokemon_count"] == 1.0
    assert names["first_pokemon_reveal_turn"] == 1.0
