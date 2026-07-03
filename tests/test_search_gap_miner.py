"""Tests for analysis/search_gap_miner.py.

Uses the real offline card catalog (like tests/test_heuristic.py) for the
is_basic / evolution classification, and an injected pilot for agreement so no
real search rule needs to be exercised end to end.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.replay_trace import SEL_CARD  # noqa: E402
from analysis.search_gap_miner import search_gap_rows, summarize  # noqa: E402

# Real card ids from the bundled offline catalog (agents.heuristics.card_index),
# mirroring tests/test_heuristic.py's own constants.
SNOVER = 722  # Basic Pokemon
MEGA_ABOMASNOW = 723  # evolvesFrom "Snover"
BASIC_ENERGY = 3  # not a Pokemon at all

CTX_TO_HAND = 7
CTX_TO_BENCH = 5


def _deck_opt(idx):
    return {"type": 3, "area": 1, "index": idx}  # AREA_DECK == 1


def _obs(*, deck_ids, bench, active=None, context=CTX_TO_HAND, your_index=0, min_count=1):
    options = [_deck_opt(i) for i in range(len(deck_ids))]
    me = {"active": [active] if active else [], "bench": bench}
    players = [me, {"active": [], "bench": []}]
    if your_index == 1:
        players = [players[1], players[0]]
    return {
        "select": {
            "type": SEL_CARD,
            "context": context,
            "minCount": min_count,
            "maxCount": 1,
            "option": options,
            "deck": [{"id": cid} for cid in deck_ids],
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


def test_agree_when_pilot_matches_expert_fetch():
    obs = _obs(deck_ids=[SNOVER, BASIC_ENERGY], bench=[{"id": SNOVER}, {"id": SNOVER}])
    rep = _replay([_step(_entry(action=[0], obs=obs), 0)])
    rows = search_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [0])
    assert len(rows) == 1
    assert rows[0]["agree"] is True
    assert rows[0]["played_is_basic"] is True


def test_disagree_when_pilot_picks_index_zero_but_expert_fetches_evolution():
    # Bench already has a Snover in play; the expert fetches the evolution
    # instead of the pilot's first-legal Basic Energy at index 0.
    obs = _obs(
        deck_ids=[BASIC_ENERGY, MEGA_ABOMASNOW],
        bench=[{"id": SNOVER}],
    )
    rep = _replay([_step(_entry(action=[1], obs=obs), 0)])
    rows = search_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [0])
    assert len(rows) == 1
    row = rows[0]
    assert row["agree"] is False
    assert row["played_is_basic"] is False
    assert row["played_is_evolution_for_board"] is True
    assert row["played_is_index_zero"] is False


def test_evolution_for_board_checks_active_too():
    obs = _obs(
        deck_ids=[MEGA_ABOMASNOW, BASIC_ENERGY],
        bench=[],
        active={"id": SNOVER},
    )
    rep = _replay([_step(_entry(action=[0], obs=obs), 0)])
    rows = search_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [0])
    assert rows[0]["played_is_evolution_for_board"] is True


def test_bench_thin_flag_tracks_my_bench_count():
    thin_obs = _obs(deck_ids=[SNOVER, BASIC_ENERGY], bench=[])
    full_obs = _obs(deck_ids=[SNOVER, BASIC_ENERGY], bench=[{"id": SNOVER}, {"id": SNOVER}])
    rep = _replay(
        [
            _step(_entry(action=[0], obs=thin_obs), 0),
            _step(_entry(action=[0], obs=full_obs), 0),
        ]
    )
    rows = search_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [0])
    assert len(rows) == 2
    assert rows[0]["bench_thin"] is True
    assert rows[1]["bench_thin"] is False


def test_includes_optional_min_count_zero_searches():
    # Most real search effects are "you may search...", reported as minCount 0
    # even though the expert picked one card; these must not be dropped.
    obs = _obs(deck_ids=[SNOVER, BASIC_ENERGY], bench=[], min_count=0)
    rep = _replay([_step(_entry(action=[0], obs=obs), 0)])
    rows = search_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [0])
    assert len(rows) == 1
    assert rows[0]["played_is_basic"] is True


def test_skips_decisions_without_a_deck_reveal():
    obs = _obs(deck_ids=[SNOVER, BASIC_ENERGY], bench=[])
    obs["select"]["deck"] = None
    rep = _replay([_step(_entry(action=[0], obs=obs), 0)])
    rows = search_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [0])
    assert rows == []


def test_skips_contexts_outside_deck_search():
    obs = _obs(deck_ids=[SNOVER, BASIC_ENERGY], bench=[], context=4)  # TO_ACTIVE, a different decision
    rep = _replay([_step(_entry(action=[0], obs=obs), 0)])
    rows = search_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [0])
    assert rows == []


def test_skips_episodes_with_no_expert_seat():
    obs = _obs(deck_ids=[SNOVER, BASIC_ENERGY], bench=[])
    rep = _replay([_step(_entry(action=[0], obs=obs), 0)], team_names=("aidy", "someone"))
    rows = search_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=lambda o: [0])
    assert rows == []


def test_pilot_exception_counts_as_disagreement_not_a_crash():
    obs = _obs(deck_ids=[SNOVER, BASIC_ENERGY], bench=[])
    rep = _replay([_step(_entry(action=[0], obs=obs), 0)])

    def boom(_obs):
        raise RuntimeError("pilot blew up")

    rows = search_gap_rows([(rep, "r.json")], {"kazuki0123"}, pilot_choose=boom)
    assert len(rows) == 1
    assert rows[0]["agree"] is False


# summarize --------------------------------------------------------------------


def test_summarize_splits_thin_vs_not_thin():
    rows = [
        {"agree": True, "bench_thin": True, "played_is_basic": True,
         "played_is_evolution_for_board": False, "played_is_index_zero": True},
        {"agree": False, "bench_thin": False, "played_is_basic": False,
         "played_is_evolution_for_board": True, "played_is_index_zero": False},
        {"agree": False, "bench_thin": False, "played_is_basic": False,
         "played_is_evolution_for_board": False, "played_is_index_zero": False},
    ]
    summary = summarize(rows)
    assert summary["n"] == 3
    assert summary["overall"]["n"] == 3
    assert summary["bench_thin"]["n"] == 1
    assert summary["bench_thin"]["agree_rate"] == 1.0
    assert summary["not_thin"]["n"] == 2
    assert summary["not_thin"]["agree_rate"] == 0.0
    assert summary["not_thin"]["evolution_rate"] == 0.5


def test_summarize_empty_rows():
    summary = summarize([])
    assert summary["n"] == 0
    assert summary["overall"]["n"] == 0
    assert summary["bench_thin"]["n"] == 0
    assert summary["not_thin"]["n"] == 0
