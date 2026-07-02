"""Expert cohort definition + census primitives (plan U25).

Resolves the 3/116-vs-40/1427 cohort fork with ONE definition: the expert seat
of an episode is the WINNING seat. Per-episode skill ratings are not in the
replay files (info carries only TeamNames / Agents, never an ELO), so the game
OUTCOME is the sole per-episode quality signal, and the winning seat's decisions
are exactly the distribution the imitation stack is meant to clone. This scales
to the full 5734-episode dataset (retiring the 3-named-team / 116-decision
starvation read that the move-ranking validator's DEFAULT_EXPERT_TEAMS produced)
and is identical to the winners-only cohort the census tiers already fall back
to, so the two forks collapse into one definition instead of drifting apart.

A census counts, per archetype family: expert-anchored episodes, MAIN decisions,
and ranking groups (the scorable multi-option single-pick decisions a pairwise
ranker learns from). The per-family group count picks the pre-committed training
tier for the target family.

Pure and defensive over the raw replay dict, and cg-free at import: family
classification takes injected archetype signatures (the census tool wires in the
real ones from analysis/archetype), so this module unit-tests without the card
engine. It reuses analysis/move_ranking_validator.iter_expert_decisions so the
census and the validator score the SAME decisions. Reads the competition
dataset, never redistributes it (replay files stay gitignored).
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.move_ranking_validator import (  # noqa: E402
    SEL_MAIN,
    iter_expert_decisions,
)

DECK_SIZE = 60

# Pre-committed cohort tiers on the target family's ranking-group count (plan
# U25). The count decides how much of the imitation pipeline is affordable; the
# thresholds are fixed here so the tier is read off the census, not chosen after
# seeing it.
TIER_FULL_MIN = 2500  # >= this: full per-archetype learned pilot
TIER_POOL_MIN = 600   # [POOL_MIN, FULL_MIN): winners-only cloning + family pooling
# below POOL_MIN: kill learned-pilot training, ship the hand-coded layer


def winner_seat(replay) -> int | None:
    """Seat index (0 or 1) that won the episode, or None for a draw / malformed.

    The winner is the seat with the strictly greater final reward. Kaggle records
    a decided PTCG game as rewards [1, -1] / [-1, 1]; a tie, a missing reward
    list, or any non-two-seat shape returns None so the episode is dropped from
    the cohort rather than credited to an ambiguous seat. Pure, never raises.
    """
    try:
        rewards = replay.get("rewards")
    except AttributeError:
        return None
    if not isinstance(rewards, (list, tuple)) or len(rewards) != 2:
        return None
    a, b = rewards[0], rewards[1]
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return None
    if isinstance(a, bool) or isinstance(b, bool):
        return None
    if a == b:
        return None
    return 0 if a > b else 1


# The winning seat IS the expert cohort seat: the single resolved definition.
# Kept as a named alias so callers read the intent ("the cohort seat") while the
# mechanism (whoever won) stays in one place.
cohort_seat = winner_seat


def team_names(replay) -> tuple | None:
    """The two seats' team handles as (name0, name1), or None when unavailable.

    Reads info.TeamNames, seat-ordered, exactly as the move-ranking validator
    does. Returns None on any shape other than a two-element list so a caller can
    skip attribution rather than raise. Pure.
    """
    try:
        names = ((replay.get("info") or {}).get("TeamNames")) or []
    except AttributeError:
        return None
    if not isinstance(names, (list, tuple)) or len(names) != 2:
        return None
    return (str(names[0]), str(names[1]))


def seat_decklists(replay) -> tuple | None:
    """The two seats' opening 60-card decklists as (deck0, deck1), or None.

    Both full decklists are recorded once, at the first step, in that seat
    record's `visualize[0].action` (a two-element list of 60 card ids, seat
    ordered). This is the only place the hidden portions of both decks are
    revealed, so it is the census's source of truth for what each seat played.
    Returns None unless both lists are present and 60 cards long, so a truncated
    or malformed opener is skipped rather than mis-classified. Pure, never raises.
    """
    try:
        steps = replay.get("steps") or []
        first = steps[0]
        vis = first[0].get("visualize") or []
        action = vis[0].get("action")
    except (AttributeError, IndexError, TypeError, KeyError):
        return None
    if not isinstance(action, (list, tuple)) or len(action) != 2:
        return None
    d0, d1 = action[0], action[1]
    if not isinstance(d0, (list, tuple)) or not isinstance(d1, (list, tuple)):
        return None
    if len(d0) != DECK_SIZE or len(d1) != DECK_SIZE:
        return None
    return (tuple(d0), tuple(d1))


def classify_family(decklist, signatures, threshold: float = 0.35) -> str:
    """Name the archetype family of a decklist, or "other".

    `signatures` maps a family name to its distinctive (non-basic-energy) card-id
    frozenset; the census tool builds it from analysis/archetype so this stays
    cg-free. A deck is assigned to the family whose signature it best COVERS: the
    fraction of that family's signature cards present in the deck. Requiring a
    coverage fraction (not a raw overlap count) above `threshold` stops a deck
    that merely shares a few staple trainers from being mislabeled as a meta
    pillar; a deck below threshold on every family is "other". Ties break on name
    for determinism. Pure, never raises.
    """
    deck_ids = set(decklist)
    best_name = "other"
    best_cover = 0.0
    for name in sorted(signatures):
        sig = signatures[name]
        if not sig:
            continue
        cover = len(deck_ids & sig) / len(sig)
        if cover > best_cover:
            best_cover = cover
            best_name = name
    return best_name if best_cover >= threshold else "other"


def _count_main_decisions(replay, seat) -> int:
    """Number of ACTIVE MAIN selects made by `seat`, regardless of option count.

    This is the looser denominator to ranking_groups: every top-level MAIN
    decision the seat faced, including the forced single-option ones a ranker
    cannot learn from. Gating mirrors iter_expert_decisions (ACTIVE, this seat,
    SEL_MAIN) so the two counts describe the same decision stream. Pure.
    """
    n = 0
    for step in replay.get("steps") or []:
        if not isinstance(step, (list, tuple)):
            continue
        for entry in step:
            if not isinstance(entry, dict) or entry.get("status") != "ACTIVE":
                continue
            obs = entry.get("observation") or {}
            sel = obs.get("select")
            current = obs.get("current")
            if sel is None or current is None:
                continue
            if current.get("yourIndex", None) != seat:
                continue
            if sel.get("type") == SEL_MAIN:
                n += 1
    return n


def census_episode(replay, signatures, threshold: float = 0.35) -> dict | None:
    """One episode's cohort contribution, or None when it has no expert seat.

    Resolves the cohort (winning) seat, its decklist and family, and counts the
    seat's MAIN decisions and ranking groups (scorable multi-option single-pick
    decisions, via move_ranking_validator.iter_expert_decisions). A draw, a
    missing reward, or an unreadable opener drops the episode (returns None) so a
    batch over thousands of games never credits an ambiguous seat. Pure.
    """
    seat = cohort_seat(replay)
    if seat is None:
        return None
    decks = seat_decklists(replay)
    if decks is None:
        return None
    names = team_names(replay)
    family = classify_family(decks[seat], signatures, threshold)
    ranking_groups = sum(1 for _ in iter_expert_decisions(replay, seat))
    return {
        "seat": seat,
        "team": names[seat] if names is not None else None,
        "family": family,
        "main_decisions": _count_main_decisions(replay, seat),
        "ranking_groups": ranking_groups,
    }


def aggregate(episode_rows) -> dict:
    """Fold census_episode rows into per-family and total counts.

    `episode_rows` is an iterable of census_episode results; None entries (draws /
    malformed) are counted as skipped so the census reports its own coverage. Per
    family it sums episodes, MAIN decisions, and ranking groups; it also tallies
    winning-seat teams (top handles) so the cohort's composition is auditable.
    Pure, never raises.
    """
    by_family = {}
    teams = Counter()
    episodes = 0
    skipped = 0
    for row in episode_rows:
        if row is None:
            skipped += 1
            continue
        episodes += 1
        fam = by_family.setdefault(
            row["family"], {"episodes": 0, "main_decisions": 0, "ranking_groups": 0}
        )
        fam["episodes"] += 1
        fam["main_decisions"] += row["main_decisions"]
        fam["ranking_groups"] += row["ranking_groups"]
        if row.get("team"):
            teams[row["team"]] += 1
    return {
        "episodes": episodes,
        "skipped": skipped,
        "by_family": by_family,
        "teams": dict(teams),
        "ranking_groups": sum(f["ranking_groups"] for f in by_family.values()),
        "main_decisions": sum(f["main_decisions"] for f in by_family.values()),
    }


def tier_for(ranking_groups: int) -> str:
    """The pre-committed training tier for a family's ranking-group count.

    "full" (>= TIER_FULL_MIN): full per-archetype learned pilot is affordable.
    "winners_pooled" ([POOL_MIN, FULL_MIN)): winners-only cloning with family
    pooling. "kill" (< POOL_MIN): too thin, drop learned-pilot training for this
    family and ship the hand-coded layer. Thresholds are fixed in this module so
    the tier is read off the census, never chosen after seeing the number.
    """
    if ranking_groups >= TIER_FULL_MIN:
        return "full"
    if ranking_groups >= TIER_POOL_MIN:
        return "winners_pooled"
    return "kill"
