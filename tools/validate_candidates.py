"""Validate legality of the U39 mined deck candidates.

Applies the rule-layer validation (construction rules, card database lookup)
to each candidate CSV extracted by U39. Reports which candidates are legal
and which have rule violations. Skips the engine check (not available in loop
environment); rule layer is sufficient for mechanical legality gates.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ptcg_agent.cards import get_card

DECK_SIZE = 60
MAX_COPIES = 4
CARD_TYPE_BASIC_ENERGY = 5


def read_deck(path) -> list:
    """Read a deck file: one card id per non-blank line."""
    text = Path(path).read_text()
    return [int(line) for line in text.split("\n") if line.strip()]


def rule_errors(deck) -> list:
    """Deck construction violations (pure Python, no engine dependency)."""
    errors = []
    if len(deck) != DECK_SIZE:
        errors.append(f"deck has {len(deck)} cards, must be {DECK_SIZE}")
    counts = Counter(deck)
    ace = 0
    unknown_cards = []
    for card_id, n in sorted(counts.items()):
        card = get_card(card_id)
        if card is None:
            unknown_cards.append(card_id)
        else:
            is_basic_energy = int(card.cardType) == CARD_TYPE_BASIC_ENERGY
            if n > MAX_COPIES and not is_basic_energy:
                errors.append(f"card {card_id} appears {n} times, max {MAX_COPIES}")
            if card.aceSpec:
                ace += n
    if unknown_cards:
        errors.append(f"unknown card IDs: {unknown_cards}")
    if ace > 1:
        errors.append(f"{ace} ACE SPEC cards, max 1")
    return errors


def validate_candidate(deck_path) -> dict:
    """Validate a single candidate deck."""
    try:
        deck = read_deck(deck_path)
        errors = rule_errors(deck)
        return {
            "ok": len(errors) == 0,
            "errors": errors,
            "deck_size": len(deck),
        }
    except Exception as e:
        return {
            "ok": False,
            "errors": [f"Exception reading deck: {e}"],
            "deck_size": None,
        }


def main(argv=None) -> int:
    decks_dir = _ROOT / "decks"
    candidate_files = sorted(decks_dir.glob("candidate_*.csv"))

    if not candidate_files:
        print("No candidate_*.csv files found in decks/")
        return 1

    legal = []
    illegal = []

    for path in candidate_files:
        verdict = validate_candidate(path)
        if verdict["ok"]:
            legal.append(path.stem)
        else:
            illegal.append((path.stem, verdict["errors"]))

    # Report summary
    print(f"\n=== Candidate Legality Validation ===\n")
    print(f"Checked: {len(candidate_files)} candidates")
    print(f"Legal:   {len(legal)}")
    print(f"Illegal: {len(illegal)}\n")

    if legal:
        print("LEGAL CANDIDATES:")
        for name in legal:
            try:
                print(f"  PASS {name}")
            except UnicodeEncodeError:
                print(f"  PASS {name.encode('ascii', 'replace').decode('ascii')}")

    if illegal:
        print("\nILLEGAL CANDIDATES:")
        for name, errors in illegal:
            try:
                print(f"  FAIL {name}")
                for err in errors:
                    print(f"    - {err}")
            except UnicodeEncodeError:
                print(f"  FAIL {name.encode('ascii', 'replace').decode('ascii')}")
                for err in errors:
                    print(f"    - {err}")

    # Write report to analysis/
    report_path = _ROOT / "analysis" / "candidate_validation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Candidate Legality Validation Report\n\n")
        f.write(f"**Date**: {Path(__file__).parent.parent / 'analysis'}  \n")
        f.write(f"**Total Candidates**: {len(candidate_files)}  \n")
        f.write(f"**Legal**: {len(legal)}  \n")
        f.write(f"**Illegal**: {len(illegal)}\n\n")

        if legal:
            f.write("## Legal Candidates\n\n")
            for name in legal:
                try:
                    f.write(f"- {name}\n")
                except UnicodeEncodeError:
                    f.write(f"- {name.encode('ascii', 'replace').decode('ascii')}\n")

        if illegal:
            f.write("\n## Illegal Candidates\n\n")
            for name, errors in illegal:
                try:
                    f.write(f"- **{name}**\n")
                except UnicodeEncodeError:
                    f.write(f"- **{name.encode('ascii', 'replace').decode('ascii')}**\n")
                for err in errors:
                    f.write(f"  - {err}\n")

    print(f"\nReport written to: {report_path}")
    return 0 if len(illegal) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
