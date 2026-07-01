"""Lock the shipped-default lever configuration of the search submission.

The search agent carries a growing set of A/B levers, each gated on a PTCG_*
environment variable and each defaulting to a fixed shipped value. A submission
runs on the ladder with a CLEAN environment (no PTCG_* overrides), so what ships
is exactly the set of module-level defaults resolved here. Getting that set wrong
burns a hard-won daily slot: a staged lever accidentally flipped on, or a
fire-on-batch lever silently turned off, changes the deployed policy without any
signal until the score comes back.

autoloop_status.md tracks this set in prose and has miscounted it before (a NEXT
listed five active search changes and missed a sixth, the unconditional thin-bench
defer). This test is the executable version of that ledger: it pins each lever's
shipped default so a regression is caught here, in the suite, instead of on the
ladder.

The split that matters for the shipped build:
  FIRE-ON-BATCH (active on the deployed policy with a clean env):
    - soft time cap 2.0s per decision      (agent_search._SOFT_CAP)
    - robustness penalty 0.25              (agent_search._ROBUST_COEF)
    - endgame solver on                    (agent_search._ENDGAME)
    - modal field-opponent prior on        (archetype._field_prior_enabled())
    - thin-bench MAIN defer (unconditional, no flag; see e44245a)
  STAGED-OFF (inert on the deployed policy):
    - rollout depth cut-off None -> terminal rollouts (agent_search._ROLLOUT_DEPTH)
    - convex empty-bench leaf floor off    (eval._BENCH_FLOOR)  [REFUTED, keep off]
    - energy-attach resequencing off       (heuristics._ENERGY_SEQ)
    - dig-for-a-Basic when thin off        (heuristics._BENCH_DIG)  [REFUTED, keep off]

Keystone coupling: the leaf-eval terms (the empty-bench floor, plus the
active-weighted and attached-energy health terms) are only read at a rollout LEAF.
With _ROLLOUT_DEPTH None every line rolls to a terminal result and a leaf is only
reached at the engine's 400-step cap, so those terms are effectively inert on the
shipped build regardless of their own flags. That is why flipping the bench floor
alone does nothing: it needs a positive rollout depth to matter.

The rollout-depth + bench-floor JOINT lever is now refuted, not merely pending: a
fidelity/efficacy squeeze means no rollout depth both fires the floor AND keeps the
rollout faithful. At depth 8 the floor flips 2/5 decisions but the depth-cut argmax
disagrees with the terminal argmax on 4/5; at depth 16 the rollout tracks terminal
2/2 but the floor flips 0/2 (tools/measure_bench_floor.py;
analysis/bench_floor_search_lever_squeezed.md). These two levers therefore stay off
permanently, and the bench-maintenance win stays in the PILOT guard (the e44245a
thin-bench defer, measured to cut our board-out 43 -> 34pct with no fidelity cost).
"""
import os

import pytest

from agents import agent_search, heuristics
from analysis import archetype
from search import eval as leaf_eval

# The constants below are bound at module import from os.environ. If a developer
# runs the suite with a PTCG_* override exported, those bindings reflect the
# override, not the shipped default, and this contract legitimately does not hold.
# Skip rather than report a false regression; the ladder never sets these.
_PTCG_OVERRIDES = sorted(k for k in os.environ if k.startswith("PTCG_"))
pytestmark = pytest.mark.skipif(
    bool(_PTCG_OVERRIDES),
    reason=f"PTCG_* override(s) set in env, shipped-default contract N/A: {_PTCG_OVERRIDES}",
)


def test_fire_on_batch_levers_are_active():
    """The levers that shape the deployed policy resolve to their shipped values."""
    assert agent_search._SOFT_CAP == 2.0
    assert agent_search._ROBUST_COEF == 0.25
    assert agent_search._ENDGAME is True
    # Read at call time (a gauntlet can toggle it mid-process); default on.
    assert archetype._field_prior_enabled() is True


def test_staged_levers_are_inert_on_the_shipped_build():
    """The A/B levers awaiting a ladder slot are off in the deployed policy."""
    # The keystone: terminal rollouts. None means no depth cut-off, so leaves are
    # only reached at the engine's 400-step cap and the leaf-eval terms below stay
    # inert regardless of their own flags.
    assert agent_search._ROLLOUT_DEPTH is None
    assert agent_search._MAX_DETS is None
    assert leaf_eval._BENCH_FLOOR is False
    assert heuristics._ENERGY_SEQ is False
    # Refuted at scale: the dig-for-a-Basic lever cut board-out at small n but the
    # effect vanished at n=360 (see analysis/bench_dig_refuted_at_scale.md). Kept
    # off permanently; the empty-bench collapse is a deck-density problem.
    assert heuristics._BENCH_DIG is False


def test_thin_bench_defer_is_unconditional():
    """The e44245a keystone fix rides the heuristic bench guard, not a flag.

    The recovered on-ladder search (ref 54218335) ran but scored 514.7, below the
    569.6 heuristic-trolley floor, because a searched MAIN move bypassed the
    heuristic's bench-development guard and boarded itself out. The fix defers a
    thin-bench MAIN decision to that guard. It is not gated on any PTCG_* flag, so
    it fires on every submission unconditionally; guard against it being quietly
    re-gated by pinning that the predicate it defers on still exists and is
    callable.
    """
    assert callable(heuristics._bench_is_thin)
