"""Extract outcome-labeled per-option training rows from the raw Kaggle episode
dumps (data/episodes/*.zip) for real top-team games.

The elite-weighted core is data/derived/top50_harvest.json (tools/top50_harvest.py's
harvest of the top-50 leaderboard teams' recent games): this tool reads its episode
ids, locates each one inside data/episodes/*.zip (each dump's members are named
"<episode_id>.json", the full Kaggle replay JSON, not just the harvest's cached
summary), and runs tools.replays_to_rows.outcome_rows_from_replay over each one to
build the chosen-option outcome model dataset (analysis/ranker_outcome_model.md).

--widen reuses tools.top50_harvest.scan_all_dumps (the same head-only pass-1 scan
top50_harvest.py already validated) with the harvest's own 50 team names but no
per-team games-per-team cap, so widening stays inside the same elite cohort the
core was drawn from rather than pulling in arbitrary ladder noise.

Zip member lookup is a single pass over every dump's namelist() (cheap: it reads
the central directory only, not member contents) so this stays fast even though
the dumps are ~750MB each; only the wanted members are actually decompressed
(zf.read), and a duplicate episode id (an episode appearing in more than one dump,
which should not happen but is not assumed) keeps the first dump found.

Dev tool only; never shipped. Reads data/episodes/*.zip (gitignored competition
data) but writes only aggregated per-option feature rows (data/training/, also
gitignored), the same redistribution posture as tools/replays_to_rows.py.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import zipfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools import replays_to_rows  # noqa: E402
from tools.top_player_tracker import DEFAULT_EPISODES_DIR, NON_DUMP_ZIP_NAMES  # noqa: E402

DEFAULT_HARVEST = _ROOT / "data" / "derived" / "top50_harvest.json"
DEFAULT_OUT_DIR = _ROOT / "data" / "training"


def harvest_episode_ids(harvest_path=DEFAULT_HARVEST) -> list:
    """Every unique episode_id across every team's games in a top50_harvest.json."""
    with open(harvest_path, encoding="utf-8") as fh:
        harvest = json.load(fh)
    ids = []
    seen = set()
    for team in harvest.get("teams", []) or []:
        for g in team.get("games", []) or []:
            eid = g.get("episode_id")
            if eid and eid not in seen:
                seen.add(eid)
                ids.append(eid)
    return ids


def harvest_team_names(harvest_path=DEFAULT_HARVEST) -> set:
    with open(harvest_path, encoding="utf-8") as fh:
        harvest = json.load(fh)
    return {team.get("team") for team in harvest.get("teams", []) or [] if team.get("team")}


def widen_episode_ids(harvest_path=DEFAULT_HARVEST, episodes_dir=None) -> list:
    """Every episode id across all dumps naming one of the harvest's 50 teams,
    with no per-team cap (unlike top50_harvest.json's games-per-team=20 window).

    Reuses tools.top50_harvest.scan_all_dumps's already-validated pass-1 scan.
    """
    from tools.top50_harvest import all_dumps, scan_all_dumps

    team_names = harvest_team_names(harvest_path)
    dumps = all_dumps(episodes_dir)
    candidates, _total = scan_all_dumps(dumps, team_names)
    ids = []
    seen = set()
    for games in candidates.values():
        for g in games:
            eid = g.get("episode_id")
            if eid and eid not in seen:
                seen.add(eid)
                ids.append(str(eid))
    return ids


def zip_index(episode_ids, episodes_dir=None) -> dict:
    """{episode_id: zip_path} for every wanted id found in any dump.

    One namelist() pass per dump (cheap; does not decompress members), stopping
    early once every wanted id has been located.
    """
    episodes_dir = Path(episodes_dir) if episodes_dir else DEFAULT_EPISODES_DIR
    wanted = set(episode_ids)
    found = {}
    for zpath in sorted(episodes_dir.glob("*.zip")):
        if not wanted:
            break
        if zpath.name in NON_DUMP_ZIP_NAMES:
            continue
        with zipfile.ZipFile(zpath) as zf:
            for name in zf.namelist():
                eid = name[:-5] if name.endswith(".json") else name
                if eid in wanted:
                    found[eid] = zpath
                    wanted.discard(eid)
    return found


def extract_rows(episode_ids, episodes_dir=None):
    """(rows, missing_episode_ids) for outcome_rows_from_replay over every
    episode id found in the dumps. A malformed or unreadable member is
    counted as missing rather than aborting the batch.
    """
    index = zip_index(episode_ids, episodes_dir)
    rows = []
    missing = []
    zf_cache = {}
    try:
        for eid in episode_ids:
            zpath = index.get(eid)
            if zpath is None:
                missing.append(eid)
                continue
            zf = zf_cache.get(zpath)
            if zf is None:
                zf = zipfile.ZipFile(zpath)
                zf_cache[zpath] = zf
            try:
                replay = json.loads(zf.read(f"{eid}.json"))
            except (KeyError, ValueError, OSError):
                missing.append(eid)
                continue
            try:
                rows.extend(replays_to_rows.outcome_rows_from_replay(replay, eid))
            except (AttributeError, TypeError, KeyError):
                missing.append(eid)
                continue
    finally:
        for zf in zf_cache.values():
            zf.close()
    return rows, missing


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--harvest", default=str(DEFAULT_HARVEST))
    ap.add_argument("--episodes-dir", default=str(DEFAULT_EPISODES_DIR))
    ap.add_argument("--widen", action="store_true",
                     help="also pull every episode across all dumps naming one of "
                          "the harvest's 50 teams, uncapped per team (not just the "
                          "harvest's games-per-team=20 window)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    core_ids = harvest_episode_ids(args.harvest)
    episode_ids = list(core_ids)
    if args.widen:
        seen = set(episode_ids)
        for eid in widen_episode_ids(args.harvest, args.episodes_dir):
            if eid not in seen:
                seen.add(eid)
                episode_ids.append(eid)

    rows, missing = extract_rows(episode_ids, args.episodes_dir)
    tag = "top50_widened" if args.widen else "top50"
    out_path = (Path(args.out) if args.out
                else DEFAULT_OUT_DIR / f"outcome_rows_{tag}_{int(time.time())}.csv")
    replays_to_rows.write_outcome_csv(rows, out_path, source=tag)
    print(f"episodes requested: {len(episode_ids)} (core {len(core_ids)}, "
          f"widened {len(episode_ids) - len(core_ids)})")
    print(f"episodes found: {len(episode_ids) - len(missing)}  missing: {len(missing)}")
    print(f"wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
