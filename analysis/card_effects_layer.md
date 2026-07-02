# Card-effect knowledge layer and coverage gate (U33 / MSR-3)

Date: 2026-07-02. Branch: feat/phase1-baseline.

## What landed

A stdlib card-knowledge layer, `agents/card_effects.py`, that names in one place
the effect signals the heuristic used to re-scan inline. The pilot's four
card-aware text predicates now delegate to it, and a coverage meter
(`tools/tag_coverage.py`) audits which cards in a deck the layer understands.

- `TAG_VOCAB` (8 tags), `TAGS_VERSION = "1"`.
- `tag_text(text)`: pure, total (None/empty -> empty frozenset), never raises.
- `resolve(card_present, text)`: three-state degradation
  (UNKNOWN_CARD / UNTAGGED_EFFECT / EMPTY, plus TAGGED); only EMPTY and TAGGED are
  covered.

The layer takes already-fetched text as input and never imports cg or looks up a
card, so it is one-directional (heuristics imports card_effects, never the
reverse) and testable without the native engine. It ships flat next to `main.py`;
`heuristics.py` imports it with the same `try: from agents import ... except
ImportError: import ...` dual path the agent entrypoint uses.

## The tags

| tag | text signal | consumed by |
| --- | --- | --- |
| DRAW | `\bdraw` | `_drills_deck` |
| SEARCH_TO_HAND | "into your hand" | `_drills_deck` |
| RECOVERS_FROM_DISCARD | "from your discard pile" and "into your hand" and not "your deck" | `_drills_deck` (carve-out) |
| DISCARDS_FROM_DECK | "discard" and ("of your deck" or "your deck for") | `_drills_deck` |
| BENCH_BASIC_FROM_DECK | "search your deck" and "onto your bench" and "basic" and "pok" | `_benches_basic_from_deck` |
| RARE_CANDY_EVOLVE | "stage 2" and "skipping the stage 1" | `_evolves_basic_to_stage2` |
| ONCE_PER_TURN | "once during your turn" | `_is_once_per_turn_ability` |
| ENERGY_ACCEL | "attach" and "energy" | knowledge-only (coverage) |

The first seven reproduce the exact boolean of the legacy inline scans; the type
gate (Item/Supporter for the three trainer predicates) stays in `heuristics.py`.
ENERGY_ACCEL is not read by any frozen predicate: it exists so an energy-attach
trainer (Waitress) resolves to TAGGED rather than an UNTAGGED_EFFECT gap, lifting
the target deck to full coverage without touching pilot behavior.

## Behavior is frozen (the load-bearing test)

`tests/test_card_effects.py::test_pool_wide_equivalence_all_four_predicates`
holds a frozen copy of every legacy inline scan and asserts the delegated
`heuristics._drills_deck / _benches_basic_from_deck / _evolves_basic_to_stage2 /
_is_once_per_turn_ability` return the identical boolean card-for-card over the
entire pool. That is what makes the delegation ship-safe: a tag definition may not
drift any predicate's answer before the golden test breaks. A drift lock pins
TAGS_VERSION and TAG_VOCAB (mirrors the engine-drift STATE LOCK). All ~60 existing
heuristic tests pass unmodified; the grader exec-load test now bundles
`card_effects.py` alongside `heuristics.py` (`_HEUR_EXTRAS`) so a missing-module
regression is caught before it can error a submission.

## Coverage meter and MSR-3 gate

`tools/tag_coverage.py`:
- `deck_coverage(deck_ids)`: per-state counts and the uncovered ids, over distinct
  cards (so a basic energy's 33 copies do not dominate the fraction).
- `deck_covered_100pct(deck_ids)`: the gate. No deck-AWARE pilot build (U37 seeds,
  U40/U41 ranker) may spend a scarce ladder slot unless the target deck is fully
  covered; a pilot that keys on tags must not be blind to a card it will play.
  Advisory now (no build reads it yet), consumed when the aware pilot lands.
- `pool_untagged_fraction()`: the ratchet. Recorded in
  `analysis/tag_coverage_baseline.json`; a test asserts the live value never rises,
  so a vocabulary regression is caught.

### Numbers (2026-07-02, TAGS_VERSION 1)

- target deck **trolley_thick**: coverage **1.000** (10/10 distinct; 6 TAGGED
  [Precious Trolley, Mega Signal, Ultra Ball, Cyrano, Lillie's Determination,
  Waitress], 4 EMPTY [Kyogre, Snover, Mega Abomasnow ex, basic W energy]).
- pool untagged fraction **0.4917** (207 / 421 effect-bearing cards). Expected to
  be high: the vocabulary is intentionally minimal (only what the pilot uses), and
  the ratchet only lets it fall as U36/U37 grow it.

## Ship note

Every heuristic-bearing submission now bundles two support modules, not one:
`--extra agents/heuristics.py --extra agents/card_effects.py`. The grader test's
`_HEUR_EXTRAS`/`_SEARCH_EXTRAS` are the canonical extras lists and enforce this.
