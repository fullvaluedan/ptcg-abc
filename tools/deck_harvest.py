"""Harvest decklists from episode datasets and rank the winning meta.

Each episode replay carries, at the deck-selection step (step 1), a 60 card
action list per seat: that seat's full decklist. info.TeamNames names each seat
and rewards[seat] being the strict maximum marks the winner. This tool reads a
directory of episode JSONs OR a daily-dataset .zip (streamed member by member,
so the ~21GB unzipped tree is never written to disk) and extracts every
(team, deck, won) triple. It then aggregates them into a winning-meta report:
the most successful deck signatures, the teams that play them, and card
frequency across winning decks. Card ids map to names via data/EN_Card_Data.csv.

Competition data only: episode datasets stay gitignored under data/ and are
never redistributed. This is a development scouting tool, never shipped with the
agent.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

# The deck-selection action is a full 60 card list. Any action list at least this
# long is a decklist; a normal in game action (a handful of card/target ids) is
# far shorter, so this threshold separates the two without a false match.
DECK_SELECT_MIN = 40
CARD_DATA_CSV = _ROOT / "data" / "EN_Card_Data.csv"


def load_card_names(path=CARD_DATA_CSV) -> dict:
    """Map card id -> (name, category) from the card database CSV.

    Returns an empty dict when the file is absent so a caller can still print a
    report with raw ids instead of aborting.
    """
    path = Path(path)
    if not path.exists():
        return {}
    out = {}
    with open(path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            raw = (row.get("Card ID") or "").strip()
            if not raw.isdigit():
                continue
            out[int(raw)] = (
                (row.get("Card Name") or "").strip(),
                (row.get("Category") or "").strip(),
            )
    return out


def deck_signature(deck) -> tuple:
    """A deck's identity: its multiset of card ids, order independent."""
    return tuple(sorted(int(c) for c in deck))


def extract_seat_decks(replay) -> list:
    """Extract one (seat, team, won, deck) record per seat from a replay.

    The decklist is the first action list at least DECK_SELECT_MIN long that a
    seat plays (the deck-selection step). won is True only for the seat whose
    reward strictly exceeds the other seat's (a draw wins for neither). Returns
    an empty list when the replay is malformed or a deck action is missing.
    """
    if not isinstance(replay, dict):
        return []
    steps = replay.get("steps")
    if not isinstance(steps, list) or not steps:
        return []
    info = replay.get("info") or {}
    names = info.get("TeamNames") or []
    rewards = replay.get("rewards") or []

    decks = {}
    for step in steps:
        if not isinstance(step, list):
            continue
        for seat, rec in enumerate(step):
            if seat in decks or not isinstance(rec, dict):
                continue
            action = rec.get("action")
            if isinstance(action, list) and len(action) >= DECK_SELECT_MIN:
                decks[seat] = [int(c) for c in action]

    records = []
    for seat, deck in decks.items():
        reward = rewards[seat] if seat < len(rewards) else None
        other = [r for i, r in enumerate(rewards) if i != seat]
        won = reward is not None and all(
            isinstance(o, (int, float)) and reward > o for o in other
        ) and bool(other)
        records.append(
            {
                "seat": seat,
                "team": names[seat] if seat < len(names) else None,
                "won": won,
                "reward": reward,
                "deck": deck,
            }
        )
    return records


def iter_replays(source):
    """Yield (member_name, replay_dict) from a directory of JSONs or a .zip.

    A .zip source is streamed member by member so the full dataset is never
    unzipped to disk. Unreadable or non JSON members are skipped rather than
    raising, so one corrupt episode does not abort a batch.
    """
    source = Path(source)
    if source.is_file() and source.suffix == ".zip":
        with zipfile.ZipFile(source) as zf:
            for name in zf.namelist():
                if not name.endswith(".json"):
                    continue
                try:
                    yield name, json.loads(zf.read(name))
                except (json.JSONDecodeError, OSError, KeyError):
                    continue
    else:
        for path in sorted(Path(source).glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    yield path.name, json.load(fh)
            except (OSError, json.JSONDecodeError):
                continue


def harvest(source, teams=None, limit=None) -> dict:
    """Aggregate decklists across an episode source into a winning-meta report.

    Groups records by deck signature, counting games and wins and collecting the
    teams that played each deck. teams (an iterable of names) restricts the
    harvest to those seats only; limit caps how many episodes are read (useful
    for a quick pass over a multi thousand episode dataset). Returns a dict with
    the per signature aggregate and the episode/record totals.
    """
    team_filter = {t.strip().lower() for t in teams} if teams else None
    by_sig = {}
    episodes = 0
    records = 0
    for _, replay in iter_replays(source):
        episodes += 1
        if limit is not None and episodes > limit:
            episodes -= 1
            break
        for rec in extract_seat_decks(replay):
            team = rec["team"]
            if team_filter is not None and (
                team is None or team.strip().lower() not in team_filter
            ):
                continue
            records += 1
            sig = deck_signature(rec["deck"])
            entry = by_sig.get(sig)
            if entry is None:
                entry = {"deck": rec["deck"], "games": 0, "wins": 0, "teams": set()}
                by_sig[sig] = entry
            entry["games"] += 1
            entry["wins"] += 1 if rec["won"] else 0
            if team:
                entry["teams"].add(team)
    return {"by_sig": by_sig, "episodes": episodes, "records": records}


def rank_decks(agg, min_games=1) -> list:
    """Rank harvested decks by wins, then win rate, then games.

    Only decks with at least min_games appearances qualify, so a single lucky
    game does not outrank a proven deck.
    """
    ranked = []
    for sig, entry in agg["by_sig"].items():
        if entry["games"] < min_games:
            continue
        win_rate = entry["wins"] / entry["games"] if entry["games"] else 0.0
        ranked.append((sig, entry, win_rate))
    ranked.sort(key=lambda t: (t[1]["wins"], t[2], t[1]["games"]), reverse=True)
    return ranked


def deck_fingerprint(deck, names) -> list:
    """A deck as (count, id, name) rows sorted by descending count then id.

    The archetype fingerprint: which cards, how many copies, human readable.
    """
    counts = Counter(int(c) for c in deck)
    rows = []
    for card_id, n in counts.items():
        name = names.get(card_id, ("?", ""))[0] if names else "?"
        rows.append((n, card_id, name))
    rows.sort(key=lambda r: (-r[0], r[1]))
    return rows


def write_deck(deck, path) -> None:
    """Write a deck as one card id per line (the decks/*.csv format)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for card_id in deck:
            fh.write(f"{int(card_id)}\n")


def _print_report(agg, names, top=5, min_games=1) -> None:
    ranked = rank_decks(agg, min_games=min_games)
    print(
        f"harvested {agg['records']} decklists over {agg['episodes']} episodes; "
        f"{len(agg['by_sig'])} distinct decks"
    )
    print(f"top {min(top, len(ranked))} by wins (min {min_games} games):")
    for i, (_, entry, win_rate) in enumerate(ranked[:top], 1):
        teams = ", ".join(sorted(entry["teams"]))[:70]
        print(
            f"\n#{i}  {entry['wins']}W / {entry['games']}G "
            f"({win_rate * 100:.0f}%)  teams: {teams}"
        )
        for n, card_id, name in deck_fingerprint(entry["deck"], names):
            print(f"    {n}x {name} ({card_id})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="harvest and rank meta decks from episodes")
    sub = ap.add_subparsers(dest="cmd", required=True)

    hp = sub.add_parser("harvest", help="rank winning decks in a dir or .zip of episodes")
    hp.add_argument("source", help="directory of episode JSONs or a daily-dataset .zip")
    hp.add_argument("--teams", default=None, help="comma separated team names to restrict to")
    hp.add_argument("--min-games", type=int, default=1, help="minimum games for a deck to rank")
    hp.add_argument("--limit", type=int, default=None, help="cap episodes read (quick pass)")
    hp.add_argument("--top", type=int, default=5, help="how many decks to print")
    hp.add_argument("--out", default=None, help="write the #1 ranked deck to this CSV path")

    args = ap.parse_args(argv)
    if args.cmd == "harvest":
        teams = [t for t in args.teams.split(",") if t.strip()] if args.teams else None
        agg = harvest(args.source, teams=teams, limit=args.limit)
        names = load_card_names()
        _print_report(agg, names, top=args.top, min_games=args.min_games)
        if args.out:
            ranked = rank_decks(agg, min_games=args.min_games)
            if ranked:
                write_deck(ranked[0][1]["deck"], args.out)
                print(f"\nwrote #1 ranked deck ({len(ranked[0][1]['deck'])} cards) to {args.out}")
            else:
                print("\nno deck met the ranking threshold; nothing written")
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
