# U90 on-evolve probe: both meta decks' engines were a named-but-unnamed ability class

## Question

L8/U90 asks two things: does the engine surface on-evolve abilities (Assemble
Alloy, Punk Up) as a distinct class at all, and does our own shipped pilot deck
ever trigger one? This is the same shape as the 0/554 ABILITY blind-spot find in
`analysis/move_ranking_diverges_ability_gap.md`: name a capability gap before
building anything to close it.

## What Assemble Alloy / Punk Up actually are

Both are the named engines of the two decklists the meta-copy work targets
(`decks/meta_archaludon.csv`, `decks/meta_grimmsnarl.csv`):

- **Archaludon ex** (card id 190, `[Ability] Assemble Alloy`): "When you play this
  Pokemon from your hand to evolve 1 of your Pokemon during your turn, you may
  attach up to 2 Basic {M} Energy cards from your discard pile to your {M} Pokemon
  in any way you like."
- **Marnie's Grimmsnarl ex** (card id 648, `[Ability] Punk Up`): "When you play
  this Pokemon from your hand to evolve 1 of your Pokemon during your turn, you
  may search your deck for up to 5 Basic {D} Energy cards and attach them to your
  Marnie's Pokemon in any way you like. Then, shuffle your deck."

Both fire once, at the moment the card is played from hand to evolve something,
never again that turn or later. That is a different trigger from the two ability
shapes `agents/heuristics.py` already knows about: a repeatable passive ability
(no limit, excluded from `PTCG_ABILITY` for loop safety) and a "once during your
turn" active ability (`_is_once_per_turn_ability`, the lever `analysis/ability_ab.md`
measured at +4.0pp offline). Neither text pattern matches "once during your turn",
so before this unit both cards resolved to `TAGGED` only via the generic
`ENERGY_ACCEL` tag ("attach" + "energy") -- present in the knowledge layer, but
with no way to tell an on-evolve trigger apart from, say, Waitress's repeatable
top-of-deck energy attach.

## What changed

Added `ON_EVOLVE_TRIGGER` to `agents/card_effects.py` TAG_VOCAB (v2, additive,
knowledge-only like `ENERGY_ACCEL`): fires on `"when you play this pok"` +
`"to evolve"`. Verified it now tags both engine cards without displacing the
existing tag:

```
190 Archaludon ex          ['ENERGY_ACCEL', 'ON_EVOLVE_TRIGGER']
648 Marnie's Grimmsnarl ex ['ENERGY_ACCEL', 'ON_EVOLVE_TRIGGER']
```

## Does our pilot ever trigger this class?

No. Checked every card in `decks/trolley.csv` and `decks/trolley_thick.csv` (the
shipped king and its A/B sibling): the only evolution line either deck plays is
Snover -> Mega Abomasnow ex, and Mega Abomasnow ex carries no effect text at all
(`heuristics._card_text` returns `None`, state `EMPTY`). Kyogre is a Basic. Neither
deck contains a card with an on-evolve ability, so `ON_EVOLVE_TRIGGER` never fires
against our own pilot's pool, and `PTCG_ABILITY` (whether on or off) has no
on-evolve case to reach regardless of trigger-detection quality.

This is a clean negative result, not a gap: the pilot lacks the CARD, not the
capability-to-recognize-it. Closing it would mean changing the deck to run an
on-evolve engine Pokemon, which is a deck-design question (out of scope for a
tag-vocabulary unit) rather than a heuristic-logic fix. Recorded here so a future
deck-design pass (or U93's transfer step) does not have to re-derive this from
scratch: if the deck ever adds a Stage 1/2 line with an on-evolve ability, the
knowledge layer will now surface it as `ON_EVOLVE_TRIGGER` rather than folding it
into the generic `ENERGY_ACCEL` bucket.

## Coverage side effect

The same v2 pass that added `ON_EVOLVE_TRIGGER` also closed the meta-deck coverage
gap this probe was piggybacked on (see `agents/card_effects.py` TAG_VOCAB v2 and
`tests/test_card_effects.py::test_meta_decks_fully_covered`):

```
meta_archaludon: coverage 0.667 (10/15) -> 1.000 (15/15)
meta_grimmsnarl: coverage 0.789 (15/19) -> 1.000 (19/19)
pool untagged fraction: 0.4917 (207/421) -> 0.4204 (177/421)
```

`analysis/tag_coverage_baseline.json` regenerated at `TAGS_VERSION "2"`; the
ratchet test only requires the fraction not rise, and it fell.
