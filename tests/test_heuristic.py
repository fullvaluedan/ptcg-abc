"""Unit and integration tests for the Phase 2 heuristic agent.

The logic tests build synthetic observation dicts shaped exactly like the raw
engine observation (camelCase keys, option dicts with only their relevant
fields), so they exercise heuristics.choose without running a match. The lethal
test derives its expected damage from the same effective_damage function it is
checking, so it stays correct regardless of weakness or resistance interplay.
"""
from agents import heuristics
from agents.agent_heuristic import agent as heuristic_agent
from tools.gauntlet import run_gauntlet


def _main_obs(option_dicts, *, energy_attached=False, my_active=None,
              opp_active=None, bench=None, your_index=0):
    me = {"active": [my_active] if my_active else [], "bench": bench or []}
    opp = {"active": [opp_active] if opp_active else []}
    players = [me, opp] if your_index == 0 else [opp, me]
    return {
        "select": {
            "type": heuristics.SEL_MAIN,
            "context": 0,
            "minCount": 1,
            "maxCount": 1,
            "option": option_dicts,
        },
        "current": {
            "yourIndex": your_index,
            "energyAttached": energy_attached,
            "players": players,
        },
    }


def _pokemon(card_id, hp, max_hp=None):
    return {"id": card_id, "hp": hp, "maxHp": max_hp or hp}


# Test scenario (energy): attach fires only when an energy attach option exists.
def test_attach_energy_chosen_when_available():
    opts = [
        {"type": heuristics.OPT_ATTACH, "inPlayArea": heuristics.AREA_ACTIVE},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, energy_attached=False,
                    my_active=_pokemon(722, 90), opp_active=_pokemon(722, 90))
    assert heuristic_agent(obs) == [0]


def test_attach_prefers_active_target():
    opts = [
        {"type": heuristics.OPT_ATTACH, "inPlayArea": 5},   # bench
        {"type": heuristics.OPT_ATTACH, "inPlayArea": heuristics.AREA_ACTIVE},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(722, 90), opp_active=_pokemon(722, 90))
    assert heuristic_agent(obs) == [1]


# Test scenario: a lethal attack is chosen when available, over other actions.
def test_lethal_attack_is_taken():
    attacks = heuristics.attack_index()
    aid, attack = next((k, a) for k, a in attacks.items() if (a.damage or 0) > 0)
    attacker_id = next(iter(heuristics.card_index()))
    opp = _pokemon(722, 90)
    eff = heuristics.effective_damage(attacker_id, attack, opp["id"])
    assert eff > 0
    opp["hp"] = eff  # set defender HP at exactly the attack's damage (lethal)
    opts = [
        {"type": heuristics.OPT_ATTACH, "inPlayArea": heuristics.AREA_ACTIVE},
        {"type": heuristics.OPT_ATTACK, "attackId": aid},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(attacker_id, 90), opp_active=opp)
    assert heuristic_agent(obs) == [1]


# Test scenario: evolve is taken when an EVOLVE option is legal.
def test_evolve_priority_over_play_and_attach():
    opts = [
        {"type": heuristics.OPT_PLAY, "index": 0},
        {"type": heuristics.OPT_EVOLVE, "index": 1},
        {"type": heuristics.OPT_ATTACH, "inPlayArea": heuristics.AREA_ACTIVE},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(722, 90), opp_active=_pokemon(722, 90))
    assert heuristic_agent(obs) == [1]


# Test scenario: retreat is chosen when active HP is low and bench is healthy and
# no lethal is available.
def test_retreat_when_low_hp_and_healthy_bench():
    opts = [
        {"type": heuristics.OPT_RETREAT},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(
        opts,
        energy_attached=True,
        my_active=_pokemon(722, 10, max_hp=90),
        opp_active=_pokemon(722, 90),
        bench=[_pokemon(722, 90)],
    )
    assert heuristic_agent(obs) == [0]


def test_no_retreat_when_active_healthy():
    opts = [
        {"type": heuristics.OPT_RETREAT},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(
        opts,
        energy_attached=True,
        my_active=_pokemon(722, 90, max_hp=90),
        opp_active=_pokemon(722, 90),
        bench=[_pokemon(722, 90)],
    )
    assert heuristic_agent(obs) == [1]  # ends turn, does not retreat


# Test scenario: a YES_NO selection returns a legal in range choice.
def test_yes_no_is_first_picks_go_second():
    sel = {
        "type": heuristics.SEL_YES_NO,
        "context": heuristics.CTX_IS_FIRST,
        "minCount": 1,
        "maxCount": 1,
        "option": [{"type": heuristics.OPT_YES}, {"type": heuristics.OPT_NO}],
    }
    assert heuristic_agent({"select": sel}) == [1]


# Test scenario: a COUNT selection returns a legal in range choice (the maximum).
def test_count_picks_max_number():
    sel = {
        "type": heuristics.SEL_COUNT,
        "context": 38,
        "minCount": 1,
        "maxCount": 1,
        "option": [
            {"type": heuristics.OPT_NUMBER, "number": 0},
            {"type": heuristics.OPT_NUMBER, "number": 3},
            {"type": heuristics.OPT_NUMBER, "number": 1},
        ],
    }
    assert heuristic_agent({"select": sel}) == [1]


def test_deck_selection_returns_60_cards():
    deck = heuristic_agent({"select": None})
    assert len(deck) == 60
    assert all(isinstance(c, int) for c in deck)


def test_first_legal_respects_counts():
    sel = {"option": [0, 1, 2, 3], "minCount": 2, "maxCount": 3}
    move = heuristics._first_legal(sel)
    assert move == [0, 1]
    assert len(set(move)) == len(move)


# Test scenario: the agent never returns an illegal move across a gauntlet.
def test_no_invalid_moves_in_short_gauntlet():
    stats = run_gauntlet("heuristic", ["random"], 6)
    assert stats["invalid_moves"] == 0
    assert stats["matches"] == 6
