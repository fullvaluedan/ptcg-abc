import tarfile
from pathlib import Path

from agents.agent_baseline import agent as baseline_agent
from ptcg_agent.engine import run_match
from kaggle_environments.envs.cabt.cabt import random_agent

ROOT = Path(__file__).resolve().parents[1]


def test_deck_selection_returns_60_cards():
    deck = baseline_agent({"select": None})
    assert len(deck) == 60
    assert all(isinstance(c, int) for c in deck)


def test_returns_legal_move_in_range_no_dups():
    obs = {"select": {"option": [0, 1, 2, 3], "minCount": 1, "maxCount": 2}}
    move = baseline_agent(obs)
    assert 1 <= len(move) <= 2
    assert len(set(move)) == len(move)
    assert all(0 <= i < 4 for i in move)


def test_completes_local_match():
    res = run_match(baseline_agent, random_agent)
    assert res["reward_a"] in (-1, 0, 1)
    assert res["steps"] > 1


def test_build_submission_has_required_layout():
    from tools import build_submission as bs

    out = bs.build(
        agent_file=str(ROOT / "agents" / "agent_baseline.py"),
        deck_file=str(ROOT / "decks" / "baseline.csv"),
        out_name="submission_test.tar.gz",
    )
    with tarfile.open(out) as tar:
        names = tar.getnames()
    top = {n.split("/")[0] for n in names}
    assert {"main.py", "deck.csv", "cg"} <= top
    assert any(n.endswith("cg/libcg.so") for n in names), "Linux engine lib missing"
    assert any(n.endswith("cg/api.py") for n in names), "cg.api missing"
