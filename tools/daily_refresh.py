"""Daily dump refresh (LOOP_BRIEF Track L, unit U80).

Kaggle publishes a new episode dump every day (dataset slugs
kaggle/pokemon-tcg-ai-battle-episodes-YYYY-MM-DD) plus a tiny -index dataset
whose manifest.csv names every published slug so far. This tool chains four
already-existing pieces into one refresh step:

  1. ensure_newest_dataset: download the newest published dump into
     data/episodes/ if we do not already have it (a ~750MB download; skipped
     when the file is already on disk, so a re-run costs almost nothing).
  2. tools.top_player_tracker re-run against that dataset (--refresh
     semantics: appends only new games to the win/loss corpora).
  3. tools.harvest_replays: pull our own newest ladder replays.
  4. tools.loop_state: recompute the current king's real-replay loss-bucket
     distribution from those replays and write it into state/current.md.

Every step is best effort and never raises: a failure in one (no network, no
Kaggle auth, empty dataset) is recorded in the returned result dict and the
remaining steps still run against whatever is already on disk, so a partial
refresh is never worse than skipping the whole thing. Dev tool only, never
shipped. data/episodes/ and data/replays/ stay gitignored competition data.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools import harvest_replays  # noqa: E402
from tools import loop_state  # noqa: E402
from tools import top_player_tracker as tpt  # noqa: E402
from tools.scout import run_kaggle  # noqa: E402

INDEX_SLUG = "kaggle/pokemon-tcg-ai-battle-episodes-index"
DEFAULT_EPISODES_DIR = _ROOT / "data" / "episodes"
DOWNLOAD_TIMEOUT_S = 1800


def fetch_index_manifest(dest_dir=None) -> dict:
    """Download the tiny -index dataset and parse its manifest.csv.

    Returns {"ok": True, "rows": [...]} sorted oldest to newest by date, or
    {"ok": False, "error": ..., "rows": []} on any download or parse failure.
    The index dataset is under 1KB and safe to re-fetch on every refresh; its
    manifest names every published daily dump slug, so the last row is the
    newest dump without paging the (rate limited) datasets-list API.
    """
    dest_dir = Path(dest_dir) if dest_dir else DEFAULT_EPISODES_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    res = run_kaggle(
        ["datasets", "download", "-d", INDEX_SLUG, "-p", str(dest_dir), "--force"],
        timeout=60,
    )
    if not res["ok"]:
        return {"ok": False, "error": res["error"], "rows": []}
    zip_path = dest_dir / "pokemon-tcg-ai-battle-episodes-index.zip"
    if not zip_path.exists():
        return {"ok": False, "error": f"expected {zip_path} after download", "rows": []}
    try:
        with zipfile.ZipFile(zip_path) as zf:
            text = zf.read("manifest.csv").decode("utf-8", "replace")
    except (KeyError, OSError, zipfile.BadZipFile) as exc:
        return {"ok": False, "error": f"could not read index manifest: {exc}", "rows": []}
    rows = list(csv.DictReader(io.StringIO(text)))
    rows.sort(key=lambda r: r.get("date", ""))
    return {"ok": True, "rows": rows}


def newest_slug(rows) -> str | None:
    """The daily_dataset_slug of the last (newest-dated) manifest row, or None."""
    return rows[-1]["daily_dataset_slug"] if rows else None


def _is_valid_zip(path: Path) -> bool:
    try:
        return zipfile.is_zipfile(path)
    except OSError:
        return False


def ensure_newest_dataset(episodes_dir=None, manifest_rows=None) -> dict:
    """Download the newest published daily dump if it is not already on disk.

    Skips the download when data/episodes/<slug>.zip already exists AND is a
    valid zip (a leftover partial file from an interrupted prior download is
    deleted and re-fetched rather than silently trusted). manifest_rows lets
    a caller reuse an already-fetched index manifest instead of downloading it
    twice in one refresh call. Returns {"ok", "slug", "path", "downloaded",
    "error"}; path is a Path on success, None otherwise.
    """
    episodes_dir = Path(episodes_dir) if episodes_dir else DEFAULT_EPISODES_DIR
    if manifest_rows is None:
        idx = fetch_index_manifest(episodes_dir)
        if not idx["ok"]:
            return {"ok": False, "error": idx["error"], "slug": None, "path": None, "downloaded": False}
        manifest_rows = idx["rows"]
    slug = newest_slug(manifest_rows)
    if slug is None:
        return {"ok": False, "error": "index manifest named no dataset", "slug": None,
                 "path": None, "downloaded": False}

    target = episodes_dir / f"{slug}.zip"
    if target.exists():
        if _is_valid_zip(target):
            return {"ok": True, "slug": slug, "path": target, "downloaded": False, "error": None}
        target.unlink()  # corrupt/partial leftover; re-download below

    dataset_ref = f"kaggle/{slug}"
    res = run_kaggle(
        ["datasets", "download", "-d", dataset_ref, "-p", str(episodes_dir)],
        timeout=DOWNLOAD_TIMEOUT_S,
    )
    if not res["ok"]:
        return {"ok": False, "error": res["error"], "slug": slug, "path": None, "downloaded": False}
    if not target.exists() or not _is_valid_zip(target):
        return {"ok": False, "error": f"download reported success but {target} is missing or not a valid zip",
                 "slug": slug, "path": None, "downloaded": False}
    return {"ok": True, "slug": slug, "path": target, "downloaded": True, "error": None}


def refresh_top_player_corpus(dataset_path, top_n=tpt.DEFAULT_TOP_N, days=tpt.DEFAULT_DAYS) -> dict:
    """Re-run the top-player tracker against dataset_path, appending only new rows.

    Mirrors tools/top_player_tracker.py's own --refresh CLI path (dedupe by
    game_id, append, rewrite the report), just called in-process instead of a
    subprocess so this tool can chain it with the other refresh steps.
    """
    lb = tpt.fetch_leaderboard(top_n)
    if not lb["ok"]:
        return {"ok": False, "error": lb["error"]}
    teams = lb["teams"]
    team_set = {t["name"] for t in teams}

    try:
        signatures = tpt.build_signatures()
    except Exception:  # noqa: BLE001 - archetype breakdown is best-effort, never fatal
        signatures = None

    win_result = tpt.collect_top_player_rows(dataset_path, team_set, days=days, signatures=signatures)
    loss_result = tpt.collect_top_player_loss_rows(dataset_path, team_set, days=days)

    stamp = f"{datetime.utcnow():%Y%m%d}"
    out_path = tpt.DEFAULT_TRAIN_DIR / f"top_player_corpus_{stamp}.csv"
    loss_out_path = tpt.DEFAULT_TRAIN_DIR / f"top_player_loss_corpus_{stamp}.csv"

    existing_ids = tpt.read_existing_game_ids(out_path)
    new_rows = tpt.dedupe_new_games(win_result["rows"], existing_ids)
    tpt.write_csv(new_rows, out_path, append=True)

    existing_loss_ids = tpt.read_existing_game_ids(loss_out_path)
    new_loss_rows = tpt.dedupe_new_games(loss_result["rows"], existing_loss_ids)
    tpt.write_csv(new_loss_rows, loss_out_path, append=True, extra_columns=["loss_bucket", "opponent"])

    report = tpt.format_report(teams, win_result, 0, days, loss_result=loss_result)
    tpt.DEFAULT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tpt.DEFAULT_REPORT_PATH.write_text(report, encoding="utf-8")

    return {
        "ok": True,
        "new_win_rows": len(new_rows),
        "new_loss_rows": len(new_loss_rows),
        "games_matched": win_result["games_matched"],
        "games_considered": win_result["games_considered"],
        "unmapped": win_result["unmapped"],
    }


def refresh_loss_distribution(ladder_dirs=None, live_refs=None) -> dict:
    """Recompute the loss-bucket distribution: per-build primary, pool-wide secondary.

    live_refs (a list of submission refs, U107b) filters the PRIMARY "top loss
    bucket" to just the live shipped builds instead of every build ever
    submitted. Pass it explicitly (as the ref_filter tools.loop_state.classify_
    dirs_per_build already understands), or leave it None to read state/current.
    md's own live_refs array -- seeded with the default two live refs via the
    canonical locked writer (tools.loop_state.ensure_live_refs) the first time
    this runs after live_refs has never been recorded at all. The pool-wide
    distribution over every dir is always computed too and kept under the
    "pool_wide" key as a secondary line, so the two views stay comparable.

    Falls back to the pool-wide distribution AS the primary -- loudly marked via
    "targeting_mode": "pool_fallback" and a human-readable "fallback_reason" --
    when live_refs is empty/absent or the manifest has zero matched episodes for
    every ref in it. A silent fallback here would render identically to real
    per-build targeting and mask a lost-update regression back to the audited-
    broken mixed-pool behavior; loop_state._render_current_md surfaces this field
    loudly whenever it is set.

    The read-modify-write against state/current.md is serialized through
    tools.loop_state.update_current (a locked, atomic read-modify-write), closing
    the standing lost-update race against the autoloop's own bash-driven refresh
    writing the same file concurrently.
    """
    dirs = ladder_dirs if ladder_dirs is not None else ["data/replays"]
    pool = loop_state.loss_distribution_from_dirs(dirs)

    def _mutate(data):
        nonlocal live_refs
        if live_refs is None:
            loop_state.ensure_live_refs(data)
            live_refs = data.get("live_refs") or []

        fallback_reason = None
        if not live_refs:
            fallback_reason = "no live_refs recorded in state/current.md"
            primary = dict(pool)
        else:
            filtered = loop_state.loss_distribution_from_dirs(dirs, ref_filter=live_refs)
            if filtered.get("games", 0) == 0:
                fallback_reason = (
                    f"live_refs {list(live_refs)} matched zero episodes in the "
                    "episode-to-ref manifest (missing coverage); falling back to "
                    "the pool-wide distribution"
                )
                primary = dict(pool)
            else:
                primary = filtered

        primary["targeting_mode"] = "pool_fallback" if fallback_reason else "per_build"
        primary["fallback_reason"] = fallback_reason
        primary["pool_wide"] = {
            "games": pool.get("games", 0),
            "wins": pool.get("wins", 0),
            "draws": pool.get("draws", 0),
            "losses": pool.get("losses", 0),
            "buckets": pool.get("buckets", {}),
            "top_bucket": pool.get("top_bucket"),
            "sample_size": pool.get("sample_size", 0),
        }
        data["loss_distribution"] = primary
        return data

    data = loop_state.update_current(_mutate)
    return data["loss_distribution"]


def refresh(episodes_dir=None, replays_dir=None, ladder_dirs=None,
            top_n=tpt.DEFAULT_TOP_N, days=tpt.DEFAULT_DAYS,
            max_episodes=harvest_replays.DEFAULT_MAX_EPISODES) -> dict:
    """Run the full daily refresh. See module docstring for the four steps."""
    result = {}

    dataset = ensure_newest_dataset(episodes_dir)
    result["dataset"] = dataset

    dataset_path = dataset.get("path")
    if dataset_path is None:
        dataset_path = tpt.newest_dataset(episodes_dir)

    if dataset_path is not None:
        result["top_player"] = refresh_top_player_corpus(dataset_path, top_n=top_n, days=days)
    else:
        result["top_player"] = {"ok": False, "error": "no episode dataset available on disk"}

    result["ladder_harvest"] = harvest_replays.harvest(dest_dir=replays_dir, max_episodes=max_episodes)
    result["loss_distribution"] = refresh_loss_distribution(ladder_dirs)

    return result


def _print_summary(result: dict) -> None:
    ds = result["dataset"]
    if ds["ok"]:
        state = "downloaded" if ds["downloaded"] else "already had"
        print(f"dataset: {state} {ds['slug']}")
    else:
        print(f"dataset: FAILED ({ds['error']})")

    tp = result["top_player"]
    if tp["ok"]:
        print(f"top-player tracker: +{tp['new_win_rows']} win rows, +{tp['new_loss_rows']} loss rows, "
              f"{tp['games_matched']}/{tp['games_considered']} games matched")
    else:
        print(f"top-player tracker: FAILED ({tp['error']})")

    lh = result["ladder_harvest"]
    if lh["ok"]:
        print(f"ladder harvest: +{len(lh['fetched'])} new replays "
              f"({len(lh['skipped'])} already had, {len(lh['failed'])} failed)")
    else:
        print(f"ladder harvest: FAILED ({lh['error']})")

    dist = result["loss_distribution"]
    print(f"loss distribution: top bucket = {dist['top_bucket']} over {dist['sample_size']} replays "
          f"(W/D/L {dist['wins']}/{dist['draws']}/{dist['losses']})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--episodes-dir", default=str(DEFAULT_EPISODES_DIR),
                     help="directory holding episode dataset .zip files")
    ap.add_argument("--replays-dir", default=None,
                     help="directory for our own harvested ladder replays (default data/replays)")
    ap.add_argument("--ladder-dir", dest="ladder_dirs", action="append", default=None,
                     help="replay dir(s) to classify for the loss distribution "
                          "(default data/replays; may repeat)")
    ap.add_argument("--top-n", type=int, default=tpt.DEFAULT_TOP_N)
    ap.add_argument("--days", type=int, default=tpt.DEFAULT_DAYS)
    ap.add_argument("--max-episodes", type=int, default=harvest_replays.DEFAULT_MAX_EPISODES)
    ap.add_argument("--out", default=None, help="write the full JSON result to this path")
    args = ap.parse_args(argv)

    result = refresh(
        episodes_dir=args.episodes_dir,
        replays_dir=args.replays_dir,
        ladder_dirs=args.ladder_dirs,
        top_n=args.top_n,
        days=args.days,
        max_episodes=args.max_episodes,
    )
    _print_summary(result)
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2, default=str))
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
