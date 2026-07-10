"""U3 / U106b matched-action extraction tests.

Fixtures are hand-built replay dicts and small synthetic DataFrames, never
real competition data (same discipline as tests/test_replays_to_rows.py,
whose helper shapes this file mirrors for the replay-JSON fixtures).
"""
import json
import zipfile

import pandas as pd
import pytest

from agents import heuristics as H
from analysis.matched_action_extraction import (
    FEATURE_COLS,
    aggregate_by_cluster,
    build_zip_index,
    extract_expert_action,
    knn_join,
    load_episode_from_zip,
    resolve_actions,
)


# --- replay-JSON fixture helpers (mirrors tests/test_replays_to_rows.py) ----

def _player(prizes=6, deck_count=50, hand_count=5, bench=None):
    return {
        "prize": [None] * prizes,
        "deckCount": deck_count,
        "handCount": hand_count,
        "active": [],
        "bench": bench or [],
    }


def _current(seat, turn=3, prizes=(6, 6)):
    return {
        "yourIndex": seat,
        "turn": turn,
        "firstPlayer": 0,
        "players": [_player(prizes=prizes[0]), _player(prizes=prizes[1])],
    }


def _inactive():
    return {"action": [], "status": "INACTIVE", "reward": 0, "observation": {"select": None, "current": None}}


def _handshake():
    return [_inactive(), _inactive()]


def _opt(otype, **kw):
    opt = {"type": otype}
    opt.update(kw)
    return opt


def _main_entry(seat, options, action, turn=3, prizes=(6, 6)):
    return {
        "action": action,
        "status": "ACTIVE",
        "reward": 0,
        "observation": {
            "select": {"option": options, "minCount": 1, "maxCount": 1, "type": H.SEL_MAIN},
            "current": _current(seat, turn=turn, prizes=prizes),
        },
    }


def _main_step(seat_deciding, options, action, turn=3):
    entry = _main_entry(seat_deciding, options, action, turn=turn)
    return [entry, _inactive()] if seat_deciding == 0 else [_inactive(), entry]


def _winner_seat0_replay(turn=5):
    """A replay seat 0 wins, with one MAIN decision at `turn`: RETREAT chosen."""
    options = [_opt(H.OPT_END), _opt(H.OPT_RETREAT)]
    return {
        "info": {"TeamNames": ["us", "them"]},
        "rewards": [1, -1],
        "steps": [
            _handshake(),
            _main_step(0, options, [1], turn=turn),  # seat0 (winner) picks option 1: RETREAT
        ],
    }


# --- 1. neighbor keys survive the join --------------------------------------

def _feature_row(**overrides):
    row = {c: 0.0 for c in FEATURE_COLS}
    row.update(overrides)
    return row


def test_knn_join_retains_neighbor_identity_not_just_distance():
    # One loss state, engineered to sit closest to expert row index 1.
    loss_states = pd.DataFrame([
        {"our_game_id": "loss1", "seat": 0, "turn": 4, "bucket": "early_collapse",
         **_feature_row(prize_diff=0.0, our_prizes_left=6.0)},
    ])
    expert_corpus = pd.DataFrame([
        {"game_id": "far_game", "seat": 0, "turn": 1, **_feature_row(prize_diff=10.0, our_prizes_left=0.0)},
        {"game_id": "near_game", "seat": 1, "turn": 7, **_feature_row(prize_diff=0.1, our_prizes_left=5.9)},
        {"game_id": "mid_game", "seat": 0, "turn": 3, **_feature_row(prize_diff=3.0, our_prizes_left=3.0)},
    ])

    joined = knn_join(loss_states, expert_corpus, k=2)

    assert len(joined) == 1
    row = joined.iloc[0]
    # The join must carry the WINNING neighbor's identity, not merely a distance.
    assert row["nn_game_id"] == "near_game"
    assert row["nn_seat"] == 1
    assert row["nn_turn"] == 7
    assert row["nn_distance"] is not None
    assert row["nn_distance"] >= 0.0


def test_knn_join_empty_loss_states_returns_empty_frame_with_columns():
    loss_states = pd.DataFrame(columns=["our_game_id", "seat", "turn", "bucket", *FEATURE_COLS])
    expert_corpus = pd.DataFrame([{"game_id": "g1", "seat": 0, "turn": 1, **_feature_row()}])
    joined = knn_join(loss_states, expert_corpus)
    assert joined.empty
    assert "nn_game_id" in joined.columns


# --- 2. zip index searches every zip, not just a same-day guess -------------

def _write_zip(path, members: dict):
    with zipfile.ZipFile(path, "w") as zf:
        for name, payload in members.items():
            zf.writestr(name, json.dumps(payload))


def test_zip_index_finds_game_id_only_present_in_next_day_zip(tmp_path):
    episodes_dir = tmp_path / "episodes"
    episodes_dir.mkdir()
    # Two dated zips: D has one episode, D+1 has a DIFFERENT episode whose
    # corpus row would naively be assumed to live in the same-day (D) zip.
    day_zip = episodes_dir / "pokemon-tcg-ai-battle-episodes-2026-07-09.zip"
    next_day_zip = episodes_dir / "pokemon-tcg-ai-battle-episodes-2026-07-10.zip"
    _write_zip(day_zip, {"111.json": {"rewards": [1, -1], "steps": []}})
    _write_zip(next_day_zip, {"222.json": {"rewards": [1, -1], "steps": []}})
    # A small manifest-only index zip must not break indexing.
    _write_zip(episodes_dir / "pokemon-tcg-ai-battle-episodes-index.zip", {"manifest.csv": {}})

    index = build_zip_index(episodes_dir)

    # game_id 222 is only in the D+1 zip; "querying for date D" means we do
    # NOT scope the lookup to day_zip -- the index must still resolve it.
    assert index["222"] == next_day_zip
    assert index["111"] == day_zip

    replay = load_episode_from_zip(index, "222")
    assert replay is not None
    assert replay["rewards"] == [1, -1]


def test_zip_index_missing_game_id_resolves_to_none(tmp_path):
    episodes_dir = tmp_path / "episodes"
    episodes_dir.mkdir()
    _write_zip(episodes_dir / "day.zip", {"111.json": {"rewards": [1, -1]}})
    index = build_zip_index(episodes_dir)
    assert load_episode_from_zip(index, "999") is None


# --- 3. action extraction returns the recorded entry["action"] index --------

def test_extract_expert_action_returns_chosen_action_category():
    replay = _winner_seat0_replay(turn=5)
    action = extract_expert_action(replay, "gameX", seat=0, turn=5)
    assert action == "RETREAT"  # option index 1 == OPT_RETREAT was entry["action"]


def test_extract_expert_action_no_matching_turn_returns_none():
    replay = _winner_seat0_replay(turn=5)
    assert extract_expert_action(replay, "gameX", seat=0, turn=99) is None


def test_extract_expert_action_wrong_seat_returns_none():
    replay = _winner_seat0_replay(turn=5)
    # seat 1 never had a MAIN decision in this fixture.
    assert extract_expert_action(replay, "gameX", seat=1, turn=5) is None


def test_resolve_actions_uses_zip_adapter_end_to_end(tmp_path):
    episodes_dir = tmp_path / "episodes"
    episodes_dir.mkdir()
    replay = _winner_seat0_replay(turn=5)
    _write_zip(episodes_dir / "day.zip", {"555.json": replay})
    zip_index = build_zip_index(episodes_dir)

    matched = pd.DataFrame([
        {"our_game_id": "ourloss1", "bucket": "early_collapse",
         "nn_game_id": "555", "nn_seat": 0, "nn_turn": 5, "nn_distance": 0.2},
        {"our_game_id": "ourloss2", "bucket": "early_collapse",
         "nn_game_id": "does_not_exist", "nn_seat": 0, "nn_turn": 5, "nn_distance": 0.9},
    ])
    resolved = resolve_actions(matched, zip_index)

    assert resolved.loc[0, "action"] == "RETREAT"
    assert pd.isna(resolved.loc[1, "action"])


# --- 4. per-game weighting: a 50-state game must not dominate 50:1 ----------

def test_aggregate_by_cluster_weights_per_game_not_per_state():
    rows = []
    # One chatty game contributing 50 states, all resolved to ATTACK.
    for i in range(50):
        rows.append({"bucket": "early_collapse", "our_game_id": "chatty_game",
                     "action": "ATTACK", "nn_distance": 0.5})
    # Four quiet games contributing one state each, all resolved to RETREAT.
    for i in range(4):
        rows.append({"bucket": "early_collapse", "our_game_id": f"quiet_game_{i}",
                     "action": "RETREAT", "nn_distance": 0.5})
    resolved = pd.DataFrame(rows)

    result = aggregate_by_cluster(resolved)
    dist = result["early_collapse"]["action_distribution"]

    # Raw-state weighting would read ATTACK at 50/54 ~= 92.6%. Per-game
    # weighting must give the chatty game exactly ONE vote out of five.
    assert dist["ATTACK"] == pytest.approx(0.2, abs=1e-6)
    assert dist["RETREAT"] == pytest.approx(0.8, abs=1e-6)
    assert result["early_collapse"]["n_games"] == 5
    assert result["early_collapse"]["support"] == 54
    assert result["early_collapse"]["n_states"] == 54


# --- 5. empty-support cluster reports support=0, never a fabricated verdict -

def test_aggregate_by_cluster_reports_support_zero_when_nothing_resolved():
    resolved = pd.DataFrame([
        {"bucket": "deckout", "our_game_id": "g1", "action": None, "nn_distance": 0.4},
        {"bucket": "deckout", "our_game_id": "g2", "action": None, "nn_distance": 0.6},
    ])
    result = aggregate_by_cluster(resolved)
    assert result["deckout"]["support"] == 0
    assert result["deckout"]["n_games"] == 0
    assert result["deckout"]["action_distribution"] == {}
    assert result["deckout"]["n_states"] == 2


def test_aggregate_by_cluster_empty_input_returns_empty_dict():
    assert aggregate_by_cluster(pd.DataFrame()) == {}


def test_aggregate_by_cluster_mixed_resolved_and_unresolved_in_same_bucket():
    resolved = pd.DataFrame([
        {"bucket": "endgame_misplay", "our_game_id": "g1", "action": "ATTACK", "nn_distance": 0.3},
        {"bucket": "endgame_misplay", "our_game_id": "g1", "action": None, "nn_distance": 0.3},
        {"bucket": "endgame_misplay", "our_game_id": "g2", "action": "END", "nn_distance": 0.5},
    ])
    result = aggregate_by_cluster(resolved)
    r = result["endgame_misplay"]
    assert r["n_states"] == 3
    assert r["support"] == 2  # only the two non-None actions
    assert r["n_games"] == 2
    assert r["action_distribution"] == {"ATTACK": 0.5, "END": 0.5}
