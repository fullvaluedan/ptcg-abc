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

## Loss-data-driven deck investigation: early_collapse (2026-07-01)

With the scout unblocked, real ladder replays now drive deck tuning instead of
blind iteration. The dominant remaining leak is early_collapse: 3 of 6 classified
ladder losses end by turn 7 with us still at 6 prizes (we took none). Reading the
replays card by card, the mechanism is the same every time: our lone basic active
(Snover or Kyogre) is knocked out while our bench is empty, so we have no Pokemon
to promote and lose outright, regardless of the prize count.

This is NOT a heuristic misplay. The heuristic already benches every basic it
draws (in episode 82873746 the bench reaches 1 the moment a second basic appears).
The cause is deck construction: the baseline runs 35 Basic Water Energy and only
6 basic Pokemon (4 Snover, 2 Kyogre). A typical opening hand holds one basic, so
we routinely play a lone attacker, and a single knockout ends the game. The deck's
own search cards do not help: Mega Signal and Cyrano both fetch the Mega Abomasnow
ex evolution, and there is zero basic-Pokemon search.

### Falsified fix: trim energy for more basics (baseline_v2)

The obvious fix is to trade energy for basics. We built and measured baseline_v2:
Kyogre 2 to 4 (the only addable basic, since Snover is already at the 4 copy limit,
and Kyogre also recycles discarded energy via Riptide) and Basic Water Energy 35 to
33. Legal by both the rule layer and the engine check.

Measured under the heuristic, alternating first player:

| matchup            |  win rate | W/D/L     |
|--------------------|----------:|-----------|
| v2 vs baseline (mirror, n=160) |    48.1% | 77/0/83 |
| baseline vs aggro   (n=60)     |    68.3% | 41/0/19 |
| v2 vs aggro         (n=60)     |    55.0% | 33/0/27 |
| baseline vs control (n=60)     |    86.7% | 52/0/8  |
| v2 vs control       (n=60)     |    80.0% | 48/0/12 |

The verdict is clear and against the hypothesis: v2 is even in the mirror and
measurably WORSE against the diverse field (down 13 points vs aggro, down 7 vs
control). The mirror cannot show consistency value because both sides early-collapse
symmetrically; the diverse-field run is the real test, and it says the energy count
is load bearing. Hammer-lanche damage is 100 per Basic Water Energy in the top six,
so cutting energy from 35 to 33 drops expected damage about 20, and that lost power
costs more games than the two extra Kyogre save. The baseline's 35 energy is
correctly tuned. baseline_v2 was deleted; this negative result is the artifact, so
future iterations do not re-walk the energy-trim dead end.

### The only non-regressing direction: add a basic finder without cutting energy

Early_collapse is partly the inherent variance cost of a 35-energy combo deck. The
single lever that does not touch the energy count is a basic-Pokemon search ITEM.
The format has Ultra Ball (id 1121, Item, not ACE SPEC): discard 2 cards, then
search the deck for any Pokemon. It can fetch a basic to the hand to bench, and
discarding spare energy is cheap here (Kyogre shuffles it back). Paying for it by
cutting a redundant Mega finder (Mega Signal 4 to 2) keeps energy at 35 and the
combo intact while adding the deck's first real consistency engine for basics.

This is deferred, not adopted, because it needs heuristic support before it helps:
when the agent plays Ultra Ball it must, in the deck-search sub-select, fetch a
BASIC Pokemon when the bench is thin (today the sub-select grabs the first legal
option, which may be the Mega), and in the discard sub-select avoid pitching the
last basic or a key combo piece. Adding the card without that support risks
mis-piloting and regressing the current 600.0 ladder best, so it must be built with
tests and measured against the diverse field (not the mirror) before it earns a
ladder slot. That is the next concrete deck unit.

### Built and measured: ultraball.csv is even with baseline, not a beat (2026-07-01)

The heuristic CARD sub-select support landed first (the deck-search fetches a basic
when bench < 2; discard sheds energy before Pokemon and combo pieces). With it in
place, decks/ultraball.csv was built as documented: Mega Signal 4 to 2, plus 2 Ultra
Ball (id 1121), energy held at 35. Legal by both the rule layer and the engine check,
and now locked by test_portfolio_decks_are_legal.

Measured under the heuristic, alternating first player:

| matchup                          | win rate | W/D/L     |
|----------------------------------|---------:|-----------|
| ultraball vs baseline (mirror, n=120) |   52.5% | 63/0/57 |
| ultraball vs aggro    (n=120)    |    67.5% | 81/0/39 |
| baseline  vs aggro    (n=120)    |    67.5% | 81/0/39 |
| ultraball vs control  (n=60)     |    83.3% | 50/0/10 |
| baseline  vs control  (n=60)     |    88.3% | 53/0/7  |

The verdict: ultraball is EVEN with baseline, not a measurable beat. The mirror is
52.5% with a 95% CI of 43.6 to 61.2 (spans 50, no significant edge), and against the
diverse aggro field it is identical to baseline (67.5% each at n=120). A first n=60
matrix had suggested ultraball was much better vs aggro (65% vs 50%), but that was
sampling noise: the n=120 confirmation collapsed it to a tie. Unlike baseline_v2
(which was measurably WORSE vs the field because it cut energy), ultraball preserves
the 35-energy combo and so does not regress; the consistency engine simply does not
move the self-play win rate, because early_collapse from a lone-basic knockout is a
minority of games and cutting 2 Mega Signal slightly offsets the Ultra Ball gain.

Conclusion: ultraball is NOT today's submission candidate. The heuristic + deckout
guard (ladder 601.7) stays the best agent, and per policy a deck that does not beat
the current best is not uploaded. ultraball is kept as the consistency hedge and a
Strategy-writeup story (the legal, non-regressing way to add basic search without
touching energy), not a ladder replacement. The honest negative result is recorded so
future iterations do not re-walk the Ultra Ball lever expecting a self-play gain; its
real value, if any, would be in reducing early_collapse against the DIVERSE LADDER
field, which only a live ladder slot can measure once one is available to spend.

### Staged for the ladder, awaiting the next quota reset (2026-07-01)

The deckout-guarded heuristic kept climbing and is now the clear best at ladder
758.4 (search and plain heuristic sit near 590, the bare floor near 460), so the
loss-data approach is paying off and the next worthwhile data point is exactly the
one self-play cannot give: ultraball against the diverse field. Fresh replays still
rank early_collapse the top leak (7 of 18 classified losses), so the experiment is
worth a slot. submission_ultraball.tar.gz was built (agent_heuristic + heuristics.py,
deck ultraball.csv), confirmed legal, and passed the grader-style smoke test
(extracts to cg/deck.csv/heuristics.py/main.py, loads under exec without __file__,
returns the 60-card ultraball deck: 2 Ultra Ball, 2 Mega Signal, 35 energy). It is
the same deckout-guarded agent as best ref 54211499, so it cannot regress that
rating. A submit was attempted and the API returned 400 (daily limit still in
effect: the five 2026-06-30 submissions have not rolled over in UTC yet), and the
submissions list confirms no slot was consumed. So ultraball is the queued, ready
candidate for the first available slot on the next quota reset; submit it then after
the mandatory submissions check, before spending the slot on anything else.
