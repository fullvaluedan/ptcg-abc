# Search does not out-pilot the meta deck: the "search unlocks a copied deck" lever is closed

Phase 4 diagnosis. The copied meta decks settled well BELOW the trolley floor on
the ladder (archaludon 412.9, grimmsnarl 411.9, vs trolley 569.6 on the same
heuristic). `analysis/archaludon_deckout_is_mandatory_draw.md` closed the
guard-tuning knob and named the ONE remaining unlock explicitly:

> the pilot fix is a modeling effort (a search agent that reaches the deck's real
> forward model, or deck-plan logic that sequences the metal engine to a payoff)

The search agent HAS recovered its real forward model on the ladder (submission
54218335 confirmed `search_ran`: per-decision overage draw jumped from ~0.02s to
~6.5s, so determinized lookahead actually runs in the grader). Search + a meta
deck is the one deployable combination never built. This iteration tests it
offline and closes it with data.

## Mirror self-collapse: search is no better than the heuristic

`tools/collapse_rate.py` runs same-policy mirror games on one deck and classifies
the loser of each. The two leaks that cap the Archaludon copy are deckout and
early_collapse (empty-bench self-KO). Matched on the same deck:

| policy    | n  | deckout      | early_collapse |
|-----------|----|--------------|----------------|
| heuristic | 60 | 11/60 (18%)  | 15/60 (25%)    |
| search    | 30 | 6/30 (20%)   | 9/30 (30%)     |

The Wilson intervals overlap completely (search deckout 95% CI ~9-38%, heuristic
~10-30%). Real lookahead self-decks and self-collapses the trainer-heavy Archaludon
engine at the SAME rate as the one-ply heuristic. It does not dig for the metal
payoff and close on prizes before the mandatory start-of-turn draw runs the deck
to zero; it mills into the identical loss. (An early n=2 spot check read 0/2 on
both buckets, pure small-sample noise the n=30 run erases.)

## Head-to-head: a noisy edge that the ladder has already refuted

Both seats bound to `decks/meta_archaludon.csv`, seat-alternating, search as seat A
(`scratchpad/h2h_archaludon.py`):

    search vs heuristic on Archaludon (n=20): 12W/8L/0D, search win rate 60.0%

Taken alone this looks like a tactical edge. It is not a submittable one, for two
reasons. First, n=20 is thin: the 60% Wilson interval is ~39-78%, so it includes a
coin flip. Second, and decisive, this is the SAME offline signal that has already
been proven non-predictive on this engine. On the trolley deck the offline
search-vs-heuristic A/B was a dead tie (50.0% over n=30) and yet on the ladder
search LOST to the heuristic outright (514.7 vs 569.6;
`analysis/search_recovered_on_ladder.md`). Offline head-to-head OVER-states search's
ladder rating here, so a noisy offline 60% is not evidence of a ladder gain; if the
same bias holds it lands at or below the heuristic's Archaludon copy (412), which is
already on the ladder and already below the trolley floor.

Crucially, the edge does NOT come from fixing the leaks that cap the deck: the
mirror table above shows search self-decks (20%) and self-collapses (30%) at the
same rate as the heuristic. Whatever the 60% is, it is not "search closes the metal
game plan before the deck mills out."

## Why, and what it agrees with

The likely mechanism is the determinization prior: `search/determinize.py` falls
back to the MIRROR assumption (model the opponent as running OUR deck), and the
rollout is the same heuristic policy, so search inherits the heuristic's game-plan
blindness and merely spends ~300x the compute to reach the same mill. That is why
its self-collapse rate is unchanged, and why an offline mirror/head-to-head edge
evaporates against the varied real field (the trolley ladder loss). Lookahead with a
mirror prior and a heuristic rollout cannot substitute for a deck plan it does not
encode.

## Decision: the lever is closed

The named unlock ("a search agent that reaches the deck's real forward model") is
tested and does not clear the submission gate. Do NOT build or submit a search +
meta-deck combination (search_archaludon / search_grimmsnarl): the only positive
offline signal is a noisy 60% head-to-head that the trolley precedent has already
shown does NOT transfer to ladder rating, and search leaves the capping deckout /
early_collapse leaks exactly where the heuristic left them. Its predicted ladder
landing is at or below the heuristic Archaludon copy already up (412), below the
trolley floor (570), so it fails the "only a genuine improvement, measured offline
first" gate. The remaining unlock is the OTHER half of the named modeling effort: deck-plan logic
that sequences the metal engine to its payoff (or a determinization prior that
models the real ladder field instead of the mirror). Both are from-scratch modeling
work, not a knob or an agent swap. The trolley deck (569.6) stays deployable; the
meta decks stay as harvested reference and gauntlet foils.

## Reproduce

```
.venv/Scripts/python.exe -c "from tools.collapse_rate import measure_deck; \
from tools.deck_validate import read_deck; \
print(measure_deck(read_deck('decks/meta_archaludon.csv'), 30, policy='search'))"
# head-to-head: bind decks/meta_archaludon.csv to both tools.deck_match.deck_bound
# seats (search vs heuristic via tools.opponents.get), seat-alternating, and tally
# the search seat outcome with analysis.loss_classifier.parse_replay
```
