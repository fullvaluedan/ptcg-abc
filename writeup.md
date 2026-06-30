# A heuristic hardened by real-engine search and ladder forensics

A Pokemon TCG agent built on three commitments: decide by the competition's exact
rules, refuse to lose to its own blunders, and tune by real ladder loss data
rather than by guesswork. It runs fully offline, never crashes, and is honest
about its own failure modes, including the one that mattered most: the discovery,
from reading our own replays, that the scored engine does not let our search run,
which redirected the whole climb onto the levers that actually execute.

## The core idea, and the constraint that reshaped it

The cabt SDK ships a forward model: `search_begin`, `search_step`, and
`search_release` in `cg/api.py`, backed by the native engine. Given a determinized
full state (our hidden cards plus a guess at the opponent's), it plays out moves at
the same speed and with the same rules as the scored match. The founding decision
was to drive that model rather than reimplement the game in Python. A hand-written
rules engine is the largest risk in any TCG search agent: any divergence from the
real rules silently poisons every rollout. Using the engine's own model removes
that risk entirely, so in self-play our rollouts are not an approximation of the
game, they are the game.

That decision built a genuinely strong self-play agent. But the central honest
finding of this project is that the *scored* engine withholds the forward model at
match time, so search is dormant on the ladder and the heuristic underneath it is
what actually plays. How we proved that, and what we did about it, is the spine of
the story below. The search machinery remains real and measured; it is the crucible
the laddering agent was forged in, not a claim about what runs on Kaggle.

## How the agent decides, step by step

**The observation.** The engine hands the agent a typed observation each turn: the
current decision (`select`), the events since the last decision (`logs`), and the
full visible `State`. Opponent hand and face-down cards are `None`, but their counts
are visible. Every decision is a `select` with a list of typed options (PLAY,
ATTACH, EVOLVE, ATTACK, RETREAT, END, and card or number sub-selections). The agent
returns indices into that option list. Because the engine only ever offers legal
options, a correctly typed response is always a legal move.

**The heuristic floor (this is what ladders).** A rules-aware heuristic is strong on
its own and, as it turned out, carries every scored match. Its priorities are
deliberately simple and progress-guaranteeing: take a knockout if one is available,
otherwise evolve, develop the bench, attach energy to the attacker, retreat an
endangered active when a healthier bench Pokemon exists, and finally attack with the
best affordable option or end the turn. It computes a real lethal: the opponent's
current HP against our best attack's damage, adjusted for the engine's x2 weakness
and flat resistance. Card sub-selections are handled with intent, not by reflex: on
a deck search with a thin bench it fetches a Basic Pokemon so a knocked-out lone
active always has backup, and on a discard cost it sheds surplus energy and spares
the Pokemon and combo line. Abilities are intentionally deprioritized, because a
stateless agent that prefers a repeatable ability over ending its turn can loop
forever; every chosen action consumes a resource, so the turn always advances. On
its own this heuristic beats the random-legal baseline about 89 percent of the time
over 200 gauntlet matches with zero illegal moves.

**Determinization and search (the self-play method).** Above the heuristic sits
determinized Monte Carlo search. The sampler reconstructs a full state the forward
model will accept: our own deck and prizes exactly (our decklist minus what we can
see), the opponent's deck, hand, prize, and face-down active sampled from a prior so
all visible counts match and every revealed card sits in a zone it could be in. The
prior defaults to a mirror and is sharpened by archetype identification: as the
opponent reveals cards, the agent matches them against archetype signatures from the
card database and biases the sample toward a consistent decklist, while always
merging in what we have actually seen so the belief never contradicts the board. For
each candidate first move the agent plays it and rolls out to a terminal result with
the heuristic as the rollout policy for both players, then picks the move with the
highest average win rate. In the gauntlet this search beats the strong heuristic
about 66 to 70 percent head to head, near 0.2 seconds per decision.

**The safety layer (low variance).** The rating is margin-independent: a one-prize
win and a blowout score the same, so the cheapest points come from never throwing a
winnable game. A deterministic safety layer takes a guaranteed knockout before
search ever runs, caps voluntary card draws when our deck is low so we never deck
ourselves out, and enforces a hard guard against the 600-second per-match thinking
bank so cumulative time can never approach a timeout (an automatic loss). Every path
ends in a guaranteed legal fallback, because a single exception forfeits the match.
Crucially, the lethal check and the deckout guard live in the heuristic itself, so
they protect the agent on the ladder whether or not search is available.

## The discovery: search is dormant on the scored ladder

Once agents were on the ladder, a scout tool pulled our own replays. The forensic
detail that cracked the case is that the engine sets `actTimeout: 0` and gives each
player a single ~600s overage bank, so the drop in that bank per decision is the
real wall-clock thinking time. In every search-agent replay, our searchable
decisions drew only 0.02 to 0.05 seconds from the bank, while the same observations
replayed locally take 500 to 830 milliseconds because search runs to its budget. The
search was not running at all on Kaggle.

The cause is precise and reproducible. The 0.02s cost is itself the clue: a forward
model that merely failed at call time would still burn the full half-second budget
loop retrying determinizations. A 0.02s cost means the agent raises *before* the
loop, on the import of `search_begin` and friends. The heuristic imports
`all_card_data` and `all_attack` from the same `cg.api` and plays card-aware moves
on the ladder, so `cg.api` imports fine and carries the card database; it simply does
not expose the `search_*` forward model at match time. The scored engine offers the
data API needed to act, but not the SDK lookahead API. We reproduced it exactly: a
`cg.api` with card data but no `search_*` makes the agent fall back in a tenth of a
millisecond, while the full SDK makes the identical call take 833 milliseconds.

So the agent now probes for the forward model and gates search on it as a first-class,
tested condition rather than a swallowed import error. The honest implication is that
the determinization, archetype priors, and endgame search are inert on the ladder by
an engine constraint, valid for self-play and as design tools but not movers of the
public score. The two submissions that look different on paper, a search build and a
heuristic build, are statistically tied around 590 precisely because they execute the
same heuristic on the scored engine. That reading is why the rest of the work targets
the levers that do run every match: the heuristic policy and the deck.

## Tuned by real loss data, not by guessing

The same replay discipline changed the laddering agent twice more. First, the
dominant real loss was self-deckout: we milled ourselves to death, once while ahead
on prizes. The deckout guard, which had only lived in the search layer, was extracted
into shared heuristic logic so it now protects every scored match; it is inert in
normal play and only caps a voluntary over-draw when the deck runs critically low.
This is the change that actually moved the public score: the search and plain
heuristic builds sit clustered around 590 because they run the same heuristic, and
the bare heuristic floor rates near 460, but the deckout-guarded heuristic climbed
well clear of both as its ladder rating settled. That gap is the strongest evidence
in the whole project that the levers which execute every match, the heuristic and
its guards, are what raise the rating, not the determinized search that is dormant
on the scored engine.

Second, with deckouts fixed, the next leak was early collapse: about half the
remaining losses ended by turn seven with us still holding all six prizes, a lone
basic attacker knocked out while the bench was empty. This is deck thinness, not
misplay. The honest part is the falsified fix: the obvious trade of energy for an
extra basic was built, measured against a diverse field, and rejected, because
cutting energy cost more games to lost damage than the extra basic saved. A
non-regressing alternative, an Ultra Ball consistency package that adds a basic-search
item without touching the energy count, was built and measured as even with the
baseline in self-play; its only possible upside is against the diverse ladder field,
which cannot be confirmed without a scored slot, so it waits as a measured candidate
rather than a guess. The dead end and the even result are both kept as artifacts so
neither is re-walked.

## The deck concept

The submitted deck is a Mega Abomasnow ex water-discard combo. Snover evolves into
Mega Abomasnow ex, a 350 HP body whose attack Hammer-lanche costs two energy and
discards the top six cards of our deck, dealing 100 damage for every Basic Water
Energy discarded. The deck runs 35 Basic Water Energy, so the top six average roughly
three energy: a two-energy attack averaging over 300 damage from a 350 HP wall. Two
Kyogre recycle discarded energy, and a lean trainer suite finds the combo. This is
one of a two-deck portfolio: a submission carries a single deck, so the portfolio is
both a development hedge and a design statement, that a deck otherwise weaker can be
the correct answer to a specific archetype. The second deck is a mono-fire control
build whose lever is type weakness; routing a 130-damage Volcanion through weakness
for 260 moved a grass-tempo matchup from roughly 80/20 against to about even. The
arbiter is the gauntlet: we build, we measure, and we submit the deck the data ranks
highest.

## Design tradeoffs and why they are defensible

**Reuse the native model instead of reimplementing the rules.** It trades a custom
simulator's freedom for exactness and a native speed floor, and removes the class of
bug that quietly ruins search agents. That it turned out to be dormant on the scored
engine is the cost of betting on an SDK feature the grader withholds, and naming that
cost honestly is the point.

**Optimize for low variance, not margin.** The lethal check, deckout guard, and time
guard exist because the scoring rewards not losing winnable games more than winning
by a lot. Most of the engineering went into the floor of outcomes, not the ceiling,
and the guards that ladder are the ones placed inside the heuristic.

**Stay offline and never crash.** No network or model calls at match time. Every
decision path terminates in a legal move; the worst case is a legal random option or
END. Unknown option types are treated as a safe pass, defending against
mid-competition rule additions.

**Let the simulator decide, always.** A council of LLMs was a development-time design
aid for hard questions, but it never votes on what is best and never ships. Every
change is kept only if a gauntlet, and then the real ladder, says it is an
improvement. That discipline is why the falsified energy trade was caught, why the
deckout fix was adopted, and why we believe our replays over our intentions when they
disagree, as they did about search.

The result is an agent that is strong, explainable, and honest about its own failure
modes: it was forged against the real game in self-play, it guards on the ladder
against the losses that actually cost rating, and it improved by reading its own
replays, including the replay that told us our cleverest machinery was asleep.
