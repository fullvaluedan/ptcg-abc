"""Type-matchup delta (plan U82, LOOP_BRIEF L6, the shared follow-on RETREAT,
PROMOTE, and the deck-search miner all independently named).

Three separate category gaps (analysis/retreat_gap_conditional.md,
analysis/promote_gap_conditional.md, analysis/search_gap_conditional.md) each
measured a majority of real expert picks that no HP, energy, or reveal-order
signal explains, and each named the same missing input: type effectiveness
(weakness/resistance) between a candidate Pokemon and the opponent's current
active. `agents/heuristics.py` already has this logic once, in
`effective_damage`, but only for a specific attack against a specific
defender. This module lifts the same weakness/resistance rule to a
attack-independent, symmetric per-Pokemon comparison, so a bench candidate can
be scored against the opponent's active even when no attack has been chosen
yet (e.g. a promote or a retreat-target decision, where the new active has not
attacked).

Pure: reads `agents.heuristics.card_index()` (already lru_cached) and nothing
else, never raises, and returns 0 (neutral) whenever either card is unknown so
a missing id degrades to "no signal" rather than a crash.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def matchup_score(mine_id, opponent_id) -> int:
    """Type-matchup delta of `mine_id` against `opponent_id`, in [-2, 2].

    Applies the same two weakness/resistance rules `effective_damage` checks
    for one specific attack, but symmetrically for both sides' printed types:

      +1  opponent's weakness matches mine's type   (I hit them for bonus)
      -1  opponent's resistance matches mine's type (they blunt my hits)
      -1  mine's weakness matches opponent's type   (they hit me for bonus)
      +1  mine's resistance matches opponent's type (I blunt their hits)

    0 when either id is unknown, or when neither side's weakness/resistance
    interacts with the other's type at all. Positive favors `mine_id`.
    """
    from agents.heuristics import card_index

    cards = card_index()
    mine = cards.get(mine_id)
    opp = cards.get(opponent_id)
    if mine is None or opp is None:
        return 0
    score = 0
    if opp.weakness is not None and opp.weakness == mine.energyType:
        score += 1
    if opp.resistance is not None and opp.resistance == mine.energyType:
        score -= 1
    if mine.weakness is not None and mine.weakness == opp.energyType:
        score -= 1
    if mine.resistance is not None and mine.resistance == opp.energyType:
        score += 1
    return score


def best_matchup_index(candidate_ids, opponent_id):
    """Index into `candidate_ids` with the highest `matchup_score` vs
    `opponent_id`, or None when `candidate_ids` is empty. Ties keep the first
    (lowest-index) candidate, mirroring `_first_legal`'s own tie behavior so a
    caller can compare "best matchup" against "first legal" fairly.
    """
    best_idx = None
    best_score = None
    for i, cid in enumerate(candidate_ids):
        score = matchup_score(cid, opponent_id)
        if best_score is None or score > best_score:
            best_idx = i
            best_score = score
    return best_idx
