"""Rule aware option classification and move selection for the heuristic agent.

Pure functions over the raw observation dict. Kept free of any ptcg_agent
package import so this module can be bundled next to main.py in a submission and
imported the same way it is imported locally. Card and attack data come from the
official cg.api, located on sys.path lazily (already importable inside a
submission, found under data/ or vendor/ for local runs).

Design choices, all aimed at a never crash agent that beats the random baseline:
- The MAIN attack option carries its attackId, so lethal is computed at the MAIN
  decision rather than a separate attack sub select.
- Abilities are intentionally not prioritized: a stateless agent that prefers a
  repeatable ability over ending the turn could loop forever. PLAY, ATTACH, and
  EVOLVE each consume a resource, so the turn always makes progress and ends.
- Near self-deckout the agent stops replaying deck-drilling trainers (the
  draw/search-into-hand engine; see _drills_deck and DRAW_CONSERVE_THRESHOLD) so
  the deck survives to close on prizes instead of milling itself to zero. Board
  development (benching a Basic, attaching an Energy) still plays.
- Every path falls through to a guaranteed legal selection.
"""
from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path

try:
    from agents import card_effects
except ImportError:  # inside a submission, main.py and card_effects.py sit together
    import card_effects


def _env_num(name, default, cast):
    """Read a tunable numeric constant from the environment, else the default.

    The CEM optimizer (tools/weight_space.py, offline) tunes the pilot by baking
    PTCG_W_* overrides into a build via tools/build_submission.py --env; each such
    knob is read here exactly like the boolean PTCG_* levers below. When the
    variable is unset (every shipped build unless a tuned vector is baked) the
    default is returned unchanged, so an un-tuned submission stays byte-identical.
    A malformed value falls back to the default rather than raising, preserving
    the never-raise contract. `cast` is int or float; the default mirrors the
    entry in tools/weight_space.PARAM_SPACE (a drift test guards the pairing).
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return cast(raw)
    except (TypeError, ValueError):
        return default


# OptionType values (api.py OptionType enum).
OPT_NUMBER = 0
OPT_YES = 1
OPT_NO = 2
OPT_CARD = 3
OPT_PLAY = 7
OPT_ATTACH = 8
OPT_EVOLVE = 9
OPT_ABILITY = 10
OPT_DISCARD = 11
OPT_RETREAT = 12
OPT_ATTACK = 13
OPT_END = 14

# SelectType values (api.py SelectType enum).
SEL_MAIN = 0
SEL_CARD = 1
SEL_COUNT = 8
SEL_YES_NO = 9

# CardType values (api.py CardType enum).
CARD_POKEMON = 0
CARD_ITEM = 1
CARD_TOOL = 2
CARD_SUPPORTER = 3
CARD_STADIUM = 4
CARD_BASIC_ENERGY = 5
CARD_SPECIAL_ENERGY = 6

# AreaType values (api.py AreaType enum).
AREA_DECK = 1
AREA_HAND = 2
AREA_DISCARD = 3
AREA_ACTIVE = 4
AREA_BENCH = 5

# SelectContext: would you like to go first?
CTX_IS_FIRST = 41

# SelectContext values where picking a card brings a Pokemon into play or hand
# (a deck search, a put-into-play, a setup placement). When our bench is thin a
# Basic Pokemon is the useful fetch: a lone active with an empty bench getting
# knocked out is the dominant early-collapse loss (see analysis/loss_classifier).
GAIN_POKEMON_CONTEXTS = frozenset({
    2,  # SETUP_BENCH_POKEMON
    5,  # TO_BENCH
    6,  # TO_FIELD
    7,  # TO_HAND
})
CTX_DISCARD = 8

# Fetch a Basic to develop only when our bench holds fewer than this many
# Pokemon, so a healthy board is never steered away from its normal fetch.
# CEM-tunable (PTCG_W_THIN_BENCH); defaults to the shipped value when unset.
THIN_BENCH = _env_num("PTCG_W_THIN_BENCH", 2, int)

# Standard damage modifiers. cabt uses x2 weakness and a flat resistance cut.
WEAKNESS_MULT = 2
RESISTANCE_CUT = 30

# Retreat when the active is at or below this fraction of its max HP.
# CEM-tunable (PTCG_W_RETREAT_HP_RATIO); defaults to the shipped value when unset.
RETREAT_HP_RATIO = _env_num("PTCG_W_RETREAT_HP_RATIO", 0.34, float)

# Energy-attach sequencing (PTCG_ENERGY_SEQ, default off). Off, the agent always
# powers the active first (attach to the active if an option targets it, else the
# first attach option). On, once the active can already pay for its cheapest
# attack, extra energy is steered onto the strongest still-underpowered benched
# attacker so the deck's payoff attacker comes online a turn sooner instead of
# overloading a front-line active that is already able to attack. Staged behind a
# flag so every shipped build stays byte-identical (off) until it is A/B'd on the
# ladder as a clean single-variable change; offline weak-bot gauntlets are not
# predictive, so the ladder is the judge (see autoloop_status.md).
# REFUTED by expert data and kept off: scored against the move-ranking breakdown
# (analysis/energy_seq_refuted_by_expert_moves.md), the top players power the active
# first exactly as the default does, so sequencing lowers exact-target ATTACH
# agreement (87/1445 -> 77/1445) and net top-1 (0.212 -> 0.210) on 4524 real expert
# MAIN decisions. It never converts an ordering miss into an attach; it only moves
# attaches we already make away from the expert's target. Killed before it cost a
# ladder slot, same as PTCG_BENCH_DIG. The flag and its measurement (this validator
# with the env var set) are kept so the refutation is re-runnable; default off means
# every shipped build stays byte-identical.
_ENERGY_SEQ = os.environ.get("PTCG_ENERGY_SEQ", "0") != "0"

# Dig-for-a-Basic when the bench is thin (PTCG_BENCH_DIG, default off). The
# empty-bench collapse loss is a draw/search-consistency failure, not a play-order
# one: in the ladder replays that collapsed, in 94% of the empty-bench decision
# moments we held NO benchable Basic to reorder onto the bench (see
# analysis/empty_bench_is_draw_variance.md), so the bench-first guard has nothing
# to bench. This lever attacks the OTHER half of that finding: when the bench is
# thin and we hold no Basic and no direct bench-fetch trainer (Precious Trolley),
# prefer a draw/search trainer that drills the deck (Ultra Ball, Cyrano, a draw
# Supporter) to FIND a Basic this turn, before spending the turn on an energy
# attach or a non-digging item. Distinct from the retired bench-ordering guard
# (that reorders a Basic you already hold; this digs when you hold none) and safe:
# the not-near-deckout branch only, so the drill never mills us toward a deckout.
# REFUTED at scale and kept off: a -7.5pp point estimate at n=160 vanished to +1.9pp
# at n=360 (analysis/bench_dig_refuted_at_scale.md), confirming the empty-bench
# collapse is a deck-density problem, not a pilot play-access one. The flag and its
# measurement (tools/measure_bench_dig.py) are kept so the refutation is re-runnable;
# default off means every shipped build stays byte-identical.
_BENCH_DIG = os.environ.get("PTCG_BENCH_DIG", "0") != "0"

# Ability activation (PTCG_ABILITY, default off). The pilot has never activated an
# ability: 0 of 554 real expert MAIN decisions where the top players used one (the
# move-ranking breakdown, analysis/move_ranking_diverges_ability_gap.md). Abilities
# are 12% of the top players' MAIN actions and the draw/search/damage engines of
# this meta (the exact engines our meta-deck copies mispiloted), so this is a whole
# category the heuristic lacks, orthogonal to the bench work refuted three times.
# The historical reason to skip abilities is loop safety: choose() is stateless and
# the engine re-calls it until the turn ends, so a pilot that preferred a REPEATABLE
# ability over ending the turn would activate it every decision forever and hang the
# match. This lever adds the branch loop-safely by activating ONLY a "once during
# your turn" ability: the engine flags such an ability used after activation, so it
# is never re-offered that turn and the turn still terminates (finitely many
# once-per-turn abilities fire, then the usual attack/end path runs). A repeatable
# ability that carries no such limit is left out precisely because it is the loop
# risk. Staged behind a default-off flag so every shipped build stays byte-identical
# until it is validated (the move-ranking breakdown) and A/B'd on the ladder; offline
# weak-bot gauntlets are not predictive, so the ladder is the judge.
_ABILITY = os.environ.get("PTCG_ABILITY", "0") != "0"

# Attack-before-attach sequencing (PTCG_ATTACK_FIRST, default off). U91's game-plan
# miner (analysis/gameplan_claims_bracket_4.md) confirmed two related within-turn
# patterns on bracket_4 real ladder replays (both gates pass: n>1400/side, claim CI
# excludes zero, prediction CI brackets the held-out test mean): winners
# attach-before-attack LESS often than losers on turns where both are already legal
# (52.4% vs 55.8%), and winners bank energy (attach with no attack that same turn)
# LESS often too (19.2% vs 23.6%). The shipped default always attaches first
# whenever an attach option is legal (PRIO_ATTACH outranks PRIO_ATTACK), so it
# over-attaches relative to BOTH cohorts in the mined data. This lever tests the
# literal prescriptive rule the plan names (U93): when a positive-value attack is
# already legal THIS decision using energy already attached (no further attach
# needed to unlock it), take the attack now instead of the discretionary attach.
# Narrow and bounded: only fires when OPT_ATTACH is also legal and best_attack
# reports eff_damage > 0; candy/evolve/play/ability/retreat priority is untouched,
# they still resolve before this check exactly as before. Staged behind a
# default-off flag so every shipped build stays byte-identical until it clears the
# bracket-ring A/B the plan requires before any ladder slot (the mined pattern is a
# correlation, not yet proven prescriptive; see the caveat in
# analysis/gameplan_claims_bracket_4.md).
_ATTACK_FIRST = os.environ.get("PTCG_ATTACK_FIRST", "0") != "0"

# Threat-aware retreat (PTCG_THREAT_RETREAT, default off). When on, allow retreat
# even if our active's HP is above the normal threshold if the opponent's active can
# OHKO us (best printed attack deals >= our current HP). Bench survivor still required.
# Flag-gated for A/B validation; default off maintains byte-identical submission.
_THREAT_RETREAT = os.environ.get("PTCG_THREAT_RETREAT", "0") != "0"

# Prize-close optimization (PTCG_PRIZE_CLOSE, default off). When we have 1-2 prizes
# remaining, prefer any legal attack that wins the game (knocks out opponent or lets
# us claim the winning prize next turn). Flag-gated for A/B validation; default off
# maintains byte-identical submission.
_PRIZE_CLOSE = os.environ.get("PTCG_PRIZE_CLOSE", "0") != "0"

# Endgame PLAY-priority correction (PTCG_ENDGAME_PLAY, default off). In the
# near-endgame (either side at or below 2 prizes remaining) with a bloated hand,
# demote the discretionary EVOLVE below PLAY so the pilot spends its hand
# (draw/search/gust trainers) before committing a non-finisher evolution, matching
# the field's top players (176 near-endgame PLAY divergences where the expert
# played a trainer and the pilot would have evolved instead -- six of the top nine
# divergence patterns, the single largest homogeneous slice; see
# analysis/endgame_play_rule_design.md cluster A). This is a within-turn REORDER,
# not a skip: PLAY and EVOLVE are both legal on every MAIN decision of the turn, so
# once the hand drops below threshold the evolution still resolves later the same
# turn. Sits below the L1 lethal FORCE unconditionally (that check returns before
# the ladder is ever built) and never RAISES evolve, only lowers it relative to the
# (possibly CEM-tuned) PRIO_PLAY. Flag-gated for A/B validation; default off keeps
# every shipped build byte-identical.
_ENDGAME_PLAY = os.environ.get("PTCG_ENDGAME_PLAY", "0") != "0"

# Hand size at or above which the endgame-play demotion engages. Cluster A's hand
# medians run 11.5 to 19; cluster B (ATTACK-instead, NOT this rule's target) runs
# 6 to 7, so 10 sits in the wide separating gap. CEM-tunable
# (PTCG_W_ENDGAME_HAND); defaults to the shipped value when unset.
ENDGAME_HAND = _env_num("PTCG_W_ENDGAME_HAND", 10, int)

# Deck-aware game-plan seeds (PTCG_SEEDS, default off). The U36 miner distills a
# target family's WINNING expert episodes into concentrated play seeds (attach /
# play / evolve card-id targets); analysis/gameplan_seeds.py emits only the blocks
# that clear BOTH the 0.90 resolution bar and their concentration bar, and
# tools/build_submission.py --env bakes the emitted seeds JSON into PTCG_SEEDS_JSON.
# This lever consumes a baked attach_target seed to steer the ATTACH step toward the
# seeded receiving Pokemon (the card the winning expert put energy on). Two
# independent guarantees keep every shipped build byte-identical today: the flag is
# default-off, AND the mined seeds channel is empty for both live targets
# (analysis/gameplans/seeds_real_run.md: meta_grimmsnarl emits 0 seeds; the one
# meta_archaludon evolve_target seed is a deck-identity fact, not a win-vs-loss edge).
# The seam exists so a future concentrated AND win-vs-loss-discriminating seed can be
# baked and A/B'd without re-architecting the pilot; no ladder slot is spent until
# such a seed exists. The remaining application points the plan names (bench / play
# targets, fetch priorities, the deckout floor) are deferred until a seed for their
# block clears the bars, to avoid speculative code the empty channel cannot exercise.
_SEEDS = os.environ.get("PTCG_SEEDS", "0") != "0"

# Block names whose emitted seed is an int card id a resolver can act on.
_SEED_TARGET_BLOCKS = ("attach_target", "play_target", "evolve_target")


def _load_seeds(raw):
    """Parse the baked seeds JSON into {block_name: card_id} for consumable blocks.

    `raw` is the PTCG_SEEDS_JSON string build_submission bakes from an
    analysis/gameplan_seeds.py emit -- either the full emit payload (with a `seeds`
    object) or the bare `seeds` object, keyed by block name with a {value, metric,
    kind} payload. Keeps only the categorical target blocks whose value is an int
    card id. Fail-open: unset, malformed, or seedless JSON returns {}, so an
    un-seeded build reads no seeds and stays byte-identical. Pure, never raises.
    """
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    seeds_obj = payload.get("seeds", payload)
    if not isinstance(seeds_obj, dict):
        return {}
    out = {}
    for name in _SEED_TARGET_BLOCKS:
        entry = seeds_obj.get(name)
        if isinstance(entry, dict) and isinstance(entry.get("value"), int):
            out[name] = entry["value"]
    return out


SEEDS = _load_seeds(os.environ.get("PTCG_SEEDS_JSON"))


def seed_target(block):
    """The seeded card id for a categorical target block, or None when unseeded.

    Returns None whenever the seeds lever is off or the block has no baked seed, so
    every consumption site collapses to its default path unless a real seed is
    present (default-off and empty-dict both yield None). Reads module state (the
    _SEEDS flag and the SEEDS table built at import); never raises.
    """
    if not _SEEDS:
        return None
    return SEEDS.get(block)


# Category ordering priorities for the pilot's MAIN decision. CEM-tunable: these
# are the genome levers the U6 gradient diagnostic showed were missing (both
# fitness channels were flat because the dominant decision driver, choose()'s
# category priority order, was not in the genome; analysis/cem_signal_flat.md).
# choose() scores each available action category by its priority and takes the
# highest-priority one that yields a legal move, so the optimizer can finally
# reorder the categories the expert move-ranking breakdown flagged (the ABILITY
# gap, the EVOLVE ordering) -- the driver of the overwhelming majority of MAIN
# decisions, which the narrow threshold knobs above could not reach.
#
# The shipped DEFAULTS descend in the exact order of the historical fixed ladder
# (rare-candy -> evolve -> play -> attach -> ability -> retreat -> attack), so an
# un-tuned build is byte-identical: each PTCG_W_PRIO_* is unset and returns its
# default, the defaults reproduce the old order, and weight_space.vector_to_env
# emits nothing. The lethal knockout (safety-1) stays hard-first ahead of all of
# these and END stays the last fallback; neither is tunable. Loop-safety does not
# depend on the order: every category is either resource-consuming
# (evolve/play/attach) or turn-ending (attack), and only a once-per-turn ability
# is ever taken, so any priority ordering still terminates the turn.
PRIO_CANDY = _env_num("PTCG_W_PRIO_CANDY", 6.0, float)
PRIO_EVOLVE = _env_num("PTCG_W_PRIO_EVOLVE", 5.0, float)
PRIO_PLAY = _env_num("PTCG_W_PRIO_PLAY", 4.0, float)
PRIO_ATTACH = _env_num("PTCG_W_PRIO_ATTACH", 3.0, float)
PRIO_ABILITY = _env_num("PTCG_W_PRIO_ABILITY", 2.0, float)
PRIO_RETREAT = _env_num("PTCG_W_PRIO_RETREAT", 1.0, float)
PRIO_ATTACK = _env_num("PTCG_W_PRIO_ATTACK", 0.0, float)


def _ensure_cg_on_path() -> None:
    try:
        import cg.api  # noqa: F401

        return
    except ImportError:
        pass
    # Local runs: the official package lives under data/ or vendor/ at the repo
    # root. Walk up from this file to find it. The grader has no __file__, but it
    # also bundles cg/ at the top level, so the import above already returned.
    if "__file__" not in globals():
        return
    here = Path(__file__).resolve()
    for parent in here.parents:
        for sub in ("data", "vendor"):
            if (parent / sub / "cg" / "api.py").exists():
                p = str(parent / sub)
                if p not in sys.path:
                    sys.path.insert(0, p)
                return


@lru_cache(maxsize=1)
def card_index() -> dict:
    _ensure_cg_on_path()
    from cg.api import all_card_data

    return {c.cardId: c for c in all_card_data()}


@lru_cache(maxsize=1)
def attack_index() -> dict:
    _ensure_cg_on_path()
    from cg.api import all_attack

    return {a.attackId: a for a in all_attack()}


@lru_cache(maxsize=1)
def _name_index() -> dict:
    """Map card name -> CardData, for tracing an evolution line by name.

    Card data records evolvesFrom as the prior stage's name (not its id), so
    resolving a chain (Stage 2 -> its Stage 1 -> that Stage 1's Basic) needs a
    by-name lookup. Cached once like card_index. Defensive: empty on any failure.
    """
    try:
        return {c.name: c for c in card_index().values() if getattr(c, "name", None)}
    except Exception:
        return {}


def options_by_type(options) -> dict:
    """Map an OptionType to the list of (index, option) pairs that have it."""
    groups: dict = {}
    for i, op in enumerate(options):
        groups.setdefault(op.get("type"), []).append((i, op))
    return groups


def _card_type(card_id):
    """The CardType of a card id, or None when the id is unknown. Never raises."""
    try:
        c = card_index().get(card_id)
    except Exception:
        return None
    return getattr(c, "cardType", None) if c is not None else None


def _card_text(card_id):
    """The card's effect text (skills concatenated), or None when unknown.

    Card data ships the skill text offline, so the effect is inspectable. Pure
    and defensive: any missing piece yields None rather than raising.
    """
    try:
        c = card_index().get(card_id)
    except Exception:
        return None
    if c is None:
        return None
    skills = getattr(c, "skills", None) or []
    parts = [s.text for s in skills if getattr(s, "text", None)]
    return " ".join(parts) if parts else None


def is_basic_pokemon(card_id) -> bool:
    """True only for a known Basic Pokemon card id. Defensive over missing data."""
    c = card_index().get(card_id) if card_id else None
    return bool(
        c is not None
        and getattr(c, "cardType", None) == CARD_POKEMON
        and getattr(c, "basic", False)
    )


def _area_zone(player, area):
    """The card list of a player's area, or None for areas without a card list."""
    if area == AREA_HAND:
        return player.get("hand")
    if area == AREA_BENCH:
        return player.get("bench")
    if area == AREA_ACTIVE:
        return player.get("active")
    if area == AREA_DISCARD:
        return player.get("discard")
    return None


def option_card_id(opt, sel, obs):
    """Resolve the cardId a CARD option refers to, or None when not determinable.

    A CARD option carries area + index, not the cardId itself. Deck-search
    options index into select.deck (the only time the deck is revealed); hand and
    board options index into the matching area of our own visible state. Pure and
    defensive: any missing piece yields None rather than raising.
    """
    try:
        cid = opt.get("cardId")
        if cid:
            return cid
        area = opt.get("area")
        idx = opt.get("index")
        if idx is None:
            return None
        deck = sel.get("deck")
        if area == AREA_DECK and deck is not None:
            return deck[idx].get("id") if 0 <= idx < len(deck) else None
        state = obs.get("current") or {}
        players = state.get("players") or []
        pi = opt.get("playerIndex")
        if pi is None:
            pi = state.get("yourIndex", 0)
        if not (0 <= pi < len(players)):
            return None
        zone = _area_zone(players[pi], area)
        if zone is not None and 0 <= idx < len(zone):
            entry = zone[idx]
            return entry.get("id") if entry else None
    except Exception:
        return None
    return None


def my_bench_count(obs):
    """Number of Pokemon on our bench (excluding the active), or None.

    The early-collapse signal: when this is low our lone active has no backup, so
    one knockout ends the game with prizes untouched.
    """
    state = obs.get("current") or {}
    yi = state.get("yourIndex", 0)
    players = state.get("players") or []
    if len(players) <= yi:
        return None
    bench = players[yi].get("bench") or []
    return sum(1 for b in bench if b)


def _bench_is_thin(obs) -> bool:
    """True when our bench holds fewer than THIN_BENCH Pokemon (early-collapse risk).

    Shared by the bench-development guard and the evolution-line driver so both
    read the same empty-bench signal. None (unknown) is treated as not thin, so a
    degenerate observation never triggers a develop-over-everything override.
    """
    b = my_bench_count(obs)
    return b is not None and b < THIN_BENCH


def effective_damage(attacker_id, attack, defender_id) -> int:
    """Damage of an attack against a defender, applying weakness and resistance.

    Falls back to the printed base damage when card data is unavailable, so an
    unknown card never causes a crash, only a less precise estimate.
    """
    dmg = getattr(attack, "damage", 0) or 0
    if attacker_id is None or defender_id is None:
        return max(dmg, 0)
    cards = card_index()
    atk = cards.get(attacker_id)
    dfn = cards.get(defender_id)
    if atk is None or dfn is None:
        return max(dmg, 0)
    if dfn.weakness is not None and dfn.weakness == atk.energyType:
        dmg *= WEAKNESS_MULT
    if dfn.resistance is not None and dfn.resistance == atk.energyType:
        dmg -= RESISTANCE_CUT
    return max(dmg, 0)


def best_attack(groups, my_active_id, defender_id, defender_hp):
    """Pick the strongest attack option.

    Returns (index, eff_damage, is_lethal) for the best ATTACK option, or None
    when no attack is available. Lethal is judged against the defender's current
    HP and beats raw damage in the ordering.
    """
    attacks = attack_index()
    best = None  # (is_lethal, eff_damage, index)
    for i, op in groups.get(OPT_ATTACK, []):
        attack = attacks.get(op.get("attackId"))
        dmg = effective_damage(my_active_id, attack, defender_id) if attack else 0
        lethal = defender_hp is not None and dmg >= defender_hp
        cand = (lethal, dmg, i)
        if best is None or cand > best:
            best = cand
    if best is None:
        return None
    return (best[2], best[1], best[0])


def _opponent_best_attack_damage(opp_active_id, my_active_id, my_active_hp) -> int:
    """Maximum damage the opponent's active can deal to us.

    Enumerates the opponent card's attacks from card data and returns the
    maximum effective damage (with weakness/resistance). Returns 0 if opponent
    has no active or no attacks available. Used to detect OHKO threats.
    """
    if opp_active_id is None or my_active_id is None:
        return 0
    cards = card_index()
    opp_card = cards.get(opp_active_id)
    if not opp_card:
        return 0
    max_dmg = 0
    # CardData.attacks holds attack IDs (ints), not attack objects; resolve
    # each through attack_index() exactly like best_attack does, or
    # effective_damage reads .damage off an int and always returns 0.
    attacks = attack_index()
    for attack_id in getattr(opp_card, 'attacks', []):
        attack = attacks.get(attack_id)
        if attack is None:
            continue
        dmg = effective_damage(opp_active_id, attack, my_active_id)
        max_dmg = max(max_dmg, dmg)
    return max_dmg


def _our_prize_count(obs) -> int:
    """Number of prize cards we have remaining, or 0 if unknown.

    Used to identify close-game situations where prize-close priority applies.
    """
    state = obs.get("current") or {}
    players = state.get("players") or []
    yi = state.get("yourIndex", 0)
    if len(players) <= yi:
        return 0
    me = players[yi]
    prize = me.get("prize")
    if isinstance(prize, list):
        return len(prize)
    return 0


def _opp_prize_count(obs) -> int:
    """Number of prize cards the opponent has remaining, or a large sentinel if unknown.

    Mirrors _our_prize_count on the opponent seat (players[1 - yourIndex]), reading
    the same public prize-pile length (no hidden-information assumption). Unlike
    _our_prize_count, which defensively returns 0 on a missing seat, this fails
    CLOSED toward "not near-endgame": a missing or malformed opponent seat returns
    a large sentinel so min(_our_prize_count, _opp_prize_count) can never look
    near-endgame on a degenerate observation. Used only by PTCG_ENDGAME_PLAY (see
    analysis/endgame_play_rule_design.md section 7, the "_opp_prize_count add" risk).
    """
    state = obs.get("current") or {}
    players = state.get("players") or []
    yi = state.get("yourIndex", 0)
    oi = 1 - yi
    if oi < 0 or len(players) <= oi:
        return 99
    prize = players[oi].get("prize")
    if isinstance(prize, list):
        return len(prize)
    return 99


def _is_prize_winning_attack(opp_active_hp) -> bool:
    """True when taking down the opponent active wins us a prize (closes the game).

    Called when we're at 1-2 prizes; if we can OHKO the opponent's active,
    we win the game immediately.
    """
    return opp_active_hp is not None and opp_active_hp > 0


def _attack_costs(card_id):
    """Sorted energy costs of a card's attacks (each cost = the number of energies
    the attack needs), or an empty list when the card or its attacks are unknown.

    Attack cost is the length of the attack's `energies` list. Pure and defensive:
    any missing card, attack, or field yields an empty list rather than raising.
    """
    try:
        c = card_index().get(card_id) if card_id else None
        atks = attack_index()
    except Exception:
        return []
    if c is None:
        return []
    costs = []
    for aid in getattr(c, "attacks", None) or []:
        a = atks.get(aid)
        if a is not None:
            costs.append(len(getattr(a, "energies", None) or []))
    return sorted(costs)


def _attached_count(slot) -> int:
    """Energy currently attached to a Pokemon slot (0 when none or unknown)."""
    return len(slot.get("energies") or []) if slot else 0


def _attach_slot_card_id(op, me):
    """Card id of the in-play Pokemon an ATTACH option would power, or None.

    The energy lands on the active or a bench slot; this reads back the card in
    that slot so a seeded attach_target can be matched against it. Pure, never
    raises on a well-formed option/me.
    """
    area = op.get("inPlayArea")
    if area == AREA_ACTIVE:
        active = _active(me)
        return active.get("id") if active else None
    if area == AREA_BENCH:
        bench = me.get("bench") or []
        bi = op.get("inPlayIndex")
        if bi is not None and 0 <= bi < len(bench) and bench[bi]:
            return bench[bi].get("id")
    return None


def _choose_attach(attach, me) -> int:
    """Index of the ATTACH option to take.

    Default (PTCG_ENERGY_SEQ off): power the active, attaching to it when an option
    targets it, else the first attach option. This is byte-identical to the prior
    inline attach step.

    With sequencing on, once the active can already pay for its cheapest attack
    (attaching more to it is not needed to attack this turn), steer the attachment
    onto the strongest still-underpowered benched attacker: a benched Pokemon whose
    biggest attack costs more than the active's cheapest attack and that is not yet
    fully powered for that attack. That brings the deck's payoff attacker online
    instead of overloading a front-line active that can already attack. Falls back
    to the active whenever no such bench target has an attach option. Pure, never
    raises.
    """
    active_attach = next(
        (i for i, op in attach if op.get("inPlayArea") == AREA_ACTIVE), None
    )
    default = active_attach if active_attach is not None else attach[0][0]
    # Deck-aware seed: when a baked attach_target names the winning expert's
    # receiving Pokemon, steer the energy onto whichever option targets a slot
    # holding that card. Inert unless the seeds lever is on and a seed is baked
    # (seed_target returns None otherwise), so an un-seeded build never enters here
    # and stays byte-identical. Falls through to the default / sequencing paths when
    # no option targets the seeded card.
    seed = seed_target("attach_target")
    if seed is not None:
        for i, op in attach:
            if _attach_slot_card_id(op, me) == seed:
                return i
    if not _ENERGY_SEQ:
        return default
    active = _active(me)
    if active is None:
        return default
    active_costs = _attack_costs(active.get("id"))
    # Power the active first until it can pay for at least its cheapest attack;
    # only surplus energy is redirected to develop a bench payoff attacker.
    if not active_costs or _attached_count(active) < active_costs[0]:
        return default
    cheapest_active = active_costs[0]
    bench = me.get("bench") or []
    best_opt = None  # (max_attack_cost, -option_index, option_index)
    for i, op in attach:
        if op.get("inPlayArea") != AREA_BENCH:
            continue
        bi = op.get("inPlayIndex")
        if bi is None or not (0 <= bi < len(bench)):
            continue
        slot = bench[bi]
        if not slot:
            continue
        costs = _attack_costs(slot.get("id"))
        if not costs:
            continue
        max_cost = costs[-1]
        # A payoff attacker: hits harder than the active's cheapest attack and is
        # not yet fully powered for its own biggest attack.
        if max_cost > cheapest_active and _attached_count(slot) < max_cost:
            cand = (max_cost, -i, i)
            if best_opt is None or cand > best_opt:
                best_opt = cand
    return best_opt[2] if best_opt is not None else default


def _active(player):
    act = player.get("active") or []
    return act[0] if act and act[0] is not None else None


def _is_once_per_turn_ability(card_id) -> bool:
    """True when a Pokemon's ability is limited to once during your turn.

    Read from the card's skill text offline (a Pokemon's ability lives in `skills`,
    separate from its `attacks`). The "once during your turn" limit is the one the
    engine flags as used after activation, so such an ability is never re-offered
    that turn: activating it always makes progress and the turn still terminates. An
    ability without that limit (a passive or repeatable ability) is the infinite-loop
    risk a stateless pilot must avoid, so it is excluded. Conservative on missing
    text: no text means the once-per-turn limit cannot be proven, so it is treated as
    unsafe and not activated. Pure, never raises.
    """
    return card_effects.ONCE_PER_TURN in card_effects.tag_text(_card_text(card_id))


def _once_per_turn_ability(ability_opts, sel, obs):
    """Option index of a loop-safe once-per-turn ability to activate, or None.

    An ABILITY option carries the area+index of the Pokemon whose ability it is, so
    resolve that Pokemon's card id (option_card_id) and read its skill text. Only an
    ability limited to "once during your turn" is returned; a repeatable ability, or
    one whose Pokemon or text cannot be resolved, is skipped so a stateless pilot can
    never loop on it. Lowest option index wins. Pure, never raises.
    """
    for oi, opt in ability_opts:
        cid = option_card_id(opt, sel, obs)
        if cid is not None and _is_once_per_turn_ability(cid):
            return oi
    return None


def lethal_move(obs, sel=None):
    """Index list for a guaranteed-knockout MAIN attack, or None.

    The search agent's safety override calls this to take a knockout before it
    ever runs search (KTD5: never miss a lethal, even when search would pick
    something else). It mirrors the first priority inside choose(), which keeps
    its own best_attack result because it also needs it for the retreat and
    non-lethal attack steps. Pure, never raises.
    """
    if sel is None:
        sel = obs.get("select") or {}
    if sel.get("type") != SEL_MAIN:
        return None
    options = sel.get("option", [])
    state = obs.get("current") or {}
    yi = state.get("yourIndex", 0)
    players = state.get("players") or []
    if len(players) < 2:
        return None
    me = players[yi]
    opp = players[1 - yi]
    my_active = _active(me)
    opp_active = _active(opp)
    ba = best_attack(
        options_by_type(options),
        my_active.get("id") if my_active else None,
        opp_active.get("id") if opp_active else None,
        opp_active.get("hp") if opp_active else None,
    )
    if ba is not None and ba[2]:  # (index, eff_damage, is_lethal)
        return [ba[0]]
    return None


def should_retreat(my_active, bench, lethal_available, opp_active=None) -> bool:
    """Retreat only when the active is endangered and a healthier bench exists.

    Skipped when a lethal attack is on the table (take the knockout instead) or
    when no bench Pokemon is in better shape than the active.

    With PTCG_THREAT_RETREAT on, also allows retreat if the opponent's active can
    OHKO us, even if our HP is above the normal threshold (requires a healthy bench).
    """
    if my_active is None or lethal_available:
        return False
    hp = my_active.get("hp", 0)
    mx = my_active.get("maxHp") or hp
    if mx <= 0:
        return False
    # Check if bench has a healthier Pokemon
    has_healthy_bench = any(b for b in (bench or []) if b and b.get("hp", 0) > hp)
    if not has_healthy_bench:
        return False
    # Threat-aware retreat: if flag is on and opponent can OHKO us, retreat.
    if _THREAT_RETREAT and opp_active is not None:
        opp_active_id = opp_active.get("id")
        my_active_id = my_active.get("id")
        opp_best_dmg = _opponent_best_attack_damage(opp_active_id, my_active_id, hp)
        if opp_best_dmg >= hp:
            return True
    # Normal retreat: active is endangered (below HP threshold).
    return hp / mx <= RETREAT_HP_RATIO


def _first_legal(sel) -> list:
    """A guaranteed legal selection: the first minCount distinct option indices."""
    n = len(sel.get("option", []))
    mn = sel.get("minCount", 1)
    mx = sel.get("maxCount", 1)
    k = mn if mn > 0 else (1 if mx >= 1 else 0)
    return list(range(min(k, n)))


# Self-deck-out guard: only engages when our deck is at or below this many cards,
# so normal play is never touched. Decking ourselves out was the dominant real
# ladder loss (see analysis/loss_classifier.py: two of three live losses were
# deckouts, one while ahead on prizes), so a voluntary over-draw on a COUNT
# selection is capped to what the deck can still support once it runs low.
# CEM-tunable (PTCG_W_DECKOUT_THRESHOLD); defaults to the shipped value when unset.
DECKOUT_THRESHOLD = _env_num("PTCG_W_DECKOUT_THRESHOLD", 5, int)


def own_deck_count(obs):
    """Our remaining deck count from the observation, or None when unavailable."""
    state = obs.get("current") or {}
    yi = state.get("yourIndex", 0)
    players = state.get("players") or []
    if len(players) <= yi:
        return None
    return players[yi].get("deckCount")


# When our deck is at or below this, stop voluntarily drilling it down with draw
# trainers. Real ladder replays (Phase 4 scout) show the deckout losses come not
# from a single over-draw COUNT but from replaying draw Supporters and Items turn
# after turn (Mega Signal, Waitress, Lillie's Determination, Cyrano) until the
# deck hits zero, twice while not behind on prizes. The COUNT guard above never
# fired in any of those games because the mill was all PLAY actions. Near deckout
# we still develop Pokemon and attack; only the card-advantage trainer is skipped
# so the deck survives long enough to close on prizes.
# CEM-tunable (PTCG_W_DRAW_CONSERVE_THRESHOLD); defaults to the shipped value when unset.
DRAW_CONSERVE_THRESHOLD = _env_num("PTCG_W_DRAW_CONSERVE_THRESHOLD", 8, int)
# Only Item and Supporter trainers can drill the deck for card advantage; a
# Pokemon, energy attach, Tool, or Stadium never does. The narrower _drills_deck
# predicate below decides which of these to actually decline near deckout.
CONSERVED_TRAINER_TYPES = frozenset({CARD_ITEM, CARD_SUPPORTER})


def _drills_deck(card_id) -> bool:
    """True when playing this trainer net-depletes our deck for no board gain.

    These are the engines that mill us toward a self-deckout: draw/search cards
    that move deck cards into hand (Mega Signal, Cyrano, Lillie's Determination,
    Ultra Ball) and deck-destruction items that discard from the deck (Hole-
    Digging Shovel, Brilliant Blender). A trainer that turns deck cards into board
    development (Precious Trolley benches a Basic, Waitress attaches an Energy) is
    kept: it is the "develop, do not hoard" play the deckout guard means to allow.
    Cards that move the discard pile back into the deck (Sacred Ash, Energy
    Recycler) grow the deck and are kept too, and a card that returns cards from
    the discard pile into the hand (Night Stretcher) never touches the deck, so it
    is a resource recovery, not a mill, and is kept as well. Card data ships the
    effect text offline so this reads the text rather than guessing by type.
    Conservative on missing data: an Item or Supporter whose text is unavailable is
    treated as a driller, preserving the prior safe skip-every-trainer behavior.
    Pure, never raises.
    """
    if _card_type(card_id) not in CONSERVED_TRAINER_TYPES:
        return False
    text = _card_text(card_id)
    if text is None:
        return True
    # Delegated to the card-knowledge layer (agents/card_effects.py): a trainer
    # drills the deck when it DRAWs, searches a card into hand that is not a
    # discard-pile recovery, or discards from the deck. tags == the exact signals
    # the old inline scan read here (test_card_effects pins the pool-wide match).
    tags = card_effects.tag_text(text)
    return (
        card_effects.DRAW in tags
        or (
            card_effects.SEARCH_TO_HAND in tags
            and card_effects.RECOVERS_FROM_DISCARD not in tags
        )
        or card_effects.DISCARDS_FROM_DECK in tags
    )


def play_card_id(opt, me):
    """The cardId a PLAY option refers to, read from our hand. None if unknown.

    A PLAY option carries a hand index (and no area), so the generic
    option_card_id, which keys off area, cannot resolve it. Pure, never raises.
    """
    cid = opt.get("cardId")
    if cid:
        return cid
    idx = opt.get("index")
    hand = (me or {}).get("hand") or []
    if isinstance(idx, int) and 0 <= idx < len(hand) and hand[idx]:
        return hand[idx].get("id")
    return None


def _first_pokemon_play(play_opts, me):
    """Option index of the first PLAY that benches a Pokemon, or None.

    A PLAY option whose card id resolves to a Pokemon type is a Basic being put
    onto the bench (evolutions are handled by the EVOLVE branch before PLAY, so
    they never reach here). Unresolvable ids are skipped, never mistaken for a
    Pokemon. Shared by the bench-development guard and the near-deckout milling
    guard so both prefer the same develop play.
    """
    return next(
        (oi for oi, opt in play_opts
         if _card_type(play_card_id(opt, me)) == CARD_POKEMON),
        None,
    )


def _benches_basic_from_deck(card_id) -> bool:
    """True when playing this trainer searches the deck and benches a Basic Pokemon.

    Precious Trolley ("Search your deck for any number of Basic Pokemon and put
    them onto your Bench") is the one card in the pool that directly fills an empty
    bench from the deck, exactly the answer to the early_collapse loss (a lone
    active knocked out with an empty bench). Card data ships the effect text
    offline, so this reads the text rather than hard-coding an id, and any Nest
    Ball style basic-to-bench search generalizes for free. A deck search that only
    grabs an evolution or ex to hand (Mega Signal, Cyrano, Ultra Ball) does not put
    a benchable Basic into play and is left out. Pure, never raises.
    """
    if _card_type(card_id) not in CONSERVED_TRAINER_TYPES:
        return False
    return card_effects.BENCH_BASIC_FROM_DECK in card_effects.tag_text(
        _card_text(card_id)
    )


def _first_bench_fetch_play(play_opts, me):
    """Option index of the first PLAY that fetches a Basic onto the bench, or None.

    When the bench is thin and no Basic is directly in hand to bench, a trainer
    that searches the deck and benches a Basic (Precious Trolley) is the develop
    play. Ordering it first matters: a hand-disrupting play kept ahead of it can
    strand it (Lillie's Determination shuffles the whole hand, including the
    Trolley, back into the deck), so the empty bench never gets filled that turn.
    """
    return next(
        (oi for oi, opt in play_opts
         if _benches_basic_from_deck(play_card_id(opt, me))),
        None,
    )


def _evolves_basic_to_stage2(card_id) -> bool:
    """True when this trainer evolves a Basic straight to a Stage 2, skipping Stage 1.

    Rare Candy ("If you have a Stage 2 card in your hand that evolves from that
    Pokemon, put that card onto the Basic Pokemon to evolve it, skipping the Stage
    1") is the accelerator that brings a deck's Stage 2 payoff attacker online a
    full turn sooner. Read from the effect text offline so any equivalent
    accelerator generalizes rather than hard-coding an id; a deck without such a
    card (the trolley deck) has no matching play and the driver below stays inert.
    Pure, never raises.
    """
    if _card_type(card_id) not in CONSERVED_TRAINER_TYPES:
        return False
    return card_effects.RARE_CANDY_EVOLVE in card_effects.tag_text(
        _card_text(card_id)
    )


def _in_play_basic_names(me) -> set:
    """Names of every un-evolved Basic Pokemon we have in play (active plus bench).

    An in-play Pokemon shows the id of its current top card, so an already-evolved
    line reports its Stage 1/2 id and is excluded; only a Basic still sitting as a
    Basic is a Rare Candy target. Pure, never raises.
    """
    cards = card_index()
    names = set()
    for zone in (me.get("active"), me.get("bench")):
        for p in (zone or []):
            cid = p.get("id") if p else None
            if cid and is_basic_pokemon(cid):
                c = cards.get(cid)
                if c is not None and getattr(c, "name", None):
                    names.add(c.name)
    return names


def _rare_candy_has_target(me) -> bool:
    """True when a Rare Candy play would actually evolve a Basic to its Stage 2.

    Rare Candy is offered whenever it sits in hand, but its effect is conditional:
    it fires only when we hold a Stage 2 whose line traces back to a Basic already
    in play. Preferring it without a target would waste the card, so confirm one:
    some Stage 2 in hand -> its Stage 1 (by name) -> that Stage 1's Basic (by name)
    matches a Basic we have in play. Pure, defensive, never raises.
    """
    in_play = _in_play_basic_names(me or {})
    if not in_play:
        return False
    cards = card_index()
    names = _name_index()
    for entry in (me or {}).get("hand") or []:
        cid = entry.get("id") if entry else None
        c = cards.get(cid) if cid else None
        if c is None or not getattr(c, "stage2", False):
            continue
        stage1 = names.get(getattr(c, "evolvesFrom", None))
        if stage1 is not None and getattr(stage1, "evolvesFrom", None) in in_play:
            return True
    return False


def _first_rare_candy_play(play_opts, me):
    """Option index of a Rare Candy play with a live Stage 2 target, or None.

    Gated on _rare_candy_has_target so the accelerator is preferred only when it
    will land a Stage 2 on a Basic in play, never burned on an empty condition.
    """
    if not _rare_candy_has_target(me):
        return None
    return next(
        (oi for oi, opt in play_opts
         if _evolves_basic_to_stage2(play_card_id(opt, me))),
        None,
    )


def choose_play(play_opts, me, obs):
    """Pick which card to PLAY, developing the bench and conserving deck near a self-deckout.

    play_opts is the list of (option_index, option) PLAY pairs. In normal play it
    benches a Basic Pokemon first whenever the bench is thin (guarding the
    early_collapse loss bucket), otherwise it keeps the prior behavior (the first
    play option). When our deck is critically low it refuses to mill: it develops
    a Pokemon if one can be played, otherwise any play it can confirm does not
    drill the deck (an energy attach, a bench-develop trainer), and returns None
    when only deck-drilling or unidentifiable plays remain so the caller ends the
    turn instead of drawing us out. A play whose card id cannot be resolved from
    the observation is treated as a potential driller near deckout: the guard
    cannot confirm it is safe, so it must not fail open and mill us (this matches
    _drills_deck staying conservative when a trainer's text is missing). In real
    play your own hand carries card ids, so this branch is inert; it only bites a
    degenerate observation, never a normal develop play. Never raises.
    """
    if not play_opts:
        return None
    deck_n = own_deck_count(obs)
    near_deckout = deck_n is not None and deck_n <= DRAW_CONSERVE_THRESHOLD
    if not near_deckout:
        # Bench development guards the #1 ladder loss bucket (early_collapse: our
        # lone active gets knocked out with an empty bench and no promote, losing
        # with prizes untouched). When the bench is thin, bench a Basic Pokemon
        # before any other play. Nothing is sacrificed: other PLAY options remain
        # legal on later decisions this same turn, since PLAY is not once-per-turn.
        if _bench_is_thin(obs):
            poke = _first_pokemon_play(play_opts, me)
            if poke is not None:
                return poke
            # No Basic in hand to bench directly: search one out of the deck onto
            # the bench (Precious Trolley) before any hand-disrupting play strands
            # it. This is the draw-access answer to the empty-bench collapse when
            # the hand holds no benchable Basic (the dominant early_collapse case).
            fetch = _first_bench_fetch_play(play_opts, me)
            if fetch is not None:
                return fetch
            # No Basic in hand and no direct bench-fetch trainer: dig for one. A
            # draw/search trainer that drills the deck (_drills_deck) can turn up a
            # Basic this turn, the untried consistency lever the empty-bench draw-
            # variance finding points at. Preferred over an energy attach or a non-
            # digging item so the thin-bench turn spends its play on finding backup.
            if _BENCH_DIG:
                dig = next(
                    (oi for oi, opt in play_opts
                     if _drills_deck(play_card_id(opt, me))),
                    None,
                )
                if dig is not None:
                    return dig
        return play_opts[0][0]
    pokemon_play = _first_pokemon_play(play_opts, me)
    if pokemon_play is not None:
        return pokemon_play
    non_draw_play = next(
        (oi for oi, opt in play_opts
         if (cid := play_card_id(opt, me)) is not None and not _drills_deck(cid)),
        None,
    )
    return non_draw_play  # None when only drilling/unknown plays remain -> skip


def cap_count_for_deckout(move, sel, obs) -> list:
    """Cap a voluntary over-draw so we never request more cards than the deck holds.

    Acts only on a COUNT selection when our deck is critically low; reduces the
    chosen number to the largest legal count the deck can still support and never
    enlarges it, so the result stays legal and strictly safer. Inert in normal
    play (deck above the threshold) and never raises. Shared by the heuristic and
    the search agent so neither mills itself to death in the endgame.
    """
    try:
        if sel.get("type") != SEL_COUNT or len(move) != 1:
            return move
        deck_n = own_deck_count(obs)
        if deck_n is None or deck_n > DECKOUT_THRESHOLD:
            return move
        opts = sel.get("option", [])
        chosen = opts[move[0]].get("number")
        if chosen is None or chosen <= deck_n:
            return move
        numbered = [
            (o.get("number", 0), i)
            for i, o in enumerate(opts)
            if o.get("type") == OPT_NUMBER
        ]
        safe = [t for t in numbered if t[0] <= deck_n]
        if safe:
            # Largest count that does not over-draw; lowest index breaks ties.
            return [max(safe, key=lambda t: (t[0], -t[1]))[1]]
        if numbered:
            # Every count over-draws, so take the smallest to lose the least deck.
            return [min(numbered, key=lambda t: (t[0], t[1]))[1]]
    except Exception:
        pass
    return move


# Discard desirability: higher is discarded sooner. Energy is the surplus a
# water-discard or consistency deck runs in bulk, so it pays a discard cost
# before any Pokemon. Pokemon (basics and the evolution combo line) are kept.
def _discard_rank(card_id) -> int:
    ct = _card_type(card_id)
    if ct == CARD_BASIC_ENERGY:
        return 3
    if ct == CARD_SPECIAL_ENERGY:
        return 2
    if ct == CARD_POKEMON:
        return 0  # keep: board development and combo pieces
    return 1  # items, supporters, stadiums, tools, or unknown


def _choose_discard(sel, obs, mn) -> list:
    """Pay a discard cost with the least valuable cards, sparing Pokemon.

    Discards minCount cards (the cheapest a cost allows, capped by how many
    options exist), choosing the most expendable first so the last basic and the
    evolution combo line survive.
    """
    if mn <= 0:
        return []
    opts = sel.get("option", [])
    ranked = sorted(
        range(len(opts)),
        key=lambda i: (-_discard_rank(option_card_id(opts[i], sel, obs)), i),
    )
    return sorted(ranked[:mn])


def _choose_card_select(sel, obs) -> list:
    """A CARD selection: fetch a Basic when thin, spare combo pieces on discard.

    On a context that puts a Pokemon into play or hand, when our bench is thin we
    pick a Basic Pokemon so a knocked-out lone active always has a backup. On a
    discard cost we shed surplus energy and keep Pokemon. Every other CARD
    selection keeps the prior first-legal behavior, so a healthy board is never
    steered off its normal play.
    """
    ctx = sel.get("context")
    mn = sel.get("minCount", 1)
    mx = sel.get("maxCount", 1)
    if ctx == CTX_DISCARD and mx >= 1:
        return _choose_discard(sel, obs, mn)
    if ctx in GAIN_POKEMON_CONTEXTS and mn <= 1 <= mx:
        bench = my_bench_count(obs)
        if bench is not None and bench < THIN_BENCH:
            basic = next(
                (i for i, o in enumerate(sel.get("option", []))
                 if is_basic_pokemon(option_card_id(o, sel, obs))),
                None,
            )
            if basic is not None:
                return [basic]
    return _first_legal(sel)


def _choose_subselect(sel, obs) -> list:
    st = sel.get("type")
    opts = sel.get("option", [])
    if st == SEL_YES_NO:
        yes = next((i for i, o in enumerate(opts) if o.get("type") == OPT_YES), None)
        no = next((i for i, o in enumerate(opts) if o.get("type") == OPT_NO), None)
        # Going second lets us attack first; otherwise prefer activating effects.
        if sel.get("context") == CTX_IS_FIRST and no is not None:
            return [no]
        if yes is not None:
            return [yes]
        if no is not None:
            return [no]
    elif st == SEL_COUNT:
        numbered = [(o.get("number", 0), i) for i, o in enumerate(opts)
                    if o.get("type") == OPT_NUMBER]
        if numbered:
            # Prefer the maximum count, but never draw ourselves out when low.
            return cap_count_for_deckout([max(numbered)[1]], sel, obs)
    elif st == SEL_CARD:
        return _choose_card_select(sel, obs)
    return _first_legal(sel)


def choose(obs) -> list:
    """Return option indices for the current decision. Never raises.

    Ordered FORCE/VETO guard stack (U37), each guard scorer-independent: it holds
    under any PRIO_* weighting, so a future learned option-scorer (U41) inserted
    below it can never override a safety guard. In priority order:

      L1 lethal FORCE      -- a guaranteed knockout is taken first, ahead of the
                              whole category scorer (test_safety guard-order lock).
      L2 ability-loop VETO -- only a once-per-turn ability is ever activated; a
                              repeatable ability is refused no matter how high the
                              ABILITY category is scored (the stateless-loop guard).
      L3 deckout VETO      -- near a self-deckout the PLAY resolver declines a
                              deck-drilling trainer even when PLAY tops the scorer.
      L4 thin-bench FORCE  -- a thin bench benches/fetches a Basic before other
                              plays, and holds Rare Candy back (early_collapse).
      L5 Rare Candy FORCE  -- with a live Stage 2 target and a healthy bench, the
                              accelerator is preferred inside the PLAY/CANDY category.

    Below the stack sits the CEM-tunable PRIO category scorer; below that, END and
    the guaranteed first-legal fallback. The three safety guards L1 (never miss a
    lethal), L2 (never loop on an ability) and L3 (never self-deckout) are locked
    scorer-independent against an adversarially maxed scorer in tests/test_safety.py,
    so the U41 scorer hook lands against a tested contract. The two strategic forces
    L4 and L5 are early_collapse/tempo levers inside the PLAY and CANDY resolvers,
    locked at the shipped weights in tests/test_heuristic.py.
    """
    sel = obs.get("select")
    if sel is None:
        return []  # deck selection is handled by the agent, not here
    if sel.get("type") != SEL_MAIN:
        return _choose_subselect(sel, obs)

    options = sel.get("option", [])
    groups = options_by_type(options)
    state = obs.get("current") or {}
    yi = state.get("yourIndex", 0)
    players = state.get("players") or []
    me = players[yi] if len(players) > yi else {}
    opp = players[1 - yi] if len(players) > 1 - yi else {}

    my_active = _active(me)
    opp_active = _active(opp)
    my_active_id = my_active.get("id") if my_active else None
    opp_active_id = opp_active.get("id") if opp_active else None
    opp_active_hp = opp_active.get("hp") if opp_active else None

    ba = best_attack(groups, my_active_id, opp_active_id, opp_active_hp)
    lethal = ba is not None and ba[2]

    # 1. Take a knockout immediately (safety-1, never reordered).
    if lethal:
        return [ba[0]]

    # 2. A genome-scored category ordering. At the shipped default priorities this
    #    reproduces the historical fixed ladder EXACTLY (rare-candy -> evolve ->
    #    play -> attach -> ability -> retreat -> attack); CEM tunes the per-category
    #    PRIO_* weights so the optimizer can reach the ordering levers the expert
    #    move-ranking breakdown flagged (the ABILITY gap, the EVOLVE ordering),
    #    which the threshold knobs could not move (analysis/cem_signal_flat.md).
    #    Each resolver returns a legal option index or None (its category is absent
    #    or its gate declines); the highest-priority resolver that yields a move
    #    wins, and the default order breaks ties so a tuned vector stays
    #    deterministic. Loop-safety is order-independent: each category consumes a
    #    resource (evolve/play/attach) or ends the turn (attack), and only a
    #    once-per-turn ability is ever taken, so any ordering terminates the turn.
    def _resolve_candy():
        # Rare Candy evolves a Basic straight to its Stage 2 (skipping Stage 1),
        # bringing the payoff attacker online a turn sooner; evolving to Stage 1
        # first would consume the Basic and waste the accelerator. Held back when
        # the bench is thin (surviving the empty-bench collapse outranks tempo) and
        # inert on decks with no such card (trolley).
        if OPT_PLAY in groups and not _bench_is_thin(obs):
            return _first_rare_candy_play(groups[OPT_PLAY], me)
        return None

    def _resolve_evolve():
        return groups[OPT_EVOLVE][0][0] if OPT_EVOLVE in groups else None

    def _resolve_play():
        return choose_play(groups[OPT_PLAY], me, obs) if OPT_PLAY in groups else None

    def _resolve_attach():
        return _choose_attach(groups[OPT_ATTACH], me) if OPT_ATTACH in groups else None

    def _resolve_attack_first():
        # PTCG_ATTACK_FIRST (default off, see the flag comment above): take an
        # already-legal positive-value attack now instead of the discretionary
        # attach. Returns None (no-op) whenever the flag is off or the narrow
        # condition does not hold, so the normal ladder (attach, then attack)
        # runs unchanged.
        if not _ATTACK_FIRST:
            return None
        if OPT_ATTACH not in groups:
            return None
        if ba is None or ba[1] <= 0:
            return None
        return ba[0]

    def _resolve_ability():
        # A once-per-turn ability engine (draw/search/damage abilities are 12% of
        # the top players' MAIN actions and the pilot has never used one, 0/554;
        # see analysis/move_ranking_diverges_ability_gap.md). Flag-guarded (default
        # off) so shipped builds stay byte-identical until validated and A/B'd;
        # loop-safe because only a "once during your turn" ability is taken.
        if _ABILITY and OPT_ABILITY in groups:
            return _once_per_turn_ability(groups[OPT_ABILITY], sel, obs)
        return None

    def _resolve_retreat():
        if OPT_RETREAT in groups and should_retreat(my_active, me.get("bench"), lethal, opp_active):
            return groups[OPT_RETREAT][0][0]
        return None

    def _resolve_attack():
        # PTCG_PRIZE_CLOSE (default off): with 1-2 prizes remaining, prefer any
        # attack that wins the game (OHKOs opponent). Falls back to best positive
        # damage attack (lethal or otherwise) if no prize-winning move is available.
        if _PRIZE_CLOSE and ba is not None and ba[2]:  # (index, eff_damage, is_lethal)
            our_prizes = _our_prize_count(obs)
            if our_prizes <= 2 and our_prizes > 0:
                # We're close on prizes and have a lethal attack: take it to win
                return ba[0]
        if ba is not None and ba[1] > 0:
            return ba[0]
        if OPT_ATTACK in groups:
            return groups[OPT_ATTACK][0][0]
        return None

    # PTCG_ENDGAME_PLAY (default off, see the flag comment above): near-endgame
    # (either side at or below 2 prizes) with a bloated hand and both OPT_PLAY and
    # OPT_EVOLVE legal, demote EVOLVE from PRIO_EVOLVE to just below PRIO_PLAY (with
    # its own tiebreak so it still outranks attach/ability/retreat/attack) so the
    # hand is spent before the discretionary evolution. Flag off, or the trigger
    # absent, leaves _evolve_prio/_evolve_tb at their historical values and the
    # ladder byte-identical.
    _endgame_play_fires = (
        _ENDGAME_PLAY
        and OPT_PLAY in groups
        and OPT_EVOLVE in groups
        and len(me.get("hand") or []) >= ENDGAME_HAND
        and min(_our_prize_count(obs), _opp_prize_count(obs)) <= 2
    )
    _evolve_prio = (PRIO_PLAY - 0.5) if _endgame_play_fires else PRIO_EVOLVE
    _evolve_tb = 2.1 if _endgame_play_fires else 1

    # (priority, default-order tiebreak, resolver).
    ladder = (
        (PRIO_CANDY, 0, _resolve_candy),
        (_evolve_prio, _evolve_tb, _resolve_evolve),
        (PRIO_PLAY, 2, _resolve_play),
        (PRIO_ATTACH + 0.5, 2.5, _resolve_attack_first),
        (PRIO_ATTACH, 3, _resolve_attach),
        (PRIO_ABILITY, 4, _resolve_ability),
        (PRIO_RETREAT, 5, _resolve_retreat),
        (PRIO_ATTACK, 6, _resolve_attack),
    )
    for _prio, _tb, resolve in sorted(ladder, key=lambda e: (-e[0], e[1])):
        idx = resolve()
        if idx is not None:
            return [idx]

    # 3. End the turn, or fall back to any legal selection.
    if OPT_END in groups:
        return [groups[OPT_END][0][0]]
    return _first_legal(sel)
