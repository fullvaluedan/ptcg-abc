# A heuristic hardened by real-engine search and ladder forensics

A Pokemon TCG agent built on three commitments: decide by the competition's exact
rules, refuse to lose to its own blunders, and tune by real ladder loss data
rather than by guesswork. It runs fully offline, never crashes, and is honest
about its failure modes, including the one that mattered most: the discovery, from
our own replays, that the scored engine does not let our search run, redirecting the
whole climb onto the levers that actually execute.

## The core idea, and the constraint that reshaped it

The cabt SDK ships a forward model, `search_begin`/`search_step`/`search_release` in
`cg/api.py`, backed by the native engine. Given a determinized full state (our hidden
cards plus a guess at the opponent's), it plays out moves at the same speed and rules
as the scored match. The founding decision was to drive that model rather than
reimplement the game in Python. A hand-written rules engine is the largest risk in any
TCG search agent: any divergence from the real rules silently poisons every rollout.
Using the engine's own model removes that risk, so in self-play our rollouts are not an
approximation of the game, they are the game.

That decision built a strong self-play agent. But the central honest finding
is that the *scored* engine withholds the forward model at match time, so search is
dormant on the ladder and the heuristic underneath is what actually plays. The search
machinery remains real and measured: the crucible the laddering agent was forged in,
not a claim about what runs on Kaggle.

## How the agent decides, step by step

**The observation.** The engine hands the agent a typed observation each turn: the
current decision (`select`), the events since the last (`logs`), and the full visible
`State`. Opponent hand and face-down cards are `None`, but their counts are visible.
Every decision is a `select` over typed options (PLAY, ATTACH, EVOLVE, ATTACK, RETREAT,
END, and card or number sub-selections); the agent returns indices into that list.
Because the engine only ever offers legal options, a correctly typed response is always
legal.

**The heuristic floor (this is what ladders).** A rules-aware heuristic is strong on
its own and, as it turned out, carries every scored match. Its priorities are
simple and progress-guaranteeing: take a knockout if one is available, otherwise
evolve, develop the bench, attach energy to the attacker, retreat an endangered
active when a healthier bench Pokemon exists, and finally attack or end the turn. The
lethal check is real: opponent HP against our best attack's damage, adjusted for the
engine's x2 weakness and flat resistance. Card sub-selections are handled with intent:
on a deck search with a thin bench it fetches a Basic so a knocked-out lone active has
backup; on a discard cost it sheds surplus energy and spares the combo line. Abilities
are deprioritized, because a stateless agent that prefers a repeatable ability over
ending its turn can loop forever; every chosen action consumes a resource, so the turn
always advances. On its own this heuristic beats the random-legal baseline about 89
percent of the time over 200 gauntlet matches with zero illegal moves.

**Determinization and search (the self-play method).** Above the heuristic sits
determinized Monte Carlo search. The sampler reconstructs a full state the forward
model will accept: our own deck and prizes exactly, the opponent's deck, hand, prize,
and face-down active sampled from a prior so all visible counts match and every
revealed card sits in a zone it could be in. The prior defaults to a mirror and is
sharpened by archetype identification: as the opponent reveals cards, the agent
matches them against archetype signatures and biases the sample toward a consistent
decklist, always merging in what we have seen so the belief never contradicts the
board. For each candidate move it rolls out to a terminal result with the heuristic as
the rollout policy for both players, then picks the highest average win rate. In the
gauntlet this search beats the strong heuristic about 66 to 70 percent head to head,
near 0.2 seconds per decision.

**The safety layer (low variance).** The rating is margin-independent: a one-prize
win and a blowout score the same, so the cheapest points come from never throwing a
winnable game. A deterministic layer takes a guaranteed knockout before search ever
runs, caps voluntary draws when the deck is low so we never deck ourselves out, and
hard-guards the 600-second per-match thinking bank so cumulative time can never reach
a timeout (an automatic loss). Every path ends in a guaranteed legal fallback, because
a single exception forfeits the match. Crucially, the lethal check and deckout guard
live in the heuristic itself, so they protect the agent on the ladder whether or not
search is available.

## The discovery: search is dormant on the scored ladder

Once agents were on the ladder, a scout tool pulled our own replays. The forensic
detail that cracked the case: the engine sets `actTimeout: 0` and gives each player a
single ~600s overage bank, so the drop in that bank per decision is the real
wall-clock thinking time. In every search-agent replay, our searchable decisions drew
only 0.02 to 0.05 seconds from the bank, while the same observations replayed locally
take 500 to 830 milliseconds because search runs to its budget. Search was not running
at all on Kaggle.

The cause is precise and reproducible. The 0.02s cost is the clue: a forward model
that failed at call time would still burn the full budget retrying determinizations,
so a 0.02s cost means the agent raises *before* the loop, on the import of
`search_begin`. Yet the heuristic imports `all_card_data` and `all_attack` from the
same `cg.api` and plays card-aware moves on the ladder, so `cg.api` itself imports
fine and carries the card database; it simply does not expose the `search_*` forward
model at match time. We reproduced it exactly: a `cg.api` with card data but no
`search_*` falls back in a tenth of a millisecond, while the full SDK takes 833.

So the agent now probes for the forward model and gates search on it as a first-class,
tested condition rather than a swallowed import error. The determinization, archetype
priors, and endgame search are inert on the ladder by an engine constraint: valid for
self-play and as design tools, but not movers of the public score. A search build and
a heuristic build, different on paper, sit statistically tied around 590 precisely
because they execute the same heuristic on the scored engine. That is why the rest of
the work targets the levers that do run every match: the heuristic policy and the deck.

## Tuned by real loss data, not by guessing

The same replay discipline changed the laddering agent twice more. First, the
dominant real loss was self-deckout: we milled ourselves to death, once while ahead
on prizes. The deckout guard, which had only lived in the search layer, was extracted
into shared heuristic logic so it now protects every scored match, inert in normal
play and only capping a voluntary over-draw when the deck runs critically low.
The proof it worked lives in the loss buckets, not the leaderboard number. Across
fresh ladder pulls of every heuristic-family submission, self-deckout fell from the
single most common loss to near zero, and the deck-thinness collapse it had masked
surfaced as the new top leak. The TrueSkill point scores are too noisy to trust here:
over small, unequal samples the heuristic builds cluster between roughly 460 and 590
and reorder between pulls, so we trust the measured bucket shift over the leaderboard
wobble. A guard living inside the heuristic, the layer that executes every match,
erased a real loss mode the dormant search could never have touched.

Second, with deckouts fixed, the next leak was early collapse: about half the
remaining losses ended by turn seven with all six prizes still ours, a lone basic
attacker knocked out while the bench was empty. This is deck thinness, not misplay,
and the heuristic cannot reach it: it already benches every Basic it draws, so an
empty bench means the hand held no second Basic. The fix has to be in the deck. The
honest part is the falsified attempts: trading energy for a basic lost more games to
reduced damage than the extra basic saved, and an Ultra Ball fetch measured
even but was retired because its discard cost cannot be afforded by turn three, when
the collapse lands. The chosen lever is Precious Trolley, an item
that puts a Basic straight onto the bench for free, exactly the turn the collapse would
fire, on the same 35-energy deck so the combo is untouched. On a scored slot it became
our best result: publicScore 850 settling to 755, roughly 160 points ahead of the
dormant-search build and every heuristic floor. The leak was in the deck, not the
code. Its own ladder replays add the honest coda: the deck wins three of four public
games, and the lone loss is no longer the turn-three opening board-out but a
turn-thirteen version of the same signature, bench at zero with the deck still full
and four prizes conceded. The next lever, submitted and validating, benches a Basic
before any other play whenever the bench runs thin, rebuilding the board mid-game.

## The deck concept

The submitted deck is a Mega Abomasnow ex water-discard combo. Snover evolves into
Mega Abomasnow ex, a 350 HP body whose attack Hammer-lanche costs two energy and
discards the top six cards of our deck, dealing 100 damage for every Basic Water
Energy discarded. The deck runs 35 Basic Water Energy, so the top six average roughly
three energy: a two-energy attack averaging over 300 damage from a 350 HP wall. Two
Kyogre recycle discarded energy. It is one of a two-deck portfolio; since a submission
carries a single deck, the portfolio is a design statement as much as a hedge, where a
deck otherwise weaker can be the right answer to a specific archetype. The second is a
mono-fire control build leaning on type weakness, routing a 130-damage Volcanion for
260 to move a grass-tempo matchup from about 80/20 against to even. The arbiter is the gauntlet: build, measure, submit the
deck the data ranks highest.

## Design tradeoffs and why they are defensible

**Reuse the native model instead of reimplementing the rules.** It trades a custom
simulator's freedom for exactness and a native speed floor, and removes the class of
bug that quietly ruins search agents. That it turned out dormant on the scored engine
is the cost of betting on an SDK feature the grader withholds, and naming that cost is
the point.

**Optimize for low variance, not margin.** The lethal check, deckout guard, and time
guard exist because the scoring rewards not losing winnable games more than winning by
a lot. Most engineering went into the floor of outcomes, not the ceiling, and the
guards that ladder live inside the heuristic.

**Stay offline and never crash.** No network or model calls at match time. Every
decision path terminates in a legal move; the worst case is a legal random option or
END. Unknown option types are treated as a safe pass, defending against
mid-competition rule additions.

**Let the simulator decide, always.** A council of LLMs was a development-time aid for
hard questions, but it never votes on what ships. Every change is kept only if a
gauntlet, then the real ladder, says it is an improvement. That discipline is why the
falsified energy trade was caught, why the deckout fix was adopted, and why we believe
our replays over our intentions when they disagree, as they did about search.

The result is an agent that is strong, explainable, and honest about its failure
modes: forged against the real game in self-play, guarding on the ladder against the
losses that actually cost rating, improved by reading its own replays, including the
one that told us our cleverest machinery was asleep.
