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
import ast
import os
import tarfile
from pathlib import Path

import pytest

from tools import build_submission as bs

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
SEARCH = ROOT / "search"
ANALYSIS = ROOT / "analysis"
SRC_PTCG_AGENT = ROOT / "src" / "ptcg_agent"
DECKS = ROOT / "decks"

# Every top-level package a shipped module's flat-layout fallback can resolve
# a bare `import X` / `from X import ...` against (a submission tarball has no
# subpackages: main.py and every extra sit together at the top level).
_FLAT_LAYOUT_SEARCH_DIRS = (AGENTS, SEARCH, ANALYSIS, SRC_PTCG_AGENT)

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
# rollout needs imitation_features (agents/), eval needs learned_eval (search/),
# move_prior needs imitation_features too, and learned_eval needs features
# (src/ptcg_agent/): all four were missing here until
# test_extras_cover_flat_layout_imports below caught the gap (the same ERROR
# class as ref 54281824, just on the non-shipped search agent). agent_search is
# not on the ladder today (search has been ladder-negative), so this had never
# actually errored a real submission, but it would the instant a search-revival
# ships it.
_SEARCH_EXTRAS = [
    *_HEUR_EXTRAS,
    str(AGENTS / "imitation_features.py"),
    str(SEARCH / "rollout.py"),
    str(SEARCH / "eval.py"),
    str(SEARCH / "learned_eval.py"),
    str(SEARCH / "move_prior.py"),
    str(SEARCH / "determinize.py"),
    str(SEARCH / "timebudget.py"),
    str(SEARCH / "endgame.py"),
    str(ANALYSIS / "archetype.py"),
    str(SRC_PTCG_AGENT / "features.py"),
]

# Each shipped entrypoint, the deck it ships, and the top-level support modules
# it imports inside a submission. Every one of these is loaded by the grader via
# exec without __file__, so every one must survive that path. The deck is also
# read and played by the engine in env.run, so a deck the engine rejects (or that
# the agent cannot pilot to a terminal reward) fails here too. The trolley case
# locks the exact queued early_collapse climb (heuristic + Precious Trolley deck).
SHIPPED_AGENTS = [
    pytest.param(str(AGENTS / "agent_baseline.py"), str(DECKS / "baseline.csv"), [], {}, id="baseline"),
    pytest.param(
        str(AGENTS / "agent_heuristic.py"),
        str(DECKS / "baseline.csv"),
        _HEUR_EXTRAS,
        {},
        id="heuristic",
    ),
    pytest.param(
        str(AGENTS / "agent_heuristic.py"),
        str(DECKS / "trolley.csv"),
        _HEUR_EXTRAS,
        {},
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
        {},
        id="heuristic-trolley_thick",
    ),
    # The L1 ladder lever (docs/plans/2026-07-02-combined-learned-eval-plan-v2.md resume state):
    # PTCG_ABILITY=1 baked at build time, same heuristic and trolley deck as the king. The pilot
    # agreed with top players on 0/554 real ABILITY decisions with the flag off; the once-per-turn
    # guard (agents/heuristics.py's _is_once_per_turn_ability) makes activation loop-safe. Offline
    # gauntlet (analysis/ability_ab.md) shows no regression before this spends a ladder slot.
    pytest.param(
        str(AGENTS / "agent_heuristic.py"),
        str(DECKS / "trolley.csv"),
        _HEUR_EXTRAS,
        {"PTCG_ABILITY": "1"},
        id="heuristic-trolley-ability",
    ),
    # U93 step 2 candidate: PTCG_ATTACK_FIRST=1 baked at build time, same heuristic and
    # trolley deck as the king. Confirmed LIVE on real positions (analysis/
    # attack_first_flip_check.md), then cleared both offline gates before spending a
    # ladder slot: the weak-bot gauntlet (analysis/attack_first_ab.md, +5.5pp, no
    # regression) and the calibrated bracket-ring A/B (analysis/attack_first_ring_check.md,
    # +10.0pp, agrees in direction).
    pytest.param(
        str(AGENTS / "agent_heuristic.py"),
        str(DECKS / "trolley.csv"),
        _HEUR_EXTRAS,
        {"PTCG_ATTACK_FIRST": "1"},
        id="heuristic-trolley-attack_first",
    ),
    pytest.param(str(AGENTS / "agent_search.py"), str(DECKS / "baseline.csv"), _SEARCH_EXTRAS, {}, id="search"),
    # The exact build queued for the next free ladder slot: the search agent
    # piloting the Precious Trolley deck. search+baseline proves the search stack
    # loads and plays; heuristic+trolley proves the trolley deck loads and plays;
    # but the deployed batch is search PILOTING trolley, a distinct integration
    # (determinize, rollout, and the heuristic rollout policy all run over the
    # trolley deck's card composition to a terminal reward). Lock it so a build or
    # pilot regression is caught here instead of erroring the submission and
    # burning a hard-won daily slot.
    pytest.param(
        str(AGENTS / "agent_search.py"), str(DECKS / "trolley.csv"), _SEARCH_EXTRAS, {}, id="search-trolley"
    ),
    # U39 promoted candidate: ring score 0.825 (n=40) vs trolley baseline 0.725,
    # delta +0.100, cleared promotion gate per analysis/candidate_decks_ring_gate.md.
    # Confirmation run passed; legality audit passed (tools/deck_validate.py);
    # pre-registered for TRACK L ladder A/B pending slot availability.
    pytest.param(
        str(AGENTS / "agent_heuristic.py"),
        str(DECKS / "candidate_yushin_ito.csv"),
        _HEUR_EXTRAS,
        {},
        id="heuristic-candidate_yushin_ito",
    ),
    # The project's strongest measured build: the yushin deck stacked with both
    # confirmed-positive levers. yushin+ability beats the trolley+ability baseline by
    # +8.0pp at n=100 (analysis/u112_stacked_ring_confirmation.md, arm 2 vs arm 1).
    # PTCG_THREAT_RETREAT=1 stacked on top of that same yushin+ability baseline adds a
    # further +6.0pp at n=100/arm, a clean ring-gate PASS (analysis/
    # u105b_threat_retreat_ring_ab.md). The threat-retreat lever was confirmed LIVE
    # against real positions only after the 2026-07-08 attack-ID fix to
    # _opponent_best_attack_damage restored nonzero threat damage (analysis/
    # u105_threat_prize_inert_check.md, superseded section at the top); the earlier
    # 2026-07-07 INERT verdict measured that bug, not the game. Lock this stack under
    # the grader path so its build is de-risked before it ever spends a ladder slot.
    pytest.param(
        str(AGENTS / "agent_heuristic.py"),
        str(DECKS / "candidate_yushin_ito.csv"),
        _HEUR_EXTRAS,
        {"PTCG_ABILITY": "1", "PTCG_THREAT_RETREAT": "1"},
        id="heuristic-yushin-ability-threat_retreat",
    ),
]


def _flat_layout_fallback_names(module_path: Path) -> set:
    """Top-level module names a submission-layout ImportError fallback needs.

    Every shipped module imports its support modules two ways: `from agents
    import X` locally, falling back to a bare `import X` (or `from X import
    ...`) "inside a submission, main.py and X.py sit together" (a tarball is
    flat, no subpackages). Ref 54281824 ERRORed because a hand-run
    build_submission.py command left card_effects.py out of --extra even
    though heuristics.py's fallback branch requires it unconditionally at
    import time; the in-process test below caught nothing because it built its
    own tarball from a hardcoded extras list that happened to already include
    it. This scans the AST for that except-ImportError shape and returns the
    bare names it falls back to import, so the extras list can be checked
    against what the code actually requires instead of what a human remembered
    to type.
    """
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        for handler in node.handlers:
            for stmt in handler.body:
                if isinstance(stmt, ast.Import):
                    names.update(alias.name.split(".")[0] for alias in stmt.names)
                elif isinstance(stmt, ast.ImportFrom) and stmt.module:
                    names.add(stmt.module.split(".")[0])
    return names


def _required_flat_extras(entry_path: Path) -> set:
    """Transitive closure of flat-layout support modules entry_path needs.

    Follows each ImportError fallback name to its source file under
    agents/search/analysis (the only places a flat-layout submission draws
    support modules from) and repeats until no new module is discovered, so a
    chain (agent_search -> rollout -> eval -> ...) is fully covered, not just
    the entrypoint's own direct fallbacks.
    """
    seen_paths = set()
    pending = [entry_path]
    required_names = set()
    while pending:
        path = pending.pop()
        if path in seen_paths:
            continue
        seen_paths.add(path)
        for name in _flat_layout_fallback_names(path):
            required_names.add(name)
            for directory in _FLAT_LAYOUT_SEARCH_DIRS:
                candidate = directory / f"{name}.py"
                if candidate.exists() and candidate not in seen_paths:
                    pending.append(candidate)
    return required_names


@pytest.mark.parametrize("agent_file, deck_file, extras, env", SHIPPED_AGENTS)
def test_extras_cover_flat_layout_imports(agent_file, deck_file, extras, env):
    """The declared extras list must satisfy every flat-layout fallback import.

    Regression test for the ref 54281824 ERROR class: a build's --extra list
    silently drifting out of sync with what the shipped code actually imports
    under the submission's flat layout. Derives the requirement from the
    source itself (not a second hand-maintained list) so a future module that
    adds a new "sits together" import is caught here even if nobody remembers
    to update SHIPPED_AGENTS' extras.
    """
    required = _required_flat_extras(Path(agent_file))
    provided = {Path(p).stem for p in extras}
    missing = required - provided
    assert not missing, (
        f"{agent_file} needs {sorted(missing)} bundled as --extra (flat-layout "
        f"ImportError fallback), but the declared extras only provide {sorted(provided)}"
    )


def _extract(tar_path: Path, dest: Path) -> None:
    with tarfile.open(tar_path) as tar:
        tar.extractall(dest)


@pytest.mark.parametrize("agent_file, deck_file, extras, env", SHIPPED_AGENTS)
def test_extracted_submission_loads_under_grader(agent_file, deck_file, extras, env, tmp_path):
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
        env=env,
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
