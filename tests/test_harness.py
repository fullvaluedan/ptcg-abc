from ptcg_agent.engine import run_match
from kaggle_environments.envs.cabt.cabt import random_agent, first_agent


def test_match_completes_with_valid_reward():
    res = run_match(random_agent, first_agent)
    assert res["reward_a"] in (-1, 0, 1)
    assert res["reward_b"] in (-1, 0, 1)
    assert res["winner"] in ("a", "b", "draw")
    assert res["steps"] > 1


def test_first_player_swap_keeps_reward_keys():
    res = run_match(random_agent, first_agent, swap_first=True)
    assert res["a_seat"] == 1
    assert res["reward_a"] in (-1, 0, 1)
    assert res["reward_b"] in (-1, 0, 1)


def test_cards_lookup_offline():
    from ptcg_agent import cards

    water_energy = cards.get_card(3)
    assert water_energy is not None
    assert water_energy.cardId == 3
    assert cards.get_card(999999999) is None
