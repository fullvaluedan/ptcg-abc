"""Tests for analysis/matchup_delta.py.

Derives real card ids with the needed weakness/resistance/type relationships
from the bundled catalog at test time (mirroring test_heuristic.py's
test_lethal_attack_is_taken), so the tests stay correct against the real card
data instead of hardcoding ids that could drift.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agents.heuristics import card_index  # noqa: E402
from analysis.matchup_delta import best_matchup_index, matchup_score  # noqa: E402


def _find_weak_pair():
    """(attacker_id, defender_id) where defender.weakness == attacker.energyType."""
    cards = card_index()
    for defender_id, dfn in cards.items():
        if dfn.weakness is None:
            continue
        for attacker_id, atk in cards.items():
            if atk.energyType == dfn.weakness and attacker_id != defender_id:
                return attacker_id, defender_id
    raise AssertionError("no weakness pair found in the bundled catalog")


def _find_resist_pair():
    """(attacker_id, defender_id) where defender.resistance == attacker.energyType."""
    cards = card_index()
    for defender_id, dfn in cards.items():
        if dfn.resistance is None:
            continue
        for attacker_id, atk in cards.items():
            if atk.energyType == dfn.resistance and attacker_id != defender_id:
                return attacker_id, defender_id
    raise AssertionError("no resistance pair found in the bundled catalog")


def test_weakness_favors_the_attacker():
    attacker_id, defender_id = _find_weak_pair()
    assert matchup_score(attacker_id, defender_id) > 0
    # symmetric: from the defender's side this is an unfavorable matchup.
    assert matchup_score(defender_id, attacker_id) < 0


def test_resistance_favors_the_defender():
    attacker_id, defender_id = _find_resist_pair()
    assert matchup_score(attacker_id, defender_id) < 0
    assert matchup_score(defender_id, attacker_id) > 0


def test_unknown_card_id_is_neutral():
    assert matchup_score(-1, -2) == 0
    real_id = next(iter(card_index()))
    assert matchup_score(real_id, -1) == 0
    assert matchup_score(-1, real_id) == 0


def test_no_weakness_or_resistance_either_side_is_neutral():
    cards = card_index()
    mine_id, other_id = next(
        (a, b)
        for a, ca in cards.items()
        for b, cb in cards.items()
        if a != b and ca.weakness is None and ca.resistance is None
        and cb.weakness is None and cb.resistance is None
    )
    assert matchup_score(mine_id, other_id) == 0


def test_best_matchup_index_picks_the_favorable_candidate():
    attacker_id, defender_id = _find_weak_pair()
    neutral_id = next(
        cid for cid, c in card_index().items()
        if c.hp and cid not in (attacker_id, defender_id)
        and matchup_score(cid, defender_id) <= 0
    )
    idx = best_matchup_index([neutral_id, attacker_id], defender_id)
    assert idx == 1


def test_best_matchup_index_empty_is_none():
    assert best_matchup_index([], 1) is None


def test_best_matchup_index_ties_keep_first():
    real_id = next(iter(card_index()))
    assert best_matchup_index([real_id, real_id], real_id) == 0
