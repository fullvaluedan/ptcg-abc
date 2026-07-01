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
    # Every deck on disk is offered as a deck:<stem> opponent.
    assert all(n.startswith("deck:") for n in ns if n not in opponents.BUILTINS)
    assert "deck:trolley" in ns  # a known committed deck


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
