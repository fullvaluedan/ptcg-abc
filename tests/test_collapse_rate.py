"""Tests for tools/collapse_rate.py.

The engine running part is a per process native singleton, so these tests cover
the pure tally logic: loser_bucket classifies the right seat from a replay, and
measure_deck aggregates the early_collapse count across games through an injected
fake env (no native engine, no network).
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.collapse_rate import loser_bucket, measure_deck  # noqa: E402


def _entry(active, *, turn=3, prizes=(6, 6), decks=(42, 41), benches=(0, 0)):
    """One per seat record. active marks the deciding seat; counts are absolute
    (index 0 is seat 0). An inactive seat carries no live decision."""
    if not active:
        return {"action": [], "status": "INACTIVE",
                "observation": {"select": None, "current": None}}
    players = [
        {"prize": [None] * prizes[0], "deckCount": decks[0], "bench": [{}] * benches[0]},
        {"prize": [None] * prizes[1], "deckCount": decks[1], "bench": [{}] * benches[1]},
    ]
    return {
        "action": [0],
        "status": "ACTIVE",
        "observation": {
            "select": {"option": [0, 1, 2]},
            "current": {"yourIndex": 0, "turn": turn, "players": players,
                        "remainingOverageTime": 600.0},
        },
    }


def _game(rewards, **kw):
    """A two step replay: deck handshake then one seat-0 decision with kw counts."""
    handshake = [_entry(False), _entry(False)]
    decision = [_entry(True, **kw), _entry(False)]
    return {"steps": [handshake, decision], "rewards": rewards}


class _FakeEnv:
    """Replays a prebuilt toJSON; run is a no op (agents are never invoked)."""

    def __init__(self, replay):
        self._replay = replay

    def run(self, order):
        return None

    def toJSON(self):
        return self._replay


def test_loser_bucket_picks_losing_seat_early_collapse():
    # Seat 0 lost a turn-3 game with a full prize bank and an empty bench: the
    # empty-bench early_collapse the consistency decks target.
    replay = _game(rewards=[-1, 1], turn=3, prizes=(6, 6), decks=(42, 41), benches=(0, 2))
    bucket, bench = loser_bucket(replay)
    assert bucket == "early_collapse"
    assert bench == 0


def test_loser_bucket_none_on_draw():
    replay = _game(rewards=[0, 0])
    assert loser_bucket(replay) is None


def test_measure_deck_counts_early_collapse_across_games():
    collapse = _game(rewards=[-1, 1], turn=3, prizes=(6, 6), decks=(42, 41), benches=(0, 2))
    deckout = _game(rewards=[-1, 1], turn=20, prizes=(4, 6), decks=(0, 18), benches=(1, 1))
    draw = _game(rewards=[0, 0])
    games = [collapse, collapse, deckout, draw]
    seq = iter(games)

    def factory():
        return _FakeEnv(next(seq))

    r = measure_deck([1, 2, 3], n_games=len(games), env_factory=factory)
    assert r["games"] == 4
    assert r["decided"] == 3          # the draw has no loser
    assert r["early_collapse"] == 2
    assert r["buckets"]["deckout"] == 1
    assert abs(r["early_collapse_rate"] - 0.5) < 1e-9
