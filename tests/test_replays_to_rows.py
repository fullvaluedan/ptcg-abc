"""U3b replay-to-rows converter tests.

Fixtures are hand-built replay dicts (matching the env.toJSON shape parse_replay
and the gauntlet state logger already read), never real competition data.
"""
import csv

from ptcg_agent.features import FEATURE_NAMES
from tools.replays_to_rows import (
    BALANCE_HI,
    BALANCE_LO,
    convert_dir,
    downsample_to_balance,
    rows_from_replay,
    write_csv,
)


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


def _active_entry(seat, turn=3, prizes=(6, 6)):
    return {
        "action": [0],
        "status": "ACTIVE",
        "reward": 0,
        "observation": {
            "select": {"option": [0, 1, 2], "minCount": 1, "maxCount": 1},
            "current": _current(seat, turn=turn, prizes=prizes),
        },
    }


def _inactive():
    return {"action": [], "status": "INACTIVE", "reward": 0, "observation": {"select": None, "current": None}}


def _handshake():
    return [
        {"action": [], "status": "INACTIVE", "reward": 0, "observation": {"select": None, "current": None}},
        {"action": [], "status": "INACTIVE", "reward": 0, "observation": {"select": None, "current": None}},
    ]


def _step(seat_deciding, turn=3):
    entry = _active_entry(seat_deciding, turn=turn)
    return [entry, _inactive()] if seat_deciding == 0 else [_inactive(), entry]


def _two_seat_replay(rewards=(1, -1)):
    """A replay where both seats get a turn to decide, seat 0 wins by default."""
    return {
        "info": {"TeamNames": ["us", "them"]},
        "rewards": list(rewards),
        "steps": [
            _handshake(),
            _step(0, turn=1),
            _step(1, turn=2),
            _step(0, turn=3),
        ],
    }


def test_rows_from_replay_labels_each_seat_with_its_own_result():
    replay = _two_seat_replay(rewards=(1, -1))
    rows = rows_from_replay(replay, "game1")

    assert len(rows) == 3  # two seat-0 decisions, one seat-1 decision
    header_len = 3 + len(FEATURE_NAMES) + 1
    assert all(len(row) == header_len for row in rows)

    seat0_labels = {row[-1] for row in rows if row[1] == 0}
    seat1_labels = {row[-1] for row in rows if row[1] == 1}
    assert seat0_labels == {1}
    assert seat1_labels == {0}
    assert all(row[0] == "game1" for row in rows)


def test_rows_from_replay_drops_draws():
    replay = _two_seat_replay(rewards=(0, 0))
    assert rows_from_replay(replay, "draw_game") == []


def test_rows_from_replay_drops_missing_rewards():
    replay = _two_seat_replay(rewards=(None, None))
    replay["rewards"] = None
    assert rows_from_replay(replay, "no_reward_game") == []


def test_rows_from_replay_falls_back_to_last_step_reward():
    replay = _two_seat_replay(rewards=(1, -1))
    del replay["rewards"]
    last_step = replay["steps"][-1]
    last_step[0]["reward"] = 1
    last_step[1]["reward"] = -1
    rows = rows_from_replay(replay, "fallback_game")
    assert rows
    assert {row[-1] for row in rows if row[1] == 0} == {1}


def test_rows_from_replay_skips_deck_handshake_only():
    replay = {"info": {"TeamNames": ["us", "them"]}, "rewards": [1, -1], "steps": [_handshake()]}
    assert rows_from_replay(replay, "handshake_only") == []


def test_convert_dir_skips_malformed_json(tmp_path):
    good = _two_seat_replay(rewards=(1, -1))
    (tmp_path / "1.json").write_text(__import__("json").dumps(good))
    (tmp_path / "2.json").write_text("{ not json")

    rows = convert_dir(tmp_path)
    assert rows
    assert all(row[0] == "1" for row in rows)


def test_downsample_leaves_balanced_data_untouched():
    rows = [["g", 0, 0, 1] for _ in range(4)] + [["g", 0, 0, 0] for _ in range(6)]
    assert downsample_to_balance(rows) == rows


def test_downsample_trims_majority_class_to_fifty_fifty():
    rows = [["g", 0, 0, 1] for _ in range(2)] + [["g", 0, 0, 0] for _ in range(18)]
    balance_before = sum(1 for r in rows if r[-1] == 1) / len(rows)
    assert not (BALANCE_LO <= balance_before <= BALANCE_HI)

    out = downsample_to_balance(rows)
    n1 = sum(1 for r in out if r[-1] == 1)
    n0 = sum(1 for r in out if r[-1] == 0)
    assert n1 == n0 == 2


def test_downsample_is_deterministic():
    rows = [["g", 0, 0, 1] for _ in range(2)] + [["g", 0, 0, 0] for _ in range(18)]
    assert downsample_to_balance(rows) == downsample_to_balance(rows)


def test_write_csv_header_has_source_column(tmp_path):
    rows = [["game1", 0, 1, *[0.0] * len(FEATURE_NAMES), 1]]
    out = write_csv(rows, tmp_path / "ladder_rows.csv")

    with open(out, newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        data = next(reader)

    assert header == ["game_id", "seat", "turn", *FEATURE_NAMES, "label", "source"]
    assert data[-1] == "ladder"
