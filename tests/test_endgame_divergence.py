"""Tests for tools/endgame_divergence.py (plan S2: endgame PLAY divergence at scale).

Covers, over synthetic fixtures only, no cg engine, no episode data:
  1. phase_of's near_endgame / mid / early split (and the unknown fallback),
  2. state_of's extraction of hand/bench/prize/deck from a synthetic observation,
  3. describe_choice's category+card/attack naming (and its NONE / fallback paths),
  4. median_signature,
  5. aggregate: the phase-by-category table, the PLAY headline numbers, and the
     top-N near-endgame PLAY divergence pattern list with counts and signatures.

A second, cg-gated block (pytest.importorskip("kaggle_environments")) exercises
our_choice_index and build_decision_record against the real pilot on a minimal
synthetic obs, so the live-wiring half of the module is covered too when the
card engine is available, without making it a hard requirement for the suite.
"""
import pytest

from tools import endgame_divergence as ed


# --- phase_of -----------------------------------------------------------------

def test_phase_of_near_endgame_when_either_side_low():
    assert ed.phase_of(2, 6) == "near_endgame"
    assert ed.phase_of(6, 0) == "near_endgame"
    assert ed.phase_of(0, 0) == "near_endgame"


def test_phase_of_early_when_neither_side_has_taken_a_prize():
    assert ed.phase_of(6, 6) == "early"
    assert ed.phase_of(5, 6) == "early"
    assert ed.phase_of(6, 5) == "early"


def test_phase_of_mid_otherwise():
    assert ed.phase_of(4, 6) == "mid"
    assert ed.phase_of(3, 3) == "mid"
    assert ed.phase_of(4, 4) == "mid"


def test_phase_of_boundary_values_exact():
    assert ed.phase_of(2, 5) == "near_endgame"  # min=2 -> near_endgame wins
    assert ed.phase_of(3, 5) == "mid"           # min=3 -> mid
    assert ed.phase_of(5, 3) == "mid"           # order-independent (min)


def test_phase_of_unknown_on_missing_or_bad_input():
    assert ed.phase_of(None, 3) == "unknown"
    assert ed.phase_of(3, None) == "unknown"
    assert ed.phase_of(True, 3) == "unknown"  # bool is not a real prize count


# --- state_of -------------------------------------------------------------

def _obs(your_index, me, opp):
    return {"current": {"yourIndex": your_index, "players": [me, opp] if your_index == 0 else [opp, me]}}


def test_state_of_reads_all_fields():
    me = {"hand": [1, 2, 3], "bench": [1], "prize": [1, 2], "deckCount": 12}
    opp = {"prize": [1, 2, 3, 4]}
    obs = _obs(0, me, opp)
    st = ed.state_of(obs)
    assert st == {"hand_size": 3, "bench_count": 1, "prize_me": 2,
                  "prize_opp": 4, "deck_count": 12}


def test_state_of_reads_seat_1_perspective_correctly():
    me = {"hand": [], "bench": [], "prize": [1], "deckCount": 0}
    opp = {"prize": [1, 2, 3, 4, 5, 6]}
    obs = _obs(1, me, opp)
    st = ed.state_of(obs)
    assert st["prize_me"] == 1
    assert st["prize_opp"] == 6


def test_state_of_defensive_on_malformed_input():
    assert ed.state_of({}) == {"hand_size": None, "bench_count": None,
                                "prize_me": None, "prize_opp": None, "deck_count": None}
    assert ed.state_of({"current": {"yourIndex": 5, "players": [{}]}}) == {
        "hand_size": None, "bench_count": None, "prize_me": None,
        "prize_opp": None, "deck_count": None,
    }
    assert ed.state_of({"current": {"yourIndex": True, "players": [{}]}})["hand_size"] is None


# --- describe_choice ------------------------------------------------------

_CARD = type("Card", (), {})()
_CARD.name = "Pikachu ex"
_ATK = type("Attack", (), {})()
_ATK.name = "Thunderbolt"


def test_describe_choice_play_with_known_card():
    resolved = {"category": "PLAY", "card_id": 42, "attack_id": None}
    assert ed.describe_choice(resolved, {42: _CARD}, {}) == "PLAY Pikachu ex"


def test_describe_choice_attack_uses_attack_index_not_card_index():
    resolved = {"category": "ATTACK", "card_id": 99, "attack_id": 7}
    assert ed.describe_choice(resolved, {99: _CARD}, {7: _ATK}) == "ATTACK Thunderbolt"


def test_describe_choice_unknown_card_falls_back_to_id():
    resolved = {"category": "PLAY", "card_id": 999, "attack_id": None}
    assert ed.describe_choice(resolved, {}, {}) == "PLAY card:999"


def test_describe_choice_unknown_attack_falls_back_to_id():
    resolved = {"category": "ATTACK", "card_id": None, "attack_id": 55}
    assert ed.describe_choice(resolved, {}, {}) == "ATTACK attack:55"


def test_describe_choice_no_card_id_is_bare_category():
    resolved = {"category": "END", "card_id": None, "attack_id": None}
    assert ed.describe_choice(resolved, {}, {}) == "END"


def test_describe_choice_none_input():
    assert ed.describe_choice(None, {}, {}) == "NONE"


# --- median_signature -------------------------------------------------------

def test_median_signature_computes_medians_and_count():
    rows = [
        {"hand_size": 4, "bench_count": 2, "prize_me": 2, "prize_opp": 1, "deck_count": 10},
        {"hand_size": 6, "bench_count": 4, "prize_me": 2, "prize_opp": 1, "deck_count": 20},
    ]
    sig = ed.median_signature(rows)
    assert "hand=5.0" in sig
    assert "bench=3.0" in sig
    assert "prizes us=2.0/opp=1.0" in sig
    assert "deck=15.0" in sig
    assert "n=2" in sig


def test_median_signature_skips_missing_fields():
    rows = [{"hand_size": None, "bench_count": 1, "prize_me": 1, "prize_opp": 1, "deck_count": None}]
    sig = ed.median_signature(rows)
    assert "hand=None" in sig
    assert "deck=None" in sig


# --- aggregate ----------------------------------------------------------------

def _rec(phase, expert_cat, agree, expert_desc="PLAY Card A", our_desc="PLAY Card A",
         hand=5, bench=2, prize_me=2, prize_opp=1, deck=10):
    return {
        "phase": phase, "expert_category": expert_cat, "our_category": expert_cat if agree else "OTHER",
        "agree": agree, "expert_desc": expert_desc, "our_desc": our_desc,
        "hand_size": hand, "bench_count": bench, "prize_me": prize_me,
        "prize_opp": prize_opp, "deck_count": deck,
    }


def test_aggregate_empty_is_all_zero():
    r = ed.aggregate([])
    assert r["total_n"] == 0
    assert r["overall_agreement"] is None
    assert r["top_patterns"] == []
    assert r["near_endgame_play"]["n"] == 0


def test_aggregate_phase_by_category_table_counts_correctly():
    records = [
        _rec("early", "PLAY", True),
        _rec("early", "PLAY", False),
        _rec("near_endgame", "PLAY", False, expert_desc="PLAY Card B", our_desc="ATTACK Move X"),
        _rec("near_endgame", "ATTACK", True, expert_desc="ATTACK Move Y", our_desc="ATTACK Move Y"),
    ]
    r = ed.aggregate(records)
    assert r["total_n"] == 4
    assert r["total_agree"] == 2
    assert r["overall_agreement"] == pytest.approx(0.5)
    assert r["table"]["early"]["PLAY"]["n"] == 2
    assert r["table"]["early"]["PLAY"]["agree"] == 1
    assert r["table"]["near_endgame"]["PLAY"]["n"] == 1
    assert r["table"]["near_endgame"]["ATTACK"]["n"] == 1
    assert r["phase_totals"]["near_endgame"]["n"] == 2


def test_aggregate_play_headline_numbers():
    records = [
        _rec("early", "PLAY", True),
        _rec("mid", "PLAY", True),
        _rec("near_endgame", "PLAY", False),
        _rec("near_endgame", "PLAY", False),
    ]
    r = ed.aggregate(records)
    # overall PLAY: 2 agree / 4 total = 0.5
    assert r["overall_play"]["n"] == 4
    assert r["overall_play"]["agreement"] == pytest.approx(0.5)
    # near-endgame PLAY: 0 agree / 2 total = 0.0
    assert r["near_endgame_play"]["n"] == 2
    assert r["near_endgame_play"]["agreement"] == pytest.approx(0.0)
    assert r["play_agreement_drop_pp"] == pytest.approx(50.0)


def test_aggregate_play_share_of_near_endgame_disagreement():
    records = [
        _rec("near_endgame", "PLAY", False),      # PLAY disagreement
        _rec("near_endgame", "ATTACK", False),    # non-PLAY disagreement
        _rec("near_endgame", "RETREAT", True),    # agreement, not counted
    ]
    r = ed.aggregate(records)
    assert r["near_endgame_disagreements_total"] == 2
    assert r["near_endgame_play_disagreements"] == 1
    assert r["play_share_of_near_endgame_disagreement"] == pytest.approx(0.5)


def test_aggregate_ignores_non_near_endgame_and_non_play_for_patterns():
    records = [
        _rec("mid", "PLAY", False, expert_desc="PLAY Card C", our_desc="PLAY Card D"),
        _rec("near_endgame", "ATTACK", False, expert_desc="ATTACK Move Z", our_desc="END"),
        _rec("near_endgame", "PLAY", True, expert_desc="PLAY Card E", our_desc="PLAY Card E"),
    ]
    r = ed.aggregate(records)
    assert r["top_patterns"] == []


def test_aggregate_pattern_counts_and_sorts_by_count_desc():
    records = (
        [_rec("near_endgame", "PLAY", False, expert_desc="PLAY A", our_desc="ATTACK X")] * 3
        + [_rec("near_endgame", "PLAY", False, expert_desc="PLAY B", our_desc="RETREAT")] * 5
        + [_rec("near_endgame", "PLAY", False, expert_desc="PLAY C", our_desc="END")] * 1
    )
    r = ed.aggregate(records)
    counts = [p["count"] for p in r["top_patterns"]]
    assert counts == [5, 3, 1]
    assert r["top_patterns"][0]["expert_did"] == "PLAY B"
    assert r["top_patterns"][0]["we_would_do"] == "RETREAT"
    assert r["distinct_near_endgame_play_divergence_patterns"] == 3


def test_aggregate_top_patterns_capped_at_ten():
    records = []
    for i in range(15):
        records.append(_rec("near_endgame", "PLAY", False,
                             expert_desc=f"PLAY Card {i}", our_desc="END"))
    r = ed.aggregate(records)
    assert len(r["top_patterns"]) == 10
    assert r["distinct_near_endgame_play_divergence_patterns"] == 15


def test_aggregate_pattern_ties_break_alphabetically():
    records = [
        _rec("near_endgame", "PLAY", False, expert_desc="PLAY Zebra", our_desc="END"),
        _rec("near_endgame", "PLAY", False, expert_desc="PLAY Apple", our_desc="END"),
    ]
    r = ed.aggregate(records)
    assert [p["expert_did"] for p in r["top_patterns"]] == ["PLAY Apple", "PLAY Zebra"]


def test_aggregate_pattern_state_signature_present():
    records = [_rec("near_endgame", "PLAY", False, hand=4, bench=1, prize_me=2, prize_opp=1, deck=8)]
    r = ed.aggregate(records)
    assert "hand=4" in r["top_patterns"][0]["state_signature"]
    assert "prizes us=2/opp=1" in r["top_patterns"][0]["state_signature"]


# --- cg-gated: the live pilot wiring -----------------------------------------

def test_our_choice_index_restores_flags_after_use():
    pytest.importorskip("kaggle_environments")
    from agents import heuristics as H

    orig_ability, orig_threat = H._ABILITY, H._THREAT_RETREAT
    ed.our_choice_index({"select": None})  # deck-selection path: no MAIN decision
    assert H._ABILITY == orig_ability
    assert H._THREAT_RETREAT == orig_threat


def test_our_choice_index_patches_both_flags_true_during_the_call(monkeypatch):
    pytest.importorskip("kaggle_environments")
    from agents import heuristics as H

    seen = {}

    def fake_choose(obs):
        seen["ability"] = H._ABILITY
        seen["threat_retreat"] = H._THREAT_RETREAT
        return [0]

    monkeypatch.setattr(H, "choose", fake_choose)
    idx = ed.our_choice_index({"select": {"type": 0, "option": [{}]}})
    assert idx == 0
    assert seen == {"ability": True, "threat_retreat": True}


def test_our_choice_index_none_on_pilot_exception(monkeypatch):
    pytest.importorskip("kaggle_environments")
    from agents import heuristics as H

    def boom(obs):
        raise RuntimeError("pilot exploded")

    monkeypatch.setattr(H, "choose", boom)
    assert ed.our_choice_index({}) is None
