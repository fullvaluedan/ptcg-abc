"""Top-50 leaderboard team game + decklist harvest.

Wraps tools.top_player_tracker (leaderboard fetch, manifest loading) and
analysis.expert_cohort (decklist extraction) rather than editing either: this
is a standalone extension for a one-shot harvest, not a change to the
existing weekly training-corpus tracker.

For each of the top-N leaderboard teams, finds every game across ALL episode
dataset dumps under data/episodes/ (not just the newest, unlike
top_player_tracker's --days window) that names that team in info.TeamNames,
keeps the most recent up to --games-per-team of them, and harvests the
decklist(s) that team ran in that window.

Performance note. A naive full json.loads over every episode across all 9
dumps (~46,700 episodes) is too slow: full parse alone runs ~50ms/episode
(measured), which is 30+ minutes just to find who played whom. Each replay's
info.TeamNames and top-level rewards both sit within the first ~1KB of the
file (measured across multiple dumps), so this instead:

  pass 1 (cheap, all episodes): stream-read only the first HEAD_BYTES of each
  zip member (zipfile.open().read(N), which does NOT decompress the whole
  member) and pull just the TeamNames and rewards JSON arrays out of that
  head fragment with json.JSONDecoder().raw_decode (handles any escaping
  inside a name correctly, unlike bracket matching). This is what determines,
  for every one of the ~46,700 episodes, who played and who won -- at
  ~0.15ms/episode, not 50ms/episode. Team names containing non-ASCII
  characters are escaped (\\uXXXX) by the dump's JSON encoder same as any
  other JSON text; raw_decode handles that natively, no separate escaped-form
  matching needed here (that workaround was only needed for a plain substring
  prefilter, which this design does not use).

  pass 2 (targeted, only the games actually kept): a full zf.read + json.loads
  + analysis.expert_cohort.seat_decklists, run only for the <= top-N *
  games-per-team distinct episodes that survive pass 1's per-team recency cut
  -- this is where the 60-card decklist actually lives (steps[0][0]'s
  visualize action), not reachable from the head.

Dev tool only, never shipped. Reads data/episodes/*.zip (gitignored
competition data) but writes only aggregated, redistributable derived output
(episode ids, dates, W/L, decklists as card ids) -- the same shape
tools/bracket_decks.py already commits to decks/*.csv.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.expert_cohort import classify_family, seat_decklists  # noqa: E402
from tools.deck_validate import validate  # noqa: E402
from tools.top_player_tracker import (  # noqa: E402
    DEFAULT_EPISODES_DIR,
    NON_DUMP_ZIP_NAMES,
    fetch_leaderboard,
    load_manifest,
)

DEFAULT_TOP_N = 50
DEFAULT_GAMES_PER_TEAM = 20
DEFAULT_MIN_DECK_GAMES = 5
DEFAULT_OUT = _ROOT / "data" / "derived" / "top50_harvest.json"
DEFAULT_SUMMARY = _ROOT / "analysis" / "top50_harvest.md"
DEFAULT_DECKS_DIR = _ROOT / "decks" / "top50"
HEAD_BYTES = 4096


def all_dumps(episodes_dir=None) -> list:
    """Every dated episode dataset zip under episodes_dir, oldest first.

    Mirrors tools.top_player_tracker.newest_dataset's filtering (excludes the
    leaderboard/index zips via NON_DUMP_ZIP_NAMES) but returns the whole
    sorted list instead of just the newest, since this harvest needs each
    team's full available history, not one day's window.
    """
    episodes_dir = Path(episodes_dir) if episodes_dir else DEFAULT_EPISODES_DIR
    return sorted(p for p in episodes_dir.glob("*.zip") if p.name not in NON_DUMP_ZIP_NAMES)


def _extract_json_array(text: str, key: str):
    """Parse the JSON array value that follows "<key>": in a text fragment, or None.

    Locates the key, then the next '[', then hands off to
    json.JSONDecoder().raw_decode from that point so any escaped character
    inside a string element (a team name with a literal ']' or a
    \\uXXXX-escaped non-ASCII name) is parsed correctly rather than
    bracket-matched by hand. Returns None when the key or a following '['
    is not found in this fragment (caller falls back or skips).
    """
    key_idx = text.find(f'"{key}"')
    if key_idx == -1:
        return None
    arr_idx = text.find("[", key_idx)
    if arr_idx == -1:
        return None
    try:
        value, _ = json.JSONDecoder().raw_decode(text[arr_idx:])
    except json.JSONDecodeError:
        return None
    return value


def _result_for(rewards, seat: int) -> str | None:
    """"W"/"L"/"D" for `seat` given a raw two-element rewards list, or None if unreadable."""
    if not isinstance(rewards, (list, tuple)) or len(rewards) != 2:
        return None
    a, b = rewards[0], rewards[1]
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return None
    if isinstance(a, bool) or isinstance(b, bool):
        return None
    if a == b:
        return "D"
    winner = 0 if a > b else 1
    return "W" if winner == seat else "L"


def scan_all_dumps(dumps: list, team_set: set) -> tuple:
    """Pass 1: head-only scan of every episode in every dump.

    Returns (candidates, total_episodes_scanned). candidates maps team name ->
    list of {episode_id, create_time (datetime|None), opponent, result,
    seat, dump, member} across ALL matched games (uncapped) -- this is the
    source for both the "matched game count" stat and, after a per-team sort
    + slice, the last-N-games window. Never raises on a single bad member;
    it is skipped and counted only in total_episodes_scanned.
    """
    candidates: dict = defaultdict(list)
    total = 0
    for dump in dumps:
        with zipfile.ZipFile(dump) as zf:
            manifest = load_manifest(zf)
            for name in zf.namelist():
                if not name.endswith(".json") or name == "manifest.csv":
                    continue
                total += 1
                try:
                    with zf.open(name) as fh:
                        head = fh.read(HEAD_BYTES).decode("utf-8", "replace")
                except (KeyError, OSError):
                    continue
                names = _extract_json_array(head, "TeamNames")
                if not isinstance(names, list) or len(names) != 2:
                    continue
                names = [str(n) for n in names]
                if names[0] not in team_set and names[1] not in team_set:
                    continue
                rewards = _extract_json_array(head, "rewards")
                eid = Path(name).stem
                create_time = manifest.get(eid)
                for seat, tname in enumerate(names):
                    if tname not in team_set:
                        continue
                    candidates[tname].append({
                        "episode_id": eid,
                        "create_time": create_time,
                        "opponent": names[1 - seat],
                        "result": _result_for(rewards, seat),
                        "seat": seat,
                        "dump": dump.name,
                        "member": name,
                    })
    return candidates, total


def recent_window(games: list, n: int) -> list:
    """The `n` most recent games, newest first.

    Sorts by create_time descending; games with no manifest timestamp sort
    after every dated game (their recency is unknown, never assumed newest).
    """
    dated = [g for g in games if g["create_time"] is not None]
    undated = [g for g in games if g["create_time"] is None]
    dated.sort(key=lambda g: g["create_time"], reverse=True)
    return (dated + undated)[:n]


def fetch_decklists(needed: set, dump_paths: dict) -> dict:
    """Pass 2: full parse, only for the specific (dump, member) pairs needed.

    needed is a set of (dump_name, member, episode_id) triples. Returns
    episode_id -> (deck0, deck1) tuple-of-60-card-id-tuples, or None when the
    replay is unreadable or carries no valid opener (see
    analysis.expert_cohort.seat_decklists). dump_paths maps dump filename ->
    Path so each dump zip is opened once regardless of how many episodes are
    pulled from it.
    """
    by_dump: dict = defaultdict(list)
    for dump_name, member, eid in needed:
        by_dump[dump_name].append((member, eid))
    out = {}
    for dump_name, items in by_dump.items():
        path = dump_paths.get(dump_name)
        if path is None:
            for member, eid in items:
                out[eid] = None
            continue
        with zipfile.ZipFile(path) as zf:
            for member, eid in items:
                try:
                    replay = json.loads(zf.read(member))
                except (json.JSONDecodeError, OSError, KeyError):
                    out[eid] = None
                    continue
                out[eid] = seat_decklists(replay)
    return out


def _ascii_slug(text: str, fallback: str) -> str:
    """A lowercase, underscore-separated ASCII slug for `text`, or `fallback` if empty.

    NFKD-normalizes then drops any character outside ASCII (a team handle
    with CJK or Cyrillic characters folds to nothing rather than to mojibake),
    so decks/top50/*.csv filenames stay portable; the original Unicode name is
    always kept alongside in the JSON/markdown output, never lost.
    """
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", norm).strip("_").lower()
    return slug or fallback


def canonical_deck(deck) -> tuple:
    """Order-independent identity for a 60-card decklist (same convention as
    tools.bracket_decks.decklist_counts): a sorted tuple of card ids."""
    return tuple(sorted(deck))


def build_harvest(top_n: int, games_per_team: int, episodes_dir=None) -> dict:
    """The full pipeline: leaderboard -> per-team recent games -> decklists."""
    lb = fetch_leaderboard(top_n)
    if not lb["ok"]:
        raise RuntimeError(f"leaderboard fetch failed: {lb['error']}")
    teams = lb["teams"]
    team_set = {t["name"] for t in teams}

    dumps = all_dumps(episodes_dir)
    if not dumps:
        raise RuntimeError(f"no episode dumps found under {episodes_dir or DEFAULT_EPISODES_DIR}")
    dump_paths = {d.name: d for d in dumps}

    candidates, total_scanned = scan_all_dumps(dumps, team_set)

    try:
        from tools.expert_census import build_signatures
        signatures = build_signatures()
    except Exception:  # noqa: BLE001 - archetype labeling is best-effort, never fatal
        signatures = None

    per_team_windows = {}
    needed = set()
    for t in teams:
        name = t["name"]
        games = candidates.get(name, [])
        window = recent_window(games, games_per_team)
        per_team_windows[name] = {"matched_game_count": len(games), "window": window}
        for g in window:
            needed.add((g["dump"], g["member"], g["episode_id"]))

    decklists_by_episode = fetch_decklists(needed, dump_paths)

    global_deck_counts: dict = defaultdict(lambda: {"count": 0, "teams": Counter()})
    team_reports = []
    for t in teams:
        name = t["name"]
        info = per_team_windows[name]
        window = info["window"]

        # One pass: resolve each game's deck (if any) and tally per-team counts
        # + first-seen recency (window is already newest-first, so the first
        # occurrence of a key is that deck's most recent appearance).
        per_game_deck_key = []
        team_deck_counts: dict = defaultdict(int)
        team_deck_first_full: dict = {}
        deck_recency: dict = {}
        for i, g in enumerate(window):
            decks = decklists_by_episode.get(g["episode_id"])
            deck = decks[g["seat"]] if decks is not None else None
            key = canonical_deck(deck) if deck is not None else None
            per_game_deck_key.append(key)
            if key is not None:
                team_deck_counts[key] += 1
                team_deck_first_full.setdefault(key, deck)
                deck_recency.setdefault(key, i)
                global_deck_counts[key]["count"] += 1
                global_deck_counts[key]["teams"][name] += 1

        # Distinct decks ordered most-recent-first; deck_index below is this
        # team's own 0-based index into `decks_out`, the join key each game
        # entry uses (not a truncated fingerprint, which could collide).
        ordered_keys = sorted(team_deck_counts, key=lambda k: deck_recency[k])
        key_to_index = {key: idx for idx, key in enumerate(ordered_keys)}

        games_out = []
        for g, key in zip(window, per_game_deck_key):
            games_out.append({
                "episode_id": g["episode_id"],
                "date": g["create_time"].isoformat() if g["create_time"] else None,
                "opponent": g["opponent"],
                "result": g["result"],
                "deck_index": key_to_index.get(key),  # index into this team's "decks" list below, or null
            })

        decks_out = []
        for key in ordered_keys:
            deck = team_deck_first_full[key]
            family = classify_family(deck, signatures) if signatures else "other"
            decks_out.append({
                "cards": list(deck),
                "games_in_window": team_deck_counts[key],
                "archetype_guess": family,
            })

        wins = sum(1 for g in games_out if g["result"] == "W")
        losses = sum(1 for g in games_out if g["result"] == "L")
        draws = sum(1 for g in games_out if g["result"] == "D")
        team_reports.append({
            "rank": t["rank"],
            "team": name,
            "rating": t["rating"],
            "matched_game_count": info["matched_game_count"],
            "games_returned": len(window),
            "win_loss_draw": {"w": wins, "l": losses, "d": draws},
            "distinct_decks": len(decks_out),
            "switched_decks": len(decks_out) > 1,
            "games": games_out,
            "decks": decks_out,
        })

    return {
        "teams": team_reports,
        "meta": {
            "top_n": top_n,
            "games_per_team_target": games_per_team,
            "episodes_scanned": total_scanned,
            "dumps": [d.name for d in dumps],
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
        "_global_deck_counts": {  # underscore: internal handoff to CSV writer, not part of the public shape
            key: {"count": v["count"], "teams": dict(v["teams"])}
            for key, v in global_deck_counts.items()
        },
    }


def write_decks(harvest: dict, decks_dir=DEFAULT_DECKS_DIR, min_games: int = DEFAULT_MIN_DECK_GAMES,
                 validate_fn=validate) -> list:
    """CSVs for every distinct deck (global, across all harvested teams) with
    >= min_games harvested games. Slug = rank + primary (most-games) team +
    archetype guess, all ASCII; the CSV itself is 60 card ids, one per line,
    the same shape every other decks/*.csv already uses. Skips (and reports)
    a deck that fails tools.deck_validate.validate, same defensive check
    tools.bracket_decks.py applies before shipping a harvested decklist.
    """
    decks_dir = Path(decks_dir)
    decks_dir.mkdir(parents=True, exist_ok=True)

    # Rebuild key -> one representative full deck (any team report carries it).
    deck_examples: dict = {}
    for team in harvest["teams"]:
        for d in team["decks"]:
            key = canonical_deck(d["cards"])
            deck_examples.setdefault(key, d["cards"])

    counts = harvest["_global_deck_counts"]
    eligible = [(key, v) for key, v in counts.items() if v["count"] >= min_games]
    eligible.sort(key=lambda kv: (-kv[1]["count"], kv[0]))

    try:
        from tools.expert_census import build_signatures
        signatures = build_signatures()
    except Exception:  # noqa: BLE001
        signatures = None

    written = []
    for i, (key, v) in enumerate(eligible, start=1):
        deck = deck_examples.get(key)
        if deck is None:
            continue
        primary_team = max(v["teams"], key=lambda n: v["teams"][n])
        family = classify_family(deck, signatures) if signatures else "other"
        team_slug = _ascii_slug(primary_team, f"team{i}")
        fam_slug = _ascii_slug(family, "") if family != "other" else ""
        parts = [f"top50_{i:02d}", team_slug]
        if fam_slug:
            parts.append(fam_slug)
        slug = "_".join(parts)

        verdict = validate_fn(list(deck))
        entry = {
            "slug": slug,
            "path": None,
            "games": v["count"],
            "teams": v["teams"],
            "primary_team": primary_team,
            "archetype_guess": family,
            "legal": verdict.get("ok", False),
        }
        if verdict.get("ok"):
            path = decks_dir / f"{slug}.csv"
            path.write_text("\n".join(str(c) for c in deck) + "\n", encoding="utf-8")
            entry["path"] = str(path)
        written.append(entry)
    return written


def _safe(text: str) -> str:
    """Down-convert text to what stdout can encode (same fix as top_player_tracker._safe)."""
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(enc, "replace").decode(enc)


def format_summary(harvest: dict, deck_files: list) -> str:
    lines = [
        "# Top-50 leaderboard harvest",
        "",
        f"Generated {harvest['meta']['generated_at']}. Scanned {harvest['meta']['episodes_scanned']} "
        f"episodes across {len(harvest['meta']['dumps'])} dumps: "
        + ", ".join(harvest["meta"]["dumps"]) + ".",
        "",
        f"Target: last {harvest['meta']['games_per_team_target']} games per team, top "
        f"{harvest['meta']['top_n']} leaderboard teams.",
        "",
        "## Coverage table",
        "",
        "| rank | team | rating | games found | games harvested | W-L-D | distinct decks |",
        "|---|---|---|---|---|---|---|",
    ]
    zero = []
    total_games = 0
    for t in harvest["teams"]:
        wld = t["win_loss_draw"]
        lines.append(
            f"| {t['rank']} | {t['team']} | {t['rating']:.1f} | {t['matched_game_count']} | "
            f"{t['games_returned']} | {wld['w']}-{wld['l']}-{wld['d']} | {t['distinct_decks']} |"
        )
        total_games += t["games_returned"]
        if t["matched_game_count"] == 0:
            zero.append(t["team"])

    lines += ["", "## Totals", ""]
    lines.append(f"- Teams covered: {len(harvest['teams'])}")
    lines.append(f"- Total harvested games (sum of games_returned): {total_games}")
    lines.append(
        f"- Teams with zero matched games: {len(zero)}"
        + (f" -- {', '.join(zero)}" if zero else "")
    )
    distinct_decks_total = len({canonical_deck(d['cards']) for t in harvest['teams'] for d in t['decks']})
    lines.append(f"- Distinct decklists across all 50 teams' harvested windows: {distinct_decks_total}")
    lines.append(
        f"- Decks with >= {DEFAULT_MIN_DECK_GAMES} harvested games (CSV-eligible): {len(deck_files)}"
    )

    lines += ["", "## Deck switches", ""]
    switchers = [t for t in harvest["teams"] if t["switched_decks"]]
    if switchers:
        for t in switchers:
            lines.append(
                f"- {t['team']} (rank {t['rank']}): {t['distinct_decks']} distinct decks in the "
                f"harvested window"
            )
    else:
        lines.append("- none: every team with a matched game ran a single decklist across its window")

    lines += ["", "## Decklist CSVs written", "", "| slug | games | legal | primary team | archetype guess | teams sharing this deck |", "|---|---|---|---|---|---|"]
    if deck_files:
        for e in deck_files:
            team_list = ", ".join(f"{k} ({v})" for k, v in sorted(e["teams"].items(), key=lambda kv: -kv[1]))
            lines.append(
                f"| {e['slug']} | {e['games']} | {'yes' if e['legal'] else 'NO (skipped, see below)'} | "
                f"{e['primary_team']} | {e['archetype_guess']} | {team_list} |"
            )
    else:
        lines.append("| (none) | | | | | |")

    skipped = [e for e in deck_files if not e["legal"]]
    if skipped:
        lines += ["", "## Skipped (illegal) decklists", ""]
        for e in skipped:
            lines.append(f"- {e['slug']}: failed tools.deck_validate.validate, no CSV written")

    lines += ["", "## Notes", "", "- Team names are matched by exact string against a game's "
              "info.TeamNames (same matching rule as tools/top_player_tracker.py); a leaderboard "
              "display-name change or a brand-new team with no games yet in the scanned dumps shows "
              "up as zero matched games above, not a silent skip.",
              "- Decklist identity is order-independent (sorted card-id tuple), matching the "
              "convention tools/bracket_decks.py already uses for harvested decklists.",
              ""]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    ap.add_argument("--games-per-team", type=int, default=DEFAULT_GAMES_PER_TEAM)
    ap.add_argument("--episodes-dir", default=str(DEFAULT_EPISODES_DIR))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    ap.add_argument("--decks-dir", default=str(DEFAULT_DECKS_DIR))
    ap.add_argument("--min-deck-games", type=int, default=DEFAULT_MIN_DECK_GAMES)
    args = ap.parse_args(argv)

    harvest = build_harvest(args.top_n, args.games_per_team, episodes_dir=args.episodes_dir)
    deck_files = write_decks(harvest, decks_dir=args.decks_dir, min_games=args.min_deck_games)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    public = {k: v for k, v in harvest.items() if not k.startswith("_")}
    public["decks_written"] = deck_files
    out_path.write_text(json.dumps(public, indent=2, ensure_ascii=False), encoding="utf-8")

    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(format_summary(harvest, deck_files), encoding="utf-8")

    total_games = sum(t["games_returned"] for t in harvest["teams"])
    zero = sum(1 for t in harvest["teams"] if t["matched_game_count"] == 0)
    print(_safe(
        f"harvested {total_games} games across {len(harvest['teams'])} teams "
        f"({zero} with zero matches); wrote {out_path}"
    ))
    print(_safe(f"wrote {len(deck_files)} deck csv(s) to {args.decks_dir}"))
    print(f"wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
