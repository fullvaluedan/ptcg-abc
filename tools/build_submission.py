"""Build a submission.tar.gz for the Simulation competition.

Stages the chosen agent file as main.py, the chosen deck as deck.csv, and the
official cg/ engine package (all platform libs), then tars them at the top level
(the layout the grader expects).

Usage:
    python tools/build_submission.py [--agent path] [--deck path] [--out name]
"""
import argparse
import shutil
import sys
import tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CG_SRC = REPO / "data" / "cg"          # official engine package (gitignored)
DECKS = REPO / "decks"
AGENTS = REPO / "agents"
BUILD = REPO / "submission"


def _config_prelude(env) -> str:
    """A main.py prelude that bakes A/B lever flags into the grader runtime.

    The grader loads main.py in a CLEAN environment, so a PTCG_* lever gated on
    os.environ cannot be enabled by exporting the variable at build time: the
    tarball carries no environment, and the flag falls back to its shipped
    default. This prelude, prepended above the agent's own imports, sets each
    variable in-process BEFORE those imports read it, so an A/B lever actually
    ships in its intended state. setdefault, not assignment, so a real
    environment override (a developer, a gauntlet) still wins; the grader never
    sets these, so on the ladder the baked value takes effect.
    """
    lines = [
        "# Submission lever config baked at build time",
        "# (tools/build_submission.py --env). Runs before the agent imports below",
        "# read os.environ, so an A/B flag reaches the grader's clean runtime.",
        "import os as _cfg_os",
    ]
    for key in sorted(env):
        lines.append(f"_cfg_os.environ.setdefault({key!r}, {env[key]!r})")
    lines.append("del _cfg_os")
    return "\n".join(lines) + "\n\n\n"


def build(agent_file, deck_file, out_name="submission.tar.gz", extras=None, env=None):
    """Stage a submission tarball.

    agent_file becomes main.py, deck_file becomes deck.csv, the official cg/
    package is bundled, and each path in extras is copied to the top level under
    its own basename. extras carries support modules the agent imports at top
    level inside the submission (for example heuristics.py).

    env is an optional {name: value} map of PTCG_* lever flags to bake into
    main.py so they reach the grader's clean runtime (see _config_prelude). When
    it is empty or None, main.py is a byte-for-byte copy of agent_file, so the
    deployed default build is never perturbed by the mechanism.
    """
    if not (CG_SRC / "api.py").exists():
        sys.exit(f"Official cg/ package not found at {CG_SRC}. Download it first.")
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)
    if env:
        (BUILD / "main.py").write_text(
            _config_prelude(env) + Path(agent_file).read_text()
        )
    else:
        shutil.copy(agent_file, BUILD / "main.py")
    shutil.copy(deck_file, BUILD / "deck.csv")
    shutil.copytree(CG_SRC, BUILD / "cg", ignore=shutil.ignore_patterns("__pycache__"))
    extra_names = []
    for src in extras or []:
        name = Path(src).name
        shutil.copy(src, BUILD / name)
        extra_names.append(name)
    out = REPO / out_name
    with tarfile.open(out, "w:gz") as tar:
        for item in ("main.py", "deck.csv", "cg", *extra_names):
            tar.add(BUILD / item, arcname=item)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default=str(AGENTS / "agent_baseline.py"))
    ap.add_argument("--deck", default=str(DECKS / "baseline.csv"))
    ap.add_argument("--out", default="submission.tar.gz")
    ap.add_argument("--extra", action="append", default=[],
                    help="support module copied to the top level (repeatable)")
    ap.add_argument("--env", action="append", default=[], metavar="KEY=VALUE",
                    help="bake a PTCG_* lever flag into main.py so it reaches the "
                         "grader's clean runtime (repeatable, e.g. PTCG_ENERGY_SEQ=1)")
    args = ap.parse_args()
    env = {}
    for pair in args.env:
        if "=" not in pair:
            sys.exit(f"--env expects KEY=VALUE, got {pair!r}")
        key, value = pair.split("=", 1)
        env[key] = value
    out = build(args.agent, args.deck, args.out, extras=args.extra, env=env)
    with tarfile.open(out) as tar:
        names = tar.getnames()
    top = sorted({n.split("/")[0] for n in names})
    has_linux = any(n.endswith("cg/libcg.so") for n in names)
    print(f"Built {out}")
    print(f"Top level entries: {top}")
    print(f"Linux engine lib present: {has_linux}")
    print(f"Baked lever flags: {env or 'none (shipped defaults)'}")


if __name__ == "__main__":
    main()
