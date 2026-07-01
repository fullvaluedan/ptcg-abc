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


# --- Self-deck-out guard (loss-data driven: deckout was the dominant real loss) ---

def _count_obs(deck_n, numbers):
    sel = {
        "type": heuristics.SEL_COUNT,
        "minCount": 1,
        "maxCount": 1,
        "option": [{"type": heuristics.OPT_NUMBER, "number": n} for n in numbers],
    }
    state = {"yourIndex": 0, "players": [
        {"active": [None], "bench": [], "deckCount": deck_n, "prize": [None] * 4, "hand": []},
        {"active": [None], "bench": []},
    ]}
    return {"select": sel, "current": state}


# Test scenario: when the deck is low, the heuristic no longer draws the max; it
# caps the count to what the deck can support so it does not deck itself out.
def test_count_capped_to_deck_when_low():
    obs = _count_obs(deck_n=3, numbers=[0, 2, 5])
    move = heuristic_agent(obs)
    chosen = obs["select"]["option"][move[0]]["number"]
    assert chosen == 2            # largest count that does not over-draw a 3 card deck
    assert chosen <= 3


# Test scenario: with a healthy deck the guard is inert and the max still wins.
def test_count_uncapped_when_deck_healthy():
    obs = _count_obs(deck_n=30, numbers=[0, 2, 5])
    move = heuristic_agent(obs)
    assert obs["select"]["option"][move[0]]["number"] == 5


# Test scenario: every count over-draws, so take the smallest to lose the least.
def test_count_least_draw_when_every_count_overdraws():
    obs = _count_obs(deck_n=0, numbers=[2, 5])
    move = heuristic_agent(obs)
    assert obs["select"]["option"][move[0]]["number"] == 2


# --- Draw-conservation near self-deckout (loss-data driven: real ladder replays
# self-mill to zero by replaying draw Supporters and Items, twice while not behind
# on prizes; the COUNT guard never fired because the mill was all PLAY actions) ---

# Real card ids from live card data, classified by their effect text:
#   722  Snover            Basic Pokemon (type 0)
#   1205 Cyrano           Supporter that searches deck Pokemon "into your hand"
#   1145 Mega Signal      Item that searches a Mega ex "into your hand"
#   1235 Waitress         Supporter that attaches a Basic Energy (no deck drill)
#   1126 Precious Trolley Item that benches Basics (develops, no deck drill)
# Only the first two drill the deck for card advantage, so only those are
# declined near a self-deckout; Waitress and Precious Trolley develop the board.
SUPPORTER_DRAW = 1205
ITEM_DRAW = 1145
SUPPORTER_ENERGY = 1235
ITEM_DEVELOP = 1126
POKEMON_PLAY = 722


def _play_main_obs(hand_ids, deck_n, *, your_index=0, bench=None):
    """A MAIN observation whose PLAY options index a hand of the given cards."""
    hand = [_card(c, your_index) for c in hand_ids]
    me = {"active": [None], "bench": bench or [],
          "hand": hand, "deckCount": deck_n}
    opp = {"active": [None], "bench": []}
    players = [me, opp] if your_index == 0 else [opp, me]
    opts = [
        {"type": heuristics.OPT_PLAY, "index": i} for i in range(len(hand_ids))
    ] + [{"type": heuristics.OPT_END}]
    return {
        "select": {
            "type": heuristics.SEL_MAIN, "context": 0,
            "minCount": 1, "maxCount": 1, "option": opts,
        },
        "current": {"yourIndex": your_index, "energyAttached": True,
                    "players": players},
    }


# Near deckout, a hand of only draw trainers is not played; the turn ends instead
# of milling us to zero.
def test_play_skips_draw_trainers_near_deckout():
    obs = _play_main_obs([SUPPORTER_DRAW, ITEM_DRAW], deck_n=4)
    move = heuristic_agent(obs)
    end_idx = len(obs["select"]["option"]) - 1
    assert move == [end_idx]            # END, not either draw trainer


# Near deckout, develop a Pokemon rather than draw, even when a draw trainer is
# the first play option.
def test_play_prefers_pokemon_over_draw_trainer_near_deckout():
    obs = _play_main_obs([SUPPORTER_DRAW, POKEMON_PLAY], deck_n=4)
    move = heuristic_agent(obs)
    assert move == [1]                  # the Pokemon play, not the supporter


# With a healthy deck and a thin bench, benching a Basic Pokemon comes first even
# though a draw supporter is the first play option: developing the board guards
# the early_collapse loss bucket (empty bench, one knockout ends the game), and
# nothing is lost since the supporter stays legal on a later decision this turn.
def test_play_benches_basic_first_when_bench_thin():
    obs = _play_main_obs([SUPPORTER_DRAW, POKEMON_PLAY], deck_n=30)
    move = heuristic_agent(obs)
    assert move == [1]                  # the Pokemon play, not the supporter


# With a healthy deck and a bench that is no longer thin, the bench-development
# guard is inert and the first play option wins, preserving prior behavior.
def test_play_unchanged_when_bench_stocked():
    stocked = [_pokemon(POKEMON_PLAY, 90), _pokemon(POKEMON_PLAY, 90)]
    obs = _play_main_obs([SUPPORTER_DRAW, POKEMON_PLAY], deck_n=30, bench=stocked)
    move = heuristic_agent(obs)
    assert move == [0]                  # first play option, guard inert


# Thin bench but no benchable Pokemon among the plays: the bench-development guard
# finds nothing to develop and falls through to the first play option, so a hand
# of only trainers is still played rather than skipped.
def test_play_first_option_when_bench_thin_but_no_pokemon():
    obs = _play_main_obs([SUPPORTER_DRAW, ITEM_DRAW], deck_n=30)  # empty bench
    move = heuristic_agent(obs)
    assert move == [0]                  # first play option, no Pokemon to bench


# Thin bench, no Basic in hand to bench directly, but a deck-search that benches a
# Basic (Precious Trolley) is in hand behind a hand-disrupting draw Supporter:
# fetch the Basic onto the bench first. Playing Cyrano first is not just a wasted
# tempo, a hand-shuffling Supporter (Lillie's Determination) would shuffle the
# Trolley back into the deck and strand the empty-bench fix for the turn.
def test_play_fetches_basic_onto_bench_before_disrupting_play():
    obs = _play_main_obs([SUPPORTER_DRAW, ITEM_DEVELOP], deck_n=30)  # empty bench
    move = heuristic_agent(obs)
    assert move == [1]                  # Precious Trolley, not the first Supporter


# A Basic in hand to bench directly still beats the deck-search fetch: put the
# Basic down (no deck shuffle, no search) rather than trolley for one out of the
# deck. Direct develop stays the first bench-development choice.
def test_play_prefers_direct_basic_over_deck_fetch_when_thin():
    obs = _play_main_obs([ITEM_DEVELOP, POKEMON_PLAY], deck_n=30)  # empty bench
    move = heuristic_agent(obs)
    assert move == [1]                  # bench the Basic, not play the Trolley


# With the bench no longer thin the fetch-priority guard is inert and the first
# play option wins, so the change cannot alter a healthy-board turn.
def test_play_fetch_priority_inert_when_bench_stocked():
    stocked = [_pokemon(POKEMON_PLAY, 90), _pokemon(POKEMON_PLAY, 90)]
    obs = _play_main_obs([SUPPORTER_DRAW, ITEM_DEVELOP], deck_n=30, bench=stocked)
    move = heuristic_agent(obs)
    assert move == [0]                  # first play option, guard inert


# The bench-fetch predicate reads the effect text: only a deck search that puts a
# Basic onto the bench qualifies. A search that only puts a card into hand (Mega
# Signal, Cyrano, Ultra Ball) does not fill an empty bench and is excluded, as is a
# non-searching develop trainer (Waitress attaches an Energy) and a Pokemon.
def test_benches_basic_from_deck_predicate_by_effect_text():
    assert heuristics._benches_basic_from_deck(ITEM_DEVELOP)       # Precious Trolley
    assert not heuristics._benches_basic_from_deck(SUPPORTER_DRAW)  # Cyrano: to hand
    assert not heuristics._benches_basic_from_deck(ITEM_DRAW)       # Mega Signal
    assert not heuristics._benches_basic_from_deck(SUPPORTER_ENERGY)  # Waitress
    assert not heuristics._benches_basic_from_deck(POKEMON_PLAY)    # a Pokemon


# Boundary: at exactly the threshold the guard is active (<=, not <), so a draw
# trainer is still declined in favor of developing a Pokemon.
def test_play_conserves_at_threshold_boundary():
    obs = _play_main_obs([SUPPORTER_DRAW, POKEMON_PLAY],
                         deck_n=heuristics.DRAW_CONSERVE_THRESHOLD)
    move = heuristic_agent(obs)
    assert move == [1]                  # the Pokemon, not the supporter


# When deckCount is absent the deckout conservation cannot judge the deck size and
# stays inert, but bench development does not depend on the deck count, so a thin
# bench still benches the Basic first.
def test_play_benches_basic_when_deck_count_missing():
    obs = _play_main_obs([SUPPORTER_DRAW, POKEMON_PLAY], deck_n=30)
    # Drop deckCount so own_deck_count returns None.
    obs["current"]["players"][0].pop("deckCount")
    move = heuristic_agent(obs)
    assert move == [1]                  # bench the Pokemon, deck-size guard inert


# Near deckout a trainer that develops the board rather than drilling the deck is
# still played: Waitress attaches an Energy (no deck drill) and powers an attack,
# so declining it would forfeit board development to save nothing. This is the
# refinement over the blunt "skip every Item and Supporter" rule.
def test_play_keeps_energy_attach_trainer_near_deckout():
    obs = _play_main_obs([SUPPORTER_ENERGY], deck_n=4)
    move = heuristic_agent(obs)
    assert move == [0]                  # Waitress played, not declined


# Near deckout a bench-developing trainer (Precious Trolley puts a Basic onto the
# Bench) is likewise played: it develops rather than drilling the deck for hand
# advantage.
def test_play_keeps_bench_develop_trainer_near_deckout():
    obs = _play_main_obs([ITEM_DEVELOP], deck_n=4)
    move = heuristic_agent(obs)
    assert move == [0]                  # Precious Trolley played, not declined


# Near deckout a real deck-drilling trainer is preferred over none, but a
# non-drilling develop play beats it: Waitress (attach) is chosen over Cyrano
# (search into hand) even when the search trainer is the first option.
def test_play_prefers_develop_over_drill_near_deckout():
    obs = _play_main_obs([SUPPORTER_DRAW, SUPPORTER_ENERGY], deck_n=4)
    move = heuristic_agent(obs)
    assert move == [1]                  # Waitress, not the searching Supporter


# Near deckout a PLAY option whose card id cannot be resolved must not fail open:
# the guard cannot prove it is safe, so it is treated as a potential driller and
# the turn ends rather than milling us. (Card data ships our own hand with ids, so
# this only bites a degenerate observation; it closes the one path by which a
# drilling trainer could slip the guard.) The option points at an empty hand slot
# so play_card_id returns None.
def test_play_skips_unidentifiable_play_near_deckout():
    obs = _play_main_obs([SUPPORTER_DRAW], deck_n=4)
    obs["current"]["players"][0]["hand"] = []   # option index no longer resolves
    move = heuristic_agent(obs)
    end_idx = len(obs["select"]["option"]) - 1
    assert move == [end_idx]            # END, not the unidentifiable play


# The same unidentifiable play with a healthy deck is still played: the guard is
# inert above the threshold, so normal develop-the-hand behavior is preserved and
# this hardening cannot regress ordinary play.
def test_play_keeps_unidentifiable_play_when_deck_healthy():
    obs = _play_main_obs([SUPPORTER_DRAW], deck_n=30)
    obs["current"]["players"][0]["hand"] = []
    move = heuristic_agent(obs)
    assert move == [0]                  # first play option, guard inert


# The drill predicate reads the effect text: search/draw-into-hand trainers drill,
# develop trainers and non-trainers do not. Conservative when text is missing.
def test_drills_deck_predicate_by_effect_text():
    assert heuristics._drills_deck(SUPPORTER_DRAW)    # Cyrano: into your hand
    assert heuristics._drills_deck(ITEM_DRAW)         # Mega Signal: into your hand
    assert heuristics._drills_deck(1227)              # Lillie's: draw 6
    assert heuristics._drills_deck(1121)              # Ultra Ball: into your hand
    assert not heuristics._drills_deck(SUPPORTER_ENERGY)  # Waitress: attaches
    assert not heuristics._drills_deck(ITEM_DEVELOP)      # Trolley: to the Bench
    assert not heuristics._drills_deck(POKEMON_PLAY)      # a Pokemon never drills
    assert not heuristics._drills_deck(-1)            # unknown id: not a trainer


# Deck-destruction items discard cards sourced from the deck with no board gain,
# so they mill us and must be declined near deckout even though they neither draw
# nor put cards "into your hand". (1078 Hole-Digging Shovel discards the top 2 of
# the deck; 1128 Brilliant Blender searches the deck for up to 5 and discards.)
def test_drills_deck_catches_deck_discard_mills():
    assert heuristics._drills_deck(1078)              # discard top 2 of your deck
    assert heuristics._drills_deck(1128)              # search deck for 5, discard


# Discard-pile recyclers shuffle cards back INTO the deck, growing it, so they are
# the opposite of a mill and must stay playable near deckout. (1129 Sacred Ash,
# 1139 Energy Recycler.)
def test_drills_deck_keeps_deck_recyclers():
    assert not heuristics._drills_deck(1129)          # discard pile -> deck
    assert not heuristics._drills_deck(1139)          # basic energy -> deck


# An Item or Supporter whose effect text is unavailable stays conservative and is
# treated as a driller, preserving the prior safe skip-every-trainer behavior.
def test_drills_deck_conservative_when_text_missing(monkeypatch):
    monkeypatch.setattr(heuristics, "_card_text", lambda cid: None)
    assert heuristics._drills_deck(ITEM_DRAW)         # Item, text gone -> conserve
    assert heuristics._drills_deck(SUPPORTER_DRAW)    # Supporter, text gone
    assert not heuristics._drills_deck(POKEMON_PLAY)  # type gate still excludes it


# A switch trainer whose text says "withdraw" must not be mistaken for a draw
# (the \bdraw boundary excludes it); it develops/repositions, it does not drill.
def test_drills_deck_ignores_withdraw(monkeypatch):
    monkeypatch.setattr(heuristics, "_card_text",
                        lambda cid: "Withdraw your Active Pokemon to your Bench.")
    assert not heuristics._drills_deck(ITEM_DRAW)     # Item, but no real draw


# A PLAY option carries a hand index, not an area; play_card_id resolves it.
def test_play_card_id_resolves_from_hand():
    me = {"hand": [_card(POKEMON_PLAY), _card(SUPPORTER_DRAW)]}
    assert heuristics.play_card_id({"type": heuristics.OPT_PLAY, "index": 1}, me) \
        == SUPPORTER_DRAW
    assert heuristics.play_card_id({"type": heuristics.OPT_PLAY, "index": 9}, me) \
        is None


# --- CARD sub-select support (loss-data driven: early_collapse from a thin bench
# and self-deckout from over-discarding combo pieces) ---

# Real card ids, classified from live card data:
#   722 Snover (Basic Pokemon), 723 Mega Abomasnow ex (evolution), 3 Basic Energy.
BASIC_POKEMON = 722
EVOLUTION = 723
BASIC_ENERGY = 3


def _card(card_id, owner=0):
    return {"id": card_id, "serial": card_id, "playerIndex": owner}


def _deck_search_obs(option_indices, deck_ids, *, bench=None, context=7,
                     your_index=0):
    me = {"active": [None], "bench": bench or [], "hand": []}
    opp = {"active": [None], "bench": []}
    players = [me, opp] if your_index == 0 else [opp, me]
    sel = {
        "type": heuristics.SEL_CARD,
        "context": context,
        "minCount": 0,
        "maxCount": 1,
        "deck": [_card(c, your_index) for c in deck_ids],
        "option": [
            {"type": heuristics.OPT_CARD, "area": heuristics.AREA_DECK,
             "index": idx, "playerIndex": your_index}
            for idx in option_indices
        ],
    }
    return {"select": sel, "current": {"yourIndex": your_index, "players": players}}


def _discard_obs(hand_ids, option_indices, *, mn=2, mx=2, your_index=0):
    hand = [_card(c, your_index) for c in hand_ids]
    me = {"active": [None], "bench": [], "hand": hand}
    opp = {"active": [None], "bench": []}
    players = [me, opp] if your_index == 0 else [opp, me]
    sel = {
        "type": heuristics.SEL_CARD,
        "context": heuristics.CTX_DISCARD,
        "minCount": mn,
        "maxCount": mx,
        "option": [
            {"type": heuristics.OPT_CARD, "area": heuristics.AREA_HAND,
             "index": idx, "playerIndex": your_index}
            for idx in option_indices
        ],
    }
    return {"select": sel, "current": {"yourIndex": your_index, "players": players}}


# Test scenario: option_card_id resolves a deck-search option through select.deck.
def test_option_card_id_from_deck():
    obs = _deck_search_obs([0, 1], [BASIC_POKEMON, EVOLUTION])
    sel = obs["select"]
    assert heuristics.option_card_id(sel["option"][0], sel, obs) == BASIC_POKEMON
    assert heuristics.option_card_id(sel["option"][1], sel, obs) == EVOLUTION


# Test scenario: option_card_id resolves a hand option through our visible state.
def test_option_card_id_from_hand():
    obs = _discard_obs([BASIC_ENERGY, BASIC_POKEMON], [0, 1])
    sel = obs["select"]
    assert heuristics.option_card_id(sel["option"][1], sel, obs) == BASIC_POKEMON


def test_is_basic_pokemon_classification():
    assert heuristics.is_basic_pokemon(BASIC_POKEMON) is True
    assert heuristics.is_basic_pokemon(EVOLUTION) is False
    assert heuristics.is_basic_pokemon(BASIC_ENERGY) is False
    assert heuristics.is_basic_pokemon(None) is False


def test_my_bench_count_excludes_active():
    obs = _deck_search_obs([0], [BASIC_POKEMON],
                           bench=[_pokemon(BASIC_POKEMON, 90), None])
    assert heuristics.my_bench_count(obs) == 1


# Test scenario: with a thin bench the deck search fetches a Basic Pokemon over an
# evolution, so the lone active gains a backup (attacks the early-collapse loss).
def test_deck_search_fetches_basic_when_bench_thin():
    obs = _deck_search_obs([0, 1], [EVOLUTION, BASIC_POKEMON], bench=[])
    assert heuristic_agent(obs) == [1]  # option 1 -> deck[1] -> Snover (Basic)


# Test scenario: with a healthy bench the search keeps the prior first-legal pick,
# so a developed board is never steered off its normal fetch (no regression).
def test_deck_search_inert_when_bench_healthy():
    bench = [_pokemon(BASIC_POKEMON, 90), _pokemon(BASIC_POKEMON, 90)]
    obs = _deck_search_obs([0, 1], [EVOLUTION, BASIC_POKEMON], bench=bench)
    assert heuristic_agent(obs) == [0]  # first legal, unchanged behavior


# Test scenario: thin bench but no Basic among the options falls back to first legal.
def test_deck_search_no_basic_option_falls_back():
    obs = _deck_search_obs([0, 1], [EVOLUTION, EVOLUTION], bench=[])
    assert heuristic_agent(obs) == [0]


# Test scenario: a discard cost sheds surplus energy and spares the Pokemon.
def test_discard_sheds_energy_spares_pokemon():
    # hand: [energy, basic pokemon, energy, evolution]; discard exactly 2.
    obs = _discard_obs([BASIC_ENERGY, BASIC_POKEMON, BASIC_ENERGY, EVOLUTION],
                       [0, 1, 2, 3], mn=2, mx=2)
    move = heuristic_agent(obs)
    assert move == [0, 2]  # the two energy, not either Pokemon


# Test scenario: when energy is scarce, items go before any Pokemon is discarded.
def test_discard_prefers_item_over_pokemon():
    # hand: [basic pokemon, item (Mega Signal 1145), evolution]; discard exactly 1.
    obs = _discard_obs([BASIC_POKEMON, 1145, EVOLUTION], [0, 1, 2], mn=1, mx=1)
    move = heuristic_agent(obs)
    assert move == [1]  # the item, sparing both Pokemon


# Test scenario: a discard returns exactly minCount distinct legal indices.
def test_discard_returns_exact_count():
    obs = _discard_obs([BASIC_ENERGY, BASIC_ENERGY, BASIC_ENERGY], [0, 1, 2],
                       mn=2, mx=2)
    move = heuristic_agent(obs)
    assert len(move) == 2
    assert len(set(move)) == 2
    assert all(0 <= i < 3 for i in move)


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


# The heuristic submission must bundle heuristics.py at the top level so main.py
# can import it inside the grader sandbox.
def test_build_submission_bundles_extra_module():
    import tarfile
    from pathlib import Path
    from tools import build_submission as bs

    root = Path(__file__).resolve().parents[1]
    out = bs.build(
        agent_file=str(root / "agents" / "agent_heuristic.py"),
        deck_file=str(root / "decks" / "baseline.csv"),
        out_name="submission_heuristic_test.tar.gz",
        extras=[str(root / "agents" / "heuristics.py")],
    )
    with tarfile.open(out) as tar:
        top = {n.split("/")[0] for n in tar.getnames()}
    assert {"main.py", "deck.csv", "cg", "heuristics.py"} <= top
