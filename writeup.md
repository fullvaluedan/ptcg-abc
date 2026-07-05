# A heuristic hardened by real-engine search and ladder forensics

**Track:** Strategy (Model Approach)

A Pokemon TCG agent built on three commitments: decide by the competition's exact
rules, refuse to lose to its own blunders, and tune by real ladder loss data, not
guesswork. It runs fully offline and never crashes. Two findings from our own
replays shaped the climb: the scored engine at first would not let our search run,
and the recovery that restored it, over a heuristic floor that carries every match
search cannot yet win.

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

With search live, changes targeted why it does not yet beat the heuristic floor. The
largest leak: searched MAIN moves bypassed the bench guard, so search boarded itself out.
The fix defers thin-bench turns to the guard and searches only when the bench is healthy.
The prior now embeds real ladder archetypes instead of self-mirrors, sharpening belief
once a card reveals archetype. The argmax is hardened against strategy fusion: moves scoring
well only in favorable hidden worlds are demoted by a spread penalty. Clock allocation was
raised from 130 to the full 600-second bank, with endgame and prize-race turns sampling
more rollout worlds. Most improvements stay measured offline; two dormant changes
(energy-attachment resequencing and richer leaf terms) were tested, measured, and kept off
because depth-cuts needed to activate them degraded the terminal-rollout accuracy we rely on.

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

## The measurement discipline

How do you know a change helped? The obvious answer, a self-play gauntlet, is a trap:
gauntlets run against built-in bots, not ladder-predictive. In the gauntlet, trolley
beats Archaludon 77% to 68%; on the real ladder, Archaludon lands below trolley. The
only oracle is the ladder itself, and it is rationed: five submissions a day, two score.

Three rules fell out of that. First, measure mechanisms, not outcomes. Loss-bucket
shifts are real facts about behavior; win-rate deltas from mirrors mean nothing. Second,
never spend a scarce slot on a lever the ladder cannot judge: flags that only activate
under a toggle stay off until they can prove themselves. Third, a known-good build must
be reclaimed to re-enter the scored pair after an experiment pushes it out. This tracking
of our best verified build—not our most recent guess—is what most teams will miss.

## Deck and pilot are one lever: the coupling result

The most useful thing we learned may be the least intuitive. With our own decks capped
near 570 and the leaderboard top near 1300, the obvious move is to copy a proven deck. We
harvested the real meta from thousands of ladder episodes and submitted exact copies of the
two best: the most-adopted Archaludon metal engine, and the Dark Grimmsnarl ex list of the
top two human players. Both scored below our own robust deck on the same agent, each landing
clearly under the roughly 570 the trolley deck reaches. The exact publicScores drift as the
live ladder keeps replaying them, so we anchor on the stable fact rather than a moving number:
neither meta copy has come within reach of the floor. A top-1300 deck made our pilot play
worse, not better.

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

## Design tradeoffs

**Reuse the native model.** Using the engine's forward model removes the risk of silent divergence from true rules. The early dormancy was the cost of that bet; the recovery was the point.

**Bench maintenance is first-class.** Empty-bench collapse was the top loss mode, so keeping a Basic in reserve is priced across every layer: the pilot benches one first, search defers thin-bench turns to the guard, and the deck raises Basic density. Measured in isolation, the guard cut empty-bench collapse from 43% to 34% (n=100 per setting). A key lesson: a symmetric mirror misreports this as adverse, so a pilot lever must be measured on one side only.

**Optimize for low variance.** No models run at match time. Every decision path terminates in a legal move, protecting against crashes that forfeit the match.

**Let the ladder decide.** Every shipped change passed a gauntlet and then the real ladder. This caught the falsified energy trade and reported the deck-copy shortcut as the honest failure it was. The result: an agent improved by reading its own replays, including the one that told us our search was asleep on the scored ladder.
