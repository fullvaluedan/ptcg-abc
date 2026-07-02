"""The expert-cohort census primitives (plan U25).

analysis/expert_cohort defines ONE cohort (the winning seat) and the counts a
census folds per archetype family. These tests pin the properties the census
tool and the tier decision rely on, over synthetic replays so no cg engine or
competition data is touched:

  1. the cohort seat is the winner; a draw or a malformed reward drops the game,
  2. both seats' opening decklists are read from step0's visualize action,
  3. family classification assigns on signature COVERAGE above a threshold, so a
     staple overlap does not mislabel a deck as a meta pillar,
  4. per-episode counts split MAIN decisions (all) from ranking groups (the
     scorable multi-option single-pick ones a ranker learns from),
  5. aggregate folds rows into per-family and total counts and skips None rows,
  6. the pre-committed tiers map ranking-group counts to training decisions.
"""
from analysis import expert_cohort as ec

# A card-id vocabulary for synthetic decks. The two families share staple ids
# (90, 91) so the threshold test has something to reject; each has its own
# distinctive ids.
SIG_ALPHA = frozenset({10, 11, 12, 13})
SIG_BETA = frozenset({20, 21, 22, 23})
SIGNATURES = {"alpha": SIG_ALPHA, "beta": SIG_BETA}


def _deck(distinct_ids, filler=8):
    """A 60-card decklist: the distinctive ids, padded to 60 with basic energy."""
    deck = list(distinct_ids)
    return tuple(deck + [filler] * (ec.DECK_SIZE - len(deck)))


def _main_entry(seat, options, action_idx):
    """One ACTIVE MAIN decision record for `seat` with `options` and a played index.

    Mirrors the shape iter_expert_decisions and _count_main_decisions gate on:
    status ACTIVE, observation.select of type MAIN (single pick), current with
    the deciding seat, and the played action as a single-index list.
    """
    return {
        "status": "ACTIVE",
        "action": [action_idx] if action_idx is not None else [],
        "observation": {
            "select": {
                "type": ec.SEL_MAIN,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": 8} for _ in range(options)],
            },
            "current": {"yourIndex": seat},
        },
    }


def _replay(rewards, deck0, deck1, decision_steps=(), names=("A", "B")):
    """A minimal replay: rewards, TeamNames, opener decklists, and MAIN decisions.

    step0 carries both decklists in seat0's visualize action; each later step is
    a one-entry step holding a decision record.
    """
    step0 = [
        {"status": "ACTIVE", "visualize": [{"action": [list(deck0), list(deck1)]}]},
        {"status": "INACTIVE"},
    ]
    steps = [step0] + [[entry] for entry in decision_steps]
    return {"rewards": list(rewards), "info": {"TeamNames": list(names)}, "steps": steps}


def test_winner_seat_and_alias():
    assert ec.winner_seat(_replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_BETA))) == 0
    assert ec.winner_seat(_replay([-1, 1], _deck(SIG_ALPHA), _deck(SIG_BETA))) == 1
    # cohort_seat is the winning seat: the single resolved definition.
    assert ec.cohort_seat is ec.winner_seat


def test_draw_and_malformed_rewards_drop():
    d = _deck(SIG_ALPHA)
    assert ec.winner_seat(_replay([0, 0], d, d)) is None
    assert ec.winner_seat({"rewards": [1]}) is None
    assert ec.winner_seat({"rewards": None}) is None
    assert ec.winner_seat({}) is None
    # a bool reward is not a real score
    assert ec.winner_seat({"rewards": [True, False]}) is None


def test_seat_decklists_read_from_opener():
    d0, d1 = _deck(SIG_ALPHA), _deck(SIG_BETA)
    decks = ec.seat_decklists(_replay([1, -1], d0, d1))
    assert decks == (d0, d1)


def test_seat_decklists_reject_wrong_length():
    short = tuple([1] * 59)
    assert ec.seat_decklists(_replay([1, -1], short, _deck(SIG_BETA))) is None
    assert ec.seat_decklists({}) is None
    assert ec.seat_decklists({"steps": []}) is None


def test_team_names():
    assert ec.team_names(_replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_BETA))) == (
        "A",
        "B",
    )
    assert ec.team_names({"info": {"TeamNames": ["only"]}}) is None
    assert ec.team_names({}) is None


def test_classify_family_by_coverage():
    # Full signature present -> that family.
    assert ec.classify_family(_deck(SIG_ALPHA), SIGNATURES) == "alpha"
    assert ec.classify_family(_deck(SIG_BETA), SIGNATURES) == "beta"


def test_classify_family_staple_overlap_is_other():
    # One shared card from each family (25% coverage) is below the 0.35 default,
    # so a deck that only clips a staple is not mislabeled a pillar.
    deck = _deck([10, 20, 99, 98])
    assert ec.classify_family(deck, SIGNATURES) == "other"
    # ... but lowering the threshold lets a partial match assign.
    assert ec.classify_family(_deck([10, 11]), SIGNATURES, threshold=0.5) == "alpha"


def test_classify_family_empty_signatures():
    assert ec.classify_family(_deck(SIG_ALPHA), {}) == "other"
    assert ec.classify_family(_deck(SIG_ALPHA), {"x": frozenset()}) == "other"


def test_census_episode_counts():
    # Winner is seat 0 (alpha). Three MAIN decisions by seat 0: two scorable
    # ranking groups (>1 option, in-range single pick) and one forced single
    # option (counts as a MAIN decision but not a ranking group). Seat 1's
    # decision must not be counted.
    steps = [
        _main_entry(0, 3, 1),   # ranking group
        _main_entry(0, 2, 0),   # ranking group
        _main_entry(0, 1, 0),   # forced single option: MAIN but not a group
        _main_entry(1, 4, 2),   # loser seat: ignored
    ]
    rep = _replay([1, -1], _deck(SIG_ALPHA), _deck(SIG_BETA), decision_steps=steps)
    row = ec.census_episode(rep, SIGNATURES)
    assert row["seat"] == 0
    assert row["family"] == "alpha"
    assert row["team"] == "A"
    assert row["main_decisions"] == 3
    assert row["ranking_groups"] == 2


def test_census_episode_drops_draw():
    d = _deck(SIG_ALPHA)
    assert ec.census_episode(_replay([0, 0], d, d), SIGNATURES) is None


def test_aggregate_folds_and_skips_none():
    rows = [
        {"seat": 0, "team": "A", "family": "alpha", "main_decisions": 5, "ranking_groups": 3},
        {"seat": 1, "team": "B", "family": "alpha", "main_decisions": 4, "ranking_groups": 2},
        {"seat": 0, "team": "A", "family": "beta", "main_decisions": 2, "ranking_groups": 1},
        None,  # a dropped draw / malformed episode
    ]
    agg = ec.aggregate(rows)
    assert agg["episodes"] == 3
    assert agg["skipped"] == 1
    assert agg["by_family"]["alpha"] == {
        "episodes": 2,
        "main_decisions": 9,
        "ranking_groups": 5,
    }
    assert agg["by_family"]["beta"]["ranking_groups"] == 1
    assert agg["ranking_groups"] == 6
    assert agg["main_decisions"] == 11
    assert agg["teams"] == {"A": 2, "B": 1}


def test_tier_thresholds():
    assert ec.tier_for(ec.TIER_FULL_MIN) == "full"
    assert ec.tier_for(ec.TIER_FULL_MIN - 1) == "winners_pooled"
    assert ec.tier_for(ec.TIER_POOL_MIN) == "winners_pooled"
    assert ec.tier_for(ec.TIER_POOL_MIN - 1) == "kill"
    assert ec.tier_for(0) == "kill"
