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

import re
import sys
from functools import lru_cache
from pathlib import Path

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
THIN_BENCH = 2

# Standard damage modifiers. cabt uses x2 weakness and a flat resistance cut.
WEAKNESS_MULT = 2
RESISTANCE_CUT = 30

# Retreat when the active is at or below this fraction of its max HP.
RETREAT_HP_RATIO = 0.34


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


def _active(player):
    act = player.get("active") or []
    return act[0] if act and act[0] is not None else None


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


def should_retreat(my_active, bench, lethal_available) -> bool:
    """Retreat only when the active is endangered and a healthier bench exists.

    Skipped when a lethal attack is on the table (take the knockout instead) or
    when no bench Pokemon is in better shape than the active.
    """
    if my_active is None or lethal_available:
        return False
    hp = my_active.get("hp", 0)
    mx = my_active.get("maxHp") or hp
    if mx <= 0 or hp / mx > RETREAT_HP_RATIO:
        return False
    return any(b for b in (bench or []) if b and b.get("hp", 0) > hp)


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
DECKOUT_THRESHOLD = 5


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
DRAW_CONSERVE_THRESHOLD = 8
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
    Recycler) grow the deck and are kept too. Card data ships the effect text
    offline so this reads the text rather than guessing by type. Conservative on
    missing data: an Item or Supporter whose text is unavailable is treated as a
    driller, preserving the prior safe skip-every-trainer behavior. Pure, never
    raises.
    """
    if _card_type(card_id) not in CONSERVED_TRAINER_TYPES:
        return False
    text = _card_text(card_id)
    if text is None:
        return True
    t = text.lower()
    # \bdraw matches "draw"/"draws" but not "withdraw" (a switch effect, no deck
    # drill). "into your hand" catches search-to-hand. A discard that names the
    # deck as the source ("of your deck", "your deck for ... discard") destroys
    # deck cards; a discard-pile recycler ("into your deck") only grows it, so it
    # is left out by requiring the deck-source phrasing rather than bare "deck".
    discards_from_deck = "discard" in t and (
        "of your deck" in t or "your deck for" in t
    )
    return (
        bool(re.search(r"\bdraw", t))
        or "into your hand" in t
        or discards_from_deck
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


def choose_play(play_opts, me, obs):
    """Pick which card to PLAY, conserving deck near a self-deckout.

    play_opts is the list of (option_index, option) PLAY pairs. In normal play it
    keeps the prior behavior (the first play option). When our deck is critically
    low it refuses to mill: it develops a Pokemon if one can be played, otherwise
    any play it can confirm does not drill the deck (an energy attach, a
    bench-develop trainer), and returns None when only deck-drilling or
    unidentifiable plays remain so the caller ends the turn instead of drawing us
    out. A play whose card id cannot be resolved from the observation is treated
    as a potential driller near deckout: the guard cannot confirm it is safe, so
    it must not fail open and mill us (this matches _drills_deck staying
    conservative when a trainer's text is missing). In real play your own hand
    carries card ids, so this branch is inert; it only bites a degenerate
    observation, never a normal develop play. Never raises.
    """
    if not play_opts:
        return None
    deck_n = own_deck_count(obs)
    if deck_n is None or deck_n > DRAW_CONSERVE_THRESHOLD:
        return play_opts[0][0]
    pokemon_play = non_draw_play = None
    for oi, opt in play_opts:
        cid = play_card_id(opt, me)
        if _card_type(cid) == CARD_POKEMON and pokemon_play is None:
            pokemon_play = oi
        if cid is not None and not _drills_deck(cid) and non_draw_play is None:
            non_draw_play = oi
    if pokemon_play is not None:
        return pokemon_play
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
    """Return option indices for the current decision. Never raises."""
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

    # 1. Take a knockout immediately.
    if lethal:
        return [ba[0]]
    # 2. Evolve, then develop the hand, then power up the attacker.
    if OPT_EVOLVE in groups:
        return [groups[OPT_EVOLVE][0][0]]
    if OPT_PLAY in groups:
        play_idx = choose_play(groups[OPT_PLAY], me, obs)
        if play_idx is not None:
            return [play_idx]
    if OPT_ATTACH in groups:
        attach = groups[OPT_ATTACH]
        active_attach = next(
            (i for i, op in attach if op.get("inPlayArea") == AREA_ACTIVE), None
        )
        return [active_attach if active_attach is not None else attach[0][0]]
    # 3. Retreat an endangered active before chipping in with a weak attack.
    if OPT_RETREAT in groups and should_retreat(
        my_active, me.get("bench"), lethal
    ):
        return [groups[OPT_RETREAT][0][0]]
    # 4. Otherwise attack with the strongest option available.
    if ba is not None and ba[1] > 0:
        return [ba[0]]
    if OPT_ATTACK in groups:
        return [groups[OPT_ATTACK][0][0]]
    # 5. End the turn, or fall back to any legal selection.
    if OPT_END in groups:
        return [groups[OPT_END][0][0]]
    return _first_legal(sel)
