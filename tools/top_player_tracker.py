"""Top-player leaderboard tracker (plan U3c, addendum v2).

Current expert data is either a stale bulk snapshot (data/episodes/*.zip) or
whoever we randomly played (ladder replays, U3a/U3b). This tool tracks the
LIVE top-N leaderboard teams, pulls their newest games specifically out of the
published episode dataset, and converts those games into training rows the
same shape as tools/replays_to_rows.py's output (source=top_player), so
tools/train_eval.py can up-weight them relative to gauntlet/ladder rows.
Refreshable weekly via --refresh.

FEASIBILITY NOTE (checked against real data, see the addendum doc): the
published episode dataset keys each seat by info.TeamNames (a team-name
string) plus rewards, never a submission id, and the Kaggle submissions API
only lists OUR OWN submissions, so other teams' per-game submission ids are
not retrievable through this API surface. Top-N teams are therefore mapped
straight off the leaderboard's teamName column and matched against a game's
info.TeamNames by exact string; a leaderboard team whose name never turns up
in any scanned episode is logged as unmapped in the report rather than
silently skipped or fuzzy-matched.

Dev tool only, never shipped. data/episodes/ and data/training/ stay
gitignored competition-derived data; the corpus CSV this writes is never
committed or redistributed.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import zipfile
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.expert_cohort import classify_family, seat_decklists, team_names  # noqa: E402
from ptcg_agent.features import FEATURE_NAMES  # noqa: E402
from tools.expert_census import build_signatures  # noqa: E402
from tools.replays_to_rows import rows_from_replay  # noqa: E402
from tools.scout import SIMULATION_SLUG, parse_cli_json, run_kaggle  # noqa: E402

DEFAULT_TOP_N = 20
DEFAULT_DAYS = 14
DEFAULT_EPISODES_DIR = _ROOT / "data" / "episodes"
DEFAULT_TRAIN_DIR = _ROOT / "data" / "training"
DEFAULT_REPORT_PATH = _ROOT / "analysis" / "top_player_report.md"
SOURCE = "top_player"
STALE_DAYS = 7
HERMES_REFRESH_CMD = (
    "python tools/top_player_tracker.py --refresh"
)


def fetch_leaderboard(top_n: int = DEFAULT_TOP_N) -> dict:
    """Top-N leaderboard teams (rank, team_id, name, rating) via the Kaggle CLI.

    Reuses tools.scout's fault tolerant Kaggle CLI wrapper: never raises,
    degrades to {"ok": False, "error": ...} on any CLI or parse failure.
    --page-size is set to top_n (capped at the CLI's 200 max) so one call
    returns exactly the rows needed without paging.
    """
    page_size = max(1, min(top_n, 200))
    res = run_kaggle([
        "competitions", "leaderboard", SIMULATION_SLUG,
        "--show", "--format", "json", "--page-size", str(page_size),
    ])
    if not res["ok"]:
        return {"ok": False, "error": res["error"], "teams": []}
    try:
        rows = parse_cli_json(res["stdout"])
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"could not parse leaderboard json: {exc}", "teams": []}
    teams = []
    for rank, row in enumerate(rows[:top_n], start=1):
        name = row.get("teamName") if isinstance(row, dict) else None
        if not name:
            continue
        try:
            rating = float(row.get("score"))
        except (TypeError, ValueError):
            rating = None
        teams.append({"rank": rank, "team_id": row.get("teamId"), "name": name, "rating": rating})
    return {"ok": True, "teams": teams}


def newest_dataset(episodes_dir=None) -> Path | None:
    """The most recently dated episode dataset .zip under episodes_dir, or None."""
    episodes_dir = Path(episodes_dir) if episodes_dir else DEFAULT_EPISODES_DIR
    zips = sorted(episodes_dir.glob("*.zip"))
    return zips[-1] if zips else None


def load_manifest(zf: zipfile.ZipFile) -> dict:
    """episode_id (str) -> create_time (datetime) from manifest.csv inside the zip.

    Returns {} when the zip carries no manifest (e.g. a minimal test fixture),
    so callers fall back to no recency filtering rather than raising.
    """
    try:
        raw = zf.read("manifest.csv").decode("utf-8", "replace")
    except KeyError:
        return {}
    out = {}
    for row in csv.DictReader(raw.splitlines()):
        eid = (row.get("episode_id") or "").strip()
        ct = (row.get("create_time") or "").strip()
        if not eid or not ct:
            continue
        try:
            out[eid] = datetime.fromisoformat(ct)
        except ValueError:
            continue
    return out


def recency_cutoff(manifest: dict, days: int):
    """The cutoff datetime (days before the manifest's own newest entry), or None.

    Anchored to the dataset's own newest create_time rather than wall-clock
    "now": the dataset is a static snapshot, so a system-clock skew between
    this machine and when the dataset was published must not make an
    otherwise fresh dataset look stale (or vice versa). None means "no
    manifest metadata available, do not filter by recency".
    """
    if not manifest:
        return None
    return max(manifest.values()) - timedelta(days=days)


def collect_top_player_rows(zip_path, team_set: set, days: int = DEFAULT_DAYS,
                             signatures=None) -> dict:
    """Scan a dataset zip for games featuring a top-N team, build training rows.

    For every episode newer than the recency cutoff (see recency_cutoff) whose
    info.TeamNames includes a name in team_set, extracts that seat's decision
    rows (tools.replays_to_rows.rows_from_replay, same schema as ladder rows)
    tagged source=top_player and team=<name>. Draws / undetermined games
    contribute no rows (rows_from_replay already drops them). A leaderboard
    name that never appears in any scanned episode's info.TeamNames is
    reported as unmapped. Never raises: a malformed member is skipped.
    """
    rows = []
    seen_names = set()
    per_team_games = Counter()
    per_team_wins = Counter()
    archetype_counts = Counter()
    newest_dt = None
    oldest_dt = None
    games_considered = 0
    games_matched = 0

    with zipfile.ZipFile(zip_path) as zf:
        manifest = load_manifest(zf)
        cutoff = recency_cutoff(manifest, days)
        for name in zf.namelist():
            if not name.endswith(".json") or name == "manifest.csv":
                continue
            eid = Path(name).stem
            create_time = manifest.get(eid)
            if cutoff is not None and (create_time is None or create_time < cutoff):
                continue
            try:
                replay = json.loads(zf.read(name))
            except (json.JSONDecodeError, OSError, KeyError):
                continue
            games_considered += 1
            names = team_names(replay)
            if names is None:
                continue
            seen_names.update(n for n in names if n)
            matched_seats = [seat for seat, n in enumerate(names) if n in team_set]
            if not matched_seats:
                continue
            game_rows = rows_from_replay(replay, eid)
            if not game_rows:
                continue
            games_matched += 1
            if create_time is not None:
                newest_dt = create_time if newest_dt is None else max(newest_dt, create_time)
                oldest_dt = create_time if oldest_dt is None else min(oldest_dt, create_time)
            decks = seat_decklists(replay) if signatures else None
            for seat in matched_seats:
                team = names[seat]
                seat_rows = [r for r in game_rows if r[1] == seat]
                if not seat_rows:
                    continue
                per_team_games[team] += 1
                if seat_rows[0][-1] == 1:
                    per_team_wins[team] += 1
                if decks is not None:
                    archetype_counts[classify_family(decks[seat], signatures)] += 1
                for r in seat_rows:
                    rows.append([*r, SOURCE, team])

    unmapped = sorted(n for n in team_set if n not in seen_names)
    return {
        "rows": rows,
        "unmapped": unmapped,
        "per_team_games": per_team_games,
        "per_team_wins": per_team_wins,
        "archetype_counts": archetype_counts,
        "newest_dt": newest_dt,
        "oldest_dt": oldest_dt,
        "games_considered": games_considered,
        "games_matched": games_matched,
    }


def dedupe_new_games(rows, existing_game_ids) -> list:
    """Drop every row whose game_id is already in existing_game_ids.

    Used on --refresh so re-scanning the dataset does not duplicate a game
    already appended to the corpus CSV in a prior run.
    """
    existing = set(existing_game_ids)
    return [r for r in rows if r[0] not in existing]


def read_existing_game_ids(path) -> set:
    path = Path(path)
    if not path.exists():
        return set()
    with open(path, newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if header is None or "game_id" not in header:
            return set()
        idx = header.index("game_id")
        return {row[idx] for row in reader}


def strip_overlap_from_ladder(ladder_csv_path, top_player_game_ids: set) -> int:
    """Drop rows from a ladder rows CSV whose game_id is also a top_player game.

    A game must not appear under both source=ladder and source=top_player;
    top_player wins the tie, so the ladder-sourced copy of that game is the
    one removed. Rewrites the file in place only when something changed;
    returns the number of rows removed.
    """
    path = Path(ladder_csv_path)
    if not top_player_game_ids or not path.exists():
        return 0
    with open(path, newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if header is None or "game_id" not in header:
            return 0
        gid_idx = header.index("game_id")
        rows = list(reader)
    keep = [r for r in rows if r[gid_idx] not in top_player_game_ids]
    removed = len(rows) - len(keep)
    if removed:
        with open(path, "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(header)
            writer.writerows(keep)
    return removed


def write_csv(rows, out_path, append: bool = False) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not (append and out_path.exists())
    mode = "a" if append and out_path.exists() else "w"
    with open(out_path, mode, newline="") as fh:
        writer = csv.writer(fh)
        if write_header:
            writer.writerow(["game_id", "seat", "turn", *FEATURE_NAMES, "label", "source", "team"])
        writer.writerows(rows)
    return out_path


def _fmt_dt(dt) -> str:
    return dt.date().isoformat() if dt else "n/a"


def _safe(text) -> str:
    """Down-convert text to what stdout can encode.

    Team handles carry non ASCII characters (CJK player handles, accents); a
    legacy Windows console defaults stdout to cp1252, which raises
    UnicodeEncodeError on those and aborts the print mid run. Swap any
    unencodable character for '?' first so the summary always prints, same
    fix tools/deck_harvest.py applies to its own report printing.
    """
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(enc, "replace").decode(enc)


def format_report(teams: list, result: dict, ladder_rows_removed: int, days: int,
                   ladder_ab_note: str | None = None, now=None) -> str:
    """Render analysis/top_player_report.md's content."""
    now = now or datetime.utcnow()
    per_games = result["per_team_games"]
    per_wins = result["per_team_wins"]
    lines = [
        "# Top-player leaderboard tracker",
        "",
        "Plan U3c (addendum v2). Tracks the live top-N leaderboard teams and pulls",
        "their newest games from the published episode dataset into a weighted",
        "training corpus (source=top_player).",
        "",
        f"Recency window: --days {days} (games older than the dataset's own newest",
        "game minus this window are dropped before matching).",
        "",
        "## Teams covered",
        "",
        "| rank | team | rating | corpus games | corpus win rate |",
        "|---|---|---|---|---|",
    ]
    for t in teams:
        name = t["name"]
        games = per_games.get(name, 0)
        wins = per_wins.get(name, 0)
        win_rate = f"{wins / games:.0%}" if games else "n/a"
        rating = f"{t['rating']:.1f}" if t["rating"] is not None else "n/a"
        lines.append(f"| {t['rank']} | {name} | {rating} | {games} | {win_rate} |")

    lines += [
        "",
        "## Coverage",
        "",
        f"- Games considered (post recency filter): {result['games_considered']}",
        f"- Games matched to a top-N team: {result['games_matched']}",
        f"- Training rows written: {len(result['rows'])}",
        f"- Date range of matched games: {_fmt_dt(result['oldest_dt'])} to "
        f"{_fmt_dt(result['newest_dt'])}",
    ]

    lines += ["", "## Archetype breakdown", ""]
    if result["archetype_counts"]:
        for fam, n in sorted(result["archetype_counts"].items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"- {fam}: {n}")
    else:
        lines.append("- (not available this run)")

    lines += ["", "## Unmapped team names", ""]
    if result["unmapped"]:
        for n in result["unmapped"]:
            lines.append(f"- {n} (no game in the scanned dataset names this team)")
    else:
        lines.append("- none")

    if ladder_rows_removed:
        lines += [
            "",
            "## Ladder overlap",
            "",
            f"- {ladder_rows_removed} ladder-sourced rows removed: same game_id also",
            "  covered under source=top_player, which wins the tie.",
        ]

    lines += ["", "## Staleness", ""]
    newest = result["newest_dt"]
    if newest is None:
        lines.append("- no matched games; staleness unknown")
    else:
        age_days = (now - newest).days
        lines.append(f"- newest matched game is {age_days} day(s) old (as of {now.date().isoformat()})")
        if age_days > STALE_DAYS:
            lines.append(
                f"- REFRESH WARNING: newest game is older than {STALE_DAYS} days; "
                "run with --refresh against a newer episode dataset."
            )

    if ladder_ab_note:
        lines += ["", "## Training weights", "", ladder_ab_note]

    lines += [
        "",
        "## Weekly refresh",
        "",
        "Intended to run every Monday 09:00 Taipei time via a Hermes scheduled",
        "task. Hermes registration is not reachable from this repo/tool, so run",
        "manually (or wire it into whatever scheduler is available) with:",
        "",
        f"    {HERMES_REFRESH_CMD}",
        "",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top-n", type=int, default=DEFAULT_TOP_N,
                     help="how many leaderboard teams to track (default 20)")
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS,
                     help="recency window in days (default 14)")
    ap.add_argument("--episodes-dir", default=str(DEFAULT_EPISODES_DIR),
                     help="directory holding episode dataset .zip files")
    ap.add_argument("--dataset", default=None,
                     help="explicit dataset .zip path (default: newest under --episodes-dir)")
    ap.add_argument("--out", default=None,
                     help="output corpus CSV path (default data/training/top_player_corpus_<date>.csv)")
    ap.add_argument("--report", default=str(DEFAULT_REPORT_PATH),
                     help="where to write the tracker report")
    ap.add_argument("--ladder-csv", default=None,
                     help="optional ladder_rows_*.csv; overlapping games are stripped from it "
                          "(top_player wins the source tie)")
    ap.add_argument("--refresh", action="store_true",
                     help="append new rows to an existing corpus CSV instead of overwriting it")
    args = ap.parse_args(argv)

    lb = fetch_leaderboard(args.top_n)
    if not lb["ok"]:
        print(f"leaderboard fetch failed: {lb['error']}")
        return 1
    teams = lb["teams"]
    team_set = {t["name"] for t in teams}

    dataset_path = Path(args.dataset) if args.dataset else newest_dataset(args.episodes_dir)
    if dataset_path is None or not Path(dataset_path).exists():
        print(f"no episode dataset found under {args.episodes_dir}")
        return 1

    try:
        signatures = build_signatures()
    except Exception:  # noqa: BLE001 - archetype breakdown is best-effort, never fatal
        signatures = None

    result = collect_top_player_rows(dataset_path, team_set, days=args.days, signatures=signatures)

    out_path = Path(args.out) if args.out else DEFAULT_TRAIN_DIR / f"top_player_corpus_{datetime.utcnow():%Y%m%d}.csv"
    rows = result["rows"]
    if args.refresh:
        existing_ids = read_existing_game_ids(out_path)
        rows = dedupe_new_games(rows, existing_ids)
        write_csv(rows, out_path, append=True)
    else:
        write_csv(rows, out_path, append=False)

    ladder_removed = 0
    if args.ladder_csv:
        ladder_removed = strip_overlap_from_ladder(args.ladder_csv, {r[0] for r in result["rows"]})

    report = format_report(teams, result, ladder_removed, args.days)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(report, encoding="utf-8")

    print(_safe(f"wrote {len(rows)} rows to {out_path}"))
    print(_safe(
        f"matched {result['games_matched']}/{result['games_considered']} games considered "
        f"to {len(team_set) - len(result['unmapped'])}/{len(team_set)} mapped teams"
    ))
    if result["unmapped"]:
        print(_safe(f"  unmapped: {', '.join(result['unmapped'])}"))
    if ladder_removed:
        print(_safe(f"  stripped {ladder_removed} overlapping rows from {args.ladder_csv}"))
    print(f"wrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
