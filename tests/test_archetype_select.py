"""The mastery-scored archetype target selector (plan U36).

tools/archetype_select picks the target family by MASTERY = wins * win_rate,
folding in the losing appearances the census (U25) drops. These tests pin the
scoring primitives over synthetic replays so no cg engine or competition data is
touched:

  1. mastery_rows classifies BOTH seats and marks the winner, unlike the
     census which credits only the winning seat,
  2. a draw / malformed reward / unreadable opener drops the episode,
  3. aggregate folds two-seat rows into per-family games and wins, skips None,
  4. mastery = wins * win_rate, so a popular-but-mediocre family loses to a
     less-played family with a higher win rate,
  5. rank_families sorts by mastery and marks "other" and thin families
     ineligible; select_target returns the top eligible family.
"""
from analysis import expert_cohort as ec
from tools import archetype_select as asel

# Two families share no distinctive ids; each has its own signature.
SIG_ALPHA = frozenset({10, 11, 12, 13})
SIG_BETA = frozenset({20, 21, 22, 23})
SIGNATURES = {"alpha": SIG_ALPHA, "beta": SIG_BETA}


def _deck(distinct_ids, filler=8):
    """A 60-card decklist: the distinctive ids, padded to 60 with basic energy."""
    deck = list(distinct_ids)
    return tuple(deck + [filler] * (ec.DECK_SIZE - len(deck)))


def _replay(rewards, deck0, deck1, names=("A", "B")):
    """A minimal decided replay: rewards, TeamNames, and both opener decklists."""
    step0 = [
        {"status": "ACTIVE", "visualize": [{"action": [list(deck0), list(deck1)]}]},
        {"status": "INACTIVE"},
    ]
    return {"rewards": list(rewards), "info": {"TeamNames": list(names)}, "steps": [step0]}


def test_mastery_rows_classifies_both_seats_with_winner():
    # Seat 0 (alpha) wins, seat 1 (beta) loses.
    rows = asel.mastery_rows(
        _replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_BETA)), SIGNATURES
    )
    assert rows == [
        {"family": "alpha", "won": True, "team": "A"},
        {"family": "beta", "won": False, "team": "B"},
    ]
    # Winner on the other seat flips the won flags.
    rows = asel.mastery_rows(
        _replay([-1, 1], _deck(SIG_ALPHA), _deck(SIG_BETA)), SIGNATURES
    )
    assert rows[0]["won"] is False
    assert rows[1]["won"] is True


def test_mastery_rows_drops_draw_and_malformed():
    d = _deck(SIG_ALPHA)
    assert asel.mastery_rows(_replay([0, 0], d, d), SIGNATURES) is None
    assert asel.mastery_rows({"rewards": [1]}, SIGNATURES) is None
    # Decided reward but unreadable opener drops too.
    assert asel.mastery_rows({"rewards": [1, -1], "steps": []}, SIGNATURES) is None


def test_aggregate_folds_games_and_wins_and_skips_none():
    rows = [
        [
            {"family": "alpha", "won": True, "team": "A"},
            {"family": "beta", "won": False, "team": "B"},
        ],
        [
            {"family": "alpha", "won": False, "team": "C"},
            {"family": "beta", "won": True, "team": "D"},
        ],
        None,  # dropped draw
    ]
    agg = asel.aggregate(rows)
    assert agg["episodes"] == 2
    assert agg["skipped"] == 1
    assert agg["by_family"]["alpha"] == {"games": 2, "wins": 1}
    assert agg["by_family"]["beta"] == {"games": 2, "wins": 1}


def test_mastery_score_penalizes_popularity_without_win_rate():
    # popular: many wins but a coin-flip win rate. sharp: fewer wins, high rate.
    popular = {"games": 1000, "wins": 500}   # wr 0.50, mastery 250.0
    sharp = {"games": 400, "wins": 320}      # wr 0.80, mastery 256.0
    assert asel.win_rate(popular) == 0.5
    assert asel.mastery_score(sharp) > asel.mastery_score(popular)
    # zero games is safe (no division), zero mastery.
    assert asel.win_rate({"games": 0, "wins": 0}) == 0.0
    assert asel.mastery_score({"games": 0, "wins": 0}) == 0.0


def test_rank_and_select_target():
    report = {
        "by_family": {
            "popular": {"games": 1000, "wins": 500},   # eligible, mastery 250.0
            "sharp": {"games": 400, "wins": 320},      # eligible, mastery 256.0
            "thin": {"games": 10, "wins": 10},         # ineligible: under min_games
            "other": {"games": 800, "wins": 700},      # ineligible: grab-bag
        }
    }
    ranking = asel.rank_families(report, min_games=50)
    # Sorted by mastery descending: other (612.5) then sharp then popular then thin.
    assert [r["family"] for r in ranking] == ["other", "sharp", "popular", "thin"]
    # "other" tops mastery but is not eligible; thin is under min_games.
    assert next(r for r in ranking if r["family"] == "other")["eligible"] is False
    assert next(r for r in ranking if r["family"] == "thin")["eligible"] is False
    # The selector picks the highest-mastery ELIGIBLE family, disagreeing with a
    # pure popularity/volume ranking.
    assert asel.select_target(ranking) == "sharp"


def test_select_target_none_when_no_eligible():
    report = {"by_family": {"other": {"games": 900, "wins": 800}, "thin": {"games": 3, "wins": 3}}}
    ranking = asel.rank_families(report, min_games=50)
    assert asel.select_target(ranking) is None


def test_rank_and_select_break_mastery_ties_by_name():
    # Two eligible families with IDENTICAL mastery: the name-ascending secondary
    # sort is the only thing that makes target selection reproducible.
    report = {
        "by_family": {
            "zeta": {"games": 100, "wins": 50},
            "alpha": {"games": 100, "wins": 50},
        }
    }
    ranking = asel.rank_families(report, min_games=50)
    assert [r["family"] for r in ranking] == ["alpha", "zeta"]
    assert asel.select_target(ranking) == "alpha"


def test_eligibility_is_inclusive_at_min_games():
    # games == min_games is eligible (>=); one below is not.
    report = {
        "by_family": {
            "edge": {"games": 50, "wins": 40},
            "under": {"games": 49, "wins": 40},
        }
    }
    ranking = asel.rank_families(report, min_games=50)
    assert next(r for r in ranking if r["family"] == "edge")["eligible"] is True
    assert next(r for r in ranking if r["family"] == "under")["eligible"] is False


def test_empty_report_ranks_empty_and_selects_none():
    # An all-dropped dataset (bad zip / all draws) yields no families.
    ranking = asel.rank_families({"by_family": {}})
    assert ranking == []
    assert asel.select_target(ranking) is None


def test_mastery_rows_team_none_when_names_unreadable():
    # Valid decided episode but malformed TeamNames: rows still return, team None.
    rep = _replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_BETA), names=("only",))
    rows = asel.mastery_rows(rep, SIGNATURES)
    assert [r["family"] for r in rows] == ["alpha", "beta"]
    assert [r["won"] for r in rows] == [True, False]
    assert [r["team"] for r in rows] == [None, None]


def test_scoring_helpers_handle_empty_stats():
    # The defensive .get defaults promise 0.0 on a partial/empty stats dict.
    assert asel.win_rate({}) == 0.0
    assert asel.mastery_score({}) == 0.0
