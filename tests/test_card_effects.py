"""Tests for the card-effect knowledge layer and its coverage meter (U33).

The load-bearing test is test_pool_wide_equivalence_*: it pins the delegated
heuristic predicates to a FROZEN copy of the legacy inline text scan, card-for-card
over the entire pool. That is what makes the U33 delegation behavior-frozen: a tag
definition may not drift the boolean any predicate returned before, so the ladder
build stays byte-identical while the knowledge moves into one named layer.
"""
import re

from agents import card_effects, heuristics
from tools import tag_coverage

# Card ids reused from the heuristic tests (real pool cards).
PRECIOUS_TROLLEY = 1126   # search deck -> Basic onto Bench
MEGA_SIGNAL = 1145        # search -> into your hand
ULTRA_BALL = 1121         # discard from hand, search -> into your hand
CYRANO = 1205             # search -> into your hand
LILLIES = 1227            # draw 6
WAITRESS = 1235           # attach a Basic Energy from the top 6
KYOGRE = 721              # vanilla Basic, no effect text
BASIC_W_ENERGY = 3        # basic energy, no effect text
NIGHT_STRETCHER = 1097    # discard pile -> hand recovery
ABILITY_ONCE = 66         # once-during-your-turn ability
ABILITY_REPEATABLE = 28   # repeatable ability


# ---- tag_text unit behavior -------------------------------------------------

def test_tag_text_none_and_empty_are_empty():
    assert card_effects.tag_text(None) == frozenset()
    assert card_effects.tag_text("") == frozenset()


def test_tag_text_draw():
    assert card_effects.DRAW in card_effects.tag_text("Draw 6 cards.")
    # \bdraw must not fire on "withdraw" (a switch, no deck drill).
    assert card_effects.DRAW not in card_effects.tag_text("Withdraw the Pokemon.")


def test_tag_text_search_to_hand_and_bench():
    trolley = heuristics._card_text(PRECIOUS_TROLLEY)
    tags = card_effects.tag_text(trolley)
    assert card_effects.BENCH_BASIC_FROM_DECK in tags
    signal = card_effects.tag_text(heuristics._card_text(MEGA_SIGNAL))
    assert card_effects.SEARCH_TO_HAND in signal


def test_tag_text_recovers_from_discard_not_touching_deck():
    tags = card_effects.tag_text(heuristics._card_text(NIGHT_STRETCHER))
    assert card_effects.RECOVERS_FROM_DISCARD in tags
    assert card_effects.DRAW not in tags


def test_tag_text_energy_accel():
    assert card_effects.ENERGY_ACCEL in card_effects.tag_text(
        heuristics._card_text(WAITRESS)
    )


def test_tag_text_once_per_turn():
    assert card_effects.ONCE_PER_TURN in card_effects.tag_text(
        heuristics._card_text(ABILITY_ONCE)
    )
    assert card_effects.ONCE_PER_TURN not in card_effects.tag_text(
        heuristics._card_text(ABILITY_REPEATABLE)
    )


def test_all_tags_are_in_vocab():
    # Every tag any pool card produces must be a declared vocab member.
    for cid in heuristics.card_index():
        assert card_effects.tag_text(heuristics._card_text(cid)) <= card_effects.TAG_VOCAB


# ---- three-state resolution -------------------------------------------------

def test_resolve_unknown_card():
    state, tags = card_effects.resolve(False, None)
    assert state == card_effects.UNKNOWN_CARD and tags == frozenset()


def test_resolve_empty_vanilla():
    state, tags = card_effects.resolve(True, None)
    assert state == card_effects.EMPTY and tags == frozenset()
    assert card_effects.is_covered(state)


def test_resolve_tagged():
    state, tags = card_effects.resolve(True, "Draw 3 cards.")
    assert state == card_effects.TAGGED and card_effects.DRAW in tags
    assert card_effects.is_covered(state)


def test_resolve_untagged_effect():
    state, tags = card_effects.resolve(True, "Flip a coin. Nothing we tag.")
    assert state == card_effects.UNTAGGED_EFFECT and tags == frozenset()
    assert not card_effects.is_covered(state)


# ---- golden pool-wide equivalence (behavior freeze) -------------------------
# Frozen copies of the legacy inline text scans the heuristic predicates used
# before U33 delegated them. If these fall out of sync with the tag layer over ANY
# pool card, the delegation changed behavior and the build is no longer identical.

_CONSERVED = heuristics.CONSERVED_TRAINER_TYPES


def _legacy_drills_deck(card_id) -> bool:
    if heuristics._card_type(card_id) not in _CONSERVED:
        return False
    text = heuristics._card_text(card_id)
    if text is None:
        return True
    t = text.lower()
    recovers_from_discard = (
        "from your discard pile" in t
        and "into your hand" in t
        and "your deck" not in t
    )
    discards_from_deck = "discard" in t and (
        "of your deck" in t or "your deck for" in t
    )
    return (
        bool(re.search(r"\bdraw", t))
        or ("into your hand" in t and not recovers_from_discard)
        or discards_from_deck
    )


def _legacy_benches_basic_from_deck(card_id) -> bool:
    if heuristics._card_type(card_id) not in _CONSERVED:
        return False
    text = heuristics._card_text(card_id)
    if not text:
        return False
    t = text.lower()
    return (
        "search your deck" in t
        and "onto your bench" in t
        and "basic" in t
        and "pok" in t
    )


def _legacy_evolves_basic_to_stage2(card_id) -> bool:
    if heuristics._card_type(card_id) not in _CONSERVED:
        return False
    text = heuristics._card_text(card_id)
    if not text:
        return False
    t = text.lower()
    return "stage 2" in t and "skipping the stage 1" in t


def _legacy_is_once_per_turn_ability(card_id) -> bool:
    text = heuristics._card_text(card_id)
    if not text:
        return False
    return "once during your turn" in text.lower()


def test_pool_wide_equivalence_all_four_predicates():
    ids = list(heuristics.card_index().keys())
    assert len(ids) > 100  # the real pool loaded, not a stub
    mismatches = []
    for cid in ids:
        pairs = (
            (heuristics._drills_deck(cid), _legacy_drills_deck(cid), "drills"),
            (heuristics._benches_basic_from_deck(cid),
             _legacy_benches_basic_from_deck(cid), "bench"),
            (heuristics._evolves_basic_to_stage2(cid),
             _legacy_evolves_basic_to_stage2(cid), "candy"),
            (heuristics._is_once_per_turn_ability(cid),
             _legacy_is_once_per_turn_ability(cid), "ability"),
        )
        for new, old, label in pairs:
            if new != old:
                mismatches.append((cid, label, new, old))
    assert not mismatches, f"delegation drifted on {mismatches[:10]}"


# ---- drift lock -------------------------------------------------------------

def test_tags_version_and_vocab_locked():
    # A change to the vocabulary or the version must break this lock, forcing a
    # deliberate re-triage (mirrors the engine-drift STATE LOCK).
    assert card_effects.TAGS_VERSION == "2"
    assert card_effects.TAG_VOCAB == frozenset({
        "DRAW",
        "SEARCH_TO_HAND",
        "RECOVERS_FROM_DISCARD",
        "DISCARDS_FROM_DECK",
        "BENCH_BASIC_FROM_DECK",
        "RARE_CANDY_EVOLVE",
        "ENERGY_ACCEL",
        "ONCE_PER_TURN",
        "ON_EVOLVE_TRIGGER",
        "ATTACK_INHERITANCE",
        "SETUP_FACEDOWN",
        "HP_BOOST",
        "OPPONENT_BENCH_SWITCH",
        "DAMAGE_REDUCTION",
        "ENERGY_RECYCLE_TO_DECK",
        "OPPONENT_HAND_DISRUPTION",
        "STADIUM_SEARCH_TO_HAND",
    })


# ---- v2 tags (U90): meta-deck coverage gap + on-evolve trigger --------------

ARCHALUDON_EX = 190          # on-evolve: Assemble Alloy
GRIMMSNARL_EX = 648          # on-evolve: Punk Up
RELICANTH = 57               # attack inheritance
CINDERACE = 666              # setup face-down
HEROS_CAPE = 1159            # +100 HP tool
BOSSES_ORDERS = 1182         # gust the opponent's bench
FULL_METAL_LAB = 1244        # stadium damage reduction
ENERGY_RECYCLER = 1139       # energy discard pile -> deck
XEROSICS_MACHINATIONS = 1197  # opponent hand disruption
SPIKEMUTH_GYM = 1259         # stadium search -> either player's hand


def test_tag_text_on_evolve_trigger():
    for cid in (ARCHALUDON_EX, GRIMMSNARL_EX):
        tags = card_effects.tag_text(heuristics._card_text(cid))
        assert card_effects.ON_EVOLVE_TRIGGER in tags
        # Both were already TAGGED via ENERGY_ACCEL; the new tag adds the
        # on-evolve semantic without displacing the existing one.
        assert card_effects.ENERGY_ACCEL in tags


def test_tag_text_v2_meta_deck_gap_cards():
    checks = (
        (RELICANTH, card_effects.ATTACK_INHERITANCE),
        (CINDERACE, card_effects.SETUP_FACEDOWN),
        (HEROS_CAPE, card_effects.HP_BOOST),
        (BOSSES_ORDERS, card_effects.OPPONENT_BENCH_SWITCH),
        (FULL_METAL_LAB, card_effects.DAMAGE_REDUCTION),
        (ENERGY_RECYCLER, card_effects.ENERGY_RECYCLE_TO_DECK),
        (XEROSICS_MACHINATIONS, card_effects.OPPONENT_HAND_DISRUPTION),
        (SPIKEMUTH_GYM, card_effects.STADIUM_SEARCH_TO_HAND),
    )
    for cid, tag in checks:
        tags = card_effects.tag_text(heuristics._card_text(cid))
        assert tag in tags, (cid, tags)


def test_meta_decks_fully_covered():
    from tools.deck_validate import read_deck
    from pathlib import Path

    root = Path(tag_coverage.__file__).resolve().parents[1]
    for name in ("meta_archaludon", "meta_grimmsnarl"):
        deck = read_deck(root / "decks" / f"{name}.csv")
        cov = tag_coverage.deck_coverage(deck)
        assert cov["coverage"] == 1.0, (name, cov["uncovered"])


# ---- coverage meter + ratchet -----------------------------------------------

def test_target_deck_fully_covered():
    from tools.deck_validate import read_deck
    from pathlib import Path

    root = Path(tag_coverage.__file__).resolve().parents[1]
    deck = read_deck(root / "decks" / f"{tag_coverage.TARGET_DECK}.csv")
    cov = tag_coverage.deck_coverage(deck)
    assert cov["coverage"] == 1.0, cov["uncovered"]
    assert tag_coverage.deck_covered_100pct(deck)


def test_gate_blocks_a_deck_with_an_unknown_card():
    # An unknown id can never be covered, so a deck containing it fails the gate.
    assert not tag_coverage.deck_covered_100pct([-1])


def test_pool_untagged_fraction_ratchets_down():
    baseline = tag_coverage.load_baseline()
    assert baseline, "baseline JSON must be committed"
    live = tag_coverage.pool_untagged_fraction()
    # The ratchet: adding tags only lowers the untagged fraction, never raises it.
    assert live["fraction"] <= baseline["pool_untagged_fraction"] + 1e-9
    # And the target deck stays fully covered at the recorded tags version.
    assert baseline["target_deck_coverage"] == 1.0
    assert baseline["tags_version"] == card_effects.TAGS_VERSION
