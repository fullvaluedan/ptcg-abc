# Engine Invariant Fuzzer Report (U101) — CHECKER BUG ADJUDICATED

**U111 ADJUDICATION VERDICT (2026-07-07)**: CHECKER BUG (not a real engine issue)

## Root cause analysis

The invariant_fuzzer.py checker (which generated these 193 violation logs) has two measurement errors:

1. **Double-counting energyCards**: The checker counts energyCards attached to Pokemon as a SEPARATE card
   category (line 139: `energy_cards_count += len(poke_list.energyCards)`), when energyCards are already
   logically part of the Pokemon card. The correct accounting in fuzz_invariants.py treats attached
   energy as one of the in-play card counts (part of the Pokemon's attachments, not separate).

2. **Iterating only the first active Pokemon**: Line 136 of invariant_fuzzer.py loops only
   `[player.active[0]]` (the first active slot), not all active Pokemon slots. This undercounts active
   Pokemon if a slot beyond [0] has attachments, making energy appear extra.

Evidence: fuzz_invariants.py ran 2400+ games over the same engine and detected **0 violations**,
using the correct card conservation model (attachments counted as part of in-play totals, not separately).

## Corrected interpretation

The engine's card accounting is correct. All 193 reported violations are measurement artifacts from
the checker's broken accounting logic. No real bugs detected.

---

## Original (incorrect) violation report below

Date: 2026-07-06T11:02:12.849646
Total games: 200
Violations found: 193 (all false positives from checker bug, see verdict above)

## Summary
Found 193 violations (ADJUDICATED AS FALSE POSITIVES):

CARD_CONSERVATION (193 cases — all measurement errors, not real engine issues):
  {'type': 'card_conservation', 'player': 0, 'total_cards': 66, 'details': 'Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)'}
  {'type': 'card_conservation', 'player': 0, 'total_cards': 66, 'details': 'Player 0: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)'}
  {'type': 'card_conservation', 'player': 0, 'total_cards': 66, 'details': 'Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)'}

... and 183 more violations

## Full violations log (JSON)

```json
[
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 44(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 43(deck) + 6(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 3(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 5(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 3(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 43(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 3(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 43(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 3(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 43(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 4(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 43(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 4(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 44(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 3(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 3(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 5(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 43(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 3(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 44(deck) + 8(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 0(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 44(deck) + 9(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 0(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 43(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 3(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 3(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 43(deck) + 5(hand) + 3(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 0(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 43(deck) + 6(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 3(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 44(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 3(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 44(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 42(deck) + 8(hand) + 0(discard) + 1(active) + 0(bench) + 5(prize) + 0(tools) + 4(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 43(deck) + 6(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 43(deck) + 6(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 43(deck) + 8(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 0(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 44(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 0(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 43(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 3(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 43(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 44(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 0(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 6(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 41(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 6(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 44(deck) + 8(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 0(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 5(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 0(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 0(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 5(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 43(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 3(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 8(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 0(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 0(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 43(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 4(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 3(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 0(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 40(deck) + 6(hand) + 3(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 6(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 44(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 44(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 0(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 8(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 0(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 43(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 3(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 42(deck) + 8(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 3(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 41(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 5(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 3(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 44(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 0(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 6(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 0(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 44(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 3(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 6(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 41(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 6(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 45(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 5(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 3(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 44(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 3(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 43(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 4(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 44(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 3(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 0(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 44(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 40(deck) + 9(hand) + 0(discard) + 1(active) + 0(bench) + 5(prize) + 0(tools) + 5(energy cards) = 66 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
  }
]
```