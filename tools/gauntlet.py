"""Gauntlet eval harness: score an agent against a pool of opponents.

Runs matches sequentially. The native engine is a per process singleton, so
concurrent matches in one process are unsafe; parallel workers each running a
sequential batch are a future optimization for large run sizes. Reports win rate
with a Wilson confidence interval, average and max decision time, and invalid
move rate (our agent should never produce an illegal move).

Optional state-outcome logging (plan U1, --log-states or PTCG_LOG_STATES=1)
records one training row per non-terminal decision state per seat, for BOTH
agents in every match, labelled with that seat's game outcome. This is the
data source for the learned evaluator (plan U4); logging is opt-in and off by
default so a normal gauntlet run pays no extra cost.

Optional move-ordering data capture (plan U8a, --log-moves or PTCG_LOG_MOVES=1)
records one row per candidate MAIN option per decision, for the eventual
winner's seat only, using agents.imitation_features.decision_features. This is
the data source for the move-ordering model (plan U8b); also opt-in and
independent of --log-states.
"""
import argparse
import csv
import math
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agents import heuristics as H  # noqa: E402
from agents import imitation_features  # noqa: E402
from ptcg_agent import observation as obs_mod  # noqa: E402
from ptcg_agent.engine import run_match  # noqa: E402
from ptcg_agent.features import FEATURE_NAMES, extract_features  # noqa: E402
from tools import opponents  # noqa: E402

DEFAULT_LOG_DIR = _ROOT / "data" / "training"


def _is_legal(move, obs) -> bool:
    sel = obs["select"]
    if sel is None:
        return isinstance(move, list) and len(move) == 60
    n = len(sel["option"])
    if not isinstance(move, list) or len(set(move)) != len(move):
        return False
    if not (sel["minCount"] <= len(move) <= sel["maxCount"]):
        return False
    return all(0 <= i < n for i in move)


def _instrument(fn, record):
    def wrapped(obs):
        t0 = time.perf_counter()
        move = fn(obs)
        record["times"].append(time.perf_counter() - t0)
        if not _is_legal(move, obs):
            record["invalid"] += 1
        return move

    return wrapped


class _StateLogger:
    """Buffers one feature row per decision state per seat, labels at game end.

    Row: game_id, seat, turn, <FEATURE_NAMES columns>, label. Rows for a game
    are held in memory only until that game's result is known (never the whole
    run), then written and flushed, so a multi-thousand-game run stays cheap.
    Draws are dropped since the plan's label is win/loss only.

    move_path, if given, additionally buffers one row per candidate MAIN option
    per decision (plan U8a's move-ordering data capture), keeping only decisions
    belonging to the eventual winner's seat at flush time (mirrors the winner-seat
    bookkeeping the label column above already needs). Row: game_id, seat,
    decision_id, n_options, option_index, is_chosen, <imitation FEATURE_NAMES>,
    source. A single-option decision carries no ranking signal (decision_features
    returns None for it), so only genuine choices are logged.
    """

    def __init__(self, path=None, move_path=None):
        self.path = Path(path) if path else None
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(self.path, "w", newline="")
            self._writer = csv.writer(self._fh)
            self._writer.writerow(["game_id", "seat", "turn", *FEATURE_NAMES, "label"])
            self._fh.flush()
        else:
            self._fh = None
            self._writer = None

        self.move_path = Path(move_path) if move_path else None
        if self.move_path is not None:
            self.move_path.parent.mkdir(parents=True, exist_ok=True)
            self._move_fh = open(self.move_path, "w", newline="")
            self._move_writer = csv.writer(self._move_fh)
            self._move_writer.writerow(
                ["game_id", "seat", "decision_id", "n_options", "option_index", "is_chosen",
                 *imitation_features.FEATURE_NAMES, "source"]
            )
            self._move_fh.flush()
        else:
            self._move_fh = None
            self._move_writer = None

    def wrap(self, agent_fn, game_id, rows, move_rows=None, decision_counter=None):
        def wrapped(obs):
            move = agent_fn(obs)
            if not obs_mod.is_deck_selection(obs):
                state = obs_mod.state(obs)
                seat = obs_mod.your_index(obs)
                if self._writer is not None and state is not None and isinstance(seat, int):
                    feats = extract_features(state, seat)
                    rows.append([game_id, seat, state.get("turn", 0), *feats])
                if (self._move_writer is not None and move_rows is not None
                        and isinstance(seat, int)):
                    sel = obs_mod.select(obs)
                    if sel is not None and sel.get("type") == H.SEL_MAIN:
                        feat_rows = imitation_features.decision_features(obs)
                        if feat_rows is not None:
                            n_options = len(feat_rows)
                            chosen = (move[0] if isinstance(move, list) and len(move) == 1
                                      and 0 <= move[0] < n_options else None)
                            decision_id = decision_counter[0]
                            decision_counter[0] += 1
                            for idx, frow in enumerate(feat_rows):
                                move_rows.append(
                                    [game_id, seat, decision_id, n_options, idx,
                                     1 if idx == chosen else 0, *frow]
                                )
            return move

        return wrapped

    def flush_game(self, rows, r0, r1, move_rows=None):
        if self._writer is not None:
            for row in rows:
                seat = row[1]
                mine, theirs = (r0, r1) if seat == 0 else (r1, r0)
                if mine == theirs:
                    continue
                self._writer.writerow([*row, 1 if mine > theirs else 0])
            self._fh.flush()
        if self._move_writer is not None and move_rows and r0 != r1:
            winner_seat = 0 if r0 > r1 else 1
            for row in move_rows:
                if row[1] == winner_seat:
                    self._move_writer.writerow([*row, "gauntlet"])
            self._move_fh.flush()

    def close(self):
        if self._fh is not None:
            self._fh.close()
        if self._move_fh is not None:
            self._move_fh.close()


def _absolute_rewards(res):
    """(reward for seat 0, reward for seat 1), undoing run_match's swap remap."""
    return (res["reward_a"], res["reward_b"]) if res["a_seat"] == 0 else (res["reward_b"], res["reward_a"])


def _wilson(wins, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def run_gauntlet(agent_name, opponent_names, n_matches, log_states=False, log_path=None,
                  log_moves=False, move_log_path=None):
    """Play n_matches split across the opponents, alternating first player.

    log_states=True (or PTCG_LOG_STATES=1 at the CLI) additionally logs one
    feature row per decision state per seat, for both agents, to log_path
    (default data/training/states_<timestamp>.csv, plan U1).

    log_moves=True (or PTCG_LOG_MOVES=1 at the CLI) additionally logs one row per
    candidate MAIN option per decision, for the eventual winner's seat only, to
    move_log_path (default data/training/move_rows_<timestamp>.csv, plan U8a).
    Independent of log_states: either, both, or neither may be enabled.
    """
    agent_fn = opponents.get(agent_name)
    rewards, times, invalid = [], [], 0
    logger = None
    if log_states or log_moves:
        logger = _StateLogger(
            (log_path or DEFAULT_LOG_DIR / f"states_{int(time.time())}.csv") if log_states else None,
            move_path=(move_log_path or DEFAULT_LOG_DIR / f"move_rows_{int(time.time())}.csv")
            if log_moves else None,
        )
    try:
        for i in range(n_matches):
            opp_fn = opponents.get(opponent_names[i % len(opponent_names)])
            rec = {"times": [], "invalid": 0}
            wrapped_a = _instrument(agent_fn, rec)
            wrapped_b = opp_fn
            rows, move_rows, decision_counter = [], [], [0]
            if logger is not None:
                wrapped_a = logger.wrap(wrapped_a, i, rows, move_rows, decision_counter)
                wrapped_b = logger.wrap(wrapped_b, i, rows, move_rows, decision_counter)
            res = run_match(wrapped_a, wrapped_b, swap_first=(i % 2 == 1))
            if logger is not None:
                logger.flush_game(rows, *_absolute_rewards(res), move_rows=move_rows)
            rewards.append(res["reward_a"])
            times.extend(rec["times"])
            invalid += rec["invalid"]
    finally:
        if logger is not None:
            logger.close()
    n = len(rewards)
    wins = sum(1 for r in rewards if r == 1)
    draws = sum(1 for r in rewards if r == 0)
    losses = sum(1 for r in rewards if r == -1)
    lo, hi = _wilson(wins, n)
    stats = {
        "agent": agent_name,
        "opponents": opponent_names,
        "matches": n,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": wins / n if n else 0.0,
        "win_rate_ci95": (round(lo, 3), round(hi, 3)),
        "avg_decision_ms": round(1000 * sum(times) / len(times), 3) if times else 0.0,
        "max_decision_ms": round(1000 * max(times), 3) if times else 0.0,
        "decisions": len(times),
        "invalid_moves": invalid,
        "invalid_rate": round(invalid / len(times), 6) if times else 0.0,
    }
    if logger is not None:
        if logger.path is not None:
            stats["log_path"] = str(logger.path)
        if logger.move_path is not None:
            stats["move_log_path"] = str(logger.move_path)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent", help="agent under test (e.g. baseline)")
    ap.add_argument("opponents", nargs="+", help="opponent names (e.g. random first)")
    ap.add_argument("-n", "--matches", type=int, default=100)
    ap.add_argument("--log-states", action="store_true",
                     help="log one feature row per decision state per seat to "
                          "data/training/ (also enabled by PTCG_LOG_STATES=1)")
    ap.add_argument("--log-moves", action="store_true",
                     help="log one row per candidate MAIN option per decision (winner's "
                          "seat only) to data/training/ (also enabled by PTCG_LOG_MOVES=1)")
    args = ap.parse_args()
    log_states = args.log_states or os.environ.get("PTCG_LOG_STATES") == "1"
    log_moves = args.log_moves or os.environ.get("PTCG_LOG_MOVES") == "1"
    s = run_gauntlet(args.agent, args.opponents, args.matches,
                      log_states=log_states, log_moves=log_moves)
    ci = s["win_rate_ci95"]
    print(f"{s['agent']} vs {s['opponents']} over {s['matches']} matches")
    print(f"  win rate: {s['win_rate']:.1%}  (95% CI {ci[0]:.1%} to {ci[1]:.1%})")
    print(f"  W/D/L: {s['wins']}/{s['draws']}/{s['losses']}")
    print(f"  decision time: avg {s['avg_decision_ms']} ms, max {s['max_decision_ms']} ms over {s['decisions']} decisions")
    print(f"  invalid moves: {s['invalid_moves']} ({s['invalid_rate']:.4%})")
    if log_states:
        print(f"  logged states to: {s['log_path']}")
    if log_moves:
        print(f"  logged move rows to: {s['move_log_path']}")


if __name__ == "__main__":
    main()
