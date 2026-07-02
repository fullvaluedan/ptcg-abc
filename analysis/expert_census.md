# Expert cohort + full census (U25)

## The cohort fork, resolved

Two incompatible "expert" samples were in play: the move-ranking validator's
3 named top-player handles (116 decisions) and CEM's 40 held-out episodes
(1427 decisions). U25 collapses both into ONE definition:

> **The expert seat of an episode is the WINNING seat.**

Rationale. The replay files carry no per-seat skill rating: `info` holds only
`TeamNames` / `Agents`, never an ELO. The game OUTCOME is therefore the sole
per-episode quality signal, and the winning seat's decisions are exactly the
distribution the imitation stack is meant to clone. This scales to the whole
dataset (retiring the 3-handle / 116-decision starvation read) and is identical
to the winners-only cohort the tiers already fall back to, so the two forks stop
drifting. Implemented in `analysis/expert_cohort.py`; census in
`tools/expert_census.py`, routed through the U30 isolation helper.

## Full census (5734-episode dataset, 2026-06-30)

`python -m tools.expert_census data/episodes/pokemon-tcg-ai-battle-episodes-2026-06-30.zip`

- **5732** episodes scored, **2** dropped (draws / malformed).
- **167,531** ranking groups (scorable multi-option single-pick MAIN decisions).
- **220,598** MAIN decisions total.

Ranking groups = the decisions a pairwise ranker learns from (the same decisions
`move_ranking_validator.iter_expert_decisions` scores). Families are assigned by
signature coverage >= 0.35 against the archetype registry (the meta pillars plus
"other" for everything below threshold on every pillar).

| family | episodes | MAIN decisions | ranking groups | tier |
| --- | --- | --- | --- | --- |
| meta_grimmsnarl | 1996 | 86061 | 67959 | full |
| meta_archaludon | 2294 | 72348 | 50422 | full |
| meta_grimmsnarl_tonakaiiii | 820 | 36059 | 29341 | full |
| other | 622 | 26130 | 19809 | full |

Top winning-seat handles: THIRD PTCG Club (186), kazuki0123 (163), S4nkurero
(147), monnosuke (105), aidy (103), Yushin Ito (101), tonakaiiii (98), The
Debauchery Tea Party (95), ShumpeiNomura (90), capbloo (90).

## Pre-committed tiers (fixed before the count, `expert_cohort.tier_for`)

- `>= 2500` ranking groups for the target family = **full** per-archetype learned pilot.
- `[600, 2500)` = winners-only cloning + family pooling.
- `< 600` = kill learned-pilot training, ship the hand-coded layer.

## Verdict: tier FULL

The target family (meta_grimmsnarl, the widest winning archetype by ranking
groups) has **67,959** ranking groups, ~27x the full-tier floor. Every family,
including "other", clears 2500 by more than an order of magnitude. Expert data is
not the binding constraint on the imitation stack.

Consequences:

- The census-thin fallbacks (winners-only pooling, kill U40/U41) do **not** fire.
  The U40/U41 learned-pilot pipeline is unblocked on the data-volume axis.
- The remaining gate on ML spend is the **U26 unit-zero ranker spike** (does a
  linear ranker actually beat the per-archetype baseline), not data scarcity.
- Grimmsnarl variants (1996 + 820 = 2816 winning seats) edge Archaludon (2294) as
  the most-won meta archetype, a signal for later deck-family selection (U39).

Continue the daily zip harvest for freshness, but no tier upgrade is needed: the
current dataset already sits in the top tier.
