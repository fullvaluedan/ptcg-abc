# Mastery-scored target selector (U36)

## Why a second selector

The U25 census already names a target family, but by ADOPTION: it counts only
the winning seat, so its verdict (meta_grimmsnarl, the widest winning archetype
by ranking groups) measures how much a deck is played and how many decisions its
winners make, not how well the deck converts. Raw wins are a popularity artifact.
U36's selector is a separate, mastery-weighted signal that folds in the LOSING
appearances the census drops (it classifies BOTH seats of every decided episode)
and scores each family by

> **mastery = expert_wins x expert_win_rate**

It is free to disagree with the Grimmsnarl prior. Pure primitives live in
`tools/archetype_select.py` (cg-free, injected signatures); the machine-readable
`targets.json` is routed through the U30 isolation helper into
`data/derived/targets/` (gitignored). This doc carries counts, never episodes.

## Full run (5734-episode dataset, 2026-06-30)

`python tools/archetype_select.py data/episodes/pokemon-tcg-ai-battle-episodes-2026-06-30.zip --decks-dir decks`

- **5732** episodes scored, **2** dropped (draws / malformed).
- Both seats classified per episode against the archetype registry (signature
  coverage >= 0.35), so `games` counts appearances and `wins` counts victories.
- Eligible as target = a real family (not "other") with `games >= 50`.

| family | games | wins | win_rate | mastery | eligible |
| --- | --- | --- | --- | --- | --- |
| meta_archaludon | 4736 | 2294 | 0.484 | 1111.16 | yes (target) |
| meta_grimmsnarl | 3759 | 1996 | 0.531 | 1059.86 | yes |
| meta_grimmsnarl_tonakaiiii | 1687 | 820 | 0.486 | 398.58 | yes |
| other | 1282 | 622 | 0.485 | 301.78 | no (grab-bag) |

## Verdict: target = meta_archaludon (by mastery), with a caveat

By the pre-committed mastery formula the target is **meta_archaludon** (1111.16),
narrowly ahead of meta_grimmsnarl (1059.86). This diverges from the census
adoption target (grimmsnarl), so the two selectors genuinely disagree, which is
the point of running both.

But read the win-rate column before trusting the headline. This is a CLOSED,
mirror-heavy cohort: every episode has exactly one winner and two seat
appearances, so total wins = total games / 2 and win_rate averages ~0.50 across
the pool. In that regime `wins x win_rate` still scales with volume, so mastery
tracks popularity more than the formula intends. The evidence:

- **meta_grimmsnarl is the ONLY family above a coin flip (0.531).** It is the
  single most SKILLFUL archetype by win rate.
- **meta_archaludon wins the mastery slot at a BELOW-0.5 win rate (0.484)** purely
  on game count (4736 vs 3759). The most-played pillar loses more than it wins yet
  still tops mastery. That is exactly the popularity artifact the metric was meant
  to suppress, only partly corrected.
- The archaludon-vs-grimmsnarl mastery gap is ~5%, inside the noise a
  volume-weighted metric carries.

## How U37/U39 should read this

The mastery target (archaludon) is not a mandate to switch the pilot's deck; it is
one input. The discriminating signal here is **win_rate, not mastery**: grimmsnarl
is the only above-0.5 family and the census's adoption target, so the two selectors
AGREE that grimmsnarl is the quality pick once volume is stripped out. Treat
grimmsnarl as the deck-aware target for U37 seeds mining and keep archaludon as the
mastery runner-up / opponent-model anchor (it is already the field-prior default in
`analysis/archetype`). If a later, more diverse dataset (a non-mirror pool, or one
with an above-0.5 archaludon) is harvested, re-run the selector: the mastery
formula only earns its keep once win rates actually spread away from 0.50.
