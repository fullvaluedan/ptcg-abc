"""Lock the --env lever-baking path of build_submission.

The grader runs main.py in a CLEAN environment, so a PTCG_* lever gated on
os.environ (rollout depth, empty-bench floor, energy resequencing) cannot be
enabled by exporting the variable when the tarball is built: the archive carries
no environment. A naive "PTCG_ENERGY_SEQ=1 python tools/build_submission.py ..."
would ship the lever OFF and burn one of the five daily ladder slots testing a
no-op. build_submission.build(env=...) bakes the flag into main.py above the
agent's imports instead; these tests pin both halves of the contract:

  1. Without env, main.py is a byte-for-byte copy of the agent file, so the
     deployed default build (the shipped floor, the queued search batch) is
     never perturbed by the mechanism.
  2. With env, the prelude sits above the agent source and, when executed in a
     clean environment, actually binds the lever ON (heuristics._ENERGY_SEQ),
     which is the exact state the grader would see.
"""
import importlib
import os

from tools import build_submission as bs

ROOT = bs.REPO
AGENT = ROOT / "agents" / "agent_heuristic.py"
DECK = ROOT / "decks" / "trolley.csv"
HEUR = ROOT / "agents" / "heuristics.py"


def test_no_env_leaves_main_byte_identical(tmp_path):
    """No baked flags -> main.py is an exact copy of the agent file."""
    out = bs.build(
        agent_file=str(AGENT),
        deck_file=str(DECK),
        out_name=str(tmp_path / "s.tar.gz"),
        extras=[str(HEUR)],
        env=None,
    )
    assert out.exists()
    main_py = (bs.BUILD / "main.py").read_text()
    assert main_py == AGENT.read_text()
    assert "_cfg_os" not in main_py


def test_env_prelude_is_baked_above_the_agent_source(tmp_path):
    """A baked flag appears in a prelude that precedes the original agent code."""
    bs.build(
        agent_file=str(AGENT),
        deck_file=str(DECK),
        out_name=str(tmp_path / "s.tar.gz"),
        extras=[str(HEUR)],
        env={"PTCG_ENERGY_SEQ": "1"},
    )
    main_py = (bs.BUILD / "main.py").read_text()
    agent_src = AGENT.read_text()
    setdefault_line = '_cfg_os.environ.setdefault(\'PTCG_ENERGY_SEQ\', \'1\')'
    assert setdefault_line in main_py
    # The prelude must run before the agent's own imports read the env, i.e. it
    # precedes the original first line of the agent source.
    first_agent_line = agent_src.splitlines()[0]
    assert main_py.index(setdefault_line) < main_py.index(first_agent_line)


def test_baked_prelude_actually_binds_the_lever_on(tmp_path):
    """Running the baked prelude under a clean env flips the shipped-off lever.

    Reproduces the grader: a clean os.environ, then main.py's prelude runs, then
    the agent imports heuristics. The prelude sets PTCG_ENERGY_SEQ, so heuristics
    binds _ENERGY_SEQ True at import, exactly the state the ladder would see.
    """
    bs.build(
        agent_file=str(AGENT),
        deck_file=str(DECK),
        out_name=str(tmp_path / "s.tar.gz"),
        extras=[str(HEUR)],
        env={"PTCG_ENERGY_SEQ": "1"},
    )
    prelude = bs._config_prelude({"PTCG_ENERGY_SEQ": "1"})

    from agents import heuristics

    had = "PTCG_ENERGY_SEQ" in os.environ
    prev = os.environ.get("PTCG_ENERGY_SEQ")
    os.environ.pop("PTCG_ENERGY_SEQ", None)
    try:
        # Clean env -> the shipped default is off.
        importlib.reload(heuristics)
        assert heuristics._ENERGY_SEQ is False
        # The baked prelude runs (its setdefault sets the flag), then the agent
        # imports heuristics: the lever is now on.
        exec(compile(prelude, "<prelude>", "exec"), {})
        importlib.reload(heuristics)
        assert heuristics._ENERGY_SEQ is True
    finally:
        if had:
            os.environ["PTCG_ENERGY_SEQ"] = prev
        else:
            os.environ.pop("PTCG_ENERGY_SEQ", None)
        importlib.reload(heuristics)
