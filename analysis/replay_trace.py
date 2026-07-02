"""Replay-trace spine: the shared resolved-decision population (plan U32).

Every downstream imitation unit -- the card-knowledge coverage gate (U33), the
game-plan miner (U36), the featurizer and dataset (U40) -- has to read the SAME
expert decisions off the same replays, split into train and test the same way, or
their numbers do not compose. This module is that single source. It owns the MAIN
single-pick decision iterator the move-ranking validator and the census already
shared, adds option-to-card/attack resolution so a consumer sees WHICH card or
attack each option refers to (not just its action category), and owns the one
canonical md5 episode split (KD4) so train / test membership is identical
everywhere it is asked.

Pure and defensive over the raw replay dict, and cg-free at import: option
resolution reads only the observation (select.deck and the visible board areas),
never the card engine, so this unit-tests without cg exactly as the census does.
The move-ranking validator and the expert cohort now import their decision
primitives from here and re-export them, so there is exactly one definition of a
scorable expert decision in the codebase. Reads the competition dataset but never
redistributes it (replay files stay gitignored).
"""
from __future__ import annotations

import hashlib

# SelectType.MAIN (api.py SelectType enum): the once-per-turn top-level decision
# where the pilot chooses among ATTACH / PLAY / EVOLVE / RETREAT / ATTACK / END.
# Kept local so the spine has no import-time dependency on the pilot module and can
# trace any replay without loading the card engine.
SEL_MAIN = 0

# OptionType (api.py OptionType enum) values that can appear at a MAIN decision,
# mapped to the action category name. A MAIN option's `type` field names the KIND
# of action, so labeling the option turns a raw index into a readable category.
OPT_CATEGORY = {
    7: "PLAY",
    8: "ATTACH",
    9: "EVOLVE",
    10: "ABILITY",
    12: "RETREAT",
    13: "ATTACK",
    14: "END",
}

# Area values (api.py Area enum) a CARD option can index into. Deck is the only
# area revealed on the select itself; the rest index the deciding player's own
# visible board. Kept local for the same reason the OptionType map is: the spine
# resolves an option to a card id from the observation alone, no card engine.
AREA_DECK = 1
AREA_HAND = 2
AREA_DISCARD = 3
AREA_ACTIVE = 4
AREA_BENCH = 5


def team_seat(replay, expert_teams) -> int | None:
    """Seat index (0 or 1) whose team name is in `expert_teams`, or None.

    A replay records the two competitors in `info.TeamNames`, seat-ordered. This
    maps the caller's set of expert handles to the seat they played. Returns None
    when neither seat (or both) match, so an episode with no clear single expert
    seat is skipped rather than scored against an unknown pilot. Pure, never raises.
    """
    try:
        names = ((replay.get("info") or {}).get("TeamNames")) or []
    except AttributeError:
        return None
    if not isinstance(names, (list, tuple)) or len(names) < 2:
        return None
    wanted = {str(t) for t in expert_teams}
    matches = [i for i in (0, 1) if str(names[i]) in wanted]
    return matches[0] if len(matches) == 1 else None


def _played_index(action) -> int | None:
    """The single option index an expert played, or None when not a single pick.

    A MAIN decision records the action as a list of chosen option indices. Only
    single-pick decisions (the ones an argmax pilot also answers with one index)
    are scorable, so anything but a one-element list of a non-negative int is None.
    """
    if not isinstance(action, (list, tuple)) or len(action) != 1:
        return None
    idx = action[0]
    if isinstance(idx, bool) or not isinstance(idx, int) or idx < 0:
        return None
    return idx


def _area_zone(player, area):
    """The card list of a player's area, or None for areas without a card list.

    Mirrors agents.heuristics._area_zone but stays cg-free and reads only the
    observation, so the spine resolves a card id without importing the pilot.
    """
    if not isinstance(player, dict):
        return None
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
    """Resolve the cardId a CARD-bearing option refers to, or None.

    A CARD option carries area + index, not the cardId itself. Deck-search options
    index into select.deck (the only time the deck is revealed); hand and board
    options index into the matching area of the deciding player's visible state.
    Mirrors agents.heuristics.option_card_id exactly but over the observation only
    (no card engine), so the spine and the pilot resolve options the same way while
    the spine stays cg-free. Pure and defensive: any missing piece yields None.
    """
    if not isinstance(opt, dict):
        return None
    try:
        cid = opt.get("cardId")
        if cid:
            return cid
        area = opt.get("area")
        idx = opt.get("index")
        if idx is None:
            return None
        deck = sel.get("deck") if isinstance(sel, dict) else None
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
            return entry.get("id") if isinstance(entry, dict) else None
    except (AttributeError, TypeError, KeyError, IndexError):
        return None
    return None


def resolve_option(opt, sel, obs) -> dict:
    """A MAIN option resolved to its category, card id, and attack id.

    Turns one raw option dict into {type, category, card_id, attack_id}: the
    OptionType, its action-category name, the card id it plays / attaches / evolves
    (via option_card_id), and the attackId an ATTACK option carries directly. A
    non-dict option or an unresolvable card yields None fields rather than raising,
    so a consumer can read WHICH card or attack every option refers to without its
    own decoder. Pure over the observation, cg-free.
    """
    if not isinstance(opt, dict):
        return {"type": None, "category": "OTHER", "card_id": None, "attack_id": None}
    otype = opt.get("type")
    return {
        "type": otype,
        "category": OPT_CATEGORY.get(otype, "OTHER"),
        "card_id": option_card_id(opt, sel, obs),
        "attack_id": opt.get("attackId"),
    }


def _scorable_main(obs, expert_index):
    """The (sel, options) of a scorable MAIN decision by `expert_index`, or None.

    A scorable decision: the deciding seat is `expert_index`, the select is a MAIN
    single-pick (minCount == maxCount == 1) among more than one option. Returns the
    select dict and its option list so both the plain and the resolved iterators
    apply exactly the same gate. None on any miss. Pure, never raises.
    """
    if not isinstance(obs, dict):
        return None
    sel = obs.get("select")
    current = obs.get("current")
    if not isinstance(sel, dict) or not isinstance(current, dict):
        return None
    if current.get("yourIndex", None) != expert_index:
        return None
    if sel.get("type") != SEL_MAIN:
        return None
    if sel.get("minCount", 1) != 1 or sel.get("maxCount", 1) != 1:
        return None
    options = sel.get("option") or []
    if len(options) <= 1:
        return None
    return sel, options


def _iter_active_obs(replay, expert_index):
    """Yield each ACTIVE observation the `expert_index` seat decided on.

    The one place the ACTIVE / this-seat gating lives, so every trace iterator reads
    the same records. A malformed step or entry is skipped. Pure, never raises.
    """
    steps = replay.get("steps") or []
    for step in steps:
        if not isinstance(step, (list, tuple)):
            continue
        for entry in step:
            if not isinstance(entry, dict) or entry.get("status") != "ACTIVE":
                continue
            obs = entry.get("observation") or {}
            yield obs, entry


def iter_expert_decisions(replay, expert_index):
    """Yield (obs, played_index) for each scorable MAIN decision by `expert_index`.

    The observation is yielded unchanged so a candidate `choose(obs)` decides on the
    exact real state, and the played index is the option the expert actually chose.
    Mirrors the ACTIVE / select / current gating in loss_classifier.parse_replay so
    the whole codebase reads the same decisions. Pure and defensive: a malformed
    step is skipped, never fatal.
    """
    for obs, entry in _iter_active_obs(replay, expert_index):
        got = _scorable_main(obs, expert_index)
        if got is None:
            continue
        _sel, options = got
        idx = _played_index(entry.get("action"))
        if idx is None or idx >= len(options):
            continue
        yield obs, idx


def iter_resolved_decisions(replay, expert_index):
    """Yield a resolved-decision record for each scorable MAIN decision.

    The richer trace every downstream unit consumes. For each scorable decision it
    yields {obs, played_index, played, options}: the raw observation, the index the
    expert chose, that option resolved (resolve_option), and every option resolved,
    so a consumer sees the card / attack behind each choice without re-deriving the
    gate or writing its own option decoder. Same gating as iter_expert_decisions.
    Pure and defensive.
    """
    for obs, entry in _iter_active_obs(replay, expert_index):
        got = _scorable_main(obs, expert_index)
        if got is None:
            continue
        sel, options = got
        idx = _played_index(entry.get("action"))
        if idx is None or idx >= len(options):
            continue
        resolved = [resolve_option(o, sel, obs) for o in options]
        yield {
            "obs": obs,
            "played_index": idx,
            "played": resolved[idx],
            "options": resolved,
        }


# --- canonical md5 episode split (KD4) --------------------------------------
#
# One deterministic train / test partition shared by every unit that reports a
# held-out number, so the split never drifts between the spike, the baseline
# recompute, and the trainer. The hash is over the episode id (the numeric replay
# stem), not the file path, so the same episode lands in the same bucket whether it
# is named "12345.json", "12345", or read from a directory or a zip.
SPLIT_TEST_PCT = 25


def episode_id_of(label) -> str:
    """The bare episode id of a replay label (drop directory and .json suffix)."""
    s = str(label)
    s = s.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if s.endswith(".json"):
        s = s[:-5]
    return s


def episode_bucket(episode_id) -> int:
    """md5(episode_id) mod 100: a stable bucket in [0, 100) for one episode.

    The single hashing rule behind the split. Hashing the string id (not a Python
    hash, which is salted per process) makes the partition reproducible across runs
    and machines. Pure.
    """
    key = episode_id_of(episode_id).encode("utf-8")
    return int(hashlib.md5(key).hexdigest(), 16) % 100


def split_of(episode_id, test_pct: int = SPLIT_TEST_PCT) -> str:
    """"test" when the episode's bucket is below `test_pct`, else "train".

    The low `test_pct` buckets are held out; everything else trains. Fixing the
    convention here (rather than at each call site) is what keeps train / test
    membership identical across units.
    """
    return "test" if episode_bucket(episode_id) < test_pct else "train"
