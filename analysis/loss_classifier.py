"""Parse cabt replays and bucket our losses.

A replay is the JSON that kaggle_environments produces (env.toJSON) and that the
Kaggle episode download returns: a top level dict with "steps" (a list of steps,
each step a two element list of per player records) and a final "rewards" pair.
Each per player record holds "observation", "action", and "status".

parse_replay turns a replay into a compact digest: the outcome plus one record
per decision (the player who was asked to act, the turn, how many options they
had, both prize counts, the remaining overage bank, and the time that decision
drew from the bank), and the final board state (both seats' prize and deck
counts). classify_loss buckets a lost game into one of several causes so the
scout can rank what is costing us games. Nothing here touches the network or the
live engine; it reads saved JSON only.

The bucket set was rebuilt against real ladder replays (Phase 4 loss data): the
dominant real failure mode is decking ourselves out (deckCount hits 0 and we
lose, sometimes while ahead on prizes), which the prize-only heuristic used to
hide inside deck_matchup. deckout and early_collapse are now distinct from a true
prize-race blowout.
"""
from __future__ import annotations

# Decision time below this is normal; a single move above it points at search
# spending too long (KTD2 budget pressure).
SLOW_DECISION_S = 10.0
# Finishing a match with less than this much of the 600s bank left means time
# pressure was shaping our play.
LOW_BANK_S = 60.0
# Prizes we still needed at the end. Six start; we win at zero remaining.
# Still needing this many (we took at most one) reads as scoring almost nothing.
STEAMROLL_REMAINING = 5
# Needing at most this many (a near win that slipped) reads as an endgame misplay.
CLOSE_REMAINING = 2
# A loss this early, with no prize race, reads as a setup failure or rule loss
# (could not field a Pokemon, illegal line) rather than anything search did.
EARLY_TURN_LIMIT = 8
# Full prize bank each player starts with.
START_PRIZES = 6
# Cumulative thinking bank per player per match (cabt.json remainingOverageTime).
BANK_S = 600.0

BUCKETS = (
    "slow_search",
    "deckout",
    "deck_matchup",
    "endgame_misplay",
    "early_collapse",
    "bad_determinization",
)


def _default_thresholds() -> dict:
    return {
        "slow_decision_s": SLOW_DECISION_S,
        "low_bank_s": LOW_BANK_S,
        "steamroll_remaining": STEAMROLL_REMAINING,
        "close_remaining": CLOSE_REMAINING,
        "early_turn_limit": EARLY_TURN_LIMIT,
    }


def _counts(current, key: str) -> list:
    """Per player count of a list valued field, or None when not yet dealt."""
    players = current.get("players") if current else None
    if not players:
        return [None, None]
    out = []
    for pl in players:
        val = pl.get(key)
        out.append(len(val) if isinstance(val, list) else None)
    return (out + [None, None])[:2]  # always two seats, even on a malformed players list


def _deck_counts(current) -> list:
    """Per player deck size from the integer deckCount field."""
    players = current.get("players") if current else None
    if not players:
        return [None, None]
    out = []
    for pl in players:
        dc = pl.get("deckCount")
        out.append(dc if isinstance(dc, int) else None)
    return (out + [None, None])[:2]  # always two seats, even on a malformed players list


def parse_replay(replay, our_index: int = 0) -> dict:
    """Turn a replay JSON into a digest of decisions, outcome, and final board.

    our_index selects which seat is us (0 or 1). Records cover every real
    decision (select is not None) by either player; decision_time is the drop in
    that player's overage bank since their previous decision. final_prize and
    final_deck track the last observed count for each absolute seat, read from
    whichever seat was active, so the end of game board is recovered even though
    only the acting seat's observation is recorded each step.
    """
    steps = replay.get("steps") or []
    rewards = replay.get("rewards")
    if not rewards and steps:
        last = steps[-1]
        rewards = [last[0].get("reward"), last[1].get("reward")]
    rewards = rewards or [None, None]

    decisions = []
    last_overage = {}  # player index -> overage at their previous decision
    final_prize = [None, None]
    final_deck = [None, None]
    max_turn = 0
    for t, step in enumerate(steps):
        for p, entry in enumerate(step):
            # Only the ACTIVE seat is deciding. An inactive seat can carry a
            # stale non null select from its last turn, so gate on status too.
            if entry.get("status") != "ACTIVE":
                continue
            obs = entry.get("observation") or {}
            sel = obs.get("select")
            current = obs.get("current")
            if sel is None or current is None:
                continue  # deck handshake (both active, select None)
            player = current.get("yourIndex", p)
            overage = obs.get("remainingOverageTime", BANK_S)
            prev = last_overage.get(player, overage)
            last_overage[player] = overage
            prizes = _counts(current, "prize")
            decks = _deck_counts(current)
            for seat in (0, 1):
                if prizes[seat] is not None:
                    final_prize[seat] = prizes[seat]
                if decks[seat] is not None:
                    final_deck[seat] = decks[seat]
            turn = current.get("turn", 0) or 0
            max_turn = max(max_turn, turn)
            decisions.append(
                {
                    "step": t,
                    "player": player,
                    "turn": turn,
                    "n_options": len(sel.get("option") or []),
                    "my_prize": prizes[player],
                    "opp_prize": prizes[1 - player],
                    "overage": overage,
                    "decision_time": max(0.0, prev - overage),
                    "action": entry.get("action"),
                }
            )

    our_reward = rewards[our_index] if rewards[our_index] is not None else None
    opp_reward = rewards[1 - our_index] if rewards[1 - our_index] is not None else None
    if our_reward is None or opp_reward is None:
        outcome = "unknown"
    elif our_reward > opp_reward:
        outcome = "win"
    elif our_reward < opp_reward:
        outcome = "loss"
    else:
        outcome = "draw"

    return {
        "our_index": our_index,
        "rewards": list(rewards),
        "outcome": outcome,
        "decisions": decisions,
        "our_decisions": [d for d in decisions if d["player"] == our_index],
        "n_decisions": len(decisions),
        "n_turns": max_turn,
        "my_prize_end": final_prize[our_index],
        "opp_prize_end": final_prize[1 - our_index],
        "my_deck_end": final_deck[our_index],
        "opp_deck_end": final_deck[1 - our_index],
    }


def classify_loss(digest: dict, thresholds: dict | None = None):
    """Return the loss bucket for a lost game, or None if it was not a loss.

    Order matters and runs most decisive first:
      1. slow_search   a timing failure is board independent and overrides all.
      2. deckout       our deck hit zero; we ran ourselves out of cards. The
                       single biggest real ladder leak, true even when we led on
                       prizes, so it ranks above any prize based reading.
      3. deck_matchup  a genuine prize race blowout: the opponent took almost
                       every prize while we took at most one.
      4. endgame_misplay  a near win that slipped (we needed one or two prizes).
      5. early_collapse   the game ended very early with no prize race, pointing
                          at a setup failure or rule loss, not search.
      6. bad_determinization  a middling loss where search judgement is suspect.
    """
    if digest.get("outcome") != "loss":
        return None
    th = {**_default_thresholds(), **(thresholds or {})}
    ours = digest.get("our_decisions") or []

    times = [d["decision_time"] for d in ours if d.get("decision_time") is not None]
    final_overage = ours[-1]["overage"] if ours and ours[-1].get("overage") is not None else BANK_S
    if (times and max(times) >= th["slow_decision_s"]) or final_overage < th["low_bank_s"]:
        return "slow_search"

    if digest.get("my_deck_end") == 0:
        return "deckout"

    my_remaining = _final_my_remaining(digest, ours)
    opp_remaining = _final_opp_remaining(digest, ours)
    if my_remaining is None:
        return "bad_determinization"

    took_at_most_one = my_remaining >= th["steamroll_remaining"]
    opp_took_almost_all = (
        opp_remaining is not None
        and opp_remaining <= START_PRIZES - th["steamroll_remaining"]
    )
    if took_at_most_one and opp_took_almost_all:
        return "deck_matchup"
    if my_remaining <= th["close_remaining"]:
        return "endgame_misplay"
    if took_at_most_one and digest.get("n_turns", 0) <= th["early_turn_limit"]:
        return "early_collapse"
    return "bad_determinization"


def _final_my_remaining(digest, ours):
    if digest.get("my_prize_end") is not None:
        return digest["my_prize_end"]
    for d in reversed(ours):
        if d.get("my_prize") is not None:
            return d["my_prize"]
    return None


def _final_opp_remaining(digest, ours):
    if digest.get("opp_prize_end") is not None:
        return digest["opp_prize_end"]
    for d in reversed(ours):
        if d.get("opp_prize") is not None:
            return d["opp_prize"]
    return None


def classify_batch(digests, thresholds: dict | None = None) -> dict:
    """Aggregate digests into a ranked loss bucket report.

    Counts wins, draws, and losses; buckets each loss; ranks the buckets by
    frequency so the biggest leak surfaces first.
    """
    digests = list(digests)
    wins = draws = losses = 0
    counts = {b: 0 for b in BUCKETS}
    for dg in digests:
        outcome = dg.get("outcome")
        if outcome == "win":
            wins += 1
        elif outcome == "draw":
            draws += 1
        elif outcome == "loss":
            losses += 1
            bucket = classify_loss(dg, thresholds)
            if bucket:
                counts[bucket] = counts.get(bucket, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    top = ranked[0][0] if ranked and ranked[0][1] > 0 else None
    return {
        "games": len(digests),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "buckets": counts,
        "ranked": ranked,
        "top_bucket": top,
    }
