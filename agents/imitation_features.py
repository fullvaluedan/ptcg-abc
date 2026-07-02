"""Ship-safe imitation featurizer over MAIN options (plan U40, piece 1 of 3).

One fixed-order numeric vector per legal MAIN option, so a learned pairwise ranker
(U41) can be trained on the top players' real decisions and shipped as a tiny
weight block that scores options at match time. This module is the ONE featurizer
the whole imitation pipeline reads (KD4): the extract tool (U40 piece 2), the
dataset builder, the trainer (U41), and the match-time scorer all import
`option_features` / `decision_features` from here, so the feature order can never
drift between training and inference.

Design (mirrors agents/heuristics.py and agents/card_effects.py so it bundles next
to main.py in a submission and imports the same way locally):
- Pure stdlib. No numpy, no sklearn, no cg import. Every card-data lookup is wrapped
  so the module imports and unit-tests without the native engine (the cg-dependent
  features simply read 0), and a batch over thousands of real decisions never aborts
  on one odd record. Never raises.
- The proven core is the U26 spike featurizer (analysis/unit_zero_spike.py): its 20
  option / option-x-state features beat the deployed heuristic by +0.087 top-1 on
  held-out expert decisions, so they are reproduced here VERBATIM (indices 0-19) and
  in the same order for continuity. The spike used numpy; this ships pure-Python
  lists.
- Added over the spike (the U33 card-knowledge signal the spike lacked): a per-option
  TAG_VOCAB multi-hot from agents/card_effects (indices below the crosses), plus three
  category-x-knowledge / timing crosses that address the two categories the spike
  regressed or the heuristic ignores (bench-a-Basic-from-deck for the early_collapse
  bucket, loop-safe once-per-turn ability for the 0-of-649 ABILITY gap, evolve timing).

Only features that VARY within a decision group carry signal in a pairwise ranker
(a scalar constant across every option cancels in the chosen-minus-other difference
vectors), so every feature here is option-specific or an option-x-state cross, not a
raw board scalar. That is why this is ~30 features, not the ~55 the plan sketched:
the plan's count was approximate and FEATURE_VERSION governs growth. Bump
FEATURE_VERSION on ANY change to FEATURE_NAMES or an extractor; a drift test pins it,
and (FEATURE_VERSION, TAGS_VERSION) is asserted at dataset load, weight load, and
build time (U40 piece 2 / U41) so a silent featurizer edit cannot mismatch a trained
weight block.
"""
from __future__ import annotations

try:
    from agents import card_effects
    from agents import heuristics as H
except ImportError:  # inside a submission, main.py and these sit together
    import card_effects
    import heuristics as H

# Bump on ANY change to FEATURE_NAMES or an extractor below. A drift test
# (tests/test_imitation_features.py) pins this so a featurizer edit is never silent.
FEATURE_VERSION = "1"

# The TAG_VOCAB multi-hot needs a deterministic order (TAG_VOCAB is a frozenset).
# This explicit tuple is that order; a test asserts set(TAG_ORDER) == TAG_VOCAB so a
# vocabulary change cannot silently desync the feature layout from the tag layer.
TAG_ORDER = (
    card_effects.DRAW,
    card_effects.SEARCH_TO_HAND,
    card_effects.RECOVERS_FROM_DISCARD,
    card_effects.DISCARDS_FROM_DECK,
    card_effects.BENCH_BASIC_FROM_DECK,
    card_effects.RARE_CANDY_EVOLVE,
    card_effects.ENERGY_ACCEL,
    card_effects.ONCE_PER_TURN,
)
_TAG_FEATURE_NAMES = tuple("tag_" + t.lower() for t in TAG_ORDER)

# Fixed feature order. Indices 0-19 are the U26 spike features verbatim (do not
# reorder: a trained weight vector keys off these positions). 20-22 are the added
# crosses; the tail is the per-option TAG_VOCAB multi-hot.
FEATURE_NAMES = (
    # --- spike core (0-19), reproduced verbatim from analysis/unit_zero_spike.py ---
    "is_play",
    "is_attach",
    "is_evolve",
    "is_ability",
    "is_retreat",
    "is_attack",
    "is_end",
    "play_basic_pokemon",
    "play_pokemon",
    "play_trainer",
    "play_energy",
    "attack_lethal",
    "attack_dmg_ratio",
    "attach_to_active",
    "attack_x_turn",
    "play_basic_x_thin_bench",
    "attack_x_active_healthy",
    "end_x_action_count",
    "attach_x_no_energy_yet",
    "attach_active_underpowered",
    # --- added crosses (20-22): card-knowledge / timing the spike lacked ---
    "play_bench_basic_from_deck",  # develop a Basic out of the deck: early_collapse lever
    "ability_once_per_turn",       # loop-safe ability (the 0-of-649 ABILITY gap)
    "evolve_x_turn",               # evolve timing (spike regressed EVOLVE)
) + _TAG_FEATURE_NAMES
N_FEATURES = len(FEATURE_NAMES)

_INDEX = {name: i for i, name in enumerate(FEATURE_NAMES)}


def feature_version() -> tuple:
    """The (FEATURE_VERSION, TAGS_VERSION) tuple asserted across the pipeline.

    A trained weight block records this pair; the dataset loader, weight loader, and
    build step compare it so a featurizer or tag-vocabulary edit that would shift the
    feature layout can never be paired with stale weights (KD4). Pure.
    """
    return (FEATURE_VERSION, card_effects.TAGS_VERSION)


def _safe(fn, default):
    """Call fn() returning default on any failure (card-engine lookups are lazy)."""
    try:
        return fn()
    except Exception:
        return default


def _state(obs):
    """(current, me, opp, my_active, opp_active) with defensive defaults."""
    st = obs.get("current") or {}
    players = st.get("players") or []
    yi = st.get("yourIndex", 0)
    me = players[yi] if 0 <= yi < len(players) else {}
    opp = players[1 - yi] if len(players) == 2 and 0 <= yi < 2 else {}
    my_active = H._active(me) if me else None
    opp_active = H._active(opp) if opp else None
    return st, me, opp, my_active, opp_active


def _hp_ratio(slot):
    if not slot:
        return 0.0
    hp = slot.get("hp", 0) or 0
    mx = slot.get("maxHp") or hp
    return (hp / mx) if mx else 0.0


def _card_type_of(opt, me):
    """(CardType int, is_basic_pokemon) for the card a PLAY option plays.

    A MAIN PLAY option carries a hand index decoded by play_card_id (the generic
    option_card_id keys off an area a PLAY option does not have). Returns
    (None, False) when the card or the card engine is unavailable; never raises.
    """
    cid = _safe(lambda: H.play_card_id(opt, me), None)
    if cid is None:
        return None, False
    ctype = _safe(lambda: H._card_type(cid), None)
    is_basic = bool(_safe(lambda: H.is_basic_pokemon(cid), False))
    return ctype, is_basic


def _option_card_tags(opt, sel, obs, me, is_play):
    """The card_effects tag frozenset for the card an option references.

    A PLAY option resolves through play_card_id (hand index); any other card-bearing
    option (ABILITY, EVOLVE, ...) resolves through the generic option_card_id
    (area + index). END / ATTACK carry no card to tag. Every step is wrapped so a
    missing card, missing text, or absent engine yields the empty frozenset rather
    than raising.
    """
    if is_play:
        cid = _safe(lambda: H.play_card_id(opt, me), None)
    else:
        cid = _safe(lambda: H.option_card_id(opt, sel, obs), None)
    if cid is None:
        return frozenset()
    text = _safe(lambda: H._card_text(cid), None)
    return _safe(lambda: card_effects.tag_text(text), frozenset())


def option_features(obs, sel, opt_index) -> list:
    """Feature vector (FEATURE_NAMES order) for one MAIN option.

    Pure and defensive: an out-of-range index, a missing field, or an unavailable
    card engine yields zeros for the affected features rather than raising, so a
    batch over thousands of real decisions never aborts on one odd record.
    """
    feats = [0.0] * N_FEATURES

    def put(name, value):
        feats[_INDEX[name]] = float(value)

    options = sel.get("option") or []
    if not (0 <= opt_index < len(options)):
        return feats
    opt = options[opt_index]
    if not isinstance(opt, dict):
        return feats
    otype = opt.get("type")

    is_play = otype == H.OPT_PLAY
    is_attach = otype == H.OPT_ATTACH
    is_evolve = otype == H.OPT_EVOLVE
    is_ability = otype == H.OPT_ABILITY
    is_attack = otype == H.OPT_ATTACK
    is_end = otype == H.OPT_END
    put("is_play", is_play)
    put("is_attach", is_attach)
    put("is_evolve", is_evolve)
    put("is_ability", is_ability)
    put("is_retreat", otype == H.OPT_RETREAT)
    put("is_attack", is_attack)
    put("is_end", is_end)

    st, me, opp, my_active, opp_active = _state(obs)
    turn = min(int(st.get("turn", 0) or 0), 10) / 10.0
    action_count = min(int(st.get("turnActionCount", 0) or 0), 6) / 6.0
    energy_attached = bool(st.get("energyAttached"))
    bench_count = _safe(lambda: H.my_bench_count(obs), None) or 0
    thin_bench = bench_count < H.THIN_BENCH
    active_healthy = _hp_ratio(my_active) > 0.5

    tags = _option_card_tags(opt, sel, obs, me, is_play)

    if is_play:
        ctype, is_basic = _card_type_of(opt, me)
        put("play_basic_pokemon", is_basic)
        put("play_pokemon", ctype == H.CARD_POKEMON)
        put("play_trainer", ctype in (H.CARD_ITEM, H.CARD_TOOL, H.CARD_SUPPORTER, H.CARD_STADIUM))
        put("play_energy", ctype in (H.CARD_BASIC_ENERGY, H.CARD_SPECIAL_ENERGY))
        put("play_basic_x_thin_bench", is_basic and thin_bench)
        put("play_bench_basic_from_deck", card_effects.BENCH_BASIC_FROM_DECK in tags)

    if is_attack:
        attack = _safe(lambda: H.attack_index().get(opt.get("attackId")), None)
        my_id = my_active.get("id") if my_active else None
        opp_id = opp_active.get("id") if opp_active else None
        dmg = _safe(lambda: H.effective_damage(my_id, attack, opp_id), 0) if attack else 0
        opp_hp = opp_active.get("hp") if opp_active else None
        opp_mx = (opp_active.get("maxHp") or opp_hp) if opp_active else None
        put("attack_lethal", opp_hp is not None and dmg >= opp_hp)
        put("attack_dmg_ratio", min(dmg / opp_mx, 1.0) if opp_mx else 0.0)
        put("attack_x_turn", turn)
        put("attack_x_active_healthy", active_healthy)

    if is_attach:
        to_active = opt.get("inPlayArea") == H.AREA_ACTIVE
        put("attach_to_active", to_active)
        put("attach_x_no_energy_yet", not energy_attached)
        if to_active and my_active is not None:
            costs = _safe(lambda: H._attack_costs(my_active.get("id")), [])
            attached = _safe(lambda: H._attached_count(my_active), 0)
            underpowered = bool(costs) and attached < costs[0]
            put("attach_active_underpowered", underpowered)

    if is_ability:
        put("ability_once_per_turn", card_effects.ONCE_PER_TURN in tags)

    if is_evolve:
        put("evolve_x_turn", turn)

    if is_end:
        put("end_x_action_count", action_count)

    # Per-option TAG_VOCAB multi-hot: the card-knowledge signal the spike lacked. A
    # tag present on the option's card lights its slot regardless of category, so the
    # ranker can key off draw / search / deck-drill / energy-accel content directly.
    for tag in tags:
        name = "tag_" + tag.lower()
        if name in _INDEX:
            feats[_INDEX[name]] = 1.0

    return feats


def decision_features(obs):
    """One feature row per legal MAIN option (a ranking group), or None.

    Returns a list of N_FEATURES-long rows in option order, or None when the
    observation has 0 or 1 options (a single-option decision carries no ranking
    signal, exactly the spike's decision_matrix gate). Pure, never raises.
    """
    sel = obs.get("select") or {}
    options = sel.get("option") or []
    if len(options) <= 1:
        return None
    return [option_features(obs, sel, i) for i in range(len(options))]
