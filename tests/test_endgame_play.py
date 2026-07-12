"""PTCG_ENDGAME_PLAY (analysis/endgame_play_rule_design.md): the endgame
EVOLVE-below-PLAY reorder.

Same synthetic-obs style as test_heuristic.py: MAIN observations shaped exactly
like the raw engine observation, built by hand so each scenario isolates one
trigger condition (flag, near-endgame, hand size, both categories legal) without
running a match. The real-card-data test is deliberately NOT mocked (the U105
lesson from test_opponent_threat_damage_nonzero_on_real_card_data: a heavily
mocked test can pass while the real wiring between two functions is broken), so
it drives heuristics.choose end to end against actual card ids from card_index().
"""
from agents import heuristics

ENDGAME_HAND = heuristics.ENDGAME_HAND  # 10 at shipped defaults


def _card(card_id):
    return {"id": card_id}


def _pokemon(card_id, hp, max_hp=None):
    return {"id": card_id, "hp": hp, "maxHp": max_hp or hp}


# 722 Snover: a real Basic Pokemon id already used by test_heuristic.py, kept as
# the active/bench filler here too so no Rare Candy target or lethal attack is
# accidentally implied by the card data.
FILLER_POKEMON = 722


def _endgame_obs(*, hand_n, our_prizes, opp_prizes, bench_n=2,
                  hand_card_id=1205, opts=None, two_players=True):
    """A MAIN decision with an EVOLVE option (select-index 0), a PLAY option
    (select-index 1) that plays hand[0], and an END option (select-index 2).

    hand_n cards, bench_n Pokemon (>= THIN_BENCH so the thin-bench guard stays
    out of the way), and prize piles sized to control near-endgame directly.
    """
    hand = [_card(hand_card_id) for _ in range(hand_n)]
    bench = [_pokemon(FILLER_POKEMON, 90) for _ in range(bench_n)]
    me = {
        "active": [_pokemon(FILLER_POKEMON, 90)],
        "bench": bench,
        "hand": hand,
        "prize": [None] * our_prizes,
    }
    players = [me]
    if two_players:
        opp = {
            "active": [_pokemon(FILLER_POKEMON, 90)],
            "bench": [],
            "prize": [None] * opp_prizes,
        }
        players.append(opp)
    default_opts = [
        {"type": heuristics.OPT_EVOLVE, "index": 0},
        {"type": heuristics.OPT_PLAY, "index": 0},
        {"type": heuristics.OPT_END},
    ]
    return {
        "select": {
            "type": heuristics.SEL_MAIN, "context": 0,
            "minCount": 1, "maxCount": 1,
            "option": opts if opts is not None else default_opts,
        },
        "current": {"yourIndex": 0, "energyAttached": True, "players": players},
    }


# --- the reorder itself ----------------------------------------------------

# With the flag on and every trigger condition satisfied (near-endgame, bloated
# hand, both categories legal), PLAY (select-index 1) is taken instead of the
# default EVOLVE (select-index 0).
def test_endgame_play_fires_and_prefers_play_over_evolve(monkeypatch):
    monkeypatch.setattr(heuristics, "_ENDGAME_PLAY", True)
    obs = _endgame_obs(hand_n=ENDGAME_HAND, our_prizes=2, opp_prizes=2)
    move = heuristics.choose(obs)
    assert move == [1]  # PLAY, demoted evolve no longer wins the ladder


# Flag off (the shipped default): identical trigger state, but the ladder is
# byte-identical to before this change, so EVOLVE still outranks PLAY.
def test_endgame_play_inactive_by_default():
    obs = _endgame_obs(hand_n=ENDGAME_HAND, our_prizes=2, opp_prizes=2)
    move = heuristics.choose(obs)
    assert move == [0]  # EVOLVE, the historical ladder order


# Explicit off, same as the default, spelled out for symmetry with the on test.
def test_endgame_play_off_matches_default(monkeypatch):
    monkeypatch.setattr(heuristics, "_ENDGAME_PLAY", False)
    obs = _endgame_obs(hand_n=ENDGAME_HAND, our_prizes=2, opp_prizes=2)
    assert heuristics.choose(obs) == [0]


# --- each trigger condition gates the reorder independently ----------------

def test_endgame_play_noop_hand_below_threshold(monkeypatch):
    monkeypatch.setattr(heuristics, "_ENDGAME_PLAY", True)
    obs = _endgame_obs(hand_n=ENDGAME_HAND - 1, our_prizes=2, opp_prizes=2)
    assert heuristics.choose(obs) == [0]  # still EVOLVE, hand too small to fire


def test_endgame_play_fires_at_exact_hand_threshold(monkeypatch):
    # Boundary: >= ENDGAME_HAND, not >, so exactly at the threshold the rule fires.
    monkeypatch.setattr(heuristics, "_ENDGAME_PLAY", True)
    obs = _endgame_obs(hand_n=ENDGAME_HAND, our_prizes=2, opp_prizes=2)
    assert heuristics.choose(obs) == [1]


def test_endgame_play_noop_not_near_endgame(monkeypatch):
    monkeypatch.setattr(heuristics, "_ENDGAME_PLAY", True)
    obs = _endgame_obs(hand_n=ENDGAME_HAND, our_prizes=3, opp_prizes=3)
    assert heuristics.choose(obs) == [0]  # both sides above 2 prizes: not near-endgame


def test_endgame_play_fires_when_only_opponent_is_close(monkeypatch):
    # near_endgame is min(our, opp) <= 2: our side can be comfortable as long as
    # the opponent is close.
    monkeypatch.setattr(heuristics, "_ENDGAME_PLAY", True)
    obs = _endgame_obs(hand_n=ENDGAME_HAND, our_prizes=5, opp_prizes=1)
    assert heuristics.choose(obs) == [1]


def test_endgame_play_noop_evolve_not_legal(monkeypatch):
    monkeypatch.setattr(heuristics, "_ENDGAME_PLAY", True)
    opts = [
        {"type": heuristics.OPT_PLAY, "index": 0},
        {"type": heuristics.OPT_END},
    ]
    obs = _endgame_obs(hand_n=ENDGAME_HAND, our_prizes=2, opp_prizes=2, opts=opts)
    assert heuristics.choose(obs) == [0]  # PLAY, the only legal category, unaffected


def test_endgame_play_noop_play_not_legal(monkeypatch):
    monkeypatch.setattr(heuristics, "_ENDGAME_PLAY", True)
    opts = [
        {"type": heuristics.OPT_EVOLVE, "index": 0},
        {"type": heuristics.OPT_END},
    ]
    obs = _endgame_obs(hand_n=ENDGAME_HAND, our_prizes=2, opp_prizes=2, opts=opts)
    assert heuristics.choose(obs) == [0]  # EVOLVE, the only legal category, unaffected


# --- interaction with the safety stack --------------------------------------

# L1 lethal FORCE runs before the ladder is even built, so a guaranteed knockout
# is taken even when the endgame-play trigger is fully satisfied.
def test_endgame_play_never_overrides_lethal(monkeypatch):
    monkeypatch.setattr(heuristics, "_ENDGAME_PLAY", True)
    attacks = heuristics.attack_index()
    aid, attack = next((k, a) for k, a in attacks.items() if (a.damage or 0) > 0)
    attacker_id = next(iter(heuristics.card_index()))
    opp_hp = heuristics.effective_damage(attacker_id, attack, FILLER_POKEMON)
    opts = [
        {"type": heuristics.OPT_EVOLVE, "index": 0},
        {"type": heuristics.OPT_PLAY, "index": 0},
        {"type": heuristics.OPT_ATTACK, "attackId": aid},
        {"type": heuristics.OPT_END},
    ]
    obs = _endgame_obs(hand_n=ENDGAME_HAND, our_prizes=2, opp_prizes=2, opts=opts)
    obs["current"]["players"][0]["active"] = [_pokemon(attacker_id, 90)]
    obs["current"]["players"][1]["active"] = [_pokemon(FILLER_POKEMON, opp_hp)]
    assert heuristics.choose(obs) == [2]  # the knockout, ahead of the whole ladder


# --- _opp_prize_count: the fail-closed mirror of _our_prize_count ----------

def test_opp_prize_count_reads_opponent_seat():
    obs = _endgame_obs(hand_n=1, our_prizes=6, opp_prizes=2)
    assert heuristics._opp_prize_count(obs) == 2


def test_opp_prize_count_sentinel_on_missing_seat():
    # Only one player in a two-player-shaped state: the opponent seat does not
    # exist. Must fail CLOSED (a large sentinel, not 0) so a degenerate obs never
    # looks like near-endgame purely because the opponent could not be read.
    obs = _endgame_obs(hand_n=1, our_prizes=6, opp_prizes=0, two_players=False)
    assert heuristics._opp_prize_count(obs) > 2


# If _opp_prize_count instead defaulted to 0 on a missing seat (the naive mirror
# of _our_prize_count's own missing-seat default), min(our, opp) would read 0 and
# the trigger would fire on every malformed observation regardless of our own
# prize count. The fail-closed sentinel must prevent that false positive here:
# our own prizes are comfortable (5, not near-endgame) and the opponent seat is
# missing, so the rule must not fire.
def test_endgame_play_fails_closed_when_opponent_seat_missing(monkeypatch):
    monkeypatch.setattr(heuristics, "_ENDGAME_PLAY", True)
    obs = _endgame_obs(hand_n=ENDGAME_HAND, our_prizes=5, opp_prizes=0,
                        two_players=False)
    assert heuristics.choose(obs) == [0]  # EVOLVE: the rule correctly stays inert


# --- non-mocked, real card data (the U105 lesson) ---------------------------

# No function used to compute the trigger or resolve PLAY/EVOLVE is mocked here;
# only the two module-level flags being tested are set, and every card id is a
# real id resolved through the actual card_index(). This is the check that would
# have caught test_opponent_threat_damage_nonzero_on_real_card_data's bug had it
# existed for this lever: a mocked _resolve_play or _resolve_evolve could pass
# every test above while the real end-to-end wiring silently no-ops.
def test_endgame_play_flips_real_choose_on_real_card_data(monkeypatch):
    monkeypatch.setattr(heuristics, "_ENDGAME_PLAY", False)
    obs = _endgame_obs(hand_n=ENDGAME_HAND, our_prizes=2, opp_prizes=1)
    off_move = heuristics.choose(obs)
    monkeypatch.setattr(heuristics, "_ENDGAME_PLAY", True)
    on_move = heuristics.choose(obs)
    assert off_move == [0]   # EVOLVE
    assert on_move == [1]    # PLAY
    assert off_move != on_move
