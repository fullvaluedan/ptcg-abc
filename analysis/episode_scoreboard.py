"""Per-episode scoreboard for scored ladder builds (plan U23).

The ladder public score is one noisy number per submission; it hides how a build
does game by game and against which opponents. This module turns a build's saved
episode replays into three settlement-grade statistics that the single score
cannot give:

  1. Raw win rate + early stop. Wins over all recorded episodes, and an
     evict verdict when a candidate sits under a floor (default 35%) after enough
     episodes (default 15). This kills a clearly losing experiment before its
     ladder number settles, freeing the slot sooner (the binding resource).

  2. Shared-bracket settlement. Two builds rarely face the same opponents, so
     comparing raw win rates is confounded by opponent strength. We bracket each
     episode by the opponent's revealed archetype (the only opponent identity
     recoverable offline from a replay; the download carries no rating), keep the
     brackets both builds actually faced, pool each build's wins and losses over
     those shared brackets, and run a one-sided two-proportion z-test. This is the
     BAND tiebreak the protocol calls for: settle WIN only if the scoreboard
     favors the candidate at the target confidence (default ~90%) on shared
     brackets, else NEUTRAL and revert.

  3. Same-build noise. Running two byte-identical copies through the scoreboard on
     their shared brackets returns the win-rate spread for free: a direct read on
     how much of any A/B gap is just noise, feeding the U22 noise model.

The pure core takes plain rows ({"bracket": ..., "outcome": ...}) and outcome
lists, so it is unit-tested with no engine, card data, or dataset. The live
wrappers reuse tools.scout (outcome + our-seat) and analysis.opponent_archetype
(the opponent bracket), which are the same helpers the loss scout already trusts.
Nothing here touches the network or the live engine; it reads saved JSON only.
"""
from __future__ import annotations

import math

# A candidate under this raw win rate after EARLY_STOP_MIN_EPISODES episodes is
# evicted without waiting for its ladder number to settle: it is already a clear
# loser and is only holding a slot. Matches the loop brief's early-evict rule.
EARLY_STOP_FLOOR = 0.35
EARLY_STOP_MIN_EPISODES = 15
# Confidence the shared-bracket settlement must clear to call a BAND result for
# the candidate (or, symmetrically, for the king). ~90% binomial confidence per
# the A/B protocol.
DEFAULT_CONFIDENCE = 0.90


def _norm_cdf(z: float) -> float:
    """Standard normal CDF via the error function (no scipy dependency)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def win_loss_draw(outcomes) -> tuple:
    """Count (wins, losses, draws) over an iterable of outcome strings."""
    w = l = d = 0
    for o in outcomes:
        if o == "win":
            w += 1
        elif o == "loss":
            l += 1
        elif o == "draw":
            d += 1
    return w, l, d


def raw_win_rate(outcomes):
    """Wins over ALL games (draws count as non-wins); None when there are none.

    Deliberately over every recorded episode, not just decisive ones: the early
    stop asks whether a build is winning enough games, period, and a build that
    draws its way to nowhere should not read as a coin flip.
    """
    outcomes = list(outcomes)
    n = len(outcomes)
    if n == 0:
        return None
    w, _l, _d = win_loss_draw(outcomes)
    return w / n


def early_stop(outcomes, min_episodes: int = EARLY_STOP_MIN_EPISODES,
               floor: float = EARLY_STOP_FLOOR) -> dict:
    """Evict verdict for a candidate: True once it is a clear loser.

    Fires only after min_episodes so a cold streak of a few games never evicts a
    real build. Returns the sample size and rate alongside the verdict so the
    ledger records why.
    """
    outcomes = list(outcomes)
    n = len(outcomes)
    wr = raw_win_rate(outcomes)
    evict = n >= min_episodes and wr is not None and wr < floor
    return {
        "n": n,
        "win_rate": wr,
        "evict": evict,
        "min_episodes": min_episodes,
        "floor": floor,
    }


def bracket_records(rows) -> dict:
    """Tally {bracket: {win, loss, draw}} from rows of {"bracket", "outcome"}.

    A row whose outcome is not win/loss/draw (e.g. "unknown") still creates the
    bracket but adds no count, so a bracket both builds merely saw with unknown
    outcomes contributes nothing to a comparison rather than being invisible.
    """
    per: dict = {}
    for r in rows:
        b = r.get("bracket")
        o = r.get("outcome")
        rec = per.setdefault(b, {"win": 0, "loss": 0, "draw": 0})
        if o in rec:
            rec[o] += 1
    return per


def _decisive(rec: dict) -> int:
    return rec.get("win", 0) + rec.get("loss", 0)


def shared_brackets(rows_a, rows_b) -> set:
    """Brackets that appear in BOTH row sets (the only fair comparison ground)."""
    return set(bracket_records(rows_a)) & set(bracket_records(rows_b))


def _pool_on_brackets(rows, brackets) -> tuple:
    """Pool (wins, losses) over just the named brackets."""
    recs = bracket_records(rows)
    w = sum(recs[b]["win"] for b in brackets if b in recs)
    l = sum(recs[b]["loss"] for b in brackets if b in recs)
    return w, l


def two_proportion_confidence(w1: int, n1: int, w2: int, n2: int):
    """One-sided confidence that rate 1 exceeds rate 2 (pooled z-test).

    Returns a probability in [0, 1], or None when either sample is empty. A
    degenerate zero standard error (both extreme and equal, or identical rates)
    returns 0.5 when the rates tie and a hard 1.0/0.0 when one strictly dominates
    with no observed variance, which is the honest reading of that data.
    """
    if n1 == 0 or n2 == 0:
        return None
    p1 = w1 / n1
    p2 = w2 / n2
    p = (w1 + w2) / (n1 + n2)
    se = math.sqrt(p * (1.0 - p) * (1.0 / n1 + 1.0 / n2))
    if se == 0.0:
        if p1 == p2:
            return 0.5
        return 1.0 if p1 > p2 else 0.0
    z = (p1 - p2) / se
    return _norm_cdf(z)


def settlement(rows_cand, rows_king, confidence: float = DEFAULT_CONFIDENCE) -> dict:
    """BAND tiebreak: does the candidate beat the king on shared brackets?

    Pools each build's wins and losses over the brackets both faced and runs a
    one-sided two-proportion test. verdict is "candidate" when confidence clears
    the bar, "king" when it clears the bar the other way (confidence <=
    1 - target, i.e. the king is favored at the same strength), else "neutral".
    """
    shared = shared_brackets(rows_cand, rows_king)
    wc, lc = _pool_on_brackets(rows_cand, shared)
    wk, lk = _pool_on_brackets(rows_king, shared)
    nc = wc + lc
    nk = wk + lk
    conf = two_proportion_confidence(wc, nc, wk, nk)
    cand_rate = wc / nc if nc else None
    king_rate = wk / nk if nk else None
    if conf is None:
        verdict = "neutral"
    elif conf >= confidence:
        verdict = "candidate"
    elif conf <= 1.0 - confidence:
        verdict = "king"
    else:
        verdict = "neutral"
    return {
        "shared_brackets": sorted(shared, key=lambda b: (b is None, b)),
        "cand_wins": wc,
        "cand_decisive": nc,
        "cand_rate": cand_rate,
        "king_wins": wk,
        "king_decisive": nk,
        "king_rate": king_rate,
        "confidence": conf,
        "favors_candidate": verdict == "candidate",
        "verdict": verdict,
    }


def same_build_spread(rows_a, rows_b) -> dict:
    """Free noise read: win-rate spread of two runs on their shared brackets."""
    shared = shared_brackets(rows_a, rows_b)
    wa, la = _pool_on_brackets(rows_a, shared)
    wb, lb = _pool_on_brackets(rows_b, shared)
    ra = wa / (wa + la) if (wa + la) else None
    rb = wb / (wb + lb) if (wb + lb) else None
    delta = abs(ra - rb) if (ra is not None and rb is not None) else None
    return {
        "shared_brackets": sorted(shared, key=lambda b: (b is None, b)),
        "rate_a": ra,
        "rate_b": rb,
        "delta": delta,
    }


# ----------------------------------------------------------------------------
# Live wrappers (read saved replay dirs). Kept below the pure core so tests cover
# the statistics without any engine, card data, or dataset.
# ----------------------------------------------------------------------------

def outcomes_from_dir(replay_dir, team=None, skip_self_play: bool = False) -> list:
    """Every episode's outcome in a replay dir (for raw win rate / early stop).

    Includes self-play validation episodes by default: raw win rate and the
    episode count are over ALL games a build was scored on. Uses only
    parse_replay and the seat helper, so no card database is loaded.
    """
    import json
    from pathlib import Path

    from analysis.loss_classifier import parse_replay
    from tools.scout import OUR_TEAM, is_self_play, our_index_from_replay

    team = team or OUR_TEAM
    outcomes = []
    for path in sorted(Path(replay_dir).glob("*.json")):
        try:
            replay = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if skip_self_play and is_self_play(replay):
            continue
        seat = our_index_from_replay(replay, team)
        our_index = seat if seat is not None else 0
        digest = parse_replay(replay, our_index=our_index)
        outcomes.append(digest.get("outcome"))
    return outcomes


def rows_from_dir(replay_dir, team=None) -> list:
    """Bracketed rows (opponent archetype + outcome) over real-opponent episodes.

    Delegates to opponent_archetype.scan_dir, which skips self-play and wires in
    the real card index; use this for the shared-bracket settlement, and
    outcomes_from_dir for the raw win rate.
    """
    from analysis.opponent_archetype import scan_dir

    tally = scan_dir(replay_dir, team=team)
    return [
        {"bracket": r["archetype"], "outcome": r["outcome"]}
        for r in tally.get("rows", [])
    ]


def scoreboard_dir(replay_dir, team=None) -> dict:
    """Full scoreboard for one build's replay dir: record, rate, early stop, brackets."""
    outcomes = outcomes_from_dir(replay_dir, team=team)
    rows = rows_from_dir(replay_dir, team=team)
    w, l, d = win_loss_draw(outcomes)
    return {
        "games": len(outcomes),
        "record": {"wins": w, "losses": l, "draws": d},
        "raw_win_rate": raw_win_rate(outcomes),
        "early_stop": early_stop(outcomes),
        "brackets": bracket_records(rows),
    }


def _main(argv=None) -> int:
    """CLI: python -m analysis.episode_scoreboard <replay_dir> [<king_dir>].

    One dir prints that build's scoreboard. Two dirs also runs the shared-bracket
    settlement of the first (candidate) against the second (king). Used to
    retrodict the recorded W/L of the known builds from their saved replays.
    """
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Per-episode scoreboard for a build")
    ap.add_argument("candidate_dir")
    ap.add_argument("king_dir", nargs="?")
    ap.add_argument("--team", default=None)
    args = ap.parse_args(argv)

    out = {"candidate": scoreboard_dir(args.candidate_dir, team=args.team)}
    if args.king_dir:
        cand_rows = rows_from_dir(args.candidate_dir, team=args.team)
        king_rows = rows_from_dir(args.king_dir, team=args.team)
        out["king"] = scoreboard_dir(args.king_dir, team=args.team)
        out["settlement"] = settlement(cand_rows, king_rows)
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
