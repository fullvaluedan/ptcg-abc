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
- Every path falls through to a guaranteed legal selection.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

# OptionType values (api.py OptionType enum).
OPT_NUMBER = 0
OPT_YES = 1
OPT_NO = 2
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
SEL_COUNT = 8
SEL_YES_NO = 9

# AreaType: the Active Spot.
AREA_ACTIVE = 4

# SelectContext: would you like to go first?
CTX_IS_FIRST = 41

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


def _choose_subselect(sel) -> list:
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
            return [max(numbered)[1]]
    return _first_legal(sel)


def choose(obs) -> list:
    """Return option indices for the current decision. Never raises."""
    sel = obs.get("select")
    if sel is None:
        return []  # deck selection is handled by the agent, not here
    if sel.get("type") != SEL_MAIN:
        return _choose_subselect(sel)

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
        return [groups[OPT_PLAY][0][0]]
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
