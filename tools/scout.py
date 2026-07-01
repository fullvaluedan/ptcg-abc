"""Scout: download our episodes and rank our losses.

Two halves. The download half is a thin, fault tolerant wrapper over the Kaggle
CLI (single token auth at ~/.kaggle/access_token); every call returns a result
dict and never raises, so a missing binary or an unauthorized episode degrades to
a clear message instead of aborting a batch. The analysis half is fully offline:
it loads saved replay JSON and runs the loss classifier to produce a ranked
bucket report. Downloaded replays are competition data and stay gitignored under
replays/; they are never redistributed.

The CLI surface this wraps (confirmed against the kaggle CLI):
  kaggle competitions submissions <slug>          list our submissions + refs
  kaggle competitions episodes <submission_id>    list episode (game) ids for a ref
  kaggle competitions replay <episode_id> -p DIR  download one replay JSON to DIR
A replay file lands as episode-<id>-replay.json. Each replay carries an
info.TeamNames pair, so the seat we played is detected per game rather than
assumed: in a public episode we may sit in either seat.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.loss_classifier import (  # noqa: E402
    SEARCH_ACTIVE_S,
    aggregate_search_activity,
    classify_batch,
    parse_replay,
    search_activity,
)

REPLAYS_DIR = _ROOT / "replays"
SIMULATION_SLUG = "pokemon-tcg-ai-battle"
# Our team name as it appears in a replay's info.TeamNames. Used to detect which
# seat we played in each downloaded episode.
OUR_TEAM = "Dan Arreola"


def kaggle_base() -> list:
    """Resolve how to invoke the Kaggle CLI in this environment.

    Prefers a real `kaggle` on PATH; otherwise falls back to running it as a
    module under the current interpreter (`python -m kaggle`), which is reliable
    inside a venv where the console script lives in Scripts/ rather than on PATH.
    The autoloop runs from .venv/Scripts/python.exe, so this fallback is what
    lets unattended scout pulls work without kaggle being on the system PATH.
    """
    found = shutil.which("kaggle")
    if found:
        return [found]
    return [sys.executable, "-m", "kaggle"]


def run_kaggle(args, timeout: int = 120) -> dict:
    """Run a kaggle CLI subcommand, capturing output without ever raising.

    Returns {"ok", "stdout", "stderr", "returncode", "error"}. ok is False when
    the binary is missing, the call times out, or it exits nonzero (unauthorized,
    missing episode), with a human readable error string.
    """
    cmd = [*kaggle_base(), *[str(a) for a in args]]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except FileNotFoundError:
        return {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "returncode": None,
            "error": "kaggle CLI not found on PATH; install it to download episodes",
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "returncode": None,
            "error": f"kaggle {' '.join(str(a) for a in args)} timed out after {timeout}s",
        }
    ok = proc.returncode == 0
    return {
        "ok": ok,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "returncode": proc.returncode,
        "error": None if ok else (proc.stderr.strip() or f"kaggle exited {proc.returncode}"),
    }


def parse_cli_json(text: str):
    """Parse the leading JSON value out of Kaggle CLI stdout.

    The CLI prints valid JSON and then appends a human readable usage tip on a
    trailing line, so plain json.loads raises "Extra data". raw_decode reads the
    first JSON value and ignores anything after it.
    """
    stripped = (text or "").lstrip()
    if not stripped:
        return []
    value, _ = json.JSONDecoder().raw_decode(stripped)
    return value


def list_submissions() -> dict:
    """List our submissions (ref, status, score) via the Kaggle CLI."""
    res = run_kaggle(["competitions", "submissions", "-c", SIMULATION_SLUG, "--format", "json"])
    if not res["ok"]:
        return {"ok": False, "error": res["error"], "submissions": []}
    try:
        subs = parse_cli_json(res["stdout"])
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"could not parse submissions json: {exc}", "submissions": []}
    return {"ok": True, "submissions": subs}


def list_episodes(submission_id) -> dict:
    """List the episode (game) ids that a submission ref has played.

    Degrades gracefully: any CLI or parse failure returns {"ok": False, ...}
    with an empty list so a caller can skip a ref and continue.
    """
    res = run_kaggle(["competitions", "episodes", str(submission_id), "--format", "json"])
    if not res["ok"]:
        return {"ok": False, "submission": submission_id, "error": res["error"], "episodes": []}
    try:
        eps = parse_cli_json(res["stdout"])
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "submission": submission_id,
            "error": f"could not parse episodes json: {exc}",
            "episodes": [],
        }
    return {"ok": True, "submission": submission_id, "episodes": eps}


def fetch_episode(episode_id, dest_dir: Path | None = None) -> dict:
    """Download a single episode replay JSON via the Kaggle CLI.

    Uses `kaggle competitions replay <id> -p DIR`, which writes
    episode-<id>-replay.json into DIR. Degrades gracefully: on any CLI failure
    returns {"ok": False, "error": ...} rather than raising, so a batch can skip
    a bad id and continue.
    """
    dest_dir = Path(dest_dir) if dest_dir else REPLAYS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    res = run_kaggle(["competitions", "replay", str(episode_id), "-p", str(dest_dir), "-q"])
    if not res["ok"]:
        return {"ok": False, "episode": episode_id, "error": res["error"]}
    path = dest_dir / f"episode-{episode_id}-replay.json"
    return {"ok": True, "episode": episode_id, "path": str(path), "dir": str(dest_dir)}


def pull_submission(submission_id, dest_dir: Path | None = None) -> dict:
    """List a submission's episodes and download every replay we do not have.

    Fault tolerant throughout: a failed listing returns early with the error, a
    failed single download is recorded and the rest continue.
    """
    dest_dir = Path(dest_dir) if dest_dir else REPLAYS_DIR
    listing = list_episodes(submission_id)
    if not listing["ok"]:
        return {"ok": False, "submission": submission_id, "error": listing["error"], "fetched": []}
    fetched, failed, skipped = [], [], []
    for ep in listing["episodes"]:
        ep_id = ep.get("id") if isinstance(ep, dict) else ep
        if ep_id is None:
            continue
        target = dest_dir / f"episode-{ep_id}-replay.json"
        if target.exists():
            skipped.append(ep_id)
            continue
        res = fetch_episode(ep_id, dest_dir=dest_dir)
        (fetched if res["ok"] else failed).append(ep_id if res["ok"] else {"episode": ep_id, "error": res["error"]})
    return {
        "ok": True,
        "submission": submission_id,
        "fetched": fetched,
        "skipped": skipped,
        "failed": failed,
    }


def is_self_play(replay) -> bool:
    """True when both seats are the same team (a validation episode).

    Kaggle runs a submission against itself to validate it before laddering.
    Those games are not ladder opponents, so they are noise for loss analysis.
    """
    info = replay.get("info") if isinstance(replay, dict) else None
    names = (info or {}).get("TeamNames") or []
    return len(names) == 2 and names[0] == names[1]


def our_index_from_replay(replay, team_name: str = OUR_TEAM):
    """Which seat we played, read from info.TeamNames; None if we are not in it.

    Matches case insensitively so a small display-name variation still resolves.
    """
    info = replay.get("info") if isinstance(replay, dict) else None
    names = (info or {}).get("TeamNames") or []
    target = team_name.strip().lower()
    for i, name in enumerate(names):
        if isinstance(name, str) and name.strip().lower() == target:
            return i
    return None


def load_replay(path) -> dict:
    """Load a replay JSON file from disk."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def digest_dir(replay_dir, team_name: str = OUR_TEAM, our_index: int = 0,
               skip_self_play: bool = True) -> list:
    """Parse every *.json replay in a directory into digests.

    Our seat is detected per replay from info.TeamNames; replays that do not name
    our team (synthetic or old files) fall back to the our_index argument.
    Self-play validation episodes are skipped by default since they are not
    ladder opponents.
    """
    digests = []
    for path in sorted(Path(replay_dir).glob("*.json")):
        try:
            replay = load_replay(path)
        except (OSError, json.JSONDecodeError):
            continue
        if skip_self_play and is_self_play(replay):
            continue
        seat = our_index_from_replay(replay, team_name)
        digests.append(parse_replay(replay, our_index=seat if seat is not None else our_index))
    return digests


def report(replay_dir, team_name: str = OUR_TEAM, our_index: int = 0,
           skip_self_play: bool = True) -> dict:
    """Build a ranked loss bucket report from saved ladder replays in a directory."""
    digests = digest_dir(replay_dir, team_name=team_name, our_index=our_index,
                         skip_self_play=skip_self_play)
    return classify_batch(digests)


def search_activity_dir(replay_dir, team_name: str = OUR_TEAM, our_index: int = 0,
                        skip_self_play: bool = True) -> dict:
    """Verify channel: did determinized search actually run over these replays.

    Parses every replay in a directory (our seat detected per game) and rolls up
    the per-decision overage-bank drawdown on our searchable moves. The aggregate
    verdict answers, from real ladder replays, whether an on-ladder search build
    recovered the forward model or stayed inert on the heuristic.
    """
    digests = digest_dir(replay_dir, team_name=team_name, our_index=our_index,
                         skip_self_play=skip_self_play)
    agg = aggregate_search_activity(digests)
    agg["per_game"] = [search_activity(dg) for dg in digests]
    return agg


def _print_search_activity(agg: dict, replay_dir) -> None:
    print(f"search activity over {agg['games']} replays in {replay_dir}")
    print(f"  games with a searchable decision: {agg['games_with_searchable']}")
    print(f"  games where search ran (draw >= {SEARCH_ACTIVE_S:.2f}s): {agg['games_search_ran']}")
    print(f"  total searchable decisions: {agg['total_searchable_decisions']}")
    print(f"  max per-decision bank draw: {agg['max_draw']:.3f}s")
    print(f"  verdict: {agg['verdict']}")


def _print_report(rep: dict, replay_dir) -> None:
    print(f"loss scout over {rep['games']} replays in {replay_dir}")
    print(f"  W/D/L: {rep['wins']}/{rep['draws']}/{rep['losses']}")
    if rep["losses"] == 0:
        print("  no losses to classify")
        return
    print("  loss buckets (most costly first):")
    for bucket, count in rep["ranked"]:
        if count:
            print(f"    {bucket}: {count}")
    if rep["top_bucket"]:
        print(f"  biggest leak: {rep['top_bucket']}")


def main():
    ap = argparse.ArgumentParser(description="scout our episodes and rank losses")
    sub = ap.add_subparsers(dest="cmd", required=True)

    rp = sub.add_parser("report", help="classify saved replays in a directory")
    rp.add_argument("dir", nargs="?", default=str(REPLAYS_DIR))
    rp.add_argument("--team", default=OUR_TEAM, help="our team name in info.TeamNames")
    rp.add_argument("--our-index", type=int, default=0, help="fallback seat when team is absent")

    sa = sub.add_parser("search-activity",
                        help="verify channel: did search actually run in these replays")
    sa.add_argument("dir", nargs="?", default=str(REPLAYS_DIR))
    sa.add_argument("--team", default=OUR_TEAM, help="our team name in info.TeamNames")
    sa.add_argument("--our-index", type=int, default=0, help="fallback seat when team is absent")

    sp = sub.add_parser("subs", help="list our submissions (ref, status, score)")

    ep = sub.add_parser("episodes", help="list episode ids for a submission ref")
    ep.add_argument("submission")

    fp = sub.add_parser("fetch", help="download one episode replay (needs Kaggle auth)")
    fp.add_argument("episode")
    fp.add_argument("-p", "--dir", default=str(REPLAYS_DIR))

    pp = sub.add_parser("pull", help="download every replay for a submission, then report")
    pp.add_argument("submission")
    pp.add_argument("-p", "--dir", default=str(REPLAYS_DIR))
    pp.add_argument("--team", default=OUR_TEAM)

    args = ap.parse_args()
    if args.cmd == "report":
        rep = report(args.dir, team_name=args.team, our_index=args.our_index)
        _print_report(rep, args.dir)
    elif args.cmd == "search-activity":
        agg = search_activity_dir(args.dir, team_name=args.team, our_index=args.our_index)
        _print_search_activity(agg, args.dir)
    elif args.cmd == "subs":
        res = list_submissions()
        if not res["ok"]:
            print(f"list submissions failed: {res['error']}")
            sys.exit(1)
        for s in res["submissions"]:
            print(f"  {s.get('ref')}  {s.get('status')}  score={s.get('publicScore')}  {s.get('description', '')[:60]}")
    elif args.cmd == "episodes":
        res = list_episodes(args.submission)
        if not res["ok"]:
            print(f"list episodes failed: {res['error']}")
            sys.exit(1)
        for e in res["episodes"]:
            print(f"  {e.get('id')}  {e.get('state')}  {e.get('type')}")
    elif args.cmd == "fetch":
        res = fetch_episode(args.episode, dest_dir=args.dir)
        if res["ok"]:
            print(f"episode {res['episode']} downloaded to {res['path']}")
        else:
            print(f"fetch failed: {res['error']}")
            sys.exit(1)
    elif args.cmd == "pull":
        res = pull_submission(args.submission, dest_dir=args.dir)
        if not res["ok"]:
            print(f"pull failed: {res['error']}")
            sys.exit(1)
        print(f"pulled submission {res['submission']}: {len(res['fetched'])} new, "
              f"{len(res['skipped'])} already had, {len(res['failed'])} failed")
        rep = report(args.dir, team_name=args.team)
        _print_report(rep, args.dir)


if __name__ == "__main__":
    main()
