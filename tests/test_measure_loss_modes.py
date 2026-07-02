"""Tests for tools/measure_loss_modes.py (plan U6's before/after loss-mode gate).

Mirrors tests/test_collapse_rate.py's pattern: a fake env replays a prebuilt
toJSON so these tests cover the tally logic (which seat is ours, bucket
counting, before/after diffing) without the native engine or a real agent.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.measure_loss_modes import compare_before_after, measure_agent  # noqa: E402


def _entry(active, *, turn=3, prizes=(6, 6), decks=(42, 41), benches=(0, 0)):
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
    handshake = [_entry(False), _entry(False)]
    decision = [_entry(True, **kw), _entry(False)]
    return {"steps": [handshake, decision], "rewards": rewards}


class _FakeEnv:
    """Replays a prebuilt toJSON; run is a no-op (agents are never invoked)."""

    def __init__(self, replay):
        self._replay = replay

    def run(self, order):
        return None

    def toJSON(self):
        return self._replay


def _fake_opponents(monkeypatch, replays):
    """Route tools.opponents.get to dummy callables and env_factory to a queue."""
    import tools.measure_loss_modes as mlm

    monkeypatch.setattr(mlm.opponents, "get", lambda name: (lambda obs: [0]))
    seq = iter(replays)
    return lambda: _FakeEnv(next(seq))


def test_measure_agent_counts_buckets_across_games(monkeypatch):
    # measure_agent alternates first player (like tools/gauntlet.py), so odd
    # indices swap which absolute seat is "ours"; build each game's counts
    # from OUR seat's point of view so the intended outcome lands regardless
    # of index parity.
    def _our_loss(bucket_kwargs, our_seat):
        theirs = 1 - our_seat
        prizes = [0, 0]
        prizes[our_seat], prizes[theirs] = bucket_kwargs["prizes"]
        decks = [0, 0]
        decks[our_seat], decks[theirs] = bucket_kwargs["decks"]
        benches = [0, 0]
        benches[our_seat], benches[theirs] = bucket_kwargs["benches"]
        rewards = [0, 0]
        rewards[our_seat], rewards[theirs] = -1, 1
        return _game(rewards, turn=bucket_kwargs["turn"], prizes=tuple(prizes),
                     decks=tuple(decks), benches=tuple(benches))

    def _our_win(our_seat):
        rewards = [0, 0]
        rewards[our_seat], rewards[1 - our_seat] = 1, -1
        return _game(rewards, turn=10, prizes=(0, 3), decks=(30, 30), benches=(2, 2))

    collapse_kwargs = {"turn": 3, "prizes": (6, 6), "decks": (42, 41), "benches": (0, 2)}
    deckout_kwargs = {"turn": 20, "prizes": (4, 6), "decks": (0, 18), "benches": (1, 1)}
    # index 0: our seat 0 (not swapped). index 1: our seat 1 (swapped). etc.
    replays = [
        _our_loss(collapse_kwargs, our_seat=0),
        _our_loss(collapse_kwargs, our_seat=1),
        _our_loss(deckout_kwargs, our_seat=0),
        _our_win(our_seat=1),
        _game([0, 0]),  # draw
    ]

    env_factory = _fake_opponents(monkeypatch, replays)
    result = measure_agent("search", ["deck:aggro"], n_games=len(replays), env_factory=env_factory)

    assert result["games"] == 5
    assert result["wins"] == 1
    assert result["draws"] == 1
    assert result["losses"] == 3
    assert result["focus_counts"] == {"deckout": 1, "early_collapse": 2}
    assert abs(result["focus_rate_of_losses"]["early_collapse"] - 2 / 3) < 1e-9
    assert abs(result["focus_rate_of_games"]["deckout"] - 1 / 5) < 1e-9


def test_measure_agent_uses_our_seat_when_swapped(monkeypatch):
    # Game 0 (not swapped, we are seat 0): a plain win, no loss bucket.
    # Game 1 (swapped, we are seat 1): seat 0 suffers the early_collapse and
    # seat 1 (us) wins -- our own loss buckets must stay empty, not pick up
    # the opponent's collapse.
    plain_win = _game(rewards=[1, -1], turn=10, prizes=(0, 3), decks=(30, 30), benches=(2, 2))
    opp_collapse = _game(rewards=[-1, 1], turn=3, prizes=(6, 6), decks=(42, 41), benches=(0, 2))
    env_factory = _fake_opponents(monkeypatch, [plain_win, opp_collapse])

    result = measure_agent("search", ["deck:aggro"], n_games=2, env_factory=env_factory)

    assert result["wins"] == 2
    assert result["losses"] == 0
    assert result["focus_counts"] == {"deckout": 0, "early_collapse": 0}


def test_compare_before_after_flags_improvement_when_rate_drops():
    before = {"focus_rate_of_losses": {"deckout": 0.5, "early_collapse": 0.3}}
    after = {"focus_rate_of_losses": {"deckout": 0.2, "early_collapse": 0.3}}

    diff = compare_before_after(before, after)

    assert diff["improved"] == {"deckout": True, "early_collapse": False}
    assert diff["diffs"]["deckout"] == -0.3
    assert diff["diffs"]["early_collapse"] == 0.0


def test_compare_before_after_ties_do_not_count_as_improved():
    before = {"focus_rate_of_losses": {"deckout": 0.4, "early_collapse": 0.4}}
    after = {"focus_rate_of_losses": {"deckout": 0.4, "early_collapse": 0.4}}

    diff = compare_before_after(before, after)

    assert diff["improved"] == {"deckout": False, "early_collapse": False}
