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


def build(agent_file, deck_file, out_name="submission.tar.gz"):
    if not (CG_SRC / "api.py").exists():
        sys.exit(f"Official cg/ package not found at {CG_SRC}. Download it first.")
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)
    shutil.copy(agent_file, BUILD / "main.py")
    shutil.copy(deck_file, BUILD / "deck.csv")
    shutil.copytree(CG_SRC, BUILD / "cg", ignore=shutil.ignore_patterns("__pycache__"))
    out = REPO / out_name
    with tarfile.open(out, "w:gz") as tar:
        for item in ("main.py", "deck.csv", "cg"):
            tar.add(BUILD / item, arcname=item)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default=str(AGENTS / "agent_baseline.py"))
    ap.add_argument("--deck", default=str(DECKS / "baseline.csv"))
    ap.add_argument("--out", default="submission.tar.gz")
    args = ap.parse_args()
    out = build(args.agent, args.deck, args.out)
    with tarfile.open(out) as tar:
        names = tar.getnames()
    top = sorted({n.split("/")[0] for n in names})
    has_linux = any(n.endswith("cg/libcg.so") for n in names)
    print(f"Built {out}")
    print(f"Top level entries: {top}")
    print(f"Linux engine lib present: {has_linux}")


if __name__ == "__main__":
    main()
