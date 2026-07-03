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

from agents.heuristics import attack_index, card_index, effective_damage  # noqa: E402
from analysis.matchup_delta import (  # noqa: E402
    best_matchup_index,
    can_knock_out,
    matchup_score,
)


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


def _find_attack_with_cost(cost):
    """(card_id, attack) with a positive-damage attack of exactly `cost` energy,
    derived from the bundled catalog."""
    atks = attack_index()
    for cid, c in card_index().items():
        for aid in getattr(c, "attacks", None) or []:
            attack = atks.get(aid)
            if attack is None:
                continue
            if (attack.damage or 0) > 0 and len(getattr(attack, "energies", None) or []) == cost:
                return cid, attack
    raise AssertionError(f"no attack with cost {cost} found in the bundled catalog")


def test_can_knock_out_true_when_cost_met_and_damage_lethal():
    attacker_id, attack = _find_attack_with_cost(0)
    opponent_id = next(cid for cid in card_index() if cid != attacker_id)
    dmg = effective_damage(attacker_id, attack, opponent_id)
    assert can_knock_out(attacker_id, 0, opponent_id, dmg) is True


def test_can_knock_out_false_when_damage_falls_short():
    attacker_id, attack = _find_attack_with_cost(0)
    opponent_id = next(cid for cid in card_index() if cid != attacker_id)
    dmg = effective_damage(attacker_id, attack, opponent_id)
    assert can_knock_out(attacker_id, 0, opponent_id, dmg + 1) is False


def test_can_knock_out_false_when_energy_cost_not_met():
    attacker_id, attack = _find_attack_with_cost(1)
    opponent_id = next(cid for cid in card_index() if cid != attacker_id)
    dmg = effective_damage(attacker_id, attack, opponent_id)
    assert can_knock_out(attacker_id, 0, opponent_id, dmg) is False


def test_can_knock_out_false_on_missing_ids():
    real_id = next(iter(card_index()))
    assert can_knock_out(None, 5, real_id, 10) is False
    assert can_knock_out(real_id, 5, None, 10) is False
    assert can_knock_out(real_id, 5, real_id, None) is False


def test_can_knock_out_false_for_unknown_card():
    real_id = next(iter(card_index()))
    assert can_knock_out(-999, 5, real_id, 1) is False
