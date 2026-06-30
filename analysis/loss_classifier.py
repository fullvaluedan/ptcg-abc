"""Parse cabt replays and bucket our losses.

A replay is the JSON that kaggle_environments produces (env.toJSON) and that the
Kaggle episode download returns: a top level dict with "steps" (a list of steps,
each step a two element list of per player records) and a final "rewards" pair.
Each per player record holds "observation", "action", and "status".

parse_replay turns a replay into a compact digest: the outcome plus one record
per decision (the player who was asked to act, the turn, how many options they
had, both prize counts, the remaining overage bank, and the time that decision
drew from the bank). classify_loss buckets a lost game into one of four causes so
the scout can rank what is costing us games. Nothing here touches the network or
the live engine; it reads saved JSON only.
"""
from __future__ import annotations

# Decision time below this is normal; a single move above it points at search
# spending too long (KTD2 budget pressure).
SLOW_DECISION_S = 10.0
# Finishing a match with less than this much of the 600s bank left means time
# pressure was shaping our play.
LOW_BANK_S = 60.0
# Prizes we still needed at the end. Six start; we win at zero remaining.
# Still needing this many (we took at most one) reads as a blowout / bad matchup.
STEAMROLL_REMAINING = 5
# Needing at most this many (a near win that slipped) reads as an endgame misplay.
CLOSE_REMAINING = 2
# Full prize bank each player starts with.
START_PRIZES = 6
# Cumulative thinking bank per player per match (cabt.json remainingOverageTime).
BANK_S = 600.0

BUCKETS = ("slow_search", "deck_matchup", "endgame_misplay", "bad_determinization")


def _default_thresholds() -> dict:
    return {
        "slow_decision_s": SLOW_DECISION_S,
        "low_bank_s": LOW_BANK_S,
        "steamroll_remaining": STEAMROLL_REMAINING,
        "close_remaining": CLOSE_REMAINING,
    }


def _prize_counts(current) -> list:
    """Remaining prize count for each player, or None when not yet dealt."""
    players = current.get("players") if current else None
    if not players:
        return [None, None]
    out = []
    for pl in players:
        prize = pl.get("prize")
        out.append(len(prize) if isinstance(prize, list) else None)
    return out


def parse_replay(replay, our_index: int = 0) -> dict:
    """Turn a replay JSON into a digest of decisions and the outcome.

    our_index selects which seat is us (0 or 1). Records cover every real
    decision (select is not None) by either player; decision_time is the drop in
    that player's overage bank since their previous decision.
    """
    steps = replay.get("steps") or []
    rewards = replay.get("rewards")
    if not rewards and steps:
        last = steps[-1]
        rewards = [last[0].get("reward"), last[1].get("reward")]
    rewards = rewards or [None, None]

    decisions = []
    last_overage = {}  # player index -> overage at their previous decision
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
            prizes = _prize_counts(current)
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
    }


def classify_loss(digest: dict, thresholds: dict | None = None):
    """Return the loss bucket for a lost game, or None if it was not a loss.

    Order matters: a timing failure is decisive and independent of the board, so
    it is checked first. Otherwise the final prize gap separates a blowout (bad
    matchup) from a near win that slipped (endgame misplay); the remainder is a
    middling loss where search judgement (its determinizations) is the suspect.
    """
    if digest.get("outcome") != "loss":
        return None
    th = {**_default_thresholds(), **(thresholds or {})}
    ours = digest.get("our_decisions") or []

    times = [d["decision_time"] for d in ours if d.get("decision_time") is not None]
    final_overage = ours[-1]["overage"] if ours and ours[-1].get("overage") is not None else BANK_S
    if (times and max(times) >= th["slow_decision_s"]) or final_overage < th["low_bank_s"]:
        return "slow_search"

    my_remaining = None
    for d in reversed(ours):
        if d.get("my_prize") is not None:
            my_remaining = d["my_prize"]
            break
    if my_remaining is None:
        return "bad_determinization"
    if my_remaining >= th["steamroll_remaining"]:
        return "deck_matchup"
    if my_remaining <= th["close_remaining"]:
        return "endgame_misplay"
    return "bad_determinization"


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
