# A heuristic hardened by real-engine search and ladder forensics

A Pokemon TCG agent built on three commitments: decide by the competition's exact
rules, refuse to lose to its own blunders, and tune by real ladder loss data, not
guesswork. It runs fully offline and never crashes. Two findings from our own
replays shaped the climb: that the scored engine at first would not let our search run,
and the recovery that got it running again, over a heuristic floor that carries every
match search cannot yet win.

## The core idea, and the constraint that reshaped it

The cabt SDK ships a forward model, `search_begin`/`search_step`/`search_release` in
`cg/api.py`, backed by the native engine. Given a determinized full state, it plays out
moves at the same speed and rules as the scored match. The founding decision was to drive
that model rather than reimplement the game in Python. A hand-written rules engine is the
largest risk in any TCG search agent: any divergence from the real rules silently poisons
every rollout. Using the engine's own model removes that risk: our rollouts are not an
approximation of the game, they are it.

That decision built a strong self-play agent, but the scored engine at first withheld the
forward model at match time, so search was dormant on the ladder until the recovery
below; the heuristic floor guarantees the agent never forfeits.

## How the agent decides, step by step

**The observation.** The engine hands the agent a typed observation each turn: the
current decision (`select`), the events since the last (`logs`), and the full visible
`State`. Opponent hand and face-down cards are `None` but their counts are visible. Every
decision is a `select` over typed options; the agent returns indices into that list, and the
engine only ever offers legal options.

**The heuristic floor.** A rules-aware heuristic is strong on its own and carries every
match search cannot. Its priorities are simple and progress-guaranteeing: take a
knockout if one is available, otherwise evolve, develop the bench, attach energy to the
attacker, retreat an endangered active when a healthier bench exists, and finally attack
or end the turn. The lethal check is real: opponent HP against our best
attack's damage, adjusted for the engine's x2 weakness and flat resistance. Card
sub-selections are handled with intent, fetching a Basic on a thin-bench deck search and
sparing the combo line on a discard cost. Abilities are deprioritized so a stateless agent cannot loop on a repeatable one. On
its own it beats the random-legal baseline 89 percent with zero illegal moves.

**Determinization and search.** Above the heuristic sits determinized Monte Carlo
search. The sampler reconstructs a full state the forward model will accept: our own deck
and prizes exactly, the opponent's hidden zones sampled from a prior so all visible counts
match and every revealed card sits in a legal zone. For each candidate move it
rolls out to a terminal result with the heuristic as the rollout policy for both players,
then picks the highest-scoring first move.

**The safety layer.** The rating is margin-independent: a one-prize win and a blowout
score the same, so the cheapest points come from never throwing a winnable game. A
deterministic layer takes a guaranteed knockout before search ever runs, caps voluntary
draws when the deck is low so we never deck ourselves out, and hard-guards the
600-second per-match thinking bank so cumulative time can never reach a timeout. Every
path ends in a guaranteed legal fallback, because a single exception forfeits the match, and
these guards live in the heuristic itself, so they protect the agent whether or not search runs.

## The discovery, and the recovery: search on the scored ladder

Once agents were on the ladder, a scout tool pulled our own replays. The forensic detail
that cracked the case: the engine sets `actTimeout: 0` and gives each player a single
~600s overage bank, so the drop in that bank per decision is the real wall-clock thinking
time. In every early search-agent replay our searchable decisions drew only 0.02 seconds
from the bank, while the same observations replayed locally take half a second or more.
Search was not running at all on Kaggle.

The cause is precise. The 0.02s cost means the agent raised before the rollout loop, on
the import of the forward model. Yet the heuristic imports `all_card_data` from the same
`cg.api`, so the module loads fine and carries the card database; the grader had registered
a shadow `cg` with card data but none of the `search_*` wrappers.

The recovery reopened the ladder to search. When the ambient `cg.api` lacks the forward
model, the agent force-loads our OWN bundled `cg` package under a private module name,
binding `search_*` against our own native library as a separate instance, with no second
`GameInitialize` to fault the singleton core. The verification lives in the same channel
that exposed the problem: after the fix, searchable decisions on the ladder drew up to
6.5 seconds from the bank instead of 0.02, so search runs against real opponents now, and
still fails safe to the heuristic if the model is ever unreachable.

Honesty about where that leaves us: running is not winning. The recovered build scores near
515, still under the 570 the same deck reaches on the heuristic alone. Real lookahead over a
noisy mirror prior does not yet out-pilot the fast policy, so the recovery is not a finish
line but what made the next levers worth pulling.

## Strengthening the recovered search

With search live, a stack of changes targets why it does not yet beat its own floor. The
largest leak was self-inflicted: a searched MAIN move bypassed the heuristic's bench guard,
so search boarded itself out and lost most ladder games to empty-bench collapse; the fix
defers thin-bench turns to that guard and searches only when the bench is healthy. The
determinization prior now models the real field from the opening turn: the highest-adoption
ladder archetypes are embedded, so before any reveal the hidden zones are dealt from the
modal opponent rather than a mirror of our own deck, and once a distinctive card shows,
belief sharpens to that archetype. The argmax is hardened against
strategy fusion: a candidate is scored by its mean rollout value minus a penalty on the
world-to-world spread, demoting a move that wins only in a favorable and possibly wrong
hidden world. And the clock is used, not hoarded: prior matches spent about 130 of the
600-second bank, so the per-move caps were raised and tiered, with the endgame
and closing prize race sampling more worlds than an ordinary turn, under a reserve guard
that keeps cumulative time clear of a timeout. Because the heuristic is also the rollout policy, teaching it to drive an evolution line with
Rare Candy toward its Stage 2 payoff deepens every rollout for free, and it steers surplus
energy onto a benched attacker rather than overloading an active that can already attack. And the leaf evaluation gained an
attached-energy term, an active-weighted health term, and a convex empty-bench cushion, so a
depth-limited rollout scores a board by how close it is to attacking, by the health of the
active that takes a prize when knocked out, and by whether it still has a bench to promote,
not by prizes alone. These are committed and await the ladder's verdict, a hypothesis under
test.

## Tuned by real loss data, not by guessing

The same replay discipline changed the laddering agent twice. First, the dominant real
loss was self-deckout: we milled ourselves to death, once while ahead on prizes. The
deckout guard was extracted from the search layer into shared heuristic logic that now
protects every scored match, capping over-draw only when the deck runs critically low. The
proof is in the loss buckets, not the leaderboard: self-deckout fell from the most common
loss to near zero, and the deck-thinness collapse it had masked surfaced as the new top leak.

Second, that new leak was early collapse: about half the remaining losses ended by turn
seven with all six prizes still ours, a lone Basic attacker knocked out while the bench
was empty. This is deck thinness, not misplay: the heuristic already benches every Basic
it draws, so an empty bench means the hand held no second Basic. The honest part is the
falsified attempts: trading energy for a Basic lost more to reduced damage than it saved,
and an Ultra Ball fetch measured even but was retired, its discard cost unaffordable by
turn three when the collapse lands.

## Deck and pilot are one lever: the coupling result

The most useful thing we learned may be the least intuitive. With our own decks capped
near 570 and the leaderboard top near 1300, the obvious move is to copy a proven deck. We
harvested the real meta from thousands of ladder episodes and submitted exact copies of the
two best: the most-adopted Archaludon metal engine, and the Dark Grimmsnarl ex list of the
top two human players. Both scored at or below our own robust deck on the
same agent, Archaludon near 425 and Grimmsnarl near 570. A top-1300 deck made our pilot
play worse, not better.

The replays say why. Our agent decks itself out on Archaludon's trainer-heavy engine, and
at that time had no plan for driving Grimmsnarl's Rare Candy line to its payoff, the exact
gap the pilot lever above now targets. A deck's
ceiling is only reachable by a pilot that executes its game plan; hand a strong plan to an
agent that cannot run it and the mismatch costs more than a robust deck. The gap to the top
is joint, and for us the binding limiter is pilot strength. That is why the climb now targets
the agent and keeps the harvested meta decks only as foils, a result most teams chasing a
deck-copy shortcut will miss.

## The deck

The deployable deck is Precious Trolley, chosen by the same loss-data discipline. Because
early collapse is rooted in deck thinness, the deck carries part of the fix and the
pilot the rest. Precious Trolley is an item that puts a Basic straight onto the bench for
free, filling the empty bench exactly when the collapse fires. On its scored slot it settled in the upper-500s inside the noisy
heuristic band. It stays the deployable deck until a stronger pilot proves it can extract
more from a harder one.

## Design tradeoffs and why they are defensible

**Reuse the native model instead of reimplementing the rules.** It trades a custom
simulator's freedom for exactness and removes the class of bug that ruins search agents; its
early dormancy on the scored engine was the cost of that bet, and naming the cost then
engineering the recovery is the point.

**Bench maintenance is a first-class behavior.** The dominant loss was an empty bench, so
keeping a Basic in reserve is priced across every layer: the pilot benches one before other
plays, search hands thin-bench turns to that guard, the leaf values a bench convexly, and
the deck raises Basic density. One loss mode, attacked on four fronts. The pilot guard was
then measured in isolation: in a controlled test where both seats pilot the same deck, the
opponent's thin-bench pressure is pinned on, and only our seat's guard is toggled, our
empty-bench early collapse fell from 43 percent to 34 percent of games, a 21 percent relative
reduction at n=100 per setting. The confidence intervals overlap, but the point estimate and
direction match the mechanism, and the measurement itself carried a methodology lesson: a
symmetric mirror that toggles the guard on both seats at once misreports it as adverse, so a
pilot lever has to be measured on our seat alone. No win rate is claimed from an offline
mirror, which meta.md shows is not ladder-predictive; the claim is only that the guard does
what it was built to do to the loss bucket it targets.

**Optimize for low variance, not margin.** Most engineering went into the floor of outcomes,
not the ceiling: no network or model calls run at match time, every decision path terminates
in a legal move, and unknown option types are treated as a safe pass against
mid-competition rule additions.

**Let the simulator decide, always.** A council of LLMs was a development-time aid, but it
never votes on what ships. Every change is kept only if a gauntlet, then the real ladder,
says it is an improvement. That discipline caught the falsified energy trade and reported
the deck-copy shortcut as the honest failure it was, not the win we hoped for. The
result is an agent forged in self-play, recovered onto the ladder when the grader hid its
forward model, and improved by reading its own replays, including the one that told us our
cleverest machinery was asleep.
