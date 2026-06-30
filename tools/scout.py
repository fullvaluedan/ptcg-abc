"""Scout: download our episodes and rank our losses.

Two halves. The download half is a thin, fault tolerant wrapper over the Kaggle
CLI (single token auth at ~/.kaggle/access_token); every call returns a result
dict and never raises, so a missing binary or an unauthorized episode degrades to
a clear message instead of aborting a batch. The analysis half is fully offline:
it loads saved replay JSON and runs the loss classifier to produce a ranked
bucket report. Downloaded replays are competition data and stay gitignored under
replays/; they are never redistributed.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.loss_classifier import classify_batch, parse_replay  # noqa: E402

REPLAYS_DIR = _ROOT / "replays"
SIMULATION_SLUG = "pokemon-tcg-ai-battle"


def run_kaggle(args, timeout: int = 120) -> dict:
    """Run a kaggle CLI subcommand, capturing output without ever raising.

    Returns {"ok", "stdout", "stderr", "returncode", "error"}. ok is False when
    the binary is missing, the call times out, or it exits nonzero (unauthorized,
    missing episode), with a human readable error string.
    """
    cmd = ["kaggle", *[str(a) for a in args]]
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


def fetch_episode(episode_id, dest_dir: Path | None = None) -> dict:
    """Download a single episode replay JSON via the Kaggle CLI.

    Degrades gracefully: on any CLI failure returns {"ok": False, "error": ...}
    rather than raising, so a batch can skip a bad id and continue.
    """
    dest_dir = Path(dest_dir) if dest_dir else REPLAYS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    res = run_kaggle(
        ["competitions", "episodes", "-c", SIMULATION_SLUG, "-e", str(episode_id), "-p", str(dest_dir)]
    )
    if not res["ok"]:
        return {"ok": False, "episode": episode_id, "error": res["error"]}
    return {"ok": True, "episode": episode_id, "dir": str(dest_dir)}


def load_replay(path) -> dict:
    """Load a replay JSON file from disk."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def digest_dir(replay_dir, our_index: int = 0) -> list:
    """Parse every *.json replay in a directory into digests."""
    digests = []
    for path in sorted(Path(replay_dir).glob("*.json")):
        try:
            replay = load_replay(path)
        except (OSError, json.JSONDecodeError):
            continue
        digests.append(parse_replay(replay, our_index=our_index))
    return digests


def report(replay_dir, our_index: int = 0) -> dict:
    """Build a ranked loss bucket report from saved replays in a directory."""
    digests = digest_dir(replay_dir, our_index=our_index)
    return classify_batch(digests)


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
    rp.add_argument("--our-index", type=int, default=0)

    fp = sub.add_parser("fetch", help="download an episode replay (needs Kaggle auth)")
    fp.add_argument("episode")
    fp.add_argument("-p", "--dir", default=str(REPLAYS_DIR))

    args = ap.parse_args()
    if args.cmd == "report":
        rep = report(args.dir, our_index=args.our_index)
        _print_report(rep, args.dir)
    elif args.cmd == "fetch":
        res = fetch_episode(args.episode, dest_dir=args.dir)
        if res["ok"]:
            print(f"episode {res['episode']} downloaded to {res['dir']}")
        else:
            print(f"fetch failed: {res['error']}")
            sys.exit(1)


if __name__ == "__main__":
    main()
