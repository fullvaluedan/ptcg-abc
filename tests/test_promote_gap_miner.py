"""Tests for analysis/promote_gap_miner.py.

Pure over hand-built replay dicts and an injected pilot callable; no native
engine, no card data, no competition dataset.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agents.heuristics import card_index  # noqa: E402
from analysis.matchup_delta import matchup_score  # noqa: E402
from analysis.replay_trace import AREA_BENCH, CTX_TO_ACTIVE, SEL_CARD  # noqa: E402
from analysis.promote_gap_miner import (  # noqa: E402
    _bench_energy_count,
    _bench_hp_ratio,
    promote_gap_rows,
    summarize,
)


def _mon(hp, max_hp, energy=0, card_id=None):
    return {"id": card_id, "hp": hp, "maxHp": max_hp, "energy": [1] * energy}


def _bench_opt(idx):
    return {"type": 3, "area": AREA_BENCH, "index": idx}


def _obs(*, bench_hps, your_index=0, opp_id=None):
    options = [_bench_opt(i) for i in range(len(bench_hps))]
    players = [
        {"active": [], "bench": [_mon(*hp) for hp in bench_hps]},
        {"active": [_mon(100, 100, card_id=opp_id)], "bench": []},
    ]
    return {
        "select": {
            "type": SEL_CARD,
            "context": CTX_TO_ACTIVE,
            "minCount": 1,
            "maxCount": 1,
            "option": options,
        },
        "current": {"yourIndex": your_index, "players": players},
    }


def _weak_pair():
    """(attacker_id, defender_id) where defender.weakness == attacker.energyType,
    derived from the real bundled catalog (mirrors tests/test_matchup_delta.py)."""
    cards = card_index()
    for defender_id, dfn in cards.items():
        if dfn.weakness is None:
            continue
        for attacker_id, atk in cards.items():
            if atk.energyType == dfn.weakness and attacker_id != defender_id:
                return attacker_id, defender_id
    raise AssertionError("no weakness pair found in the bundled catalog")


def _entry(*, action, obs, status="ACTIVE"):
    return {"action": action, "status": status, "observation": obs}


def _step(entry, seat):
    other = {"action": [], "status": "INACTIVE", "observation": {"select": None, "current": None}}
    return [entry, other] if seat == 0 else [other, entry]


def _replay(steps, team_names=("kazuki0123", "aidy")):
    return {"info": {"TeamNames": list(team_names)}, "steps": steps}


# promote_gap_rows -----------------------------------------------------------


def test_agree_when_pilot_matches_expert_pick():
    obs = _obs(bench_hps=[(50, 100), (90, 90)])
    rep = _replay([_step(_entry(action=[1], obs=obs), 0)])
    rows = promote_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [1])
    assert len(rows) == 1
    assert rows[0]["agree"] is True
    assert rows[0]["played_hp_ratio"] == 1.0
    assert rows[0]["played_is_max_hp_ratio"] is True
    assert rows[0]["played_is_index_zero"] is False


def test_disagree_when_pilot_picks_first_legal_but_expert_picks_healthier():
    # first_legal-style pilot always answers index 0; the expert promotes the
    # healthier bench mon at index 1 instead.
    obs = _obs(bench_hps=[(10, 100), (90, 90)])
    rep = _replay([_step(_entry(action=[1], obs=obs), 0)])
    rows = promote_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [0])
    assert len(rows) == 1
    row = rows[0]
    assert row["agree"] is False
    assert row["played_is_max_hp_ratio"] is True
    assert row["played_is_index_zero"] is False


def test_max_energy_flag_identifies_the_most_invested_bench_mon():
    # index 0 has the higher hp ratio, index 1 has the most energy invested; the
    # expert promotes index 1, so max-energy tracks the real pick where
    # max-hp-ratio does not.
    obs = _obs(bench_hps=[(90, 100, 0), (50, 100, 2)])
    rep = _replay([_step(_entry(action=[1], obs=obs), 0)])
    rows = promote_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [1])
    assert rows[0]["played_is_max_energy"] is True
    assert rows[0]["played_is_max_hp_ratio"] is False


def test_best_matchup_flag_identifies_expert_pick_by_type():
    # index 0 is a neutral matchup, index 1 hits the opponent's weakness; the
    # expert promotes index 1 even though it has less energy and a lower hp
    # ratio, so matchup (not hp or energy) is what actually explains the pick.
    attacker_id, defender_id = _weak_pair()
    obs = _obs(
        bench_hps=[(90, 100, 2, None), (10, 100, 0, attacker_id)],
        opp_id=defender_id,
    )
    rep = _replay([_step(_entry(action=[1], obs=obs), 0)])
    rows = promote_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [0])
    row = rows[0]
    assert row["played_is_best_matchup"] is True
    assert row["played_matchup_score"] == matchup_score(attacker_id, defender_id)
    assert row["played_matchup_score"] > 0
    assert row["played_is_max_hp_ratio"] is False
    assert row["played_is_max_energy"] is False


def test_matchup_fields_none_when_opponent_active_unknown():
    obs = _obs(bench_hps=[(50, 100), (90, 90)], opp_id=None)
    rep = _replay([_step(_entry(action=[1], obs=obs), 0)])
    rows = promote_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [1])
    assert rows[0]["played_matchup_score"] is None
    assert rows[0]["played_is_best_matchup"] is False


def test_skips_episodes_with_no_expert_seat():
    obs = _obs(bench_hps=[(50, 100), (90, 90)])
    rep = _replay([_step(_entry(action=[1], obs=obs), 0)], team_names=("aidy", "someone"))
    rows = promote_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [1])
    assert rows == []


def test_only_scores_the_to_active_context():
    obs = _obs(bench_hps=[(50, 100), (90, 90)])
    obs["select"]["context"] = 3  # SWITCH, a different decision entirely
    rep = _replay([_step(_entry(action=[1], obs=obs), 0)])
    rows = promote_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [1])
    assert rows == []


def test_pilot_exception_counts_as_disagreement_not_a_crash():
    obs = _obs(bench_hps=[(50, 100), (90, 90)])
    rep = _replay([_step(_entry(action=[1], obs=obs), 0)])

    def boom(_obs):
        raise RuntimeError("pilot blew up")

    rows = promote_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=boom)
    assert len(rows) == 1
    assert rows[0]["agree"] is False


# _bench_hp_ratio / _bench_energy_count --------------------------------------


def test_bench_hp_ratio_none_on_missing_or_out_of_range():
    assert _bench_hp_ratio([], 0) is None
    assert _bench_hp_ratio([{"hp": 0, "maxHp": 0}], 0) is None
    assert _bench_hp_ratio([{"hp": 30, "maxHp": 60}], 0) == 0.5


def test_bench_energy_count_none_on_out_of_range_zero_when_missing():
    assert _bench_energy_count([], 0) is None
    assert _bench_energy_count([{"hp": 1, "maxHp": 1}], 0) == 0
    assert _bench_energy_count([{"hp": 1, "maxHp": 1, "energy": [1, 2]}], 0) == 2


# summarize --------------------------------------------------------------------


def test_summarize_rates():
    rows = [
        {"agree": True, "played_is_max_hp_ratio": True, "played_is_max_energy": False,
         "played_is_best_matchup": True, "played_is_index_zero": True},
        {"agree": False, "played_is_max_hp_ratio": True, "played_is_max_energy": True,
         "played_is_best_matchup": False, "played_is_index_zero": False},
        {"agree": False, "played_is_max_hp_ratio": False, "played_is_max_energy": False,
         "played_is_best_matchup": False, "played_is_index_zero": False},
        {"agree": False, "played_is_max_hp_ratio": False, "played_is_max_energy": False,
         "played_is_best_matchup": False, "played_is_index_zero": False},
    ]
    summary = summarize(rows)
    assert summary["n"] == 4
    assert summary["agree_rate"] == 0.25
    assert summary["max_hp_ratio_rate"] == 0.5
    assert summary["max_energy_rate"] == 0.25
    assert summary["best_matchup_rate"] == 0.25
    assert summary["index_zero_rate"] == 0.25


def test_summarize_empty_rows():
    summary = summarize([])
    assert summary["n"] == 0
    assert summary["agree_rate"] == 0.0
