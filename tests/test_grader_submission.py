"""Regression test for the grader's exec-without-__file__ agent loading.

The Kaggle grader loads a submission's main.py by reading its source and running
exec(code, {}) with a globals dict that has NO __file__ (see
kaggle_environments.agent.get_last_callable). Any module-load-time reference to
__file__ raises NameError, the agent never loads, and the whole submission is
marked ERROR. A previous heuristic submission (ref 54207787) ERRORED for exactly
this reason: _read_deck built a candidate path with Path(__file__) at import.

This test reproduces the grader path on purpose: it builds a real submission,
extracts the tarball to a temp dir, chdirs in (the grader runs from the agent
dir), and runs env.run([extracted main.py, "random"]). It MUST exercise the
env.run-on-extracted-tarball path (a file-path agent string), not a module
import, because importing main.py as a module DEFINES __file__ and hides the bug.
"""
import os
import tarfile
from pathlib import Path

import pytest

from tools import build_submission as bs

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
SEARCH = ROOT / "search"
ANALYSIS = ROOT / "analysis"
DECKS = ROOT / "decks"

# The heuristic pilot and every entrypoint that reuses it (the search rollout
# policy) import agents/card_effects.py from agents/heuristics.py, so the
# card-knowledge layer MUST ship alongside heuristics.py or the delegated import
# raises at match load and errors the submission. Bundle them as one unit.
_HEUR_EXTRAS = [
    str(AGENTS / "heuristics.py"),
    str(AGENTS / "card_effects.py"),
]

# The top-level support modules each shipped entrypoint imports inside a built
# submission (the search agent pulls in the whole search/ and analysis/ stack).
_SEARCH_EXTRAS = [
    *_HEUR_EXTRAS,
    str(SEARCH / "rollout.py"),
    str(SEARCH / "eval.py"),
    str(SEARCH / "determinize.py"),
    str(SEARCH / "timebudget.py"),
    str(SEARCH / "endgame.py"),
    str(ANALYSIS / "archetype.py"),
]

# Each shipped entrypoint, the deck it ships, and the top-level support modules
# it imports inside a submission. Every one of these is loaded by the grader via
# exec without __file__, so every one must survive that path. The deck is also
# read and played by the engine in env.run, so a deck the engine rejects (or that
# the agent cannot pilot to a terminal reward) fails here too. The trolley case
# locks the exact queued early_collapse climb (heuristic + Precious Trolley deck).
SHIPPED_AGENTS = [
    pytest.param(str(AGENTS / "agent_baseline.py"), str(DECKS / "baseline.csv"), [], id="baseline"),
    pytest.param(
        str(AGENTS / "agent_heuristic.py"),
        str(DECKS / "baseline.csv"),
        _HEUR_EXTRAS,
        id="heuristic",
    ),
    pytest.param(
        str(AGENTS / "agent_heuristic.py"),
        str(DECKS / "trolley.csv"),
        _HEUR_EXTRAS,
        id="heuristic-trolley",
    ),
    # The validated next deck candidate (thicker-basic trolley: Kyogre 2->4,
    # energy 35->33), staged to ladder-test as a clean single-variable deck A/B
    # against trolley on the first slot after the scored-pair reclaim. It cut the
    # mirror empty-bench collapse 80.8%->65.4% (n=240, p<0.001) with no win-rate
    # regression (see analysis/collapse_rate_thick_deck.md). Lock it under the
    # grader path so its build is de-risked before it ever spends a daily slot.
    pytest.param(
        str(AGENTS / "agent_heuristic.py"),
        str(DECKS / "trolley_thick.csv"),
        _HEUR_EXTRAS,
        id="heuristic-trolley_thick",
    ),
    pytest.param(str(AGENTS / "agent_search.py"), str(DECKS / "baseline.csv"), _SEARCH_EXTRAS, id="search"),
    # The exact build queued for the next free ladder slot: the search agent
    # piloting the Precious Trolley deck. search+baseline proves the search stack
    # loads and plays; heuristic+trolley proves the trolley deck loads and plays;
    # but the deployed batch is search PILOTING trolley, a distinct integration
    # (determinize, rollout, and the heuristic rollout policy all run over the
    # trolley deck's card composition to a terminal reward). Lock it so a build or
    # pilot regression is caught here instead of erroring the submission and
    # burning a hard-won daily slot.
    pytest.param(str(AGENTS / "agent_search.py"), str(DECKS / "trolley.csv"), _SEARCH_EXTRAS, id="search-trolley"),
]


def _extract(tar_path: Path, dest: Path) -> None:
    with tarfile.open(tar_path) as tar:
        tar.extractall(dest)


@pytest.mark.parametrize("agent_file, deck_file, extras", SHIPPED_AGENTS)
def test_extracted_submission_loads_under_grader(agent_file, deck_file, extras, tmp_path):
    """A built, extracted submission loads and finishes a match via env.run.

    Mirrors the grader: file-path agent string -> exec without __file__, agent
    dir on sys.path, cwd is the agent dir. A NameError at module load (the
    __file__ bug) would make the agent error and the reward invalid.
    """
    tar_path = bs.build(
        agent_file=agent_file,
        deck_file=deck_file,
        out_name=str(tmp_path / "submission_grader_test.tar.gz"),
        extras=extras,
    )
    extract_dir = tmp_path / "extracted"
    extract_dir.mkdir()
    _extract(Path(tar_path), extract_dir)

    main_py = extract_dir / "main.py"
    assert main_py.exists()
    assert (extract_dir / "deck.csv").exists()
    assert (extract_dir / "cg" / "api.py").exists()

    from kaggle_environments import make

    cwd = os.getcwd()
    os.chdir(extract_dir)
    try:
        env = make("cabt")
        # File-path agent string forces the grader's exec-without-__file__ load
        # path; the second seat is the builtin random opponent.
        env.run([str(main_py), "random"])
    finally:
        os.chdir(cwd)

    last = env.steps[-1]
    # Our agent sits in seat 0. A failed load yields an error/None reward; a
    # clean load that plays a full match yields a real terminal reward.
    reward = last[0]["reward"]
    assert reward in (-1, 0, 1), f"agent did not load/finish cleanly: reward={reward}"
    assert last[0]["status"] in ("DONE", "ACTIVE", "INACTIVE"), last[0]["status"]
    assert len(env.steps) > 1
