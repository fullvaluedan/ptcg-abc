"""U9: endgame solver.

Covers the unit's test scenarios: the endgame trigger fires at the intended
prize and resource thresholds and not before; a constructed forced-win endgame
position is solved (the guaranteed knockout is taken even when search disagrees);
and the boosted endgame search respects the hard time guard (a low bank caps the
larger soft cap to the reserve fraction). agent_baseline is imported before any
make_env use to avoid a namespace-package collision with kaggle's bundled agents.
"""
import agents.agent_baseline as baseline  # noqa: F401  (import order, see module docstring)
import agents.agent_search as agent_search
from agents import heuristics
from search import endgame
from search.timebudget import RESERVE_FRACTION, TimeBudget


def _state(my_prizes, opp_prizes, deck_n, hand_n=0):
    return {
        "yourIndex": 0,
        "players": [
            {
                "active": [None], "bench": [], "deckCount": deck_n,
                "prize": [None] * my_prizes, "hand": [None] * hand_n,
            },
            {"active": [None], "bench": [], "prize": [None] * opp_prizes},
        ],
    }


# --- the trigger fires at the intended thresholds and not before -------------

def test_endgame_fires_on_low_prizes_and_small_resources():
    obs = {"current": _state(my_prizes=2, opp_prizes=3, deck_n=8, hand_n=3)}
    assert endgame.is_endgame(obs)


def test_endgame_inert_with_full_deck():
    # Prizes are low, but a big deck means the hidden state is still large.
    obs = {"current": _state(my_prizes=2, opp_prizes=2, deck_n=40, hand_n=5)}
    assert not endgame.is_endgame(obs)


def test_endgame_inert_with_high_prizes():
    # Small deck, but neither player is close to taking their last prizes.
    obs = {"current": _state(my_prizes=6, opp_prizes=5, deck_n=6, hand_n=2)}
    assert not endgame.is_endgame(obs)


def test_endgame_threshold_is_inclusive_boundary():
    # Exactly at both thresholds (min prize == 2, deck+hand == 12) still fires;
    # one card more of resource does not.
    at = {"current": _state(my_prizes=2, opp_prizes=4, deck_n=10, hand_n=2)}
    over = {"current": _state(my_prizes=2, opp_prizes=4, deck_n=11, hand_n=2)}
    assert endgame.is_endgame(at)
    assert not endgame.is_endgame(over)


def test_endgame_safe_default_on_malformed_obs():
    assert not endgame.is_endgame({})
    assert not endgame.is_endgame({"current": {"players": []}})
    # Missing deckCount cannot be judged, so do not force an expensive search.
    obs = {"current": {"yourIndex": 0, "players": [
        {"prize": [None, None]}, {"prize": [None, None]}]}}
    assert not endgame.is_endgame(obs)


# --- the boost levers --------------------------------------------------------

def test_endgame_soft_cap_never_below_normal_play():
    assert endgame.endgame_soft_cap(0.5) == endgame.ENDGAME_SOFT_CAP
    # A normal soft cap larger than the endgame cap is never reduced.
    assert endgame.endgame_soft_cap(10.0) == 10.0


def test_endgame_dets_widens_cap_and_keeps_time_bounded():
    assert endgame.endgame_dets(None) is None      # time-bounded stays time-bounded
    assert endgame.endgame_dets(3) == 3 * endgame.ENDGAME_DET_MULTIPLIER


# --- the prize-race middle tier ---------------------------------------------

def test_prize_race_fires_on_low_prizes_with_a_full_deck():
    # A closing turn the endgame solver misses: prizes are low but the deck is big.
    obs = {"current": _state(my_prizes=3, opp_prizes=5, deck_n=40, hand_n=6)}
    assert endgame.is_prize_race(obs)
    assert not endgame.is_endgame(obs)


def test_prize_race_inert_while_both_players_lead():
    obs = {"current": _state(my_prizes=4, opp_prizes=5, deck_n=40)}
    assert not endgame.is_prize_race(obs)


def test_prize_race_threshold_is_inclusive_boundary():
    at = {"current": _state(my_prizes=3, opp_prizes=6, deck_n=40)}
    over = {"current": _state(my_prizes=4, opp_prizes=6, deck_n=40)}
    assert endgame.is_prize_race(at)
    assert not endgame.is_prize_race(over)


def test_prize_race_safe_default_on_malformed_obs():
    assert not endgame.is_prize_race({})
    assert not endgame.is_prize_race({"current": {"players": []}})


def test_endgame_implies_prize_race():
    # Every near-decided endgame is also a prize race (min prize <= 2 <= 3), so the
    # endgame tier always takes precedence over the moderate prize-race tier.
    obs = {"current": _state(my_prizes=2, opp_prizes=3, deck_n=8, hand_n=3)}
    assert endgame.is_endgame(obs)
    assert endgame.is_prize_race(obs)


def test_prize_race_boost_levers():
    assert endgame.prize_race_soft_cap(0.5) == endgame.PRIZE_RACE_SOFT_CAP
    assert endgame.prize_race_soft_cap(10.0) == 10.0     # never reduce a larger cap
    assert endgame.prize_race_dets(None) is None
    assert endgame.prize_race_dets(3) == 3 * endgame.PRIZE_RACE_DET_MULTIPLIER


def test_prize_race_boost_is_below_the_endgame_boost():
    # The middle tier is a moderate boost, strictly between normal play and the
    # full endgame commitment, so a closing turn is not searched as hard as a
    # near-decided one.
    assert 0.5 < endgame.PRIZE_RACE_SOFT_CAP < endgame.ENDGAME_SOFT_CAP
    assert 1 < endgame.PRIZE_RACE_DET_MULTIPLIER < endgame.ENDGAME_DET_MULTIPLIER


# --- a constructed forced-win position is solved ----------------------------

def _damaging_attack_id():
    for aid, atk in heuristics.attack_index().items():
        if (getattr(atk, "damage", 0) or 0) > 0:
            return aid
    raise AssertionError("no damaging attack found in the card database")


def test_forced_win_endgame_is_solved(monkeypatch):
    """In an endgame position with a guaranteed knockout, the agent takes it.

    The position is a genuine endgame (low prizes, tiny deck), so the solver is
    engaged, yet the deterministic lethal layer still solves the forced win even
    when the stochastic search prefers ending the turn.
    """
    aid = _damaging_attack_id()
    sel = {
        "type": heuristics.SEL_MAIN, "minCount": 1, "maxCount": 1,
        "option": [
            {"type": heuristics.OPT_ATTACK, "attackId": aid},  # index 0: lethal
            {"type": heuristics.OPT_END},                      # index 1
        ],
    }
    state = {
        "yourIndex": 0,
        "players": [
            {"active": [{"id": None}], "bench": [], "deckCount": 4,
             "prize": [None], "hand": []},
            {"active": [{"id": None, "hp": 1, "maxHp": 100}], "bench": [],
             "prize": [None]},
        ],
    }
    obs = {"select": sel, "current": state, "search_begin_input": "x"}
    assert endgame.is_endgame(obs)                 # the regime is genuinely endgame

    # Search would end the turn; the forced win must still be taken.
    monkeypatch.setattr(agent_search.rollout, "search_decision", lambda *a, **k: [1])
    assert agent_search.agent(obs) == [0]


# --- the boosted search respects the hard time guard ------------------------

def test_endgame_budget_is_boosted_when_engaged(monkeypatch):
    """A non-lethal endgame MAIN decision gets the larger endgame soft cap."""
    sel = {
        "type": heuristics.SEL_MAIN, "minCount": 1, "maxCount": 1,
        "option": [{"type": heuristics.OPT_END}, {"type": heuristics.OPT_PLAY}],
    }
    obs = {"select": sel, "current": _state(my_prizes=2, opp_prizes=3, deck_n=6),
           "search_begin_input": "x"}

    captured = {}

    def spy(_obs, _deck, budget, *a, **k):
        captured["budget"] = budget
        return [0]

    monkeypatch.setattr(agent_search, "_BUDGET", TimeBudget(soft_cap=0.5))
    monkeypatch.setattr(agent_search.rollout, "search_decision", spy)
    agent_search.agent(obs)
    # Fresh bank, so the boosted soft cap binds (well under remaining * fraction).
    assert captured["budget"] == endgame.ENDGAME_SOFT_CAP


def test_prize_race_decision_gets_the_moderate_budget(monkeypatch):
    """A closing prize-race MAIN decision (still a full deck) gets the middle cap.

    The endgame solver does not fire here (the deck is large), so before the
    middle tier this decision kept the small default cap despite being pivotal.
    """
    sel = {
        "type": heuristics.SEL_MAIN, "minCount": 1, "maxCount": 1,
        "option": [{"type": heuristics.OPT_END}, {"type": heuristics.OPT_PLAY}],
    }
    obs = {"select": sel, "current": _state(my_prizes=3, opp_prizes=5, deck_n=40),
           "search_begin_input": "x"}
    assert not endgame.is_endgame(obs) and endgame.is_prize_race(obs)

    captured = {}

    def spy(_obs, _deck, budget, *a, **k):
        captured["budget"] = budget
        return [0]

    monkeypatch.setattr(agent_search, "_BUDGET", TimeBudget(soft_cap=0.5))
    monkeypatch.setattr(agent_search.rollout, "search_decision", spy)
    agent_search.agent(obs)
    assert captured["budget"] == endgame.PRIZE_RACE_SOFT_CAP


def test_endgame_tier_takes_precedence_over_prize_race(monkeypatch):
    """When both tiers apply, the near-decided endgame gets the larger boost."""
    sel = {
        "type": heuristics.SEL_MAIN, "minCount": 1, "maxCount": 1,
        "option": [{"type": heuristics.OPT_END}, {"type": heuristics.OPT_PLAY}],
    }
    obs = {"select": sel, "current": _state(my_prizes=2, opp_prizes=3, deck_n=6),
           "search_begin_input": "x"}
    assert endgame.is_endgame(obs) and endgame.is_prize_race(obs)

    captured = {}

    def spy(_obs, _deck, budget, *a, **k):
        captured["budget"] = budget
        return [0]

    monkeypatch.setattr(agent_search, "_BUDGET", TimeBudget(soft_cap=0.5))
    monkeypatch.setattr(agent_search.rollout, "search_decision", spy)
    agent_search.agent(obs)
    assert captured["budget"] == endgame.ENDGAME_SOFT_CAP


def test_normal_decision_keeps_the_small_budget(monkeypatch):
    """Outside the endgame the per-move budget stays at the normal soft cap."""
    sel = {
        "type": heuristics.SEL_MAIN, "minCount": 1, "maxCount": 1,
        "option": [{"type": heuristics.OPT_END}, {"type": heuristics.OPT_PLAY}],
    }
    obs = {"select": sel, "current": _state(my_prizes=5, opp_prizes=5, deck_n=40),
           "search_begin_input": "x"}

    captured = {}

    def spy(_obs, _deck, budget, *a, **k):
        captured["budget"] = budget
        return [0]

    monkeypatch.setattr(agent_search, "_BUDGET", TimeBudget(soft_cap=0.5))
    monkeypatch.setattr(agent_search.rollout, "search_decision", spy)
    agent_search.agent(obs)
    assert captured["budget"] == 0.5


def test_endgame_boost_respects_hard_time_guard():
    """Even boosted, a single decision never exceeds the remaining-bank fraction."""
    b = TimeBudget(hard_bank=100.0, soft_cap=0.5)
    b.record(98.0)  # remaining 2.0
    # The endgame cap (4.0) is far above the reserve, so the reserve fraction binds
    # and the boosted decision is capped well under the bank, not at 4.0 seconds.
    allotted = b.allot(endgame.ENDGAME_SOFT_CAP)
    assert allotted == 2.0 * RESERVE_FRACTION
    assert allotted < endgame.ENDGAME_SOFT_CAP
