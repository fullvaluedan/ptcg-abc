#!/usr/bin/env python3
"""Deck exploration: deduplicate mining results and identify novel candidates.

P2 directives:
1. Load mining clusters from analysis/top_rated_mining.md
2. Deduplicate against existing decks in decks/*.csv
3. Identify top NEW candidates by play count
4. Score through calibrated ring
5. Pre-register only those that clear trolley's 0.85 ring win rate
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.deck_harvest import deck_signature  # noqa: E402


class Candidate(NamedTuple):
    cluster_num: int
    team_name: str
    play_count: int
    signature: tuple[int, ...]
    is_new: bool
    duplicate_of: str | None = None


def load_existing_decks(decks_dir: Path) -> dict[str, tuple[int, ...]]:
    """Load all existing deck signatures from decks/*.csv.

    Returns {deck_name: signature_tuple}
    """
    decks = {}
    for deck_file in sorted(decks_dir.glob("*.csv")):
        with open(deck_file) as f:
            cards = [int(line.strip()) for line in f if line.strip()]
            if len(cards) == 60:
                name = deck_file.stem
                decks[name] = deck_signature(cards)
    return decks


def parse_mining_results(mining_file: Path) -> list[dict]:
    """Parse top_rated_mining.md to extract cluster info.

    Returns list of {cluster, team_name, play_count, signature, original_teams}
    """
    with open(mining_file, encoding="utf-8", errors="replace") as f:
        content = f.read()

    clusters = []
    # Match "### Cluster N: M plays by K teams" and the signature line
    cluster_pattern = r"### Cluster (\d+): (\d+) plays by \d+ teams.*?\nTeams: (.*?)\n.*?Signature: \[(.*?)\]"
    for match in re.finditer(cluster_pattern, content, re.DOTALL):
        cluster_num = int(match.group(1))
        play_count = int(match.group(2))
        teams_str = match.group(3)
        sig_str = match.group(4)

        # Extract teams (comma-separated, may have commas in names; use first team only for now)
        team_names = [t.strip() for t in teams_str.split(",")]
        primary_team = team_names[0] if team_names else "unknown"

        # Parse signature: extract the numeric values from the sparse representation
        # The format is "7, 7, 7, 7, 7, 7, 7, 7, 7, 7]... (60 cards)"
        sig_nums = re.findall(r"\d+", sig_str.split("]")[0])  # Before the "...]" marker
        signature = tuple(int(x) for x in sig_nums)

        clusters.append({
            "cluster": cluster_num,
            "team": primary_team,
            "play_count": play_count,
            "signature": signature,
            "all_teams": team_names,
        })

    return clusters


def deduplicate_candidates(
    clusters: list[dict], existing_decks: dict[str, tuple[int, ...]]
) -> list[Candidate]:
    """Deduplicate clusters against existing decks. Return ranked list of candidates."""
    candidates = []
    existing_sigs = set(existing_decks.values())
    existing_sigs_to_names = {sig: name for name, sig in existing_decks.items()}

    for cluster in clusters:
        sig = cluster["signature"]
        if len(sig) != 60:
            # Skip incomplete signatures
            continue

        is_new = sig not in existing_sigs
        duplicate_of = existing_sigs_to_names.get(sig) if not is_new else None

        candidate = Candidate(
            cluster_num=cluster["cluster"],
            team_name=cluster["team"],
            play_count=cluster["play_count"],
            signature=sig,
            is_new=is_new,
            duplicate_of=duplicate_of,
        )
        candidates.append(candidate)

    # Sort by play count descending
    return sorted(candidates, key=lambda c: c.play_count, reverse=True)


def report_deduplication(candidates: list[Candidate], output_file: Path) -> None:
    """Write deduplication report to analysis/deck_explore_dedup.md"""
    new_candidates = [c for c in candidates if c.is_new]
    duplicates = [c for c in candidates if not c.is_new]

    with open(output_file, "w") as f:
        f.write("# Deck Exploration: Deduplication Report\n\n")
        f.write(f"**Total clusters analyzed:** {len(candidates)}\n")
        f.write(f"**New candidates:** {len(new_candidates)}\n")
        f.write(f"**Duplicates of existing decks:** {len(duplicates)}\n\n")

        f.write("## New Candidates (ranked by play count)\n\n")
        for c in new_candidates:
            f.write(f"### Cluster {c.cluster_num}: {c.team_name} ({c.play_count} plays)\n")
            f.write(f"- Signature: {c.signature[:10]}... (60 cards)\n\n")

        f.write("## Duplicates (existing decks)\n\n")
        for c in duplicates:
            f.write(f"- Cluster {c.cluster_num} ({c.team_name}, {c.play_count} plays) ")
            f.write(f"= `{c.duplicate_of}`\n")


def main():
    decks_dir = _ROOT / "decks"
    mining_file = _ROOT / "analysis" / "top_rated_mining.md"
    output_file = _ROOT / "analysis" / "deck_explore_dedup.md"

    print(f"Loading existing decks from {decks_dir}...")
    existing_decks = load_existing_decks(decks_dir)
    print(f"  Found {len(existing_decks)} existing deck signatures")

    print(f"Parsing mining results from {mining_file}...")
    clusters = parse_mining_results(mining_file)
    print(f"  Parsed {len(clusters)} clusters")

    print("Deduplicating...")
    candidates = deduplicate_candidates(clusters, existing_decks)

    new_count = sum(1 for c in candidates if c.is_new)
    dup_count = sum(1 for c in candidates if not c.is_new)
    print(f"  {new_count} new candidates, {dup_count} duplicates of existing decks")

    print(f"Writing report to {output_file}...")
    report_deduplication(candidates, output_file)

    print("\nTop 5 new candidates by play count:")
    for c in sorted(candidates, key=lambda x: x.play_count, reverse=True)[:5]:
        if c.is_new:
            print(f"  Cluster {c.cluster_num}: {c.team_name} ({c.play_count} plays)")

    # Return candidates for further processing
    return candidates


if __name__ == "__main__":
    main()
