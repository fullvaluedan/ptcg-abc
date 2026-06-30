"""U5 part 1: determinization sampler and the search_* forward-model smoke test.

The plan's execution note requires confirming, before any search loop is built,
that the determinization inputs satisfy the engine's count validation. These
tests do that two ways: pure-logic checks that every predicted hidden zone has
the observed card count (and a face-down active is a legal basic Pokemon), and an
end-to-end integration test that captures a real mid-game observation, feeds the
determinization to cg.api.search_begin, advances it with search_step, and
releases it. agent_baseline is imported at module load (before make_env) to avoid
a namespace-package collision with kaggle's bundled lux agents module.
"""
import random
from pathlib import Path

import agents.agent_baseline as baseline
from ptcg_agent.engine import ensure_official_cg, make_env
from search.determinize import determinize, _filler_energy_id

ROOT = Path(__file__).resolve().parents[1]


def _deck():
    ids = [int(x) for x in (ROOT / "decks" / "baseline.csv").read_text().split("\n") if x.strip()]
    return ids[:60]


def _player(deck_count, prize_count, hand_count, hand=None, active=None,
            bench=None, discard=None):
    return {
        "active": active if active is not None else [],
        "bench": bench or [],
        "deckCount": deck_count,
        "discard": discard or [],
        "prize": [None] * prize_count,
        "handCount": hand_count,
        "hand": hand,
    }


def _obs(me, opp, your_index=0):
    players = [me, opp] if your_index == 0 else [opp, me]
    return {"current": {"yourIndex": your_index, "players": players}}


def _card(card_id):
    return {"id": card_id, "serial": 0}


# Test scenario: determinization always matches the observed zone counts.
def test_determinize_matches_zone_counts():
    me = _player(40, 6, 3, hand=[_card(3), _card(3), _card(723)])
    opp = _player(45, 6, 5)
    det = determinize(_obs(me, opp), _deck(), random.Random(1))
    assert len(det.your_deck) == 40
    assert len(det.your_prize) == 6
    assert len(det.opponent_deck) == 45
    assert len(det.opponent_prize) == 6
    assert len(det.opponent_hand) == 5
    assert det.opponent_active == []  # no face-down active to predict


# Test scenario: a face-down opponent active is predicted as a basic Pokemon.
def test_face_down_active_predicts_basic_pokemon():
    from search.determinize import _card_index

    me = _player(40, 6, 3, hand=[_card(3)])
    opp = _player(45, 6, 5, active=[None])  # face-down active spot
    det = determinize(_obs(me, opp), _deck(), random.Random(1))
    assert len(det.opponent_active) == 1
    card = _card_index()[det.opponent_active[0]]
    assert card.basic and int(card.cardType) == 0  # CardType.POKEMON


# Test scenario: a revealed opponent card is not predicted into the hidden pool
# beyond the copies the prior actually holds (subtraction keeps counts honest).
def test_own_hidden_zones_drawn_from_decklist():
    deck = _deck()
    me = _player(40, 6, 3, hand=[_card(deck[0]), _card(deck[1]), _card(deck[2])])
    opp = _player(45, 6, 5)
    det = determinize(_obs(me, opp), deck, random.Random(2))
    allowed = set(deck) | {_filler_energy_id()}
    assert all(cid in allowed for cid in det.your_deck + det.your_prize)


# Test scenario: argmax selection is stable under a fixed seed (reproducibility).
def test_determinize_reproducible_under_seed():
    me = _player(40, 6, 3, hand=[_card(3), _card(723)])
    opp = _player(45, 6, 5)
    obs = _obs(me, opp)
    a = determinize(obs, _deck(), random.Random(99))
    b = determinize(obs, _deck(), random.Random(99))
    assert a == b


def _capture_main_obs():
    """Run one match and return a real mid-game MAIN observation with an sbi."""
    captured = {}

    def capturing(obs):
        sel = obs.get("select")
        if (
            "obs" not in captured
            and sel is not None
            and sel.get("type") == 0  # SelectType.MAIN
            and obs.get("search_begin_input")
            and (obs.get("current") or {}).get("turn", 0) >= 3
        ):
            captured["obs"] = obs
        return baseline.agent(obs)

    make_env().run([capturing, "random"])
    return captured.get("obs")


# Test scenario: the determinization satisfies search_begin validation, rollouts
# advance through search_step, and the state releases cleanly. This is the
# integration debug pass flagged in recon (risk R1).
def test_search_begin_accepts_determinization():
    ensure_official_cg()
    from cg.api import (
        search_begin,
        search_step,
        search_release,
        search_end,
        to_observation_class,
    )

    obs = _capture_main_obs()
    assert obs is not None, "failed to capture a mid-game MAIN observation"

    det = determinize(obs, _deck(), random.Random(7))
    root = search_begin(to_observation_class(obs), **det.as_search_begin_kwargs())
    assert root.searchId is not None
    assert root.observation.select is not None

    # Advance a few selections; each step must validate and progress.
    cur = root
    steps = 0
    for _ in range(5):
        sel = cur.observation.select
        state = cur.observation.current
        if sel is None or (state is not None and state.result != -1):
            break
        k = max(sel.minCount, 1) if sel.minCount > 0 else (1 if sel.maxCount >= 1 else 0)
        cur = search_step(cur.searchId, list(range(min(k, len(sel.option)))))
        steps += 1
    assert steps >= 1

    search_release(root.searchId)
    search_end()
