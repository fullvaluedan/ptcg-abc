"""Tests for analysis/replay_trace.py, the shared resolved-decision spine (U32).

Covers the decision primitives lifted here (team_seat, _played_index, the MAIN
single-pick gate), the new option-to-card/attack resolution, and the canonical
md5 episode split. Every fixture is a hand-built replay dict so the spine is
exercised without the card engine, matching how the census and validator test.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.replay_trace import (  # noqa: E402
    AREA_DECK,
    AREA_HAND,
    CTX_TO_ACTIVE,
    OPT_CATEGORY,
    SEL_CARD,
    SEL_MAIN,
    episode_bucket,
    episode_id_of,
    iter_expert_card_decisions,
    iter_expert_decisions,
    iter_resolved_decisions,
    option_card_id,
    resolve_option,
    split_of,
    team_seat,
)


# fixtures ------------------------------------------------------------------

def _main_entry(*, seat, action, options=None, n_options=3, sel_type=SEL_MAIN,
                min_count=1, max_count=1, status="ACTIVE", deck=None, players=None,
                context=None):
    """One ACTIVE seat record for a MAIN decision by `seat`.

    `options` supplies real option dicts (for resolution tests); otherwise a bare
    n-option list of index placeholders is used (index-only gating tests).
    """
    opt = options if options is not None else list(range(n_options))
    sel = {"type": sel_type, "minCount": min_count, "maxCount": max_count, "option": opt}
    if deck is not None:
        sel["deck"] = deck
    if context is not None:
        sel["context"] = context
    current = {"yourIndex": seat}
    if players is not None:
        current["players"] = players
    return {
        "action": action,
        "status": status,
        "observation": {"select": sel, "current": current},
    }


def _inactive():
    return {"action": [], "status": "INACTIVE",
            "observation": {"select": None, "current": None}}


def _step(active_entry, seat):
    return [active_entry, _inactive()] if seat == 0 else [_inactive(), active_entry]


def _replay(steps, team_names=("kazuki0123", "aidy")):
    return {"info": {"TeamNames": list(team_names)}, "steps": steps}


# team_seat / _played_index / gating (lifted, must still behave) -------------

def test_team_seat_resolves_single_expert():
    rep = _replay([], team_names=("aidy", "kazuki0123"))
    assert team_seat(rep, {"kazuki0123"}) == 1
    assert team_seat(rep, {"nobody"}) is None


def test_iter_yields_only_scorable_main_single_pick():
    steps = [
        _step(_main_entry(seat=0, action=[2]), 0),                 # scorable
        _step(_main_entry(seat=1, action=[1]), 1),                 # wrong seat
        _step(_main_entry(seat=0, action=[0], n_options=1), 0),    # single option
        _step(_main_entry(seat=0, action=[0], sel_type=9), 0),     # not MAIN
        _step(_main_entry(seat=0, action=[0, 1], max_count=2), 0), # multi-pick
        _step(_main_entry(seat=0, action=[9]), 0),                 # out of range
    ]
    got = list(iter_expert_decisions(_replay(steps), expert_index=0))
    assert len(got) == 1
    obs, idx = got[0]
    assert idx == 2 and obs["select"]["type"] == SEL_MAIN


def test_iter_skips_malformed_without_raising():
    steps = ["not-a-step", [None, {"status": "ACTIVE"}],
             _step(_main_entry(seat=0, action=[1]), 0)]
    got = list(iter_expert_decisions(_replay(steps), expert_index=0))
    assert len(got) == 1 and got[0][1] == 1


def test_iter_card_yields_only_scorable_promote_in_contexts():
    steps = [
        _step(_main_entry(seat=0, action=[1], sel_type=SEL_CARD,
                           context=CTX_TO_ACTIVE), 0),                      # scorable
        _step(_main_entry(seat=1, action=[0], sel_type=SEL_CARD,
                           context=CTX_TO_ACTIVE), 1),                      # wrong seat
        _step(_main_entry(seat=0, action=[0], sel_type=SEL_CARD,
                           context=CTX_TO_ACTIVE, n_options=1), 0),         # single option
        _step(_main_entry(seat=0, action=[0], sel_type=SEL_MAIN,
                           context=CTX_TO_ACTIVE), 0),                      # not CARD
        _step(_main_entry(seat=0, action=[0], sel_type=SEL_CARD,
                           context=99), 0),                                 # wrong context
        _step(_main_entry(seat=0, action=[0, 1], sel_type=SEL_CARD,
                           context=CTX_TO_ACTIVE, max_count=2), 0),         # multi-pick
        _step(_main_entry(seat=0, action=[9], sel_type=SEL_CARD,
                           context=CTX_TO_ACTIVE), 0),                      # out of range
    ]
    got = list(
        iter_expert_card_decisions(_replay(steps), expert_index=0, contexts={CTX_TO_ACTIVE})
    )
    assert len(got) == 1
    obs, idx = got[0]
    assert idx == 1 and obs["select"]["context"] == CTX_TO_ACTIVE


def test_iter_card_default_min_counts_excludes_optional_pick():
    # An optional "you may search" effect reports minCount 0; the {1}-only
    # default (a forced pick, e.g. a post-knockout promote) must not count it.
    steps = [
        _step(_main_entry(seat=0, action=[0], sel_type=SEL_CARD,
                           context=CTX_TO_ACTIVE, min_count=0), 0),
    ]
    got = list(
        iter_expert_card_decisions(_replay(steps), expert_index=0, contexts={CTX_TO_ACTIVE})
    )
    assert got == []


def test_iter_card_min_counts_param_includes_optional_pick():
    steps = [
        _step(_main_entry(seat=0, action=[0], sel_type=SEL_CARD,
                           context=CTX_TO_ACTIVE, min_count=0), 0),
    ]
    got = list(
        iter_expert_card_decisions(
            _replay(steps), expert_index=0, contexts={CTX_TO_ACTIVE},
            min_counts=frozenset({0, 1}),
        )
    )
    assert len(got) == 1 and got[0][1] == 0


def test_iter_card_skips_malformed_without_raising():
    steps = ["not-a-step", [None, {"status": "ACTIVE"}],
              _step(_main_entry(seat=0, action=[1], sel_type=SEL_CARD,
                                 context=CTX_TO_ACTIVE), 0)]
    got = list(
        iter_expert_card_decisions(_replay(steps), expert_index=0, contexts={CTX_TO_ACTIVE})
    )
    assert len(got) == 1 and got[0][1] == 1


# option resolution ---------------------------------------------------------

def test_resolve_option_category_and_attack_id():
    end = resolve_option({"type": 14}, {}, {})
    assert end["category"] == "END" and end["card_id"] is None
    atk = resolve_option({"type": 13, "attackId": 777}, {}, {})
    assert atk["category"] == "ATTACK" and atk["attack_id"] == 777


def test_resolve_option_unknown_type_is_other():
    r = resolve_option({"type": 999}, {}, {})
    assert r["category"] == "OTHER"
    assert OPT_CATEGORY.get(999) is None


def test_resolve_option_non_dict_is_safe():
    r = resolve_option("nope", {}, {})
    assert r == {"type": None, "category": "OTHER", "card_id": None, "attack_id": None}


def test_option_card_id_direct_cardid():
    assert option_card_id({"type": 7, "cardId": 42}, {}, {}) == 42


def test_option_card_id_from_deck_area():
    sel = {"deck": [{"id": 10}, {"id": 20}, {"id": 30}]}
    opt = {"type": 7, "area": AREA_DECK, "index": 1}
    assert option_card_id(opt, sel, {}) == 20


def test_option_card_id_from_hand_area_of_deciding_seat():
    obs = {"current": {"yourIndex": 1, "players": [
        {"hand": [{"id": 111}]},
        {"hand": [{"id": 222}, {"id": 333}]},
    ]}}
    opt = {"type": 7, "area": AREA_HAND, "index": 1}  # playerIndex defaults to yourIndex
    assert option_card_id(opt, {}, obs) == 333


def test_option_card_id_out_of_range_and_missing_are_none():
    assert option_card_id({"type": 7, "area": AREA_DECK, "index": 5},
                          {"deck": [{"id": 1}]}, {}) is None
    assert option_card_id({"type": 7, "area": AREA_HAND}, {}, {}) is None  # no index


def test_iter_resolved_decisions_record_shape():
    options = [
        {"type": 8, "cardId": 5},            # ATTACH card 5
        {"type": 13, "attackId": 900},       # ATTACK 900  (played)
        {"type": 14},                        # END
    ]
    entry = _main_entry(seat=0, action=[1], options=options)
    rec = list(iter_resolved_decisions(_replay([_step(entry, 0)]), 0))
    assert len(rec) == 1
    r = rec[0]
    assert r["played_index"] == 1
    assert r["played"]["category"] == "ATTACK" and r["played"]["attack_id"] == 900
    assert [o["category"] for o in r["options"]] == ["ATTACH", "ATTACK", "END"]
    assert r["options"][0]["card_id"] == 5


# md5 episode split ---------------------------------------------------------

def test_episode_id_of_strips_dir_and_suffix():
    assert episode_id_of("12345.json") == "12345"
    assert episode_id_of("some/dir/12345.json") == "12345"
    assert episode_id_of("some\\dir\\12345.json") == "12345"
    assert episode_id_of("12345") == "12345"


def test_episode_bucket_deterministic_and_in_range():
    b = episode_bucket("999")
    assert 0 <= b < 100
    assert episode_bucket("999") == b                       # stable across calls
    assert episode_bucket("999.json") == b                  # id, not the path
    assert episode_bucket("path/999.json") == b


def test_split_of_partitions_by_bucket():
    # split is a pure function of the bucket; the boundary is test_pct exclusive.
    assert split_of("777", test_pct=0) == "train"           # nothing is test at 0
    assert split_of("777", test_pct=100) == "test"          # everything is test at 100
    b = episode_bucket("abc")
    assert split_of("abc", test_pct=b) == "train"           # bucket == pct -> train
    assert split_of("abc", test_pct=b + 1) == "test"        # bucket < pct  -> test
