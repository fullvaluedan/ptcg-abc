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
