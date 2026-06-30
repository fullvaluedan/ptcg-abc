# Two deck portfolio (U11)

A submission carries one deck (KTD7), so the portfolio is a Strategy concept and
a development hedge: build two decks that cover different parts of the field,
measure them against each other and the existing baseline, and submit whichever
the gauntlet ranks highest. This note records the concept, the matchup logic, and
the measured matrix that selects the deck to submit.

## The decks

All three share one proven trainer suite so the matrix isolates the Pokemon and
energy, not the support package: 4x Mega Signal, 4x Lillie's Determination,
4x Waitress, 2x Cyrano, 1x Maximum Belt (the ACE SPEC), then Pokemon and basic
energy.

### baseline (the incumbent): Mega Abomasnow ex water discard combo
Snover evolving into Mega Abomasnow ex (megaEx, 350 HP). Hammer-lanche costs two
energy and discards the top six cards, doing 100 damage for each Basic Water
Energy discarded. The deck floods 35 Basic Water Energy, so the top six average
roughly three water energy: a two energy attack that averages 300 plus damage off
a 350 HP body. Two Kyogre recycle the discarded energy with Riptide. This is a
genuinely strong tuned combo and is the bar the new decks are measured against.

### aggro: Mega Heracross ex grass tempo and mill
Four Mega Heracross ex (megaEx but Basic, so no evolution step and a more
consistent open than the baseline's Snover line). Mountain Ramming costs three
grass energy for 170 damage and discards the top two cards of the opponent's
deck, adding a deck out clock on top of the damage. Four Terapagos accelerate
energy (Prism Charge searches and attaches three basic energy at once) and trade
single prizes; three Chansey wall. The plan: come online fast off Terapagos, hit
170 every turn, and grind the opponent's deck down.

### control: fire type counter and prize trade
Four Gouging Fire ex and four Volcanion (single prize, 130 damage), mono fire.
The lever is type weakness: the aggro deck's Mega Heracross ex is weak to fire, so
Volcanion's 130 doubles to 260 and one shots a 280 HP Heracross for a single
prize, while Gouging Fire ex's Blaze Blitz (260, one shot per active stint) cleans
up. Fire is neutral into the baseline's water combo, so this deck is a deliberate
counter to grass aggression rather than an all rounder.

## Measured matrix (heuristic policy, 24 matches per pairing, alternating first)

Row deck's win rate against the column deck:

|            | vs aggro | vs control | vs baseline | overall |
|------------|---------:|-----------:|------------:|--------:|
| aggro      |        - |      45.8% |       54.2% |   50.0% |
| control    |    41.7% |          - |       25.0% |   33.3% |
| baseline   |    58.3% |      75.0% |           - |   66.7% |

Intervals are wide at 24 matches (roughly plus or minus 18 points); the table is
directional, and a few hundred match confirmation run is the next step before any
submission decision rests on it.

## What the matrix says

- The fire weakness counter works as intended. Before it, an attack only heuristic
  piloting a slow control deck lost about 80 percent to the grass tempo deck;
  routing the counter through type weakness moved the aggro versus control matchup
  to roughly even (42 to 46 percent each way). That swing is the portfolio's point:
  a deck that is otherwise weaker can be a correct answer to a specific archetype.
- The aggro deck is the strongest of the two new builds and is about even with the
  tuned baseline combo (within the interval), so it is a real contender, not a
  downgrade.
- The baseline combo still ranks highest overall. The arbiter (tools/deck_match.py)
  therefore selects baseline as the deck to submit today; the new decks are the
  hedge and the Strategy story, not yet a replacement.

## Why control underperforms in raw win rate

The live policy is the attack first heuristic, which rewards cheap repeatable
damage and cannot exploit disruption, healing, or prize denial. So a slow "control
the game" build collapses to "whoever hits hardest on a survivable body," which is
exactly what the baseline combo does best. The control deck earns its place only
through the weakness counter, not through control mechanics the current policy
cannot pilot. Once the search agent (and later loss data from the scout) drives
deck choice, a true disruption build can be revisited; for now the honest portfolio
is one strong tempo deck plus one type counter.

## Next steps

- Confirm the matrix over a few hundred matches per pairing for tight intervals.
- Re-run the matrix under the search policy, which may pilot the tanks better than
  the heuristic and shift the ranking.
- When the scout's loss data is available, tune the decks toward the buckets that
  actually cost games rather than by blind iteration.
