# The RETREAT target choice is not a gap, and matchup-swap is refuted there too

## Finding

`analysis/retreat_gap_conditional.md` found the pilot misses 89.1% of real
RETREAT decisions (the MAIN "retreat or not" pick) and theorized, but did not
measure, that the dominant high-HP slice (464/614, barely-hurt actives) is a
**tempo / matchup swap**: bringing in a specific bench attacker regardless of
health. That miner could not test the theory because it never looked at WHICH
bench Pokemon the expert actually brings in -- that is a separate CARD
decision, `SelectContext.SWITCH` (`analysis/replay_trace.CTX_SWITCH`, the
follow-up pick right after a MAIN RETREAT choice, distinct from the
post-knockout `TO_ACTIVE` promote).

Reading `agents/heuristics.py` shows the shipped pilot has no rule for this
decision either: `_choose_card_select`'s `GAIN_POKEMON_CONTEXTS` set omits
`SWITCH`, so every retreat-target pick falls to `_first_legal`, the same shape
the PROMOTE gap had before it was measured. This unit built
`analysis/retreat_target_miner.py` to measure it directly, mirroring
`analysis/promote_gap_miner.py`'s profile (hp ratio, energy, type matchup,
index zero) plus a new `matchup_delta` field comparing the played target's
matchup against the OUTGOING active's matchup specifically, split by the same
active_hp_ratio >= 0.9 threshold the parent finding used.

## Evidence (analysis/retreat_target_miner.py, 2026-07-02 dataset, limit 1500)

```
expert teams: kazuki0123, tonakaiiii, The Debauchery Tea Party
real expert retreat-target (SWITCH) decisions scored: 219

overall (n=219):
  pilot (_first_legal) agreement rate: 86.3%
  expert picked the max hp-ratio bench option: 82.6%
  expert picked the max-energy bench option:  86.3%
  expert picked the best type-matchup option: 64.4%
  target matchup beats outgoing active's:     27.9%
  expert picked bench index 0:                86.3%

high-HP active (>=0.9) (n=140):
  pilot (_first_legal) agreement rate: 87.9%
  expert picked the best type-matchup option: 65.7%
  target matchup beats outgoing active's:     22.9%

lower-HP active (<0.9) (n=79):
  pilot (_first_legal) agreement rate: 83.5%
  expert picked the best type-matchup option: 62.0%
  target matchup beats outgoing active's:     36.7%
```

Restricting to decisions with a real choice (more than one bench candidate,
n=197 of 219; the remaining 22 have exactly one legal bench mon and no real
pick to make) changes almost nothing: agreement stays 85.8%, and
`matchup_improves` stays low (29.4% overall, 23.8% in the high-HP slice).

## Interpretation

Two separate findings, both against the parent theory:

1. **The target choice itself is not a gap.** `_first_legal` (today's
   shipped behavior, since `SWITCH` is unruled) already agrees with the real
   expert pick 86.3% of the time, including on decisions with a genuine
   multi-candidate choice. This closely tracks `max_hp_ratio` (82.6%),
   suggesting the bench's option order and its HP order are correlated in
   this dataset, not that a hidden matchup rule is doing the work. There is
   no lever to build here: the current arbitrary behavior already matches
   top players most of the time.
2. **Matchup-swap is refuted as the driver, a second time.** `best_matchup`
   (64.4%) looks high, but ties at `matchup_score == 0` (the common case: most
   candidate pairs have no weakness/resistance interaction) resolve to the
   first bench option by construction, so this number is inflated by the same
   ordering artifact as (1), not independent evidence for matchup. The
   direct test -- does the target's matchup score actually beat the
   OUTGOING active's -- is the real check, and it comes back low: 27.9%
   overall, and only 22.9% in the exact high-HP slice
   (`retreat_gap_conditional.md`'s 464/614 bucket) the theory was proposed
   for. If top players were swapping to fix a bad matchup, this number would
   be well above half; instead the large majority of retreats (77%+) do NOT
   improve the type matchup at all.

This is the second independent refutation of the matchup-swap theory:
`analysis/promote_gap_conditional.md` already found type matchup explains at
most 39.6% of real PROMOTE picks (checked, not assumed), and now the RETREAT
target itself shows the same shape at an even lower rate. Both gaps
originally looked like plausible "matchup awareness" stories; both, once
actually measured with the same shared `matchup_delta.py` primitive, turned
out not to be primarily about matchup.

## Why this closes (not opens) a lever

There is nothing to ship from this unit: the target sub-decision already
performs near-parity with the shipped pilot, and the matchup-swap explanation
for WHY top players retreat while barely hurt is now refuted, not just
untested. The open question -- what top players are actually optimizing for
when they retreat a full-HP active -- remains unanswered. Named-but-unchecked
candidates from `retreat_gap_conditional.md` (an immediate knockout the
bench mon enables, an ability/attack the current board state calls for) are
still live; a combined signal in the same shape `promote_gap_conditional.md`
proposed (matchup AND an immediate-knockout check together) is the next
concrete step if this is pursued further, not a fourth single-field guess.

## Conclusion

RETREAT's target choice (`SelectContext.SWITCH`) is not a shippable gap: the
current arbitrary `_first_legal` behavior already agrees with top players
86.3% of the time. The matchup-swap theory named in
`analysis/retreat_gap_conditional.md` as the likely explanation for the much
larger MAIN retreat-timing gap is refuted when measured directly against the
target choice (22.9% match-up improvement in the exact high-HP bucket named,
well under half). The RETREAT MAIN gap itself (89.1% threshold_miss) is
therefore still open with no confirmed cause, having now ruled out both an
HP-threshold fix (the original miner) and a matchup-swap story (this unit).
