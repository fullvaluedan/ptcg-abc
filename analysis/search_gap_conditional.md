# U82 category mining v2: deck-search picks (TO_BENCH/TO_FIELD/TO_HAND)

LOOP_BRIEF L6's next named sub-gap after RETREAT (analysis/retreat_gap_conditional.md)
and PROMOTE (analysis/promote_gap_conditional.md): "deck-search picks (what they
fetch with ball/search effects)". Tool: `analysis/search_gap_miner.py`.
Tests: `tests/test_search_gap_miner.py` (10 cases) plus two new spine tests in
`tests/test_replay_trace.py` for the `min_counts` extension this unit needed.

## What the pilot already does here

`agents.heuristics._choose_card_select`'s `GAIN_POKEMON_CONTEXTS` rule (built for
the early_collapse loss bucket) fetches a Basic Pokemon whenever the bench is
thin, on any context that brings a Pokemon into play or hand. Every other
deck-search decision -- the majority, since a healthy board is thin far less
often than not -- falls straight to `_first_legal`, which answers deck-reveal
index 0 with zero regard for what the fetched card is.

## Data and gate note

Full 2026-07-02 dataset, `--limit 1500` (the deck-search decision is common
enough that a truncated read still reaches a large n, unlike PROMOTE). 2424 real
expert TO_BENCH/TO_FIELD/TO_HAND decisions scored.

Building this miner required extending the shared spine
(`analysis.replay_trace.iter_expert_card_decisions` / `_scorable_card`): the
shipped gate required `minCount == 1`, which is correct for a FORCED pick (the
post-knockout promote) but wrong here -- real search effects are almost always
optional ("you may search your deck..."), so their select reports `minCount: 0`
even when the expert visibly picked one card. An initial full-dataset run with
the unmodified gate scored exactly 0 decisions, which is what surfaced the bug.
Added an optional `min_counts` parameter (default `{1}`, unchanged for the
promote miner) so a caller can opt into the `{0, 1}` population; two new spine
tests lock both the old default and the new opt-in behavior.

## Results

```
                    n      pilot agree   fetched Basic   fetched evo-for-board   picked index 0
overall           2424        45.4%          43.7%              26.3%               45.7%
bench_thin          414        28.7%          48.3%              16.7%               30.7%
not_thin           2010        48.8%          42.8%              28.3%               48.8%
```

("evo-for-board": the fetched card's `evolvesFrom` matches the name of a Pokemon
already in play, active or bench, for that seat -- an immediate-use evolution
target as opposed to a card being banked for later.)

`not_thin`'s pilot-agreement rate equals its index-zero rate exactly (48.8%,
both to one decimal), confirming the pilot really is running plain
`_first_legal` there with no override at all, same shape as the PROMOTE finding.

## The category-coverage number, and why it does not translate into a rule

Checked whether "is it a Basic, or does it evolve something already in play"
explains the real pick as a CATEGORY, independent of which specific card wins
within that category: 70.0% of all 2424 decisions (71.0% in the not_thin
subset) fetch a card that is either a Basic Pokemon or an immediate
evolution-for-board. That is a much stronger category signal than either
RETREAT or PROMOTE turned up.

But testing the obvious rule this implies -- "prefer any Basic option, else any
evolution-for-board option, else first-legal" -- against the same 2424 real
decisions only agrees 41.5%, WORSE than the pilot's current 45.4%. The reason:
most deck-search reveals containing a Basic or an evolution-for-board contain
MORE THAN ONE (a 60-card deck typically runs 2-4 copies of an early-game Basic,
plus whichever OTHER Basics or evolution pieces the search also reveals), so
"prefer the category, first within it" only fixes the coarse
Basic-vs-Item-vs-other distinction and then falls back to the same
reveal-order arbitrariness the current rule already has, at the exact moment
the two candidates are both Basics or both evolutions and the real choice is
about WHICH species, not which category.

## Verdict: confirmed gap, no shippable lever yet (mirrors RETREAT/PROMOTE)

The 70% category-coverage number is a genuine and useful finding (it rules out
"there is no learnable structure here at all"), but it is not itself a rule:
building "prefer a Basic, else an evolution" against this evidence would ship a
lever that is measured to UNDERPERFORM the current arbitrary behavior, which is
the same trap the RETREAT and PROMOTE gaps warned against (guessing a fix at the
strength of the current arbitrary rule, or worse). The real missing input is
species/archetype-level: which SPECIFIC Basic or evolution the current board
plan wants, not just its category. That is the same missing "what matchup/plan
am I actually running" signal RETREAT and PROMOTE's follow-on both point at, so
a future combined feature (deck-archetype-aware fetch preference, or the same
matchup-delta feature named in the other two conditional docs) is the next real
lever for all three gaps at once, not a one-off deck-search rule.

## Next step (not built this iteration)

A species-aware fetch rule needs to know the board's CURRENT PLAN (what
evolution line is it running, what basic count does it already have banked)
to pick among multiple same-category candidates -- exactly the missing
capability TRACK S's archetype work (U9a/U9b/U9c) targets from the opposite
side (predicting the OPPONENT's plan). Whether OUR OWN in-progress deck plan
can be read cheaply enough to drive this fetch choice is worth checking before
committing to a species-level miner.
