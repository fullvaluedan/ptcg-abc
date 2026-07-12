"""PTCG_RANKER (analysis/ranker_outcome_model.md): the outcome-labeled
per-option policy ranker action selector.

Same synthetic-obs style as test_heuristic.py / test_safety.py: MAIN
observations shaped exactly like the raw engine observation, built by hand so
each scenario isolates one condition (flag, safety-guard interaction,
argmax wiring) without running a match or the native engine's search. Real
card ids reused from test_safety.py/test_heuristic.py's already-verified
pool: 722 Snover (filler Basic), 66 Dudunsparce (once-per-turn ability),
28 Poltchageist (repeatable ability), 1205 Cyrano / 1145 Mega Signal
(deck-drilling Supporter/Item).

Required coverage (per the plan): flag-off byte-identity, a non-mocked
scoring test on real card data (the U105 lesson: a heavily mocked test can
pass while the real wiring between two functions is broken), and a ranker
preference flip on a constructed pair of options.
"""
from agents import heuristics
from agents import imitation_features as IF
from search import learned_ranker

FILLER = 722
ABILITY_ONCE = 66          # Dudunsparce
ABILITY_REPEATABLE = 28    # Poltchageist
SUPPORTER_DRAW = 1205      # Cyrano
ITEM_DRAW = 1145           # Mega Signal


def _pokemon(card_id, hp, max_hp=None):
    return {"id": card_id, "hp": hp, "maxHp": max_hp or hp}


def _main_obs(option_dicts, *, energy_attached=True, my_active=None,
              opp_active=None, bench=None, hand=None, deck_count=30):
    me = {
        "active": [my_active] if my_active else [],
        "bench": bench or [],
        "hand": hand or [],
        "deckCount": deck_count,
        "prize": [None] * 6,
    }
    opp = {"active": [opp_active] if opp_active else [], "bench": [], "prize": [None] * 6}
    return {
        "select": {
            "type": heuristics.SEL_MAIN, "context": 0, "minCount": 1, "maxCount": 1,
            "option": option_dicts,
        },
        "current": {"yourIndex": 0, "energyAttached": energy_attached,
                    "players": [me, opp]},
    }


def setup_function(_fn):
    learned_ranker._model = None
    learned_ranker._load_attempted = False


def teardown_function(_fn):
    learned_ranker._model = None
    learned_ranker._load_attempted = False


# --- flag-off byte-identity --------------------------------------------------

def test_ranker_off_is_default():
    assert heuristics._RANKER is False


def test_ranker_off_never_builds_a_candidate_set(monkeypatch):
    # With the flag off (the shipped default), _resolve_ranker's first line
    # must return None before touching _ranker_safe_indices at all: this is
    # the actual byte-identical short-circuit, not a coincidental match on
    # this one obs. A version of _ranker_safe_indices that raises proves the
    # off path never reaches it.
    def _boom(*_a, **_k):
        raise AssertionError("_ranker_safe_indices must not be called when PTCG_RANKER is off")

    monkeypatch.setattr(heuristics, "_ranker_safe_indices", _boom)
    opts = [
        {"type": heuristics.OPT_ATTACH, "inPlayArea": heuristics.AREA_ACTIVE},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(FILLER, 90), opp_active=_pokemon(FILLER, 90))
    move = heuristics.choose(obs)
    assert move == [0]  # normal ladder: attach outranks end


def test_ranker_off_matches_historical_ladder_even_when_the_model_would_disagree(monkeypatch):
    # Even if the ranker WOULD prefer a different option, the flag being off
    # means it is never consulted, so choose() is unaffected by what the
    # scorer says.
    monkeypatch.setattr(learned_ranker, "score_option", lambda _f: 0.99)
    opts = [
        {"type": heuristics.OPT_RETREAT},
        {"type": heuristics.OPT_ATTACH, "inPlayArea": heuristics.AREA_ACTIVE},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(FILLER, 90), opp_active=_pokemon(FILLER, 90))
    assert heuristics.choose(obs) == [1]  # attach, the historical ladder order


# --- non-mocked, real card data (the U105 lesson) ---------------------------

def test_ranker_scores_real_card_data_end_to_end():
    # No function used to build features or score them is mocked: real card
    # ids, the real imitation_features featurizer, and the real committed
    # search/ranker_model.json.
    opts = [
        {"type": heuristics.OPT_ATTACH, "inPlayArea": heuristics.AREA_ACTIVE},
        {"type": heuristics.OPT_RETREAT},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(FILLER, 90), opp_active=_pokemon(FILLER, 60),
                     bench=[_pokemon(FILLER, 90)])
    feat_rows = IF.decision_features(obs)
    assert feat_rows is not None
    assert len(feat_rows) == 3
    scores = [learned_ranker.score_option(row) for row in feat_rows]
    assert all(s is not None and 0.0 <= s <= 1.0 for s in scores)


def test_ranker_choose_end_to_end_on_real_card_data(monkeypatch):
    # choose() itself, flag on, real card ids, the real committed model:
    # must return a legal index, never raise.
    monkeypatch.setattr(heuristics, "_RANKER", True)
    opts = [
        {"type": heuristics.OPT_ATTACH, "inPlayArea": heuristics.AREA_ACTIVE},
        {"type": heuristics.OPT_RETREAT},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(FILLER, 90), opp_active=_pokemon(FILLER, 60),
                     bench=[_pokemon(FILLER, 90)])
    move = heuristics.choose(obs)
    assert isinstance(move, list) and len(move) == 1
    assert 0 <= move[0] < len(opts)


# --- ranker preference flip on a constructed pair of options ----------------

def test_ranker_argmax_flips_choose_to_the_higher_scored_option(monkeypatch):
    monkeypatch.setattr(heuristics, "_RANKER", True)
    opts = [
        {"type": heuristics.OPT_RETREAT},                                   # index 0
        {"type": heuristics.OPT_ATTACH, "inPlayArea": heuristics.AREA_ACTIVE},  # index 1
        {"type": heuristics.OPT_END},                                       # index 2
    ]
    obs = _main_obs(opts, my_active=_pokemon(FILLER, 90), opp_active=_pokemon(FILLER, 60),
                     bench=[_pokemon(FILLER, 90)])

    # Historical ladder (flag off) picks ATTACH (index 1).
    monkeypatch.setattr(heuristics, "_RANKER", False)
    assert heuristics.choose(obs) == [1]

    # Force the scorer to strictly prefer RETREAT (index 0) over every other
    # option: the argmax must flip choose() to it.
    def _prefers_retreat(features):
        is_retreat = features[IF._INDEX["is_retreat"]]
        return 0.9 if is_retreat else 0.1

    monkeypatch.setattr(learned_ranker, "score_option", _prefers_retreat)
    monkeypatch.setattr(heuristics, "_RANKER", True)
    assert heuristics.choose(obs) == [0]  # flipped to RETREAT, the higher-scored option


def test_ranker_argmax_flips_back_when_scorer_preference_flips(monkeypatch):
    # Same construction, opposite preference: the ranker must track whichever
    # option the scorer currently favors, proving the pick is a real argmax
    # over the candidate set and not a hardcoded index.
    monkeypatch.setattr(heuristics, "_RANKER", True)
    opts = [
        {"type": heuristics.OPT_RETREAT},
        {"type": heuristics.OPT_ATTACH, "inPlayArea": heuristics.AREA_ACTIVE},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(FILLER, 90), opp_active=_pokemon(FILLER, 60),
                     bench=[_pokemon(FILLER, 90)])

    def _prefers_attach(features):
        is_attach = features[IF._INDEX["is_attach"]]
        return 0.9 if is_attach else 0.1

    monkeypatch.setattr(learned_ranker, "score_option", _prefers_attach)
    assert heuristics.choose(obs) == [1]  # ATTACH, per the mocked preference


# --- interaction with the safety stack (L1/L2/L3 never overridden) ---------

def test_ranker_never_overrides_lethal(monkeypatch):
    monkeypatch.setattr(heuristics, "_RANKER", True)
    # A scorer that would love to avoid the attack, if it were ever consulted.
    monkeypatch.setattr(learned_ranker, "score_option", lambda _f: 0.01)
    attacks = heuristics.attack_index()
    aid, attack = next((k, a) for k, a in attacks.items() if (a.damage or 0) > 0)
    opp_hp = heuristics.effective_damage(FILLER, attack, FILLER)
    opts = [
        {"type": heuristics.OPT_RETREAT},
        {"type": heuristics.OPT_ATTACK, "attackId": aid},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(FILLER, 90), opp_active=_pokemon(FILLER, opp_hp),
                     bench=[_pokemon(FILLER, 90)])
    assert heuristics.choose(obs) == [1]  # the knockout, ahead of the ranker entirely


def test_ranker_excludes_repeatable_ability_from_candidates(monkeypatch):
    # L2: even a scorer that strongly prefers the repeatable ability must
    # never see it as a candidate; with only END left as a safe candidate
    # (<2 candidates), the ranker resolver declines and the ladder's own
    # (also loop-safe) ability veto handles it.
    monkeypatch.setattr(heuristics, "_RANKER", True)
    monkeypatch.setattr(learned_ranker, "score_option", lambda _f: 0.99)
    opts = [
        {"type": heuristics.OPT_ABILITY, "area": heuristics.AREA_ACTIVE, "index": 0},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(ABILITY_REPEATABLE, 90), opp_active=_pokemon(FILLER, 90))
    assert heuristics.choose(obs) == [1]  # END, never the looping ability


def test_ranker_safe_indices_excludes_repeatable_ability():
    opts = [
        {"type": heuristics.OPT_ABILITY, "area": heuristics.AREA_ACTIVE, "index": 0},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(ABILITY_REPEATABLE, 90), opp_active=_pokemon(FILLER, 90))
    me = obs["current"]["players"][0]
    assert heuristics._ranker_safe_indices(opts, obs, me) == [1]


def test_ranker_safe_indices_keeps_once_per_turn_ability():
    opts = [
        {"type": heuristics.OPT_ABILITY, "area": heuristics.AREA_ACTIVE, "index": 0},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(ABILITY_ONCE, 90), opp_active=_pokemon(FILLER, 90))
    me = obs["current"]["players"][0]
    assert heuristics._ranker_safe_indices(opts, obs, me) == [0, 1]


def test_ranker_excludes_deckout_drilling_play_from_candidates(monkeypatch):
    # L3: near a self-deckout, a scorer that loves both drilling PLAY options
    # must never get the chance to pick either; only END is left safe.
    monkeypatch.setattr(heuristics, "_RANKER", True)
    monkeypatch.setattr(learned_ranker, "score_option", lambda _f: 0.99)
    hand = [{"id": SUPPORTER_DRAW}, {"id": ITEM_DRAW}]
    opts = [
        {"type": heuristics.OPT_PLAY, "index": 0},
        {"type": heuristics.OPT_PLAY, "index": 1},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(FILLER, 90), opp_active=_pokemon(FILLER, 90),
                     hand=hand, deck_count=4)
    assert heuristics.choose(obs) == [2]  # END, not either draw trainer


def test_ranker_safe_indices_excludes_drilling_play_near_deckout():
    hand = [{"id": SUPPORTER_DRAW}]
    opts = [{"type": heuristics.OPT_PLAY, "index": 0}, {"type": heuristics.OPT_END}]
    obs = _main_obs(opts, my_active=_pokemon(FILLER, 90), opp_active=_pokemon(FILLER, 90),
                     hand=hand, deck_count=4)
    me = obs["current"]["players"][0]
    assert heuristics._ranker_safe_indices(opts, obs, me) == [1]


def test_ranker_safe_indices_keeps_drilling_play_when_deck_is_healthy():
    hand = [{"id": SUPPORTER_DRAW}]
    opts = [{"type": heuristics.OPT_PLAY, "index": 0}, {"type": heuristics.OPT_END}]
    obs = _main_obs(opts, my_active=_pokemon(FILLER, 90), opp_active=_pokemon(FILLER, 90),
                     hand=hand, deck_count=30)
    me = obs["current"]["players"][0]
    assert heuristics._ranker_safe_indices(opts, obs, me) == [0, 1]


def test_ranker_falls_through_to_ladder_when_fewer_than_two_safe_candidates(monkeypatch):
    # A single-safe-candidate decision (the ability excluded, leaving only
    # END) must never call the scorer at all -- there is nothing to rank.
    monkeypatch.setattr(heuristics, "_RANKER", True)

    def _boom(_features):
        raise AssertionError("score_option must not be called with <2 safe candidates")

    monkeypatch.setattr(learned_ranker, "score_option", _boom)
    opts = [
        {"type": heuristics.OPT_ABILITY, "area": heuristics.AREA_ACTIVE, "index": 0},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(ABILITY_REPEATABLE, 90), opp_active=_pokemon(FILLER, 90))
    assert heuristics.choose(obs) == [1]


def test_ranker_falls_through_to_ladder_when_model_unavailable(monkeypatch):
    # Every candidate scores None (a missing/corrupt model): the resolver
    # must decline entirely rather than picking an arbitrary tied option, so
    # choose() falls back to the historical ladder.
    monkeypatch.setattr(heuristics, "_RANKER", True)
    monkeypatch.setattr(learned_ranker, "score_option", lambda _f: None)
    opts = [
        {"type": heuristics.OPT_RETREAT},
        {"type": heuristics.OPT_ATTACH, "inPlayArea": heuristics.AREA_ACTIVE},
        {"type": heuristics.OPT_END},
    ]
    obs = _main_obs(opts, my_active=_pokemon(FILLER, 90), opp_active=_pokemon(FILLER, 60),
                     bench=[_pokemon(FILLER, 90)])
    assert heuristics.choose(obs) == [1]  # ATTACH, the historical ladder order
