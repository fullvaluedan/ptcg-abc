"""Tests for analysis/retreat_gap_miner.py.

Pure over hand-built replay dicts and an injected pilot callable; no native
engine, no card data, no competition dataset. Each test pins one bucket
(agree / preempted / threshold_miss) with a state simple enough to hand-verify
against agents.heuristics.should_retreat's own real HP-ratio rule.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.replay_trace import SEL_MAIN  # noqa: E402
from analysis.retreat_gap_miner import (  # noqa: E402
    _hp_ratio,
    retreat_gap_rows,
    summarize,
)

# OptionType values (api.py OptionType enum) used by the fixtures below.
_OPT_EVOLVE = 9
_OPT_RETREAT = 12
_OPT_ATTACK = 13


def _mon(hp, max_hp):
    return {"hp": hp, "maxHp": max_hp}


def _obs(*, option_types, players, your_index=0):
    return {
        "select": {
            "type": SEL_MAIN,
            "minCount": 1,
            "maxCount": 1,
            "option": [{"type": t} for t in option_types],
        },
        "current": {"yourIndex": your_index, "players": players},
    }


def _entry(*, action, obs, status="ACTIVE"):
    return {"action": action, "status": status, "observation": obs}


def _step(entry, seat):
    other = {"action": [], "status": "INACTIVE", "observation": {"select": None, "current": None}}
    return [entry, other] if seat == 0 else [other, entry]


def _replay(steps, team_names=("kazuki0123", "aidy")):
    return {"info": {"TeamNames": list(team_names)}, "steps": steps}


def _players(active_hp, active_max, bench_hps):
    return [
        {
            "active": [_mon(active_hp, active_max)],
            "bench": [_mon(hp, mx) for hp, mx in bench_hps],
        },
        {"active": [_mon(100, 100)], "bench": []},
    ]


# retreat_gap_rows ------------------------------------------------------------


def test_agree_when_pilot_matches_expert_retreat():
    # Active low HP (20/100 = 0.20 < RETREAT_HP_RATIO 0.34), healthier bench
    # exists: the real rule says retreat, and the injected pilot echoes it.
    obs = _obs(
        option_types=[_OPT_ATTACK, _OPT_RETREAT],
        players=_players(20, 100, [(90, 90)]),
    )
    rep = _replay([_step(_entry(action=[1], obs=obs), 0)])
    rows = retreat_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [1])
    assert len(rows) == 1
    assert rows[0]["bucket"] == "agree"
    assert rows[0]["active_hp_ratio"] == 0.20
    assert rows[0]["bench_best_hp_ratio"] == 1.0


def test_preempted_when_rule_agrees_but_pilot_picks_something_else():
    # Same low-HP state (rule says retreat), but the pilot's injected answer is
    # a different category (EVOLVE), simulating a higher-priority preemption.
    obs = _obs(
        option_types=[_OPT_EVOLVE, _OPT_RETREAT],
        players=_players(20, 100, [(90, 90)]),
    )
    rep = _replay([_step(_entry(action=[1], obs=obs), 0)])
    rows = retreat_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [0])
    assert len(rows) == 1
    row = rows[0]
    assert row["bucket"] == "preempted"
    assert row["pilot_category"] == "EVOLVE"


def test_threshold_miss_when_rule_disagrees_on_the_real_state():
    # Active at full HP: should_retreat's own ratio gate (hp/mx > RETREAT_HP_RATIO)
    # returns False regardless of what the pilot picks, so a real expert retreat
    # here is a genuine rule gap, not an ordering artifact.
    obs = _obs(
        option_types=[_OPT_ATTACK, _OPT_RETREAT],
        players=_players(100, 100, [(90, 90)]),
    )
    rep = _replay([_step(_entry(action=[1], obs=obs), 0)])
    rows = retreat_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [0])
    assert len(rows) == 1
    row = rows[0]
    assert row["bucket"] == "threshold_miss"
    assert row["pilot_category"] == "ATTACK"
    assert row["active_hp_ratio"] == 1.0


def test_threshold_miss_when_no_healthier_bench_exists():
    # Active is hurt (below the ratio gate) but no bench mon is healthier, so the
    # rule's second condition fails too: still threshold_miss either way.
    obs = _obs(
        option_types=[_OPT_ATTACK, _OPT_RETREAT],
        players=_players(20, 100, [(10, 90)]),
    )
    rep = _replay([_step(_entry(action=[1], obs=obs), 0)])
    rows = retreat_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [0])
    assert rows[0]["bucket"] == "threshold_miss"


def test_only_real_retreat_decisions_are_scored():
    # An ATTACK decision (expert plays index 0, which is ATTACK) is not a RETREAT
    # decision at all and must be skipped entirely.
    obs = _obs(
        option_types=[_OPT_ATTACK, _OPT_RETREAT],
        players=_players(20, 100, [(90, 90)]),
    )
    rep = _replay([_step(_entry(action=[0], obs=obs), 0)])
    rows = retreat_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [0])
    assert rows == []


def test_skips_episodes_with_no_expert_seat():
    obs = _obs(option_types=[_OPT_ATTACK, _OPT_RETREAT], players=_players(20, 100, [(90, 90)]))
    rep = _replay([_step(_entry(action=[1], obs=obs), 0)], team_names=("aidy", "someone"))
    rows = retreat_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [1])
    assert rows == []


def test_pilot_exception_counts_as_no_match_not_a_crash():
    obs = _obs(
        option_types=[_OPT_ATTACK, _OPT_RETREAT],
        players=_players(100, 100, [(90, 90)]),
    )
    rep = _replay([_step(_entry(action=[1], obs=obs), 0)])

    def boom(_obs):
        raise RuntimeError("pilot blew up")

    rows = retreat_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=boom)
    assert len(rows) == 1
    assert rows[0]["bucket"] == "threshold_miss"
    assert rows[0]["pilot_category"] == "NONE"


# _hp_ratio -------------------------------------------------------------------


def test_hp_ratio_none_on_missing_or_zero_max():
    assert _hp_ratio(None) is None
    assert _hp_ratio({"hp": 0, "maxHp": 0}) is None
    assert _hp_ratio({"hp": 30, "maxHp": 60}) == 0.5


# summarize --------------------------------------------------------------------


def test_summarize_counts_buckets_and_bins_threshold_miss_ratios():
    rows = [
        {"bucket": "agree", "active_hp_ratio": 0.2},
        {"bucket": "preempted", "active_hp_ratio": 0.2},
        {"bucket": "threshold_miss", "active_hp_ratio": 0.95},
        {"bucket": "threshold_miss", "active_hp_ratio": 0.91},
        {"bucket": "threshold_miss", "active_hp_ratio": 0.5},
        {"bucket": "threshold_miss", "active_hp_ratio": None},
    ]
    summary = summarize(rows)
    assert summary["n"] == 6
    assert summary["counts"] == {"agree": 1, "preempted": 1, "threshold_miss": 4}
    assert summary["threshold_miss_hp_ratio_bins"] == {0.9: 2, 0.5: 1}


def test_summarize_empty_rows():
    summary = summarize([])
    assert summary["n"] == 0
    assert summary["counts"] == {"agree": 0, "preempted": 0, "threshold_miss": 0}
    assert summary["threshold_miss_hp_ratio_bins"] == {}
