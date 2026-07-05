"""Select genuinely NEW deck candidates from the U39 top-rated mining output
(plan U39 step 2 correction, 2026-07-05).

analysis/top_rated_mining.md (queue item 4) clustered 800+-rated players'
winning decklists but never deduped the clusters against decks already on
disk: 2 of its top 3 clusters turned out to be undocumented duplicates of
decks already tested and refuted under the generic pilot (meta_grimmsnarl,
meta_grimmsnarl_tonakaiiii; analysis/meta_decks_underperform_on_ladder.md).
This tool re-mines, dedupes by full 60-card signature against every
decks/*.csv on disk, and writes the top-k genuinely new candidates as
decks/candidate_<slug>.csv for tools.ring_calibrate scoring.

Dev tool only; never shipped. Reads the competition episode dataset but
never redistributes it (data/episodes stays gitignored); the decklists it
writes are 60 card ids, the same shape as every other decks/*.csv already
committed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.deck_validate import validate  # noqa: E402
from tools.top_player_tracker import DEFAULT_EPISODES_DIR, newest_dataset  # noqa: E402
from tools.top_rated_deck_mining import (  # noqa: E402
    LEADERBOARD_PATH,
    MIN_RATING,
    cluster_decks,
    mine_top_rated_decks,
)

DEFAULT_DECKS_DIR = _ROOT / "decks"
CANDIDATE_PREFIX = "candidate_"
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def load_existing_signatures(decks_dir=None) -> dict:
    """{sorted 60-card signature tuple: file path} for every decks/*.csv.

    A malformed or non-60-card file is skipped rather than raising, so one
    bad deck file cannot crash deduplication.
    """
    decks_dir = Path(decks_dir) if decks_dir else DEFAULT_DECKS_DIR
    out = {}
    for path in sorted(decks_dir.glob("*.csv")):
        try:
            ids = [int(line) for line in path.read_text(encoding="utf-8").split() if line.strip()]
        except (OSError, ValueError):
            continue
        if len(ids) != 60:
            continue
        out[tuple(sorted(ids))] = str(path)
    return out


def slug_for(teams) -> str:
    """A filesystem-safe stem from the first team name, or 'unknown'."""
    if not teams:
        return "unknown"
    raw = str(teams[0]).lower()
    slug = _SLUG_RE.sub("_", raw).strip("_")
    return slug or "unknown"


def rank_new_candidates(clusters: dict, existing_sigs: dict, top_k: int = 5) -> dict:
    """Clusters ranked by play count, tagged NEW or DUPLICATE of an existing deck.

    Returns {"new": [...], "duplicates": [...]}, each entry carrying deck,
    count, teams, and (for duplicates) the matched existing path. Pure over
    its inputs so it is unit-testable without the engine or real data.
    """
    ranked = sorted(clusters.items(), key=lambda kv: -kv[1]["count"])
    new_entries, dup_entries = [], []
    for sig, info in ranked:
        key = tuple(sorted(sig))
        match = existing_sigs.get(key)
        entry = {"deck": list(sig), "count": info["count"], "teams": sorted(info["teams"])}
        if match:
            entry["duplicate_of"] = match
            dup_entries.append(entry)
        else:
            new_entries.append(entry)
            if len(new_entries) >= top_k:
                break
    return {"new": new_entries, "duplicates": dup_entries}


def write_candidate_decks(new_entries: list, decks_dir=None, validate_fn=validate) -> list:
    """Write decks/candidate_<slug>.csv for each legal new candidate.

    A candidate that fails validate_fn is skipped and recorded in the
    returned list with ok=False rather than written, mirroring
    tools.bracket_decks.top_decklists's never-force-fit-an-illegal-deck rule.
    """
    decks_dir = Path(decks_dir) if decks_dir else DEFAULT_DECKS_DIR
    decks_dir.mkdir(parents=True, exist_ok=True)
    written = []
    seen_slugs = set()
    for entry in new_entries:
        slug = slug_for(entry["teams"])
        base_slug = slug
        i = 2
        while slug in seen_slugs:
            slug = f"{base_slug}_{i}"
            i += 1
        seen_slugs.add(slug)
        verdict = validate_fn(entry["deck"])
        result = {**entry, "slug": slug, "ok": verdict.get("ok", False)}
        if result["ok"]:
            path = decks_dir / f"{CANDIDATE_PREFIX}{slug}.csv"
            path.write_text("\n".join(str(c) for c in entry["deck"]) + "\n", encoding="utf-8")
            result["path"] = str(path)
        else:
            result["rule_errors"] = verdict.get("rule_errors")
        written.append(result)
    return written


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--episodes", type=Path, default=None,
                     help=f"episode dataset zip or dir (default: newest in {DEFAULT_EPISODES_DIR})")
    ap.add_argument("--leaderboard", type=Path, default=LEADERBOARD_PATH)
    ap.add_argument("--min-rating", type=float, default=MIN_RATING)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--top-k", type=int, default=3, help="how many new candidates to write (default 3)")
    ap.add_argument("--decks-dir", default=str(DEFAULT_DECKS_DIR))
    ap.add_argument("--out", default=None, help="optional JSON report path")
    args = ap.parse_args(argv)

    source = args.episodes or newest_dataset(DEFAULT_EPISODES_DIR)
    if source is None or not Path(source).exists():
        print(f"no episode dataset found under {DEFAULT_EPISODES_DIR}")
        return 1
    if not Path(args.leaderboard).exists():
        print(f"leaderboard cache not found: {args.leaderboard}")
        return 1

    team_decks, scanned, matches = mine_top_rated_decks(
        source, args.min_rating, args.leaderboard, limit=args.limit
    )
    clusters = cluster_decks(team_decks)
    existing = load_existing_signatures(args.decks_dir)
    ranked = rank_new_candidates(clusters, existing, top_k=args.top_k)
    written = write_candidate_decks(ranked["new"], args.decks_dir)

    print(f"scanned {scanned} episodes, {matches} winning matches by {args.min_rating}+ rated teams")
    print(f"{len(clusters)} unique signatures, {len(ranked['duplicates'])} duplicates of existing decks")
    print(f"wrote {sum(1 for w in written if w['ok'])} new candidate deck(s):")
    for w in written:
        status = "OK" if w["ok"] else f"REJECTED ({w.get('rule_errors')})"
        print(f"  {w['slug']}: {w['count']} plays, teams={w['teams'][:3]} -> {status}")

    if args.out:
        Path(args.out).write_text(json.dumps({"ranked": ranked, "written": written}, indent=2), encoding="utf-8")
        print(f"wrote report {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
