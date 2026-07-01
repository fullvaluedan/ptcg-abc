"""Tests for analysis/move_ranking_validator.py.

The validator is pure over the raw replay dict, so these cover the decision
extraction, the top-1 agreement tally, expert-seat resolution, and the zip/dir
loader with hand-built replays and fake pilots. No native engine, no card data,
and no competition dataset are touched: the pilot is always an injected callable,
so a MAIN decision's expected pick is known exactly.
"""
import json
import sys
import zipfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.move_ranking_validator import (  # noqa: E402
    SEL_MAIN,
    agreement,
    category_confusion,
    decision_categories,
    iter_expert_decisions,
    load_replays,
    score_replays,
    team_seat,
)


def _main_entry(*, seat, action, n_options=3, sel_type=SEL_MAIN, min_count=1,
                max_count=1, status="ACTIVE"):
    """One per seat record for a MAIN-style decision by `seat`.

    The option list is just indices (content is irrelevant to the validator, which
    only compares chosen indices), and yourIndex marks the deciding seat.
    """
    return {
        "action": action,
        "status": status,
        "observation": {
            "select": {
                "type": sel_type,
                "minCount": min_count,
                "maxCount": max_count,
                "option": list(range(n_options)),
            },
            "current": {"yourIndex": seat},
        },
    }


def _inactive():
    return {"action": [], "status": "INACTIVE",
            "observation": {"select": None, "current": None}}


def _step(active_entry, seat):
    """A two-seat step where `seat` is the acting entry and the other is inactive."""
    return [active_entry, _inactive()] if seat == 0 else [_inactive(), active_entry]


def _replay(steps, team_names=("kazuki0123", "aidy")):
    return {"info": {"TeamNames": list(team_names)}, "steps": steps}


# team_seat -----------------------------------------------------------------

def test_team_seat_resolves_single_expert():
    rep = _replay([], team_names=("aidy", "kazuki0123"))
    assert team_seat(rep, {"kazuki0123"}) == 1
    assert team_seat(rep, {"aidy"}) == 0


def test_team_seat_none_when_both_or_neither_match():
    rep = _replay([], team_names=("kazuki0123", "tonakaiiii"))
    assert team_seat(rep, {"kazuki0123", "tonakaiiii"}) is None  # ambiguous
    assert team_seat(rep, {"nobody"}) is None


def test_team_seat_none_on_malformed_info():
    assert team_seat({"info": {}}, {"x"}) is None
    assert team_seat({"info": {"TeamNames": ["only-one"]}}, {"only-one"}) is None
    assert team_seat({}, {"x"}) is None


# iter_expert_decisions -----------------------------------------------------

def test_iter_yields_only_expert_main_single_pick_multi_option():
    steps = [
        _step(_main_entry(seat=0, action=[2]), 0),          # scorable
        _step(_main_entry(seat=1, action=[1]), 1),          # wrong seat
        _step(_main_entry(seat=0, action=[0], n_options=1), 0),  # single option
        _step(_main_entry(seat=0, action=[0], sel_type=9), 0),   # not MAIN
        _step(_main_entry(seat=0, action=[0, 1], max_count=2), 0),  # multi-pick
        _step(_main_entry(seat=0, action=[]), 0),           # empty action
        _step(_main_entry(seat=0, action=[9]), 0),          # out of range
    ]
    got = list(iter_expert_decisions(_replay(steps), expert_index=0))
    assert len(got) == 1
    obs, idx = got[0]
    assert idx == 2
    assert obs["select"]["type"] == SEL_MAIN


def test_iter_skips_inactive_and_malformed_steps_without_raising():
    steps = [
        "not-a-step",
        [None, {"status": "ACTIVE"}],  # entry with no observation
        _step(_main_entry(seat=0, action=[1], status="INACTIVE"), 0),  # not active
        _step(_main_entry(seat=0, action=[1]), 0),  # the one real decision
    ]
    got = list(iter_expert_decisions(_replay(steps), expert_index=0))
    assert len(got) == 1 and got[0][1] == 1


# agreement -----------------------------------------------------------------

def _echo_pilot(obs):
    """A pilot that always returns option 1 (used to hit or miss known picks)."""
    return [1]


def test_agreement_partial_for_fixed_index_pilot():
    # A pilot that always picks index 1 matches only the decisions whose expert pick
    # was 1. Expert actions cycle 0,1,2,0,1,2 across six decisions, so two match.
    steps = [_step(_main_entry(seat=0, action=[i % 3]), 0) for i in range(6)]
    res = agreement(_replay(steps), _echo_pilot, expert_index=0)
    assert res == {"n": 6, "agree": 2, "agreement": 2 / 6}


def test_agreement_perfect_pilot_scores_one():
    # A pilot that echoes the played index scores 1.0. We simulate it by making the
    # pilot read the expert pick out of a side channel keyed on the option count.
    steps = [_step(_main_entry(seat=0, action=[2]), 0),
             _step(_main_entry(seat=0, action=[0]), 0)]
    rep = _replay(steps)
    picks = iter([2, 0])

    def oracle(obs):
        return [next(picks)]

    res = agreement(rep, oracle, expert_index=0)
    assert res["agreement"] == 1.0 and res["n"] == 2


def test_agreement_counts_raising_pilot_as_non_match():
    steps = [_step(_main_entry(seat=0, action=[1]), 0)]

    def boom(obs):
        raise RuntimeError("pilot blew up")

    res = agreement(_replay(steps), boom, expert_index=0)
    assert res == {"n": 1, "agree": 0, "agreement": 0.0}


def test_agreement_none_when_no_expert_decisions():
    res = agreement(_replay([]), _echo_pilot, expert_index=0)
    assert res == {"n": 0, "agree": 0, "agreement": None}


# score_replays -------------------------------------------------------------

def test_score_replays_aggregates_and_skips_no_expert_episodes():
    good = _replay(
        [_step(_main_entry(seat=1, action=[1]), 1)],
        team_names=("aidy", "kazuki0123"),
    )
    no_expert = _replay(
        [_step(_main_entry(seat=0, action=[1]), 0)],
        team_names=("aidy", "someone"),
    )
    res = score_replays(
        [(good, "g.json"), (no_expert, "n.json")],
        _echo_pilot,
        {"kazuki0123"},
    )
    assert res["episodes"] == 1
    assert res["skipped"] == 1
    assert res["n"] == 1 and res["agree"] == 1
    assert res["agreement"] == 1.0
    assert res["rows"][0]["episode"] == "g.json" and res["rows"][0]["seat"] == 1


# load_replays --------------------------------------------------------------

def test_load_replays_from_dir_respects_limit_and_skips_bad_json(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(_replay([])), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(_replay([])), encoding="utf-8")
    (tmp_path / "c.json").write_text("{not valid", encoding="utf-8")
    loaded = list(load_replays(tmp_path, limit=1))
    assert len(loaded) == 1  # limit honored, bad json never counted
    loaded_all = list(load_replays(tmp_path))
    # a and b parse, c is skipped
    assert len(loaded_all) == 2


# decision_categories / category_confusion ---------------------------------

# OptionType values that map to categories (api.py OptionType enum).
_OPT_PLAY = 7
_OPT_ATTACH = 8
_OPT_ATTACK = 13
_OPT_END = 14


def _typed_main_entry(*, seat, action, option_types):
    """A MAIN decision whose options carry real OptionType `type` fields.

    option_types is the per-option list of OptionType ints, so a test can pin what
    action category each index resolves to and check the expert-vs-pilot labeling.
    """
    return {
        "action": action,
        "status": "ACTIVE",
        "observation": {
            "select": {
                "type": SEL_MAIN,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": t} for t in option_types],
            },
            "current": {"yourIndex": seat},
        },
    }


def test_decision_categories_labels_expert_and_pilot_choice():
    # Options: [ATTACH, PLAY, ATTACK]. Expert played index 0 (ATTACH); the pilot
    # picks index 2 (ATTACK), a disagreement labeled by both categories.
    entry = _typed_main_entry(
        seat=0, action=[0], option_types=[_OPT_ATTACH, _OPT_PLAY, _OPT_ATTACK]
    )
    rep = _replay([_step(entry, 0)])
    rows = list(decision_categories(rep, lambda obs: [2], expert_index=0))
    assert rows == [("ATTACH", "ATTACK", False)]


def test_decision_categories_agreement_true_on_same_index():
    entry = _typed_main_entry(
        seat=0, action=[1], option_types=[_OPT_ATTACH, _OPT_PLAY, _OPT_ATTACK]
    )
    rep = _replay([_step(entry, 0)])
    rows = list(decision_categories(rep, lambda obs: [1], expert_index=0))
    assert rows == [("PLAY", "PLAY", True)]


def test_decision_categories_bad_pilot_answer_labeled_none():
    entry = _typed_main_entry(
        seat=0, action=[2], option_types=[_OPT_ATTACH, _OPT_PLAY, _OPT_ATTACK]
    )
    rep = _replay([_step(entry, 0)])

    def boom(obs):
        raise RuntimeError("nope")

    rows = list(decision_categories(rep, boom, expert_index=0))
    assert rows == [("ATTACK", "NONE", False)]


def test_category_confusion_aggregates_by_expert_category_and_matrix():
    # Two expert decisions: one ATTACH the pilot matches, one END the pilot answers
    # with ATTACK (a divergence). Confusion tallies per expert category and the
    # substitution matrix.
    e1 = _typed_main_entry(
        seat=0, action=[0], option_types=[_OPT_ATTACH, _OPT_ATTACK]
    )  # expert ATTACH at 0
    e2 = _typed_main_entry(
        seat=0, action=[1], option_types=[_OPT_ATTACK, _OPT_END]
    )  # expert END at 1
    rep = _replay([_step(e1, 0), _step(e2, 0)])

    # Pilot always picks index 0: matches e1 (ATTACH) but on e2 picks index 0 (ATTACK)
    # while the expert played END.
    conf = category_confusion([(rep, "r.json")], lambda obs: [0], {"kazuki0123"})
    assert conf["episodes"] == 1 and conf["skipped"] == 0
    assert conf["n"] == 2 and conf["agree"] == 1
    assert conf["by_expert"]["ATTACH"] == {"n": 1, "agree": 1}
    assert conf["by_expert"]["END"] == {"n": 1, "agree": 0}
    assert conf["matrix"]["ATTACH"] == {"ATTACH": 1}
    assert conf["matrix"]["END"] == {"ATTACK": 1}


def test_category_confusion_skips_no_expert_episode():
    entry = _typed_main_entry(seat=0, action=[0], option_types=[_OPT_ATTACH])
    rep = _replay([_step(entry, 0)], team_names=("aidy", "someone"))
    conf = category_confusion([(rep, "r.json")], lambda obs: [0], {"kazuki0123"})
    assert conf["episodes"] == 0 and conf["skipped"] == 1
    assert conf["n"] == 0 and conf["agreement"] is None


def test_load_replays_from_zip(tmp_path):
    zp = tmp_path / "eps.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("1.json", json.dumps(_replay([])))
        zf.writestr("2.json", json.dumps(_replay([])))
        zf.writestr("manifest.csv", "id,team\n")  # non-json ignored
    loaded = list(load_replays(zp))
    assert len(loaded) == 2
    assert all(name.endswith(".json") for _, name in loaded)
