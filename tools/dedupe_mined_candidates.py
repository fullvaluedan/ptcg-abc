"""Dedupe mined deck candidates against existing decks and identify new candidates."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
MINING_DATA = _ROOT / "data" / "derived" / "top_rated_decks.json"
DECKS_DIR = _ROOT / "decks"
OUTPUT_DEDUP_REPORT = _ROOT / "analysis" / "mined_candidates_dedup_report.md"


def load_existing_decks():
    """Load all existing deck CSVs and compute their signatures."""
    existing = {}
    for deck_file in DECKS_DIR.glob("*.csv"):
        deck_name = deck_file.stem
        with open(deck_file, "r") as f:
            cards = [int(line.strip()) for line in f if line.strip()]
        if len(cards) == 60:
            sig = tuple(sorted(cards))
            existing[deck_name] = {
                "path": deck_file,
                "cards": cards,
                "signature": sig,
            }
    return existing


def load_mined_decks():
    """Load mined decks from top_rated_decks.json."""
    with open(MINING_DATA, "r") as f:
        data = json.load(f)

    mined = []
    for team, decks_list in data.get("team_decks", {}).items():
        for i, deck_info in enumerate(decks_list):
            sig = tuple(deck_info.get("signature", []))
            if len(sig) == 60:  # Only valid 60-card decks
                mined.append(
                    {
                        "team": team,
                        "deck_index": i,
                        "cards": list(sig),  # Already a sorted list
                        "signature": sig,
                        "play_count": deck_info.get("count", 0),
                    }
                )
    return mined


def find_duplicates_and_new(existing, mined):
    """Identify which mined decks are duplicates and which are new.

    Returns:
        (duplicates, new): lists of mined decks
            duplicates: [(mined_idx, existing_deck_name), ...]
            new: [mined_idx, ...]
    """
    existing_sigs = {
        deck["signature"]: name for name, deck in existing.items()
    }

    duplicates = []
    new = []

    for idx, mined_deck in enumerate(mined):
        sig = mined_deck["signature"]
        if sig in existing_sigs:
            duplicates.append((idx, existing_sigs[sig]))
        else:
            new.append(idx)

    return duplicates, new


def save_new_candidate_csv(cards, team_name, candidate_name):
    """Save a new candidate deck as a CSV file."""
    output_path = DECKS_DIR / f"{candidate_name}.csv"
    with open(output_path, "w") as f:
        for card_id in cards:
            f.write(f"{card_id}\n")
    return output_path


def generate_report(existing, mined, duplicates, new):
    """Generate a markdown report of the deduplication."""
    lines = [
        "# Mined Candidate Deduplication Report",
        "",
        "## Summary",
        f"- Existing deck signatures: {len(existing)}",
        f"- Mined deck signatures: {len(mined)}",
        f"- Duplicates found: {len(duplicates)}",
        f"- New candidates: {len(new)}",
        "",
    ]

    lines.append("## Duplicates")
    lines.append("")
    if duplicates:
        lines.append("| Mined Team | Mined Deck Index | Play Count | Matches Existing Deck |")
        lines.append("|---|---|---|---|")
        for mined_idx, existing_name in sorted(duplicates):
            mined_deck = mined[mined_idx]
            lines.append(
                f"| {mined_deck['team']} | {mined_deck['deck_index']} | "
                f"{mined_deck['play_count']} | {existing_name} |"
            )
    else:
        lines.append("No exact duplicates found.")
    lines.append("")

    lines.append("## New Candidates (by play count)")
    lines.append("")
    if new:
        lines.append("| Team | Deck Index | Play Count | Candidate Name |")
        lines.append("|---|---|---|---|")
        new_sorted = sorted(
            [(i, mined[i]) for i in new],
            key=lambda x: x[1]["play_count"],
            reverse=True,
        )
        for idx, (mined_idx, mined_deck) in enumerate(new_sorted):
            candidate_name = (
                f"candidate_{mined_deck['team'].lower().replace(' ', '_')}"
            )
            lines.append(
                f"| {mined_deck['team']} | {mined_deck['deck_index']} | "
                f"{mined_deck['play_count']} | {candidate_name} |"
            )
    else:
        lines.append("No new candidates found.")
    lines.append("")

    return "\n".join(lines)


def main():
    """Main: dedupe mined candidates and report."""
    existing = load_existing_decks()
    mined = load_mined_decks()
    duplicates, new = find_duplicates_and_new(existing, mined)

    report = generate_report(existing, mined, duplicates, new)

    with open(OUTPUT_DEDUP_REPORT, "w", encoding="utf-8") as f:
        f.write(report)

    # Write summary to stdout as plain ASCII
    summary = [
        f"Deduplication complete:",
        f"  Existing decks: {len(existing)}",
        f"  Mined decks: {len(mined)}",
        f"  Duplicates: {len(duplicates)}",
        f"  New candidates: {len(new)}",
        f"  Report saved to {OUTPUT_DEDUP_REPORT}",
    ]
    for line in summary:
        print(line)


if __name__ == "__main__":
    import sys

    if "--create-candidates" in sys.argv:
        existing = load_existing_decks()
        mined = load_mined_decks()
        _, new = find_duplicates_and_new(existing, mined)

        created = []
        for mined_idx in new:
            mined_deck = mined[mined_idx]
            team = mined_deck["team"]
            # Sanitize candidate name: lowercase, replace spaces with _, remove non-ASCII
            candidate_name = f"candidate_{team.lower().replace(' ', '_').replace('&', 'and')}"
            try:
                candidate_name.encode("ascii")
            except UnicodeEncodeError:
                # Skip Unicode team names for now
                continue

            # Skip if this candidate already exists
            if (DECKS_DIR / f"{candidate_name}.csv").exists():
                continue

            path = save_new_candidate_csv(
                mined_deck["cards"], team, candidate_name
            )
            created.append((candidate_name, mined_deck["play_count"]))

        if created:
            print(f"Created {len(created)} new candidate CSV files")
    else:
        main()
