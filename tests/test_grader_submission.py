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

# The top-level support modules each shipped entrypoint imports inside a built
# submission (the search agent pulls in the whole search/ and analysis/ stack).
_SEARCH_EXTRAS = [
    str(AGENTS / "heuristics.py"),
    str(SEARCH / "rollout.py"),
    str(SEARCH / "eval.py"),
    str(SEARCH / "determinize.py"),
    str(SEARCH / "timebudget.py"),
    str(ANALYSIS / "archetype.py"),
]

# Each shipped entrypoint and the top-level support modules it imports inside a
# submission. Every one of these is loaded by the grader via exec without
# __file__, so every one must survive that path.
SHIPPED_AGENTS = [
    pytest.param(str(AGENTS / "agent_baseline.py"), [], id="baseline"),
    pytest.param(
        str(AGENTS / "agent_heuristic.py"),
        [str(AGENTS / "heuristics.py")],
        id="heuristic",
    ),
    pytest.param(str(AGENTS / "agent_search.py"), _SEARCH_EXTRAS, id="search"),
]


def _extract(tar_path: Path, dest: Path) -> None:
    with tarfile.open(tar_path) as tar:
        tar.extractall(dest)


@pytest.mark.parametrize("agent_file, extras", SHIPPED_AGENTS)
def test_extracted_submission_loads_under_grader(agent_file, extras, tmp_path):
    """A built, extracted submission loads and finishes a match via env.run.

    Mirrors the grader: file-path agent string -> exec without __file__, agent
    dir on sys.path, cwd is the agent dir. A NameError at module load (the
    __file__ bug) would make the agent error and the reward invalid.
    """
    tar_path = bs.build(
        agent_file=agent_file,
        deck_file=str(DECKS / "baseline.csv"),
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
