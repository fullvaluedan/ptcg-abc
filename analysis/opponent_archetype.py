"""Correlate ladder game outcomes with the opponent's deck archetype (Phase 4).

The loss classifier (analysis/loss_classifier.py) buckets our OWN end state: an
empty bench, a self-deckout, a prize blowout. It never looks across the table,
so the "deck_matchup" bucket it names was never grounded in which opponents
actually beat us. This module reads the opponent's revealed Pokemon from a
replay, labels their archetype by the headline attacker, and tallies our
win/loss record per archetype. If losses cluster on one archetype a tech card is
a real lever; if they spread across the whole field the collapse is opponent
agnostic and no sideboard card can fix it (the empty bench is our own bricking).

Pure over the replay dict plus injected card helpers (name_of, is_pokemon), so
the core is unit-tested offline without the card database. scan_dir wires in the
real card index and the scout seat/outcome helpers for live pulls.
"""
from __future__ import annotations

# Areas that hold face-up opponent Pokemon we can read a card id from. Prize and
# face-down cards read as None, and the hand is hidden, so none of those leak in.
_POKEMON_AREAS = ("active", "bench")


def revealed_opponent_pokemon(replay, opp_seat, is_pokemon) -> dict:
    """Multiset of opponent Pokemon card ids revealed across the whole game.

    opp_seat is the absolute seat (0 or 1) the opponent played; is_pokemon is a
    predicate card_id -> bool. Walks every step and both per player records,
    since only the acting seat carries a populated observation on a given step.
    Pure and defensive: any missing piece is skipped, never raised.
    """
    seen: dict = {}
    for step in replay.get("steps") or []:
        for rec in step:
            if not isinstance(rec, dict):
                continue
            obs = rec.get("observation") or {}
            current = obs.get("current") or {}
            players = current.get("players") or []
            if not (0 <= opp_seat < len(players)):
                continue
            opp = players[opp_seat] or {}
            for area in _POKEMON_AREAS:
                for entry in (opp.get(area) or []):
                    if not entry:
                        continue
                    cid = entry.get("id")
                    if cid is not None and is_pokemon(cid):
                        seen[cid] = seen.get(cid, 0) + 1
    return seen


def is_headline_name(name) -> bool:
    """True for a deck's headline attacker: a Mega evolution or an ex Pokemon.

    These name the archetype (Mega Starmie ex, Dragapult ex); support Pokemon
    (Fezandipiti, Dunsparce) and evolution stages are not tells on their own.
    """
    return bool(name) and (name.startswith("Mega ") or name.endswith(" ex"))


def archetype_label(id_counts, name_of, headline=is_headline_name) -> str:
    """Label an opponent by their revealed Pokemon.

    Prefers the headline attacker (Mega/ex line) so a deck is named by what wins
    it the game rather than by whatever basic happened to be revealed first. Ties
    on reveal frequency break on card id for determinism. Falls back to the most
    seen Pokemon, or a sentinel when nothing Pokemon was revealed.
    """
    ordered = sorted(id_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    names = [name_of(cid) for cid, _ in ordered]
    for n in names:
        if headline(n):
            return n
    # Most-seen named Pokemon; skip ids whose name did not resolve so an unknown
    # card never becomes the archetype label. Sentinel when nothing named shows.
    return next((n for n in names if n), "(unrevealed)")


def tally_matchups(rows) -> dict:
    """Tally win/loss/draw per archetype from (archetype, outcome) rows.

    outcome is one of "win", "loss", "draw" (anything else is ignored, e.g. an
    "unknown" reward). Returns {"per": {archetype: {win, loss, draw}}, "totals":
    {win, loss, draw}}. Pure; the caller sorts and formats for a report.
    """
    per: dict = {}
    totals = {"win": 0, "loss": 0, "draw": 0}
    for arch, outcome in rows:
        if outcome not in totals:
            continue
        rec = per.setdefault(arch, {"win": 0, "loss": 0, "draw": 0})
        rec[outcome] += 1
        totals[outcome] += 1
    return {"per": per, "totals": totals}


def scan_dir(replay_dir, team=None, our_index_fallback=0) -> dict:
    """Live wrapper: tally our matchups over every ladder replay in a directory.

    Wires the pure core to the real card database (agents.heuristics.card_index)
    and the scout seat/outcome helpers. Self-play (validation) games are skipped:
    both seats are our team, so they are not ladder opponents. Returns the
    tally_matchups result plus a per-game "rows" list for a detailed report.
    """
    import json
    from pathlib import Path

    from agents.heuristics import CARD_POKEMON, card_index
    from analysis.loss_classifier import parse_replay
    from tools.scout import OUR_TEAM, is_self_play, our_index_from_replay

    team = team or OUR_TEAM
    cards = card_index()

    def name_of(cid):
        c = cards.get(cid)
        return getattr(c, "name", None) if c is not None else None

    def is_pokemon(cid):
        c = cards.get(cid)
        return c is not None and getattr(c, "cardType", None) == CARD_POKEMON

    rows = []
    for path in sorted(Path(replay_dir).glob("*.json")):
        try:
            replay = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if is_self_play(replay):
            continue
        seat = our_index_from_replay(replay, team)
        our_index = seat if seat is not None else our_index_fallback
        digest = parse_replay(replay, our_index=our_index)
        outcome = digest.get("outcome")
        opp = revealed_opponent_pokemon(replay, 1 - our_index, is_pokemon)
        arch = archetype_label(opp, name_of)
        rows.append({"file": Path(path).name, "archetype": arch, "outcome": outcome})

    tally = tally_matchups((r["archetype"], r["outcome"]) for r in rows)
    tally["rows"] = rows
    return tally
