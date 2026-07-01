"""U7: the card-data-aware value function and the rollout depth cut-off.

The value function must order clearly winning states above clearly losing ones,
let board health and presence break ties between equal-prize positions, and never
let an estimate outrank a real terminal result. The depth cut-off must stop a
rollout early and return a board estimate instead of running to terminal.
"""
from dataclasses import dataclass, field

from search import eval as ev
from search import rollout


def _pokemon(hp, max_hp, energy=0):
    return {"id": 1, "hp": hp, "maxHp": max_hp,
            "energyCards": [{"id": 2}] * energy}


def _player(prizes_left, active=None, bench=None):
    return {
        "prize": [None] * prizes_left,
        "active": [active] if active else [],
        "bench": list(bench or []),
    }


def _state(me, opp, your_index=0, result=ev.RESULT_ONGOING):
    players = [None, None]
    players[your_index] = me
    players[1 - your_index] = opp
    return {"result": result, "players": players}


# --- ordering: winning beats losing -----------------------------------------

def test_clearly_winning_outranks_clearly_losing():
    full = _pokemon(120, 120)
    winning = _state(_player(1, active=full, bench=[full, full]),
                     _player(5, active=_pokemon(20, 120)))
    losing = _state(_player(5, active=_pokemon(20, 120)),
                    _player(1, active=full, bench=[full, full]))
    assert ev.board_value(winning, 0) > 0 > ev.board_value(losing, 0)


def test_value_is_symmetric_between_seats():
    full = _pokemon(120, 120)
    state = _state(_player(2, active=full, bench=[full]),
                   _player(5, active=_pokemon(30, 120)))
    assert ev.board_value(state, 0) == -ev.board_value(state, 1)


# --- prize dominates, board breaks ties --------------------------------------

def test_prize_lead_dominates_board_strength():
    full = _pokemon(120, 120)
    # We are a prize ahead but our board is weaker; the prize lead still wins.
    state = _state(_player(2, active=_pokemon(20, 120)),
                   _player(4, active=full, bench=[full, full, full]))
    assert ev.board_value(state, 0) > 0


def test_health_breaks_a_prize_tie():
    healthy = _pokemon(120, 120)
    hurt = _pokemon(20, 120)
    ahead = _state(_player(3, active=healthy), _player(3, active=hurt))
    tie = _state(_player(3, active=hurt), _player(3, active=hurt))
    assert ev.board_value(ahead, 0) > ev.board_value(tie, 0) == 0.0


def test_board_presence_breaks_a_prize_tie():
    full = _pokemon(120, 120)
    wider = _state(_player(3, active=full, bench=[full, full]),
                   _player(3, active=full))
    assert ev.board_value(wider, 0) > 0


# --- estimates never outrank a terminal result -------------------------------

def test_terminal_outranks_any_estimate():
    full = _pokemon(120, 120)
    # The best possible non-terminal board, yet still below a real win.
    best_board = _state(_player(1, active=full, bench=[full] * 5),
                        _player(6, active=_pokemon(1, 120)))
    assert ev.board_value(best_board, 0) < ev.WIN
    won = _state(_player(1, active=full), _player(6, active=full), result=0)
    assert ev.shaped_value(won, 0) == ev.WIN


def test_board_value_bounded_within_a_terminal_result():
    full = _pokemon(120, 120)
    worst = _state(_player(6, active=_pokemon(1, 120)),
                   _player(1, active=full, bench=[full] * 5))
    assert -ev.WIN < ev.board_value(worst, 0) < ev.WIN


def test_missing_players_is_neutral():
    assert ev.board_value({"players": []}, 0) == 0.0
    assert ev.shaped_value({"result": ev.RESULT_ONGOING, "players": [{}]}, 0) == 0.0


# --- attached energy breaks a tie the other board terms cannot ---------------

def test_energy_breaks_a_prize_health_and_width_tie():
    # Same prizes, same HP, same board width; we hold more attached energy, so our
    # board is closer to attacking and scores higher.
    powered = _pokemon(120, 120, energy=3)
    empty = _pokemon(120, 120, energy=0)
    ahead = _state(_player(3, active=powered), _player(3, active=empty))
    tie = _state(_player(3, active=empty), _player(3, active=empty))
    assert ev.board_value(ahead, 0) > ev.board_value(tie, 0) == 0.0


def test_energy_term_is_symmetric_between_seats():
    state = _state(_player(3, active=_pokemon(120, 120, energy=4)),
                   _player(3, active=_pokemon(120, 120, energy=1)))
    assert ev.board_value(state, 0) == -ev.board_value(state, 1)


def test_energy_never_outranks_a_prize_lead():
    # A mountain of energy on a prize-behind board still loses to a prize lead.
    loaded = _pokemon(120, 120, energy=20)
    behind = _state(_player(5, active=loaded, bench=[loaded, loaded]),
                    _player(2, active=_pokemon(120, 120, energy=0)))
    assert ev.board_value(behind, 0) < 0


def test_energy_term_is_bounded_and_clamped():
    # An absurd energy pile saturates at ENERGY_SHAPING; the whole estimate stays
    # below a real win.
    pile = _pokemon(120, 120, energy=99)
    state = _state(_player(3, active=pile), _player(3, active=_pokemon(120, 120)))
    assert 0 < ev.board_value(state, 0) <= ev.ENERGY_SHAPING + 1e-9
    assert ev.board_value(state, 0) < ev.WIN


def test_missing_energy_field_is_neutral():
    # A slot without an energyCards field contributes nothing rather than raising.
    bare = {"id": 1, "hp": 120, "maxHp": 120}
    state = _state(_player(3, active=bare), _player(3, active=bare))
    assert ev.board_value(state, 0) == 0.0


# --- rollout depth cut-off ---------------------------------------------------

@dataclass
class _FakeState:
    """We (index 0) are a prize ahead, so the board estimate is positive."""

    result: int = ev.RESULT_ONGOING
    players: list = field(default_factory=lambda: [
        {"prize": [None, None], "active": [], "bench": []},
        {"prize": [None] * 6, "active": [], "bench": []},
    ])


@dataclass
class _FakeObs:
    current: object
    select: object
    searchId: int = 1


class _Carrier:
    def __init__(self):
        sel = {"type": 0, "option": [0, 1], "minCount": 1, "maxCount": 1}
        self.observation = _FakeObs(_FakeState(), sel)
        self.searchId = 1


class _FakeStep:
    """A search_step that never terminates: it always yields another MAIN choice.

    Without a depth cut-off the rollout runs until max_steps; with one it stops
    early and returns a board estimate from the current state.
    """

    def __init__(self):
        self.calls = 0

    def __call__(self, search_id, select):
        self.calls += 1
        return _Carrier()


def test_rollout_depth_stops_early_and_returns_estimate():
    step = _FakeStep()
    value = rollout.rollout(1, [0], 0, step, max_steps=1000, value_depth=3)
    # First step plays the candidate, then exactly value_depth policy steps run.
    assert step.calls == 1 + 3
    # We are a prize ahead, so the estimate is positive and below a real win.
    assert 0 < value < ev.WIN


def test_rollout_without_depth_runs_to_step_cap():
    step = _FakeStep()
    rollout.rollout(1, [0], 0, step, max_steps=5, value_depth=None)
    # No early cut-off, so it steps until max_steps is exhausted (plus the first).
    assert step.calls == 1 + 5
