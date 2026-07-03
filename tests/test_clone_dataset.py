"""Tests for the top-player clone dataset builder (plan U70, tools/clone_dataset.py).

Everything here runs over synthetic replays built in-process; no competition
data is read or written. Pins the properties U71's trainer will rely on:

  1. only seats whose team is in team_set contribute groups, win or lose,
  2. a drawn or malformed-reward episode contributes nothing,
  3. every group in one episode shares that episode's split (episode-level,
     never decision-level, held-out),
  4. write_npz / load_npz / iter_groups round-trip a group's features, played
     index, and metadata exactly,
  5. summarize folds groups into per-family / per-team / per-split counts.
"""
from agents import heuristics as H
from analysis.expert_cohort import DECK_SIZE
from analysis.replay_trace import episode_id_of, split_of
from tools import clone_dataset as CD

SIG_ALPHA = frozenset({10, 11, 12, 13})
SIG_BETA = frozenset({20, 21, 22, 23})
SIGNATURES = {"alpha": SIG_ALPHA, "beta": SIG_BETA}


def _deck(distinct_ids, filler=8):
    deck = list(distinct_ids)
    return tuple(deck + [filler] * (DECK_SIZE - len(deck)))


def _opt(otype):
    return {"type": otype}


def _obs(seat, options, turn=1):
    return {
        "select": {"type": H.SEL_MAIN, "minCount": 1, "maxCount": 1, "option": options},
        "current": {
            "turn": turn,
            "yourIndex": seat,
            "turnActionCount": 0,
            "energyAttached": False,
            "players": [
                {"active": [], "bench": [], "hand": [], "discard": []},
                {"active": [], "bench": [], "hand": [], "discard": []},
            ],
        },
    }


def _main_entry(seat, n_options, played_idx, turn=1):
    """One ACTIVE MAIN decision record with n_options generic options."""
    options = [_opt(H.OPT_END) for _ in range(n_options)]
    return {
        "status": "ACTIVE",
        "action": [played_idx],
        "observation": _obs(seat, options, turn=turn),
    }


def _replay(rewards, deck0, deck1, decision_steps=(), names=("A", "B")):
    step0 = [
        {"status": "ACTIVE", "visualize": [{"action": [list(deck0), list(deck1)]}]},
        {"status": "INACTIVE"},
    ]
    steps = [step0] + [[entry] for entry in decision_steps]
    return {"rewards": list(rewards), "info": {"TeamNames": list(names)}, "steps": steps}


def test_only_matched_team_contributes_groups():
    steps = [_main_entry(0, 3, 1), _main_entry(1, 2, 0)]
    rep = _replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_BETA), steps, names=("A", "B"))
    groups = list(CD.replay_groups(rep, "ep1", {"A"}, SIGNATURES))
    assert len(groups) == 1
    assert groups[0]["team"] == "A"
    assert groups[0]["family"] == "alpha"
    assert groups[0]["won"] is True
    assert groups[0]["played"] == 1
    assert len(groups[0]["features"]) == 3


def test_both_seats_matched_when_both_are_top_teams():
    steps = [_main_entry(0, 3, 0), _main_entry(1, 2, 1)]
    rep = _replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_BETA), steps, names=("A", "B"))
    groups = list(CD.replay_groups(rep, "ep1", {"A", "B"}, SIGNATURES))
    teams = {g["team"] for g in groups}
    assert teams == {"A", "B"}
    won_by_team = {g["team"]: g["won"] for g in groups}
    assert won_by_team["A"] is True
    assert won_by_team["B"] is False


def test_unmatched_team_contributes_nothing():
    steps = [_main_entry(0, 3, 1)]
    rep = _replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_BETA), steps, names=("A", "B"))
    assert list(CD.replay_groups(rep, "ep1", {"someone_else"}, SIGNATURES)) == []


def test_draw_contributes_nothing():
    d = _deck(SIG_ALPHA)
    steps = [_main_entry(0, 3, 1)]
    rep = _replay([0, 0], d, d, steps, names=("A", "B"))
    assert list(CD.replay_groups(rep, "ep1", {"A"}, SIGNATURES)) == []


def test_malformed_reward_contributes_nothing():
    rep = {"info": {"TeamNames": ["A", "B"]}, "steps": []}
    assert list(CD.replay_groups(rep, "ep1", {"A"}, SIGNATURES)) == []


def test_missing_decklist_contributes_nothing():
    rep = {"rewards": [1, -1], "info": {"TeamNames": ["A", "B"]}, "steps": []}
    assert list(CD.replay_groups(rep, "ep1", {"A"}, SIGNATURES)) == []


def test_forced_single_option_decision_is_skipped():
    # decision_features returns None for a <=1-option select: no ranking signal.
    steps = [_main_entry(0, 1, 0)]
    rep = _replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_BETA), steps, names=("A", "B"))
    assert list(CD.replay_groups(rep, "ep1", {"A"}, SIGNATURES)) == []


def test_split_is_episode_level_not_decision_level():
    steps = [_main_entry(0, 3, 0), _main_entry(0, 2, 1)]
    rep = _replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_BETA), steps, names=("A", "B"))
    eid = episode_id_of("12345.json")
    groups = list(CD.replay_groups(rep, eid, {"A"}, SIGNATURES))
    assert len(groups) == 2
    expected = split_of(eid)
    assert all(g["split"] == expected for g in groups)


def test_build_dataset_counts_matched_and_skipped_episodes():
    matched = _replay(
        [1, -1], _deck(SIG_ALPHA), _deck(SIG_BETA), [_main_entry(0, 3, 0)], names=("A", "B")
    )
    unmatched = _replay(
        [1, -1], _deck(SIG_ALPHA), _deck(SIG_BETA), [_main_entry(0, 3, 0)], names=("X", "Y")
    )
    groups, meta = CD.groups_from_replays(
        [(matched, "1.json"), (unmatched, "2.json")], {"A"}, SIGNATURES
    )
    assert len(groups) == 1
    assert meta == {"episodes_matched": 1, "episodes_skipped": 1}


def test_summarize_folds_by_family_team_split():
    groups = [
        {"family": "alpha", "team": "A", "split": "train"},
        {"family": "alpha", "team": "A", "split": "test"},
        {"family": "beta", "team": "B", "split": "train"},
    ]
    summary = CD.summarize(groups)
    assert summary["groups"] == 3
    assert summary["by_family"] == {"alpha": 2, "beta": 1}
    assert summary["by_team"] == {"A": 2, "B": 1}
    assert summary["by_split"] == {"train": 2, "test": 1}


def test_npz_round_trip(tmp_path):
    groups = [
        {
            "features": [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]],
            "played": 2,
            "team": "A",
            "family": "alpha",
            "won": True,
            "episode": "1",
            "split": "train",
        },
        {
            "features": [[0.5, 0.5]],
            "played": 0,
            "team": "B",
            "family": "beta",
            "won": False,
            "episode": "2",
            "split": "test",
        },
    ]
    out = tmp_path / "clones" / "groups.npz"
    CD.write_npz(groups, out)
    assert out.exists()
    data = CD.load_npz(out)
    restored = list(CD.iter_groups(data))
    assert len(restored) == 2
    assert restored[0]["played"] == 2
    assert restored[0]["team"] == "A"
    assert restored[0]["family"] == "alpha"
    assert restored[0]["won"] is True
    assert restored[0]["episode"] == "1"
    assert restored[0]["split"] == "train"
    assert [list(row) for row in restored[0]["features"]] == groups[0]["features"]
    assert restored[1]["played"] == 0
    assert [list(row) for row in restored[1]["features"]] == groups[1]["features"]


def test_write_npz_handles_empty_groups(tmp_path):
    out = tmp_path / "empty.npz"
    CD.write_npz([], out)
    data = CD.load_npz(out)
    assert list(CD.iter_groups(data)) == []
    from agents import imitation_features
    assert data["X"].shape == (0, imitation_features.N_FEATURES)
