"""Validate a cabt deck for legality (U11).

Two layers, both required before a deck is trusted:

1. Construction rules in Python, for clear messages: exactly 60 cards, at most 4
   copies of any single non basic energy card, and at most 1 ACE SPEC. Basic
   energy is exempt from the copy limit (a deck may run dozens of one energy).

2. The engine's own check, which is ground truth. battle_start returns
   errorPlayer == -1 for a legal deck and the offending seat plus an errorType
   otherwise. We pair the deck under test in seat 0 against a known legal partner
   (the baseline deck) so only seat 0 can fault, then free the battle.

This is a development tool. It is never shipped with the agent.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Card data is a genuine dependency of the rule layer; cards.get_card is itself
# lazy, so importing it here does not load the native library at import time.
from ptcg_agent.cards import get_card  # noqa: E402

DECK_SIZE = 60
MAX_COPIES = 4
CARD_TYPE_BASIC_ENERGY = 5

# Informational only: the engine's errorType codes observed during recon.
_ERROR_TYPE_NAMES = {
    2: "too many copies of a card",
    3: "no basic Pokemon",
    4: "more than one ACE SPEC",
}


def read_deck(path) -> list:
    """Read a deck file: one card id per non blank line."""
    text = Path(path).read_text()
    return [int(line) for line in text.split("\n") if line.strip()]


def rule_errors(deck) -> list:
    """Deck construction violations, as human readable strings (empty if legal).

    Pure Python over the card database; does not touch the native engine, so it
    is safe to call anywhere and gives a precise reason a deck is illegal. One
    card lookup per distinct id covers both the copy limit and the ACE SPEC count.
    """
    errors = []
    if len(deck) != DECK_SIZE:
        errors.append(f"deck has {len(deck)} cards, must be exactly {DECK_SIZE}")
    counts = Counter(deck)
    ace = 0
    for card_id, n in sorted(counts.items()):
        card = get_card(card_id)
        is_basic_energy = card is not None and int(card.cardType) == CARD_TYPE_BASIC_ENERGY
        if n > MAX_COPIES and not is_basic_energy:
            errors.append(f"card {card_id} appears {n} times, max {MAX_COPIES}")
        if card is not None and card.aceSpec:
            ace += n
    if ace > 1:
        errors.append(f"{ace} ACE SPEC cards, max 1")
    return errors


def engine_check(deck, partner=None) -> dict:
    """Run the deck through the engine's battle_start legality check (seat 0).

    Returns a dict with ok (errorPlayer == -1 for our seat), the raw errorPlayer
    and errorType, and a name for the errorType when known. The partner deck
    (default: the baseline deck) sits in seat 1 and is known legal, so any fault
    is attributed to the deck under test. The battle is always freed.
    """
    from ptcg_agent.engine import ensure_official_cg

    ensure_official_cg()
    from cg.game import battle_finish, battle_start

    if partner is None:
        partner = read_deck(_ROOT / "decks" / "baseline.csv")

    # battle_start raises on a non 60 deck; the rule layer reports that cleanly.
    if len(deck) != DECK_SIZE or len(partner) != DECK_SIZE:
        return {"ok": False, "errorPlayer": 0, "errorType": None, "reason": "deck size"}

    obs, sd = battle_start(list(deck), list(partner))
    result = {
        "ok": sd.errorPlayer == -1,
        "errorPlayer": sd.errorPlayer,
        "errorType": sd.errorType,
        "reason": _ERROR_TYPE_NAMES.get(sd.errorType) if sd.errorPlayer != -1 else None,
    }
    if obs is not None:
        battle_finish()
    return result


def validate(deck) -> dict:
    """Full legality verdict: construction rules and the engine check combined.

    Skips the native engine round trip when the construction rules already prove
    the deck illegal (engine is then None); a clean deck still gets the engine's
    ground truth check.
    """
    rules = rule_errors(deck)
    engine = engine_check(deck) if not rules else None
    return {
        "ok": not rules and engine["ok"],
        "rule_errors": rules,
        "engine": engine,
    }


def _format(name: str, verdict: dict) -> str:
    lines = [f"{name}: {'LEGAL' if verdict['ok'] else 'ILLEGAL'}"]
    for e in verdict["rule_errors"]:
        lines.append(f"  rule: {e}")
    eng = verdict["engine"]
    if eng is not None and not eng["ok"]:
        detail = eng.get("reason") or f"errorType {eng['errorType']}"
        lines.append(f"  engine: seat {eng['errorPlayer']} fault ({detail})")
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        argv = [str(_ROOT / "decks" / "baseline.csv")]
    rc = 0
    for path in argv:
        verdict = validate(read_deck(path))
        print(_format(Path(path).name, verdict))
        if not verdict["ok"]:
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
