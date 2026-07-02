"""U10: low-variance safety layer above the search agent.

Covers the unit's test scenarios: a guaranteed lethal is always taken even when
search disagrees, a self-deck-out over-draw is vetoed when a smaller count
exists, the hard time guard trips before the bank is at risk and the agent stops
searching, and every safety path returns a legal move (including across a full
match where search is force-disabled). agent_baseline is imported before make_env
to avoid a namespace-package collision with kaggle's bundled lux agents module.
"""
import agents.agent_baseline as baseline  # noqa: F401  (import order, see module docstring)
import agents.agent_search as agent_search
from agents import heuristics
from search.timebudget import SAFETY_RESERVE, TimeBudget


def _damaging_attack_id():
    """A real attackId with positive printed damage, from the engine card data."""
    for aid, atk in heuristics.attack_index().items():
        if (getattr(atk, "damage", 0) or 0) > 0:
            return aid
    raise AssertionError("no damaging attack found in the card database")


# --- Safety 1: never miss a lethal ------------------------------------------

def test_lethal_is_taken_even_when_search_disagrees(monkeypatch):
    aid = _damaging_attack_id()
    sel = {
        "type": heuristics.SEL_MAIN, "minCount": 1, "maxCount": 1,
        "option": [
            {"type": heuristics.OPT_ATTACK, "attackId": aid},  # index 0: lethal
            {"type": heuristics.OPT_END},                      # index 1
        ],
    }
    # No attacker/defender card ids, so effective_damage uses the printed damage;
    # the defender is at 1 HP, so any damaging attack is a knockout.
    state = {
        "yourIndex": 0,
        "players": [
            {"active": [{"id": None}], "bench": [], "deckCount": 30, "prize": [None] * 4, "hand": []},
            {"active": [{"id": None, "hp": 1, "maxHp": 100}], "bench": []},
        ],
    }
    obs = {"select": sel, "current": state, "search_begin_input": "x"}

    # Search would pick END; the safety layer must override it with the lethal.
    monkeypatch.setattr(agent_search.rollout, "search_decision", lambda *a, **k: [1])
    assert agent_search.agent(obs) == [0]


# --- Safety 2: hard time guard ----------------------------------------------

def test_at_risk_trips_before_the_hard_bank():
    b = TimeBudget()  # default HARD_BANK = 540
    b.record(b.hard_bank - SAFETY_RESERVE - 1.0)
    assert not b.at_risk
    b.record(2.0)
    assert b.at_risk
    # The guard always fires strictly before the hard bank is exhausted.
    assert b.spent < b.hard_bank


def test_search_is_skipped_when_bank_at_risk(monkeypatch):
    # A non-lethal, searchable MAIN decision.
    sel = {
        "type": heuristics.SEL_MAIN, "minCount": 1, "maxCount": 1,
        "option": [{"type": heuristics.OPT_END}, {"type": heuristics.OPT_PLAY}],
    }
    state = {"yourIndex": 0, "players": [
        {"active": [None], "bench": [], "deckCount": 30, "prize": [None] * 4, "hand": []},
        {"active": [None], "bench": []},
    ]}
    obs = {"select": sel, "current": state, "search_begin_input": "x"}

    called = {"n": 0}

    def spy(*a, **k):
        called["n"] += 1
        return [0]

    monkeypatch.setattr(agent_search.rollout, "search_decision", spy)
    spent_budget = TimeBudget()
    spent_budget.spent = spent_budget.hard_bank  # well past the safety reserve
    monkeypatch.setattr(agent_search, "_BUDGET", spent_budget)

    move = agent_search.agent(obs)
    assert called["n"] == 0                      # search never ran
    assert agent_search._is_legal(move, sel)     # heuristic still returned legally


# --- Safety 3: self-deck-out veto -------------------------------------------

def _count_obs(deck_n):
    sel = {
        "type": heuristics.SEL_COUNT, "minCount": 1, "maxCount": 1,
        "option": [
            {"type": heuristics.OPT_NUMBER, "number": 0},
            {"type": heuristics.OPT_NUMBER, "number": 2},
            {"type": heuristics.OPT_NUMBER, "number": 5},
        ],
    }
    state = {"yourIndex": 0, "players": [
        {"active": [None], "bench": [], "deckCount": deck_n, "prize": [None] * 4, "hand": []},
        {"active": [None], "bench": []},
    ]}
    return {"select": sel, "current": state}


def test_overdraw_is_capped_to_deck_count_when_low():
    obs = _count_obs(deck_n=3)
    move = agent_search.agent(obs)
    chosen = obs["select"]["option"][move[0]]["number"]
    assert chosen <= 3            # never request more than the deck holds
    assert chosen == 2            # the largest legal count that does not deck us out
    assert agent_search._is_legal(move, obs["select"])


def test_deckout_veto_inert_in_normal_play():
    obs = _count_obs(deck_n=30)
    move = agent_search.agent(obs)
    # Deck is healthy, so the heuristic's max-count choice stands.
    assert obs["select"]["option"][move[0]]["number"] == 5


def test_deckout_picks_least_draw_when_every_count_overdraws():
    # Empty deck and no zero-draw option: every count over-draws, so the veto
    # must fall back to the smallest count rather than returning the largest.
    sel = {
        "type": heuristics.SEL_COUNT, "minCount": 1, "maxCount": 1,
        "option": [
            {"type": heuristics.OPT_NUMBER, "number": 2},
            {"type": heuristics.OPT_NUMBER, "number": 5},
        ],
    }
    state = {"yourIndex": 0, "players": [
        {"active": [None], "bench": [], "deckCount": 0, "prize": [None] * 4, "hand": []},
        {"active": [None], "bench": []},
    ]}
    obs = {"select": sel, "current": state}
    move = agent_search.agent(obs)
    assert obs["select"]["option"][move[0]]["number"] == 2
    assert agent_search._is_legal(move, sel)


# --- Safety 4: always legal, even over a full match with search disabled -----

def test_safety_path_legal_across_full_match(monkeypatch):
    from ptcg_agent.engine import make_env

    # A hard bank equal to the safety reserve makes at_risk true from spent==0, so
    # search is skipped every turn and the safety + heuristic path runs the whole
    # match. Deck selection resets spent to 0, which keeps the guard tripped.
    monkeypatch.setattr(agent_search, "_BUDGET", TimeBudget(hard_bank=SAFETY_RESERVE))
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


# --- Safety 5: unknown enum values degrade to a legal fallback (U30) ----------
# The grader can hand the agent an OptionType or SelectType the pilot does not
# recognise (a new card mechanic, an engine bump). U30 requires those unknown
# values to degrade to a legal selection rather than raise, since any exception
# forfeits the match. These negative tests lock the crash-class defence so a
# later refactor cannot silently drop it.

import agents.agent_heuristic as agent_heuristic  # noqa: E402


def _legal(move, sel):
    n = len(sel.get("option", []))
    return (
        isinstance(move, list)
        and len(set(move)) == len(move)
        and sel.get("minCount", 1) <= len(move) <= sel.get("maxCount", 1)
        and all(isinstance(i, int) and 0 <= i < n for i in move)
    )


def test_choose_degrades_unknown_select_type():
    # A SelectType the pilot has no branch for must still return a legal move.
    sel = {"type": 777, "minCount": 1, "maxCount": 1,
           "option": [{"type": heuristics.OPT_END}, {"type": heuristics.OPT_YES}]}
    move = heuristics.choose({"select": sel, "current": {}})
    assert _legal(move, sel)


def test_choose_unknown_select_respects_min_count():
    # The fallback honours minCount, returning distinct legal indices.
    sel = {"type": 888, "minCount": 2, "maxCount": 2,
           "option": [{"type": 1}, {"type": 2}, {"type": 3}]}
    move = heuristics.choose({"select": sel, "current": {}})
    assert _legal(move, sel)
    assert len(move) == 2


def test_choose_degrades_unknown_option_types_in_main():
    # A MAIN decision whose options are all unrecognised OptionTypes: no resolver
    # fires and there is no END, so the first-legal fallback must still answer.
    sel = {"type": heuristics.SEL_MAIN, "minCount": 1, "maxCount": 1,
           "option": [{"type": 555}, {"type": 556}]}
    obs = {"select": sel, "current": {"yourIndex": 0, "players": [{}, {}]}}
    move = heuristics.choose(obs)
    assert _legal(move, sel)


def test_choose_prefers_end_over_unknown_options():
    # END is a clean turn-ender, so it is chosen over unknown option types.
    sel = {"type": heuristics.SEL_MAIN, "minCount": 1, "maxCount": 1,
           "option": [{"type": 555}, {"type": heuristics.OPT_END}]}
    obs = {"select": sel, "current": {"yourIndex": 0, "players": [{}, {}]}}
    move = heuristics.choose(obs)
    assert move == [1]


def test_submitted_agent_never_raises_when_choose_raises(monkeypatch):
    # If choose() itself blows up on an exotic obs, the shipped entrypoint still
    # returns a legal move via its guaranteed fallback rather than forfeiting.
    def boom(_obs):
        raise RuntimeError("simulated pilot crash")

    monkeypatch.setattr(agent_heuristic.heuristics, "choose", boom)
    sel = {"type": heuristics.SEL_MAIN, "minCount": 1, "maxCount": 1,
           "option": [{"type": heuristics.OPT_END}, {"type": heuristics.OPT_YES}]}
    move = agent_heuristic.agent({"select": sel, "current": {}})
    assert _legal(move, sel)


def test_submitted_agent_last_resort_on_broken_select():
    # A select object so malformed that even _first_legal cannot read it must not
    # crash the agent; the documented last resort is [0].
    move = agent_heuristic.agent({"select": ["not", "a", "dict"]})
    assert move == [0]


# --- Safety 6: ordered guard stack is scorer-independent (U37) ----------------
# choose()'s FORCE/VETO guards (lethal, ability-loop, deckout) must hold no matter
# how the CEM-tunable PRIO_* category scorer is weighted, so a learned option
# scorer (U41) inserted below them can never override a safety guard. test_heuristic
# checks each guard at the shipped weights; these pin the guards against an
# ADVERSARIALLY maxed scorer, the exact regression the U41 hook depends on. Card
# ids are the same real cards test_heuristic uses (28 Poltchageist repeatable
# ability; 1205 Cyrano / 1145 Mega Signal deck-drilling trainers).
ABILITY_REPEATABLE = 28
SUPPORTER_DRAW = 1205
ITEM_DRAW = 1145

_PRIO_NAMES = (
    "PRIO_CANDY", "PRIO_EVOLVE", "PRIO_PLAY", "PRIO_ATTACH",
    "PRIO_ABILITY", "PRIO_RETREAT", "PRIO_ATTACK",
)


def _max_out_scorer(monkeypatch, **overrides):
    # Drive every category weight to a huge value so the scorer maximally prefers
    # whatever category is present; per-category overrides let a test single out one.
    for name in _PRIO_NAMES:
        monkeypatch.setattr(heuristics, name, overrides.get(name, 1e9))


def _pokemon(card_id, hp, max_hp=None):
    return {"id": card_id, "hp": hp, "maxHp": max_hp or hp}


def _main_obs(option_dicts, *, my_active=None, opp_active=None, me_extra=None):
    me = {"active": [my_active] if my_active else [], "bench": []}
    me.update(me_extra or {})
    opp = {"active": [opp_active] if opp_active else []}
    return {
        "select": {"type": heuristics.SEL_MAIN, "minCount": 1, "maxCount": 1,
                   "option": option_dicts},
        "current": {"yourIndex": 0, "energyAttached": True, "players": [me, opp]},
    }


def test_lethal_force_beats_adversarially_maxed_scorer(monkeypatch):
    # L1: a guaranteed knockout is taken even when every scorer weight is maxed
    # toward a non-attack category, proving the lethal FORCE sits above any scorer.
    # Defender HP is set to the effective damage so the attack is exactly lethal
    # regardless of any weakness or resistance interplay.
    attacks = heuristics.attack_index()
    aid, attack = next((k, a) for k, a in attacks.items() if (a.damage or 0) > 0)
    _max_out_scorer(monkeypatch)
    opp = _pokemon(722, 90)
    opp["hp"] = heuristics.effective_damage(722, attack, opp["id"])
    opts = [
        {"type": heuristics.OPT_EVOLVE, "index": 0},          # index 0: scorer bait
        {"type": heuristics.OPT_ATTACK, "attackId": aid},     # index 1: the knockout
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(722, 90), opp_active=opp)
    assert heuristics.choose(obs) == [1]


def test_ability_loop_veto_holds_against_maxed_scorer(monkeypatch):
    # L2: with the ability lever on AND PRIO_ABILITY maxed, a REPEATABLE ability is
    # still refused (the stateless-loop veto is scorer-independent); the turn ends.
    monkeypatch.setattr(heuristics, "_ABILITY", True)
    _max_out_scorer(monkeypatch)
    opts = [
        {"type": heuristics.OPT_ABILITY, "area": heuristics.AREA_ACTIVE, "index": 0},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(ABILITY_REPEATABLE, 90),
                    opp_active=_pokemon(722, 90))
    assert heuristics.choose(obs) == [1]  # END, never the looping ability


def test_deckout_veto_holds_against_maxed_play_scorer(monkeypatch):
    # L3: near a self-deckout, a hand of only deck-drilling trainers is refused even
    # when PLAY is the top-scored category; the pilot ends the turn rather than mill.
    _max_out_scorer(monkeypatch)  # PRIO_PLAY maxed with the rest
    hand = [{"id": SUPPORTER_DRAW}, {"id": ITEM_DRAW}]
    opts = [
        {"type": heuristics.OPT_PLAY, "index": 0},
        {"type": heuristics.OPT_PLAY, "index": 1},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(722, 90), opp_active=_pokemon(722, 90),
                    me_extra={"hand": hand, "deckCount": 4})
    assert heuristics.choose(obs) == [2]  # END, not either draw trainer
