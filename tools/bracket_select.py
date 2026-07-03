"""Bracket-band opponent selection (LOOP_BRIEF Track L, unit U81 step 1).

The U73 clone ring calibrated against the top-20 leaderboard teams and FAILED
(tau 0.429, analysis/ring_calibration.md): the top-20 are too subtle to
imitate AND the wrong bracket anyway, since matchmaking pairs us with the
~450-750-rated field (our own team sits at rating ~548, rank ~2900 of ~4100),
not the champions. This tool builds the team set the REBUILT ring should
imitate: every team whose live leaderboard rating falls in the target band,
unioned with every opponent named in our own harvested ladder replays (a
guaranteed real-bracket sample, no rating lookup needed).

Two independent sources, unioned:
  1. fetch_full_leaderboard: `kaggle competitions leaderboard -d` downloads
     the ENTIRE public leaderboard as one CSV (unlike --show, which is capped
     at page-size 200 and only covers the very top of the field), then
     band_teams filters it to [low, high] by Score. The download lands in its
     own data/leaderboard_cache/ directory, never data/episodes/: the kaggle
     CLI always names this file "<competition-slug>.zip", and
     tools.top_player_tracker.newest_dataset picks the lexicographically LAST
     "*.zip" under episodes_dir as the newest episode dump (by design, see
     its own test). "pokemon-tcg-ai-battle.zip" sorts after every real dated
     dump ("pokemon-tcg-ai-battle-episodes-2026-07-02.zip" etc, since "-" <
     "." in the shared prefix), so dropping the leaderboard zip into
     data/episodes/ would permanently shadow the real dumps for every other
     tool that calls newest_dataset (clone_dataset.py, daily_refresh.py).
  2. opponents_from_replays: info.TeamNames from our own data/replays/*.json,
     skipping self-play validation episodes and any replay where our own
     team cannot be confidently matched (no guessing which seat is ours).

Output is a small JSON team list under data/training/ (gitignored, same tier
as every other data/training/* artifact), meant to feed
`tools/clone_dataset.py --teams <name> <name> ...` in place of a fresh
top-N leaderboard fetch. Dev tool only; never shipped. Every network call is
fault tolerant (never raises) and degrades to an empty result set on failure.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.expert_cohort import team_names  # noqa: E402
from tools.scout import OUR_TEAM, SIMULATION_SLUG, is_self_play, load_replay, our_index_from_replay, run_kaggle  # noqa: E402

DEFAULT_LEADERBOARD_DIR = _ROOT / "data" / "leaderboard_cache"
DEFAULT_REPLAYS_DIR = _ROOT / "data" / "replays"
DEFAULT_OUT_DIR = _ROOT / "data" / "training"
DEFAULT_BAND_LOW = 450.0
DEFAULT_BAND_HIGH = 750.0


def fetch_full_leaderboard(dest_dir=None, timeout: int = 120) -> dict:
    """Download and parse the entire public leaderboard CSV.

    Returns {"ok", "rows", "error"}; rows is a list of
    {"rank", "team_id", "name", "rating"} dicts, or [] on any download,
    zip, or parse failure. Unlike tools.top_player_tracker.fetch_leaderboard
    (--show, capped at page-size 200), -d downloads the full field so a
    mid-pack rating band is actually reachable. dest_dir must never be the
    episode-dump directory (see the module docstring for why); the default
    is a dedicated cache directory instead.
    """
    dest_dir = Path(dest_dir) if dest_dir else DEFAULT_LEADERBOARD_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    res = run_kaggle(
        ["competitions", "leaderboard", SIMULATION_SLUG, "-d", "-p", str(dest_dir)],
        timeout=timeout,
    )
    if not res["ok"]:
        return {"ok": False, "error": res["error"], "rows": []}
    zip_path = dest_dir / f"{SIMULATION_SLUG}.zip"
    if not zip_path.exists():
        return {"ok": False, "error": f"expected {zip_path} after download", "rows": []}
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not names:
                return {"ok": False, "error": f"no csv inside {zip_path}", "rows": []}
            text = zf.read(names[0]).decode("utf-8-sig", "replace")
    except (KeyError, OSError, zipfile.BadZipFile) as exc:
        return {"ok": False, "error": f"could not read leaderboard csv: {exc}", "rows": []}

    rows = []
    for raw in csv.DictReader(io.StringIO(text)):
        name = raw.get("TeamName")
        if not name:
            continue
        try:
            rank = int(raw.get("Rank"))
        except (TypeError, ValueError):
            rank = None
        try:
            rating = float(raw.get("Score"))
        except (TypeError, ValueError):
            rating = None
        rows.append({"rank": rank, "team_id": raw.get("TeamId"), "name": name, "rating": rating})
    return {"ok": True, "rows": rows, "error": None}


def band_teams(rows, low: float = DEFAULT_BAND_LOW, high: float = DEFAULT_BAND_HIGH) -> dict:
    """name -> rating for every leaderboard row with low <= rating <= high."""
    out = {}
    for r in rows:
        rating = r.get("rating")
        if rating is None:
            continue
        if low <= rating <= high:
            out[r["name"]] = rating
    return out


def opponents_from_replays(replays_dir=None, team_name: str = OUR_TEAM) -> set:
    """Opponent team names from our own harvested ladder replays.

    Skips self-play validation episodes and any replay where our own team
    cannot be confidently matched by name (our_index_from_replay returns
    None): a bracket sample should never guess which seat is ours.
    """
    replays_dir = Path(replays_dir) if replays_dir else DEFAULT_REPLAYS_DIR
    opponents = set()
    if not replays_dir.is_dir():
        return opponents
    for path in sorted(replays_dir.glob("*.json")):
        try:
            replay = load_replay(path)
        except (OSError, json.JSONDecodeError):
            continue
        if is_self_play(replay):
            continue
        names = team_names(replay)
        if names is None:
            continue
        our_seat = our_index_from_replay(replay, team_name)
        if our_seat is None:
            continue
        opponents.add(names[1 - our_seat])
    return opponents


def select_bracket(leaderboard_rows, replays_dir=None, team_name: str = OUR_TEAM,
                    low: float = DEFAULT_BAND_LOW, high: float = DEFAULT_BAND_HIGH) -> dict:
    """Union the two team sources into one bracket team list.

    Returns {"teams": [name, ...] sorted, "ratings": {name: rating or None},
    "band_count", "replay_opponent_count", "union_count"}. Pure over its
    inputs (leaderboard_rows already fetched, no I/O here besides the
    replay directory scan) so it is easy to unit test.
    """
    band = band_teams(leaderboard_rows, low, high)
    replay_opponents = opponents_from_replays(replays_dir, team_name)
    all_rows_by_name = {r["name"]: r["rating"] for r in leaderboard_rows if r.get("name")}

    teams = sorted(set(band) | replay_opponents)
    ratings = {name: (band.get(name) if name in band else all_rows_by_name.get(name)) for name in teams}
    return {
        "teams": teams,
        "ratings": ratings,
        "band_count": len(band),
        "replay_opponent_count": len(replay_opponents),
        "union_count": len(teams),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--leaderboard-dir", default=str(DEFAULT_LEADERBOARD_DIR),
                     help="directory to download the leaderboard zip into "
                          "(must not be the episode-dump directory)")
    ap.add_argument("--replays-dir", default=str(DEFAULT_REPLAYS_DIR),
                     help="directory of our own harvested ladder replays")
    ap.add_argument("--low", type=float, default=DEFAULT_BAND_LOW)
    ap.add_argument("--high", type=float, default=DEFAULT_BAND_HIGH)
    ap.add_argument("--out", default=None,
                     help="output JSON path (default data/training/bracket_teams.json)")
    args = ap.parse_args(argv)

    lb = fetch_full_leaderboard(args.leaderboard_dir)
    if not lb["ok"]:
        print(f"leaderboard download failed: {lb['error']}")
        return 1

    selection = select_bracket(lb["rows"], args.replays_dir, low=args.low, high=args.high)

    out_path = Path(args.out) if args.out else DEFAULT_OUT_DIR / "bracket_teams.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(selection, indent=2), encoding="utf-8")

    print(f"leaderboard rows: {len(lb['rows'])}")
    print(f"band [{args.low}, {args.high}]: {selection['band_count']} teams")
    print(f"replay opponents: {selection['replay_opponent_count']} teams")
    print(f"union: {selection['union_count']} teams")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
