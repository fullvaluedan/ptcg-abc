"""Tests for tools/top50_loss_modes.py's classifier decontamination (plan:
classifier decontamination + verified corrections).

analysis.expert_cohort.classify_family scores a decklist's coverage of a
family signature; a signature built from a full representative decklist
includes generic format staples that appear in most top-50 decks regardless
of archetype, which can clear the coverage threshold on staple overlap alone
with zero archetype-defining cards in common (verified real cases: nasuo445's
Cynthia's Garchomp ex toolbox, ZETADIVISION's Dragapult ex toolbox, both
misclassified as meta_grimmsnarl_tonakaiiii). These tests pin
decontaminate_signatures' contract without touching analysis/expert_cohort.py
or reading any episode data.
"""
from tools import top50_loss_modes as lm


def test_staple_card_ids_is_a_real_nonempty_set():
    assert len(lm.STAPLE_CARD_IDS) == 16
    assert all(isinstance(cid, int) for cid in lm.STAPLE_CARD_IDS)


def test_decontaminate_signatures_strips_staples_from_every_family():
    staple = next(iter(lm.STAPLE_CARD_IDS))
    signatures = {
        "alpha": frozenset({1, 2, 3}) | lm.STAPLE_CARD_IDS,
        "beta": frozenset({10, 11}) | {staple},
    }
    out = lm.decontaminate_signatures(signatures)
    assert out["alpha"] == frozenset({1, 2, 3})
    assert out["beta"] == frozenset({10, 11})
    assert staple not in out["alpha"]
    assert staple not in out["beta"]


def test_decontaminate_signatures_never_mutates_input():
    signatures = {"alpha": frozenset({1, 2}) | lm.STAPLE_CARD_IDS}
    original = dict(signatures)
    lm.decontaminate_signatures(signatures)
    assert signatures == original


def test_decontaminate_signatures_all_staple_family_becomes_empty_not_an_error():
    signatures = {"alpha": frozenset(lm.STAPLE_CARD_IDS)}
    out = lm.decontaminate_signatures(signatures)
    assert out["alpha"] == frozenset()


def test_decontaminated_classify_family_rejects_staple_only_overlap():
    """The concrete defect: a deck that shares ONLY staples with a family
    signature clears the raw 0.35 threshold but must NOT clear it once
    decontaminated (mirrors the verified nasuo445 / ZETADIVISION cases,
    without reading any real decklist)."""
    from analysis.expert_cohort import classify_family

    staples = list(lm.STAPLE_CARD_IDS)[:6]
    family_signature = frozenset({900, 901, 902, 903}) | frozenset(staples)  # 4 defining + 6 staples
    raw_signatures = {"alpha": family_signature}

    # A deck with 6 of the 10 raw-signature cards (all staples, 0 defining
    # cards): raw coverage 6/10 = 0.6, clears the default 0.35 threshold.
    deck = list(staples) + [8] * 54
    assert classify_family(deck, raw_signatures) == "alpha"

    # Decontaminated: signature shrinks to the 4 defining cards, none of which
    # this deck has, so coverage is 0/4 = 0.0 and it correctly falls to "other".
    decontam = lm.decontaminate_signatures(raw_signatures)
    assert classify_family(deck, decontam) == "other"


def test_decontaminated_classify_family_still_accepts_a_real_pilot():
    """A deck that actually plays the family's defining cards (plus staples)
    must still classify correctly after decontamination -- the fix should not
    make the classifier unable to recognize a genuine archetype pilot."""
    from analysis.expert_cohort import classify_family

    staples = list(lm.STAPLE_CARD_IDS)[:6]
    family_signature = frozenset({900, 901, 902, 903}) | frozenset(staples)
    decontam = lm.decontaminate_signatures({"alpha": family_signature})

    real_pilot_deck = [900, 901, 902, 903] + list(staples) + [8] * 50
    assert classify_family(real_pilot_deck, decontam) == "alpha"
