# Engine Invariant Fuzzer Report (U101)

Date: 2026-07-06T10:25:36.946507
Total games: 50
Violations found: 49

## Summary
Found 49 violations:

CARD_CONSERVATION (49 cases):
  {'type': 'card_conservation', 'player': 0, 'total_cards': 66, 'details': 'Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)'}
  {'type': 'card_conservation', 'player': 1, 'total_cards': 59, 'details': 'Player 1: 43(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 3(energy cards) = 59 (expected 60)'}
  {'type': 'card_conservation', 'player': 0, 'total_cards': 66, 'details': 'Player 0: 46(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)'}

... and 39 more violations

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
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 43(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 3(energy cards) = 59 (expected 60)"
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
    "details": "Player 1: 42(deck) + 6(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 3(energy cards) = 59 (expected 60)"
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
    "details": "Player 1: 45(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 0,
    "total_cards": 66,
    "details": "Player 0: 41(deck) + 9(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 3(energy cards) = 66 (expected 60)"
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
    "details": "Player 0: 44(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 3(energy cards) = 66 (expected 60)"
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
    "details": "Player 0: 45(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
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
    "details": "Player 1: 44(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
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
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
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
    "details": "Player 1: 42(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 4(energy cards) = 59 (expected 60)"
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
    "details": "Player 1: 43(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 42(deck) + 6(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 3(energy cards) = 59 (expected 60)"
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
    "details": "Player 1: 45(deck) + 4(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
  },
  {
    "type": "card_conservation",
    "player": 1,
    "total_cards": 59,
    "details": "Player 1: 42(deck) + 8(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
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
    "details": "Player 1: 45(deck) + 5(hand) + 0(discard) + 1(active) + 1(bench) + 6(prize) + 0(tools) + 1(energy cards) = 59 (expected 60)"
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
    "details": "Player 1: 44(deck) + 6(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 2(energy cards) = 59 (expected 60)"
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
    "details": "Player 0: 46(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 0(energy cards) = 66 (expected 60)"
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
    "details": "Player 0: 45(deck) + 7(hand) + 0(discard) + 1(active) + 0(bench) + 6(prize) + 0(tools) + 1(energy cards) = 66 (expected 60)"
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
  }
]
```