"""U6 scout and loss classifier tests.

Replay parsing and bucketing are exercised on synthetic replays shaped exactly
like env.toJSON output, plus one real local match. The Kaggle CLI wrapper is
exercised only on its graceful failure paths so the suite stays fully offline.
"""
import json

from analysis.loss_classifier import (
    BUCKETS,
    classify_batch,
    classify_loss,
    parse_replay,
)
from tools import scout


def _decision(player, turn, n_options, my_prize, opp_prize, overage):
    """One per player record as it appears inside a replay step."""
    return {
        "action": [0],
        "status": "ACTIVE",
        "reward": 0,
        "observation": {
            "remainingOverageTime": overage,
            "select": {"option": list(range(n_options)), "minCount": 1, "maxCount": 1},
            "current": {
                "yourIndex": player,
                "turn": turn,
                "players": [
                    {"prize": [None] * (my_prize if player == 0 else opp_prize)},
                    {"prize": [None] * (opp_prize if player == 0 else my_prize)},
                ],
            },
        },
    }


def _inactive():
    return {"action": [], "status": "INACTIVE", "reward": 0, "observation": {"select": None, "current": None}}


def _replay(rows, rewards):
    """Build a replay from rows of (player, turn, n_options, my_prize, opp_prize, overage).

    Each row becomes a step with the acting player's record in their seat and an
    inactive placeholder in the other, matching env.toJSON's two entry steps.
    """
    steps = [[_inactive(), _inactive()]]  # deck handshake, both select None
    for player, turn, n_opt, myp, oppp, ov in rows:
        step = [None, None]
        step[player] = _decision(player, turn, n_opt, myp, oppp, ov)
        step[1 - player] = _inactive()
        steps.append(step)
    return {"steps": steps, "rewards": rewards}


def test_parse_outcome_and_records():
    rep = _replay(
        [(0, 1, 3, 6, 6, 600.0), (0, 3, 5, 5, 4, 599.0)],
        rewards=[1, -1],
    )
    dg = parse_replay(rep, our_index=0)
    assert dg["outcome"] == "win"
    assert dg["n_decisions"] == 2
    assert len(dg["our_decisions"]) == 2
    last = dg["our_decisions"][-1]
    assert last["my_prize"] == 5 and last["opp_prize"] == 4
    assert last["n_options"] == 5 and last["turn"] == 3
    # decision_time is the drop in our own overage bank since the prior decision.
    assert abs(last["decision_time"] - 1.0) < 1e-9


def test_inactive_stale_select_not_counted():
    # The engine leaves an inactive seat a stale non null select. Only the seat
    # marked ACTIVE is a real decision, so the stale one must not be recorded.
    active = _decision(1, 2, 3, 6, 6, 600.0)
    stale = _decision(0, 1, 2, 6, 6, 600.0)
    stale["status"] = "INACTIVE"  # stale select, not acting
    rep = {"steps": [[_inactive(), _inactive()], [stale, active]], "rewards": [-1, 1]}
    dg = parse_replay(rep, our_index=1)
    assert dg["n_decisions"] == 1
    assert dg["our_decisions"][0]["player"] == 1


def test_outcome_from_our_index():
    rep = _replay([(1, 2, 2, 5, 6, 600.0)], rewards=[1, -1])
    assert parse_replay(rep, our_index=1)["outcome"] == "loss"
    assert parse_replay(rep, our_index=0)["outcome"] == "win"


def test_classify_steamroll_is_deck_matchup():
    # We lost having taken only one prize (five still remaining): a blowout.
    rep = _replay(
        [(0, 1, 3, 6, 6, 600.0), (0, 5, 4, 5, 1, 599.5)],
        rewards=[-1, 1],
    )
    assert classify_loss(parse_replay(rep)) == "deck_matchup"


def test_classify_close_is_endgame_misplay():
    # We needed one more prize and lost: a near win that slipped.
    rep = _replay(
        [(0, 4, 3, 3, 2, 600.0), (0, 8, 4, 1, 1, 599.0)],
        rewards=[-1, 1],
    )
    assert classify_loss(parse_replay(rep)) == "endgame_misplay"


def test_classify_slow_search_wins_over_board():
    # A single slow move flags timing even though the board looks like a misplay.
    rep = _replay(
        [(0, 4, 3, 2, 2, 600.0), (0, 8, 4, 1, 1, 585.0)],  # 15s on one move
        rewards=[-1, 1],
    )
    assert classify_loss(parse_replay(rep)) == "slow_search"


def test_classify_low_bank_is_slow_search():
    rep = _replay(
        [(0, 4, 3, 3, 3, 200.0), (0, 8, 4, 3, 1, 40.0)],  # ended under the 60s bank floor
        rewards=[-1, 1],
    )
    assert classify_loss(parse_replay(rep)) == "slow_search"


def test_classify_middling_is_bad_determinization():
    rep = _replay(
        [(0, 3, 3, 4, 3, 600.0), (0, 7, 4, 3, 1, 599.0)],
        rewards=[-1, 1],
    )
    assert classify_loss(parse_replay(rep)) == "bad_determinization"


def test_classify_returns_none_for_non_loss():
    rep = _replay([(0, 1, 3, 5, 6, 600.0)], rewards=[1, -1])
    assert classify_loss(parse_replay(rep)) is None


def test_classify_batch_ranks_buckets():
    steamroll = parse_replay(_replay([(0, 5, 3, 5, 1, 600.0)], rewards=[-1, 1]))
    close = parse_replay(_replay([(0, 8, 3, 1, 1, 599.0)], rewards=[-1, 1]))
    another_steamroll = parse_replay(_replay([(0, 5, 3, 6, 0, 600.0)], rewards=[-1, 1]))
    win = parse_replay(_replay([(0, 3, 3, 4, 6, 600.0)], rewards=[1, -1]))
    rep = classify_batch([steamroll, close, another_steamroll, win])
    assert rep["games"] == 4
    assert rep["wins"] == 1 and rep["losses"] == 3
    assert rep["buckets"]["deck_matchup"] == 2
    assert rep["buckets"]["endgame_misplay"] == 1
    assert rep["top_bucket"] == "deck_matchup"
    assert rep["ranked"][0][0] == "deck_matchup"
    assert set(rep["buckets"]) == set(BUCKETS)


def test_report_over_directory(tmp_path):
    json.dump(_replay([(0, 5, 3, 5, 1, 600.0)], rewards=[-1, 1]), open(tmp_path / "a.json", "w"))
    json.dump(_replay([(0, 3, 3, 4, 6, 600.0)], rewards=[1, -1]), open(tmp_path / "b.json", "w"))
    open(tmp_path / "broken.json", "w").write("{ not json")
    rep = scout.report(tmp_path)
    assert rep["games"] == 2  # the broken file is skipped, not fatal
    assert rep["wins"] == 1 and rep["losses"] == 1
    assert rep["top_bucket"] == "deck_matchup"


def test_run_kaggle_missing_binary(monkeypatch):
    def _boom(*a, **k):
        raise FileNotFoundError()

    monkeypatch.setattr(scout.subprocess, "run", _boom)
    res = scout.run_kaggle(["competitions", "list"])
    assert res["ok"] is False
    assert "kaggle CLI not found" in res["error"]


def test_fetch_episode_handles_unauthorized(monkeypatch, tmp_path):
    class _Proc:
        returncode = 1
        stdout = ""
        stderr = "403 Forbidden"

    monkeypatch.setattr(scout.subprocess, "run", lambda *a, **k: _Proc())
    res = scout.fetch_episode("12345", dest_dir=tmp_path)
    assert res["ok"] is False
    assert "403" in res["error"]


def test_parse_real_match():
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from ptcg_agent.engine import make_env
    from agents.agent_baseline import agent

    env = make_env()
    env.run([agent, agent])
    dg = parse_replay(env.toJSON(), our_index=0)
    assert dg["outcome"] in ("win", "loss", "draw")
    assert dg["n_decisions"] > 0
    assert all(d["n_options"] >= 1 for d in dg["decisions"])
