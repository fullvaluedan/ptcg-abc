"""Bracket-band opponent decklists for the practice ring (plan U81, step 2).

tools/bracket_select.py already found WHO we actually face (the ~450-750
rating band, unioned with our own real ladder opponents). This tool finds
WHAT they play: it scans the daily episode dump for every MAIN-decision
replay where one seat's team is in that bracket set, canonicalizes each
seat's opening 60-card decklist (analysis.expert_cohort.seat_decklists), and
counts how often each exact decklist was played. The most-played legal
decklists become new `bracket_<rank>.csv` files under decks/, which
tools.opponents.bracket_clone_names() auto-discovers as `clone:bracket_<rank>`
opponents with no further wiring: they use the same first-legal-plus-safety
pilot U71 already found is the practical ceiling for a harvested decklist, no
trained model needed.

Unlike tools/clone_dataset.py (which only walks TOP-20 team games, since that
is the dataset it reads), this scans the FULL daily dump: bracket-band teams
essentially never appear as a seat in a top-20 game, so the top-20 dataset
would yield almost nothing for this bracket.

A decklist a real game actually played should already be legal (the grader's
own engine accepted it), but tools.deck_validate.validate is still run as a
defensive check before a decklist is shipped as a ring opponent: a truncated
or malformed replay could otherwise smuggle a bad decklist into the ring.

Dev tool only; never shipped. Reads the competition episode dataset but never
redistributes it (data/episodes and data/training stay gitignored); the
decklists it writes are 60 card ids, the same shape as every other decks/*.csv
already committed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.expert_cohort import seat_decklists, team_names  # noqa: E402
from analysis.move_ranking_validator import load_replays  # noqa: E402
from tools.deck_validate import validate  # noqa: E402
from tools.opponents import BRACKET_DECK_PREFIX  # noqa: E402
from tools.top_player_tracker import DEFAULT_EPISODES_DIR, newest_dataset  # noqa: E402

DEFAULT_TEAMS_PATH = _ROOT / "data" / "training" / "bracket_teams.json"
DEFAULT_DECKS_DIR = _ROOT / "decks"
DEFAULT_TOP_K = 6


def _console_safe(text: str) -> str:
    """`text` re-encoded to drop characters the current stdout encoding cannot
    print (a team name may hold arbitrary Unicode; Windows consoles often use
    cp1252, which is not a superset of it). Print-only; never touches data on
    disk, so the JSON report keeps every character exactly as harvested.
    """
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding)


def load_team_set(path=DEFAULT_TEAMS_PATH) -> set:
    """The team name set from bracket_select.py's output JSON, or empty on any read failure.

    Never raises: a missing or malformed teams file degrades to an empty set,
    same fault-tolerant shape as every other Kaggle-derived tool here.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    teams = data.get("teams")
    if not isinstance(teams, list):
        return set()
    return {str(t) for t in teams}


def decklist_counts(replay_label_pairs, team_set) -> dict:
    """canonical decklist (sorted card-id tuple) -> {"count", "teams"} over replay_label_pairs.

    Both seats of a replay are checked independently against team_set, so a
    bracket-vs-bracket game contributes both decklists. A replay with an
    unreadable team-name pair or decklist is skipped, never fatal (mirrors
    tools.clone_dataset.replay_groups).
    """
    counts = {}
    for replay, _label in replay_label_pairs:
        names = team_names(replay)
        if names is None:
            continue
        decks = seat_decklists(replay)
        if decks is None:
            continue
        for seat, name in enumerate(names):
            if name not in team_set:
                continue
            key = tuple(sorted(decks[seat]))
            entry = counts.setdefault(key, {"count": 0, "teams": set()})
            entry["count"] += 1
            entry["teams"].add(name)
    return counts


def top_decklists(counts: dict, k: int = DEFAULT_TOP_K, validate_fn=validate) -> list:
    """The k most-played legal decklists, ranked by occurrence count then deck id for determinism.

    validate_fn is injectable so tests never touch the native card engine;
    defaults to tools.deck_validate.validate. A decklist that fails validation
    is skipped, not force-fit into the ring.
    """
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1]["count"], kv[0]))
    out = []
    for deck, info in ranked:
        if len(out) >= k:
            break
        verdict = validate_fn(list(deck))
        if not verdict.get("ok"):
            continue
        out.append({"deck": deck, "count": info["count"], "teams": sorted(info["teams"])})
    return out


def write_decks(selected: list, decks_dir=DEFAULT_DECKS_DIR) -> list:
    """Write decks/bracket_<rank>.csv for each selected decklist, 1-indexed by rank.

    Returns the written paths in rank order. decks_dir is created if absent.
    """
    decks_dir = Path(decks_dir)
    decks_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, entry in enumerate(selected, start=1):
        path = decks_dir / f"{BRACKET_DECK_PREFIX}{i}.csv"
        path.write_text("\n".join(str(c) for c in entry["deck"]) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def build(source, team_set, k: int = DEFAULT_TOP_K, limit=None, validate_fn=validate) -> dict:
    """The full U81 step-2 pipeline: read the dataset, count decklists, keep the top-k legal ones."""
    pairs = load_replays(source, limit=limit)
    counts = decklist_counts(pairs, team_set)
    selected = top_decklists(counts, k=k, validate_fn=validate_fn)
    return {"distinct_decklists": len(counts), "selected": selected}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", nargs="?", default=None,
                     help="episode dataset .zip or a directory of *.json replays "
                          "(default: newest under --episodes-dir)")
    ap.add_argument("--episodes-dir", default=str(DEFAULT_EPISODES_DIR),
                     help="directory holding episode dataset .zip files")
    ap.add_argument("--teams-path", default=str(DEFAULT_TEAMS_PATH),
                     help="bracket_select.py output JSON (default data/training/bracket_teams.json)")
    ap.add_argument("--decks-dir", default=str(DEFAULT_DECKS_DIR),
                     help="directory to write bracket_<rank>.csv into (default decks/)")
    ap.add_argument("--top-k", type=int, default=DEFAULT_TOP_K,
                     help="how many most-played legal decklists to keep (default %(default)s)")
    ap.add_argument("--limit", type=int, default=None,
                     help="cap episodes read (default: the whole dataset)")
    ap.add_argument("--out", default=None, help="optional JSON report path")
    args = ap.parse_args(argv)

    source = Path(args.source) if args.source else newest_dataset(args.episodes_dir)
    if source is None or not Path(source).exists():
        print(f"no episode dataset found under {args.episodes_dir}")
        return 1

    team_set = load_team_set(args.teams_path)
    if not team_set:
        print(f"no bracket teams loaded from {args.teams_path}; run tools/bracket_select.py first")
        return 1

    result = build(source, team_set, k=args.top_k, limit=args.limit, validate_fn=validate)
    paths = write_decks(result["selected"], args.decks_dir)

    print(f"distinct bracket decklists seen: {result['distinct_decklists']}")
    print(f"selected top {len(result['selected'])}:")
    for i, entry in enumerate(result["selected"], start=1):
        sample_teams = _console_safe(", ".join(entry["teams"][:3]))
        print(f"  {BRACKET_DECK_PREFIX}{i}: {entry['count']} games, teams e.g. [{sample_teams}]")
    print(f"wrote {len(paths)} deck csv(s) to {args.decks_dir}")

    if args.out:
        report = {
            "distinct_decklists": result["distinct_decklists"],
            "selected": [
                {"rank": i, "count": e["count"], "teams": e["teams"]}
                for i, e in enumerate(result["selected"], start=1)
            ],
        }
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"wrote report {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
