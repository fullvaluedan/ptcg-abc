"""Tests for the pure feature extractor (plan U2, src/ptcg_agent/features.py).

Builds minimal fake state dicts (the same raw camelCase shape search/eval.py
and heuristics.py read) covering a normal board, an empty bench, and missing
fields, then checks the extractor never raises, always returns a fixed-length
vector, and keeps values in their expected ranges.
"""
from ptcg_agent.features import FEATURE_NAMES, N_FEATURES, extract_features


def _pokemon(hp, max_hp, energy_count=0):
    return {
        "hp": hp,
        "maxHp": max_hp,
        "energyCards": [{"id": 1}] * energy_count,
    }


def _player(prizes=6, deck_count=50, hand_count=5, active=None, bench=None):
    return {
        "prize": [None] * prizes,
        "deckCount": deck_count,
        "handCount": hand_count,
        "active": [active] if active else [],
        "bench": bench or [],
    }


def _state(players, turn=3, first_player=0, supporter_played=False, energy_attached=False):
    return {
        "turn": turn,
        "firstPlayer": first_player,
        "supporterPlayed": supporter_played,
        "energyAttached": energy_attached,
        "players": players,
    }


def test_feature_names_and_vector_length_match():
    assert len(FEATURE_NAMES) == N_FEATURES
    assert len(set(FEATURE_NAMES)) == N_FEATURES


def test_normal_board_vector_is_well_formed():
    me = _player(active=_pokemon(80, 120, energy_count=2),
                 bench=[_pokemon(60, 60), _pokemon(30, 90)])
    opp = _player(active=_pokemon(50, 100, energy_count=1), bench=[_pokemon(90, 90)])
    state = _state([me, opp])

    vec = extract_features(state, 0)

    assert len(vec) == N_FEATURES
    assert all(isinstance(v, float) for v in vec)
    by_name = dict(zip(FEATURE_NAMES, vec))
    assert -1.0 <= by_name["prize_diff"] <= 1.0
    assert 0.0 <= by_name["our_active_hp_frac"] <= 1.0
    assert 0.0 <= by_name["their_active_hp_frac"] <= 1.0
    assert 0.0 <= by_name["our_bench_hp_frac"] <= 1.0
    assert by_name["our_bench_size"] == 2.0
    assert by_name["our_bench_nonempty"] == 1.0
    assert by_name["our_energy"] == 2.0
    assert by_name["their_energy"] == 1.0


def test_empty_bench_is_zero_not_missing():
    me = _player(active=_pokemon(80, 120), bench=[])
    opp = _player(active=_pokemon(50, 100), bench=[])
    state = _state([me, opp])

    vec = extract_features(state, 0)
    by_name = dict(zip(FEATURE_NAMES, vec))

    assert by_name["our_bench_size"] == 0.0
    assert by_name["our_bench_nonempty"] == 0.0
    assert by_name["our_bench_hp_frac"] == 0.0


def test_missing_fields_return_zero_vector_not_exception():
    assert extract_features({}, 0) == [0.0] * N_FEATURES
    assert extract_features(None, 0) == [0.0] * N_FEATURES
    assert extract_features({"players": []}, 0) == [0.0] * N_FEATURES
    assert extract_features({"players": [{}, {}]}, 5) == [0.0] * N_FEATURES


def test_malformed_player_entries_never_raise():
    state = _state([{"active": [None], "bench": [None, {}]}, {}])
    vec = extract_features(state, 0)
    assert len(vec) == N_FEATURES


def test_turn_number_is_clamped_and_seat_indexing_is_symmetric():
    me = _player(active=_pokemon(80, 120))
    opp = _player(active=_pokemon(50, 100))
    state = _state([me, opp], turn=999)

    vec0 = extract_features(state, 0)
    vec1 = extract_features(state, 1)
    by0 = dict(zip(FEATURE_NAMES, vec0))
    by1 = dict(zip(FEATURE_NAMES, vec1))

    assert by0["turn_number"] == 40.0
    assert by0["prize_diff"] == -by1["prize_diff"]
    assert by0["our_active_hp_frac"] == by1["their_active_hp_frac"]
