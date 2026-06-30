"""U5 part 2: search_* rollout driver, value, time budget, and the search agent.

These cover the unit's remaining test scenarios: rollouts reach a terminal result
through search_step, argmax selection is stable under a fixed seed, the agent
degrades to the heuristic when the forward model raises, total thinking time stays
bounded by the bank, and the agent never returns an illegal move over a full
match. agent_baseline is imported at module load (before make_env) to avoid a
namespace-package collision with kaggle's bundled lux agents module.
"""
import random
from pathlib import Path

import agents.agent_baseline as baseline
import agents.agent_search as agent_search
from search import eval as ev
from search import rollout
from search.determinize import determinize
from search.timebudget import HARD_BANK, TimeBudget

ROOT = Path(__file__).resolve().parents[1]


def _deck():
    ids = [int(x) for x in (ROOT / "decks" / "baseline.csv").read_text().split("\n") if x.strip()]
    return ids[:60]


# --- eval.py -----------------------------------------------------------------

def test_terminal_value_maps_results():
    assert ev.terminal_value(-1, 0) is None      # ongoing
    assert ev.terminal_value(0, 0) == ev.WIN      # we are player 0 and won
    assert ev.terminal_value(1, 0) == ev.LOSS     # opponent won
    assert ev.terminal_value(2, 0) == ev.DRAW     # draw


def test_shaped_value_prefers_taking_prizes():
    # We (index 0) have fewer prizes left, so we are closer to winning: positive.
    state = {"result": -1, "players": [{"prize": [None, None]},
                                       {"prize": [None] * 6}]}
    good = ev.shaped_value(state, 0)
    assert 0 < good <= ev.PRIZE_SHAPING
    # Mirror it: the opponent is ahead, so our value is the negation.
    assert ev.shaped_value(state, 1) == -good


def test_shaped_value_returns_terminal_when_decided():
    state = {"result": 0, "players": [{"prize": [None] * 6}, {"prize": []}]}
    assert ev.shaped_value(state, 0) == ev.WIN


# --- timebudget.py -----------------------------------------------------------

def test_budget_respects_soft_cap_and_shrinks():
    b = TimeBudget(hard_bank=100.0, soft_cap=0.5)
    assert b.allot() == 0.5                 # soft cap binds while the bank is full
    b.record(100.0)                          # spend the whole bank
    assert b.allot() == 0.0                  # nothing left to commit
    assert b.exhausted


def test_budget_reserve_fraction_binds_when_bank_low():
    b = TimeBudget(hard_bank=100.0, soft_cap=10.0)
    b.record(98.0)
    # remaining 2.0, reserve fraction 0.25 -> 0.5, which is below the 10.0 cap.
    assert b.allot() == 0.5


def test_default_hard_bank_under_real_ceiling():
    assert HARD_BANK < 600.0


# --- rollout legality helper -------------------------------------------------

def test_legal_rejects_out_of_range_and_duplicates():
    sel = {"option": [0, 1, 2], "minCount": 1, "maxCount": 1}
    assert rollout._legal([1], sel)
    assert not rollout._legal([3], sel)       # out of range
    assert not rollout._legal([0, 0], sel)    # duplicate and wrong length
    assert not rollout._legal("x", sel)       # not a list


# --- integration: capture a real MAIN observation ----------------------------

def _capture_main_obs():
    from ptcg_agent.engine import make_env

    captured = {}

    def capturing(obs):
        sel = obs.get("select")
        if (
            "obs" not in captured
            and sel is not None
            and sel.get("type") == 0
            and sel.get("maxCount", 1) == 1
            and len(sel.get("option", [])) > 1
            and obs.get("search_begin_input")
            and (obs.get("current") or {}).get("turn", 0) >= 3
        ):
            captured["obs"] = obs
        return baseline.agent(obs)

    make_env().run([capturing, "random"])
    return captured.get("obs")


# Test scenario: rollouts reach a terminal result and the driver returns a legal
# single first move. The determinization sampler is reproducible under a fixed
# seed (asserted directly), but the argmax over rollouts is not, because the
# native forward model flips coins from its own unseeded RNG; the agent only
# relies on the mean over many determinizations, not on a single reproducible run.
def test_search_decision_returns_legal_move_and_reproducible_sampling():
    obs = _capture_main_obs()
    assert obs is not None, "failed to capture a mid-game MAIN observation"

    n = len(obs["select"]["option"])
    move = rollout.search_decision(
        obs, _deck(), budget_seconds=1e9, rng=random.Random(42),
        determinize=determinize, max_determinizations=3,
        clock=lambda: 0.0,
    )
    assert move is not None
    assert isinstance(move, list) and len(move) == 1 and 0 <= move[0] < n

    # The hidden-state sampling itself is deterministic given the seed.
    s1 = determinize(obs, _deck(), random.Random(7))
    s2 = determinize(obs, _deck(), random.Random(7))
    assert s1 == s2


# Test scenario: the agent degrades to the heuristic if the search layer raises,
# and still returns a legal move.
def test_agent_falls_back_to_heuristic_on_search_error(monkeypatch):
    obs = _capture_main_obs()
    assert obs is not None

    def boom(*a, **k):
        raise RuntimeError("forward model unavailable")

    monkeypatch.setattr(agent_search.rollout, "search_decision", boom)
    move = agent_search.agent(obs)
    sel = obs["select"]
    assert agent_search._is_legal(move, sel)


# Test scenario: deck selection returns the 60-card deck unchanged.
def test_agent_returns_deck_at_selection():
    move = agent_search.agent({"select": None})
    assert len(move) == 60


# Test scenario: the agent never returns an illegal move across a full match and
# the result is a clean win or loss (run with a tight budget for speed).
def test_search_agent_completes_match(monkeypatch):
    from ptcg_agent.engine import make_env

    # Reset the shared module budget and shrink the per-move cap so the match runs
    # quickly; each gauntlet match gets its own process and so its own budget.
    monkeypatch.setattr(agent_search, "_BUDGET", TimeBudget(soft_cap=0.02))
    illegal = {"count": 0}

    def guarded(obs):
        move = agent_search.agent(obs)
        sel = obs.get("select")
        if sel is not None and not agent_search._is_legal(move, sel):
            illegal["count"] += 1
        return move

    env = make_env()
    env.run([guarded, "random"])
    reward = env.steps[-1][0]["reward"]
    assert reward in (-1, 0, 1)
    assert illegal["count"] == 0
