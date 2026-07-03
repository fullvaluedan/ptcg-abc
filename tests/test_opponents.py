"""Tests for the diverse opponent pool (plan U4).

The hermetic tests exercise name resolution, the deck read, and the deck-at-
selection behavior with no engine or card data. The final integration test runs a
real match against a deck-parameterized opponent and needs the local cg/ data, the
same assumption as test_gauntlet.test_gauntlet_stats_shape.
"""
import pytest

from tools import opponents


def test_names_include_builtins_and_deck_opponents():
    ns = opponents.names()
    for b in opponents.BUILTINS:
        assert b in ns
    # Every non-builtin name is either a deck:<stem> or a clone:<family> opponent.
    rest = [n for n in ns if n not in opponents.BUILTINS]
    assert all(n.startswith("deck:") or n.startswith("clone:") for n in rest)
    assert "deck:trolley" in ns  # a known committed deck


def test_clone_family_names_subset_of_clone_families_and_on_disk():
    fams = opponents.clone_family_names()
    assert fams, "clone families should be non-empty when their decks exist on disk"
    assert all(f in opponents.CLONE_FAMILIES for f in fams)
    assert fams == sorted(fams)


def test_names_include_one_clone_per_clone_family():
    ns = opponents.names()
    for fam in opponents.clone_family_names():
        assert f"clone:{fam}" in ns


def test_pool_is_subset_of_names_and_deck_prefixed():
    p = opponents.pool()
    ns = set(opponents.names())
    assert p, "pool should be non-empty when decks exist on disk"
    assert all(n.startswith("deck:") for n in p)
    assert all(n in ns for n in p)
    # POOL_DECKS order is preserved (harvested meta first), skipping any absent.
    expected = [f"deck:{d}" for d in opponents.POOL_DECKS if f"deck:{d}" in p]
    assert p == expected


def test_get_unknown_name_raises():
    with pytest.raises(KeyError):
        opponents.get("nope")


def test_get_unknown_deck_raises_with_known_list():
    with pytest.raises(KeyError):
        opponents.get("deck:does_not_exist")


def test_get_unknown_clone_family_raises():
    with pytest.raises(KeyError):
        opponents.get("clone:does_not_exist")


def test_get_known_clone_family_resolves():
    fam = opponents.clone_family_names()[0]
    agent = opponents.get(f"clone:{fam}")
    assert callable(agent)


def test_read_deck_csv_reads_sixty(tmp_path):
    csv = tmp_path / "d.csv"
    csv.write_text("\n".join(str(i) for i in range(1, 71)))  # 70 ids
    deck = opponents._read_deck_csv(csv)
    assert deck == list(range(1, 61))  # first 60, in order


def test_read_deck_csv_rejects_short_deck(tmp_path):
    csv = tmp_path / "short.csv"
    csv.write_text("\n".join(str(i) for i in range(10)))
    with pytest.raises(ValueError):
        opponents._read_deck_csv(csv)


def test_deck_opponent_returns_deck_at_selection():
    deck = list(range(100, 160))  # 60 sentinel ids
    agent = opponents._deck_opponent(deck)
    # sel is None is the deck-selection step: the opponent returns its own deck.
    assert agent({"select": None}) == deck


def test_deck_opponent_never_raises_on_bad_state():
    # A degenerate observation must fall through to a guaranteed-legal selection,
    # never raise, so one flaky state never forfeits an opponent's match.
    agent = opponents._deck_opponent(list(range(60)))
    move = agent({"select": {"option": [0, 1], "minCount": 1, "maxCount": 1}})
    assert isinstance(move, list) and len(move) >= 1


def test_clone_opponent_returns_deck_at_selection():
    deck = list(range(200, 260))  # 60 sentinel ids
    agent = opponents._clone_opponent(deck)
    assert agent({"select": None}) == deck


def test_clone_opponent_never_raises_on_bad_state():
    agent = opponents._clone_opponent(list(range(60)))
    move = agent({"select": {"option": [0, 1], "minCount": 1, "maxCount": 1}})
    assert isinstance(move, list) and len(move) >= 1


def test_clone_opponent_picks_first_legal_when_no_lethal_available():
    # No lethal on the table: the clone must fall through to first-legal
    # (index 0), never the full heuristics.choose() strategic ladder -- the
    # whole point of U71's candidate (b) design.
    from agents import heuristics

    sel = {
        "type": heuristics.SEL_MAIN, "minCount": 1, "maxCount": 1,
        "option": [
            {"type": heuristics.OPT_RETREAT, "area": 1, "index": 0},
            {"type": heuristics.OPT_END},
        ],
    }
    state = {
        "yourIndex": 0,
        "players": [
            {"active": [{"id": None, "hp": 100, "maxHp": 100}],
             "bench": [{"id": None, "hp": 100, "maxHp": 100}],
             "deckCount": 30, "prize": [None] * 4, "hand": []},
            {"active": [{"id": None, "hp": 100, "maxHp": 100}], "bench": []},
        ],
    }
    obs = {"select": sel, "current": state}
    agent = opponents._clone_opponent(list(range(60)))
    assert agent(obs) == [0]


def test_clone_opponent_takes_lethal_over_first_legal():
    from agents import heuristics

    def _damaging_attack_id():
        for aid, atk in heuristics.attack_index().items():
            if (getattr(atk, "damage", 0) or 0) > 0:
                return aid
        raise AssertionError("no damaging attack found in the card database")

    aid = _damaging_attack_id()
    sel = {
        "type": heuristics.SEL_MAIN, "minCount": 1, "maxCount": 1,
        "option": [
            {"type": heuristics.OPT_END},           # index 0: first legal
            {"type": heuristics.OPT_ATTACK, "attackId": aid},  # index 1: lethal
        ],
    }
    state = {
        "yourIndex": 0,
        "players": [
            {"active": [{"id": None}], "bench": [], "deckCount": 30, "prize": [None] * 4, "hand": []},
            {"active": [{"id": None, "hp": 1, "maxHp": 100}], "bench": []},
        ],
    }
    obs = {"select": sel, "current": state}
    agent = opponents._clone_opponent(list(range(60)))
    assert agent(obs) == [1]


def test_safe_first_legal_index_vetoes_repeatable_ability():
    # A repeatable (non-once-per-turn) ability at index 0 must be skipped in
    # favor of the next legal option, the same stateless-loop guard choose()
    # applies (agents/heuristics.py's L2), so a first-legal picker can never
    # get stuck reselecting the same repeatable option forever.
    from agents import heuristics
    from tools import opponents as opp_mod

    sel = {
        "type": heuristics.SEL_MAIN, "minCount": 1, "maxCount": 1,
        "option": [
            {"type": heuristics.OPT_ABILITY, "area": 0, "index": 0},
            {"type": heuristics.OPT_END},
        ],
    }
    obs = {"select": sel, "current": {"yourIndex": 0, "players": [{"active": [{"id": None}], "bench": []}, {}]}}

    import agents.heuristics as h

    orig_cid = h.option_card_id
    orig_once = h._is_once_per_turn_ability
    h.option_card_id = lambda opt, sel, obs: 1  # a resolvable card id
    h._is_once_per_turn_ability = lambda cid: False  # not once-per-turn: unsafe
    try:
        assert opp_mod._safe_first_legal_index(sel, obs) == [1]
    finally:
        h.option_card_id = orig_cid
        h._is_once_per_turn_ability = orig_once


def test_gauntlet_vs_deck_opponent_runs_a_full_match():
    # Integration: the heuristic plays the trolley-deck opponent for two matches
    # with zero invalid moves. Needs the local engine + card data (skipped if the
    # cg/ competition package is not present, matching the gauntlet's assumption).
    pytest.importorskip("kaggle_environments")
    from tools.gauntlet import run_gauntlet

    stats = run_gauntlet("heuristic", ["deck:trolley"], 2)
    assert stats["matches"] == 2
    assert stats["wins"] + stats["draws"] + stats["losses"] == 2
    assert stats["invalid_moves"] == 0
    assert stats["decisions"] > 0


def test_gauntlet_vs_clone_opponent_runs_a_full_match():
    # Integration: the heuristic plays a clone: opponent (first-legal-plus-
    # safety, piloting a harvested top-team deck) for two matches with zero
    # invalid moves and no hang (the ability-loop veto's real job).
    pytest.importorskip("kaggle_environments")
    from tools.gauntlet import run_gauntlet

    fam = opponents.clone_family_names()[0]
    stats = run_gauntlet("heuristic", [f"clone:{fam}"], 2)
    assert stats["matches"] == 2
    assert stats["wins"] + stats["draws"] + stats["losses"] == 2
    assert stats["invalid_moves"] == 0
    assert stats["decisions"] > 0
