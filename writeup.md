# Determinized search over the engine's own forward model

A Pokemon TCG agent that decides by replaying the future with the competition's
exact rules, picks the line that wins most often across plausible hidden states,
and refuses to lose to its own blunders. It runs fully offline, never crashes,
and is tuned by real ladder loss data rather than by guesswork.

## The core idea

The cabt SDK ships a forward model: `search_begin`, `search_step`, and
`search_release` in `cg/api.py`, backed by the native engine. Given a
determinized full state (our hidden cards plus a guess at the opponent's), it
plays out moves at the same speed and with the same rules as the scored match.
The central decision in this project was to drive that model rather than
reimplement the game in Python. A hand-written rules engine is the largest risk
in any TCG search agent, because any divergence from the real rules silently
poisons every rollout. Using the engine's own model removes that risk entirely:
our rollouts are not an approximation of the game, they are the game.

So at each meaningful decision the agent does the following. It samples K
plausible hidden states consistent with everything it can see (determinization).
For each candidate first move it plays that move and then rolls the position out
to a terminal result using a fast heuristic policy for both players. It averages
the win/loss outcome across the samples and candidates, then picks the move with
the highest expected value. This is determinized Monte Carlo search, specialized
to a hidden-information card game and grounded in the real engine.

## How the agent decides, step by step

**The observation.** The engine hands the agent a typed observation each turn:
the current decision (`select`), the events since the last decision (`logs`), and
the full visible `State`. Opponent hand and face-down cards are `None`, but their
counts are visible. Every decision is a `select` with a list of typed options
(PLAY, ATTACH, EVOLVE, ATTACK, RETREAT, END, and card or number sub-selections).
The agent returns indices into that option list. Because the engine only ever
offers legal options, a correctly typed response is always a legal move.

**The heuristic floor.** Underneath the search sits a rules-aware heuristic that
is strong on its own and serves three roles: the rollout policy inside search,
the fallback when search cannot run, and the source of the safety overrides. Its
priorities are deliberately simple and progress-guaranteeing: take a knockout if
one is available, otherwise evolve, develop the bench, attach energy to the
attacker, retreat an endangered active when a healthier bench Pokemon exists, and
finally attack with the best affordable option or end the turn. It computes a
real lethal: the opponent's current HP against our best attack's damage, adjusted
for the engine's x2 weakness and flat resistance. Abilities are intentionally
deprioritized, because a stateless agent that prefers a repeatable ability over
ending its turn can loop forever; every chosen action consumes a resource, so the
turn always advances. On its own this heuristic beats the random-legal baseline
about 85 percent of the time over 200 gauntlet matches with zero illegal moves.

**Determinization.** The sampler reconstructs a full state the forward model will
accept. Our own deck and prizes are known exactly (our decklist minus the cards
we can see). The opponent's deck, hand, prize, and face-down active are sampled
from a prior so that all the visible counts match and every card already revealed
in the logs is placed in a zone it could actually be in. The prior defaults to a
mirror of our own deck and is sharpened by archetype identification (below). The
forward model validates these counts on `search_begin`, so a bad sample is caught
rather than silently wrong; if validation ever fails, the agent degrades to the
heuristic for that decision.

**Archetype-aware priors.** As the opponent reveals cards (plays, attachments,
evolutions, attacks), the agent matches them against a registry of archetype
signatures built from the card database and biases the determinization toward a
consistent decklist. The sampled deck is always merged to contain the cards we
have actually seen, so the belief can never contradict the visible board. With an
unrecognized opening it falls back to a broad mirror prior. Better priors mean
the rollouts are run against a more realistic opponent, which makes the expected
values more trustworthy.

**The safety layer (low variance).** The rating is margin-independent: a one-prize
win and a blowout score the same, so the cheapest points come from never throwing
a winnable game. A deterministic safety layer sits above search. It takes a
guaranteed knockout before search ever runs, even when the search would disagree.
It caps voluntary card draws when our deck is low, so we never deck ourselves out.
And it enforces a hard time guard against the 600-second per-match thinking bank,
answering instantly from the heuristic once the bank is within a reserve of the
limit, so cumulative thinking time can never approach a timeout (a timeout is an
automatic loss). Every path ends in a guaranteed legal fallback, because a single
exception forfeits the match.

**Time budget and endgame.** Forced or trivial decisions cost almost nothing;
pivotal ones get more determinizations. When the state space is small (low prize
counts, a small combined hand and deck) the agent recognizes the endgame and
spends a larger share of the bank to search it harder, which is exactly where
exact play matters most. A single decision is always bounded to a fraction of the
remaining bank, so even a boosted endgame decision cannot threaten the guard.

In the gauntlet, the search agent beats the strong heuristic about 66 to 70
percent head to head while keeping average decision time near 0.2 seconds and the
worst case around 1 second, comfortably inside the bank.

## The deck concept

The submitted deck is a Mega Abomasnow ex water-discard combo. Snover evolves into
Mega Abomasnow ex, a 350 HP body whose attack Hammer-lanche costs two energy and
discards the top six cards of our deck, dealing 100 damage for every Basic Water
Energy discarded. The deck runs 35 Basic Water Energy, so the top six average
roughly three energy: a two-energy attack that averages over 300 damage from a
350 HP wall. Two Kyogre recycle the discarded energy. A lean trainer suite (Mega
Signal, Lillie's Determination, Waitress, Cyrano, and a Maximum Belt as the single
ACE SPEC) finds the combo and pushes damage over knockout thresholds.

This is one of a two-deck portfolio, the second strand of the Strategy concept.
A submission carries a single deck, so the portfolio is both a development hedge
and a deliberate design statement: a deck that is otherwise weaker can be the
correct answer to a specific archetype. The second deck is a mono-fire control
build whose lever is type weakness. A grass tempo deck (Mega Heracross ex) is weak
to fire, so a 130-damage Volcanion doubles to 260 and one-shots it for a single
prize. Measured head to head, routing the counter through weakness moved that
matchup from roughly 80/20 against to about even, which is the whole point of the
portfolio. The arbiter is the gauntlet: we build, we measure, and we submit the
deck the data ranks highest. Today that is the tuned combo; the portfolio and its
matchup logic are the story, the combo is the current pick.

## Tuned by real loss data, not by guessing

Once agents were on the ladder, a scout tool pulled our own episode replays and a
loss classifier bucketed every defeat. This changed the agent twice in ways that
self-play alone would not have surfaced.

First, the dominant real loss was self-deckout: we milled ourselves to death, once
while ahead on prizes. The deckout guard, which had only been in the search agent,
was extracted into shared logic and added to the laddering heuristic. It is inert
in normal play and only caps a voluntary over-draw when the deck runs critically
low.

Second, with deckouts fixed, the next leak was early collapse: about half the
remaining losses ended by turn seven with us still holding all six prizes. Reading
the replays card by card showed a single mechanism: a lone basic attacker knocked
out while the bench was empty, leaving nothing to promote. This is not a misplay,
it is deck thinness (35 energy and only six basic Pokemon). The honest part of the
story is the falsified fix: the obvious trade of energy for an extra basic was
built, measured against a diverse field, and rejected, because cutting energy cost
more games to lost damage than the extra basic saved. The negative result is kept
as an artifact so the dead end is not re-walked. The next non-regressing lever, a
basic-search item that adds consistency without touching the energy count, is
identified and queued behind the heuristic support it needs. Measuring before
adopting is the method, and a documented dead end is a real result.

## Design tradeoffs and why they are defensible

**Reuse the native model instead of reimplementing the rules.** The biggest
decision, and the one that most distinguishes this approach. It trades the freedom
of a custom simulator for exactness and a native speed floor, and it removes the
class of bug that quietly ruins search agents.

**Optimize for low variance, not margin.** The safety layer and the deckout and
timeout guards exist because the scoring rewards not losing winnable games more
than it rewards winning by a lot. Most of the engineering went into the floor of
outcomes, not the ceiling.

**Stay offline and never crash.** No network or model calls at match time. Every
decision path terminates in a legal move; the worst case is a legal random option
or END. Enum handling treats unknown option types as a safe pass rather than a
crash, defending against mid-competition rule additions.

**Let the simulator decide, always.** A council of LLMs was used as a
development-time design aid for hard questions, but it never votes on what is best
and never ships. Every change is kept only if a gauntlet of opponents, and then
the real ladder, says it is an improvement. That discipline is why the falsified
energy trade was caught and why the deckout fix was adopted.

The result is an agent that is strong, explainable, and honest about its own
failure modes: it searches the real game, it guards against the losses that
actually cost rating, and it improves by reading its own replays.
