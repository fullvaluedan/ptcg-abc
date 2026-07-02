"""Tests for the early-turn archetype silver-label rows tool (plan U9a).

Fixtures are hand-built replay dicts, never real competition data. Card
lookups are a small stand-in world (mirrors tests/test_scout.py's opponent
archetype fixtures) rather than the real engine, so these stay fast and
hermetic; tools/replays_to_archetype_rows.real_predicates() (the real wiring)
is exercised only by the CLI, not by these tests.
"""
import csv
import json

from analysis.early_archetype_features import FEATURE_NAMES
from tools.replays_to_archetype_rows import (
    MIN_LABEL_GAMES,
    OTHER,
    collapse_rare_labels,
    convert_dir,
    label_counts,
    row_from_replay,
    write_csv,
)

# id -> (name, is_pokemon). No card DB needed.
_CARDS = {
    100: ("Mega Starmie ex", True),
    101: ("Staryu", True),
    200: ("Fezandipiti ex", True),
    300: ("Basic {W} Energy", False),
}


def _name_of(cid):
    return _CARDS.get(cid, (None, False))[0]


def _is_pokemon(cid):
    return _CARDS.get(cid, (None, False))[1]


def _energy_type_of(cid):
    return 3 if cid == 300 else None


_PREDICATES = (_name_of, _is_pokemon, _energy_type_of)


def _board_step(turn, opp_seat, active=None, bench=None):
    current = {
        "turn": turn,
        "firstPlayer": 0,
        "yourIndex": opp_seat,
        "players": [None, None],
    }
    current["players"][opp_seat] = {"active": active or [], "bench": bench or []}
    current["players"][1 - opp_seat] = {"active": [], "bench": []}
    rec = {"status": "ACTIVE", "observation": {"current": current}}
    return [rec]


def _mon(cid, energy_ids=None):
    return {"id": cid, "energyCards": [{"id": e} for e in (energy_ids or [])]}


def _replay(opp_steps, team_names=("us", "them")):
    return {"info": {"TeamNames": list(team_names)}, "steps": opp_steps}


def test_row_from_replay_returns_label_and_feature_vector():
    replay = _replay([
        _board_step(1, opp_seat=1, active=[_mon(101)]),
        _board_step(3, opp_seat=1, active=[_mon(100, [300])], bench=[_mon(101)]),
    ])
    result = row_from_replay(replay, _PREDICATES)
    assert result is not None
    label, feats = result
    assert label == "Mega Starmie ex"  # headline attacker over the whole game
    assert len(feats) == len(FEATURE_NAMES)


def test_row_from_replay_skips_self_play():
    replay = _replay([_board_step(1, opp_seat=1, active=[_mon(100)])], team_names=("us", "us"))
    assert row_from_replay(replay, _PREDICATES) is None


def test_row_from_replay_none_for_non_dict():
    assert row_from_replay(None, _PREDICATES) is None
    assert row_from_replay("not-a-replay", _PREDICATES) is None


def test_row_from_replay_falls_back_when_team_not_found():
    replay = _replay([_board_step(1, opp_seat=1, active=[_mon(100)])], team_names=("someone else", "them"))
    # our_index_from_replay can't find "us" -> falls back to our_index_fallback=0, opp_seat=1
    result = row_from_replay(replay, _PREDICATES, our_index_fallback=0)
    assert result is not None
    label, _feats = result
    assert label == "Mega Starmie ex"


def test_collapse_rare_labels_folds_below_threshold():
    rows = (
        [("Mega Starmie ex", [0.0])] * 4
        + [("Dragapult ex", [0.0])] * 1
        + [("Alakazam", [0.0])] * 2
    )
    out = collapse_rare_labels(rows, min_games=3)
    labels = [label for label, _feats in out]
    assert labels.count("Mega Starmie ex") == 4  # meets threshold, kept
    assert labels.count(OTHER) == 3  # Dragapult (1) + Alakazam (2) folded in
    assert "Dragapult ex" not in labels
    assert "Alakazam" not in labels


def test_collapse_rare_labels_default_threshold_matches_module_constant():
    assert MIN_LABEL_GAMES == 5


def test_convert_dir_skips_malformed_and_self_play(tmp_path):
    good = _replay([_board_step(1, opp_seat=1, active=[_mon(100, [300])])])
    self_play = _replay([_board_step(1, opp_seat=1, active=[_mon(101)])], team_names=("us", "us"))
    (tmp_path / "1.json").write_text(json.dumps(good))
    (tmp_path / "2.json").write_text(json.dumps(self_play))
    (tmp_path / "3.json").write_text("{ not json")

    rows = convert_dir(tmp_path, predicates=_PREDICATES, min_games=1)
    assert len(rows) == 1
    assert rows[0][0] == "1"
    assert rows[0][1] == "Mega Starmie ex"
    assert len(rows[0]) == 2 + len(FEATURE_NAMES)


def test_convert_dir_collapses_rare_labels(tmp_path):
    common = _replay([_board_step(1, opp_seat=1, active=[_mon(100)])])  # Mega Starmie ex
    rare = _replay([_board_step(1, opp_seat=1, active=[_mon(200)])])  # Fezandipiti ex, seen once
    for i in range(3):
        (tmp_path / f"common{i}.json").write_text(json.dumps(common))
    (tmp_path / "rare.json").write_text(json.dumps(rare))

    rows = convert_dir(tmp_path, predicates=_PREDICATES, min_games=3)
    labels = {row[1] for row in rows}
    assert labels == {"Mega Starmie ex", OTHER}


def test_label_counts():
    rows = [["g1", "A", 0.0], ["g2", "A", 0.0], ["g3", OTHER, 0.0]]
    assert label_counts(rows) == {"A": 2, OTHER: 1}


def test_write_csv_header_and_source(tmp_path):
    rows = [["game1", "Mega Starmie ex", *[0.0] * len(FEATURE_NAMES)]]
    out = write_csv(rows, tmp_path / "archetype_rows.csv")

    with open(out, newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        data = next(reader)

    assert header == ["game_id", "label", *FEATURE_NAMES, "source"]
    assert data[-1] == "ladder"
