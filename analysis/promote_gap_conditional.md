# The PROMOTE gap: a previously-unmeasured category with no rule at all

## Finding

A post-knockout promote (choosing which bench Pokemon becomes the new active
after the active is knocked out) is a `SelectContext.TO_ACTIVE` CARD decision,
not a MAIN category, so it was never covered by the move-ranking breakdown
(`analysis/move_ranking_diverges_ability_gap.md` only scores MAIN decisions).
Reading `agents/heuristics.py` shows the shipped pilot has **no dedicated rule
for it at all**: `_choose_card_select`'s `GAIN_POKEMON_CONTEXTS` set covers
`SETUP_BENCH_POKEMON`, `TO_BENCH`, `TO_FIELD`, `TO_HAND`, but omits
`TO_ACTIVE`. Every promote decision therefore falls straight through to
`_first_legal`, which always returns bench index 0 regardless of any
candidate's HP, energy investment, or anything else about the board.

This is a distinct kind of gap from ATTACH (already root-caused as ordering,
`energy_seq_refuted_by_expert_moves.md`) or RETREAT (already root-caused as a
missing matchup signal, `analysis/retreat_gap_conditional.md`): there is no
existing rule to be preempted or under-thresholded here. The pick is simply
arbitrary today.

## New spine primitive

`iter_expert_card_decisions` did not exist before this unit; `analysis/replay_trace.py`
(the U32 decision spine) only exposed a MAIN single-pick iterator. This unit adds
`iter_expert_card_decisions(replay, expert_index, contexts)` and `_scorable_card`,
generalizing `_scorable_main`/`iter_expert_decisions`'s exact gate shape (single
pick, more than one option, correct seat) to any `SelectType.CARD` decision
filtered by a caller-supplied context set, so a future deck-search-pick miner
(`TO_HAND`/`TO_FIELD`/`TO_BENCH` from a played fetch effect) can reuse the same
primitive instead of duplicating the gate.

## Evidence (analysis/promote_gap_miner.py, 2026-07-02 dataset, full scan of all 5153 replays)

```
expert teams: kazuki0123, tonakaiiii, The Debauchery Tea Party
real expert promote (post-knockout TO_ACTIVE) decisions scored: 91
  pilot (_first_legal) agreement rate: 36.3%
  expert picked the max hp-ratio bench option: 35.2%
  expert picked the max-energy bench option:  36.3%
  expert picked bench index 0:                36.3%
```

(n=91 is the real promote-decision population found across the entire
2026-07-03 dump, not a `--limit`-truncated sample; this decision only fires
once per knockout with a non-empty bench, so it is naturally rarer than
ATTACH/RETREAT/ABILITY.)

## Interpretation

Three candidate signals were checked against the real expert pick, each
independently: bench index 0 (what `_first_legal` already produces for free),
the bench option with the highest current HP ratio, and the bench option with
the most energy attached. **None of the three clears even 37%.** Note
`agree` and `played_is_index_zero` are identical by construction (the
injected/default pilot's answer literally is index 0 every time), confirming
the pilot is not doing anything beyond first-legal today.

Unlike the RETREAT gap, where a clear majority (75.6% of misses) shared one
property (near-full HP, pointing at a matchup-swap story), no single simple
per-candidate feature here explains anywhere near a majority of real picks.
This does not mean the decision is random: it means HP ratio and raw energy
count, checked one at a time, are not the (or not the only) governing signal.
Plausible remaining candidates not yet checked: type match-up against the
opponent's active (weakness/resistance, the same missing signal the RETREAT
gap named), whether a bench mon can score an immediate knockout on promotion,
retained Prize-card implications, or some combination of these rather than any
single field.

## Why this is not a shippable lever yet

At n=91 with no candidate signal clearing 37%, there is not yet a concrete,
well-supported rule to write (unlike ABILITY, a clean capability flip). Coding
"promote highest HP" or "promote most energy" against this evidence would be
guessing at the same strength as the current arbitrary `_first_legal`, and
risks the same shape of refutation the ATTACH energy-sequencing lever already
hit when it was shipped on intuition instead of measurement. The concrete next
step (not yet built) is to add a matchup-delta feature per bench candidate
(type effectiveness against the opponent's active, mirroring the RETREAT gap's
named follow-on) and re-run this same miner before any promote rule is coded.

## Conclusion

PROMOTE is a confirmed, previously-unmeasured, currently-unruled category (the
pilot's answer here is pure `_first_legal`, not even the thin-bench Basic-fetch
logic other CARD contexts get). It joins RETREAT as a gap whose fix plausibly
needs type-matchup awareness the heuristic does not have today, rather than a
cheap threshold tune. Recorded here, with the new general-purpose
`iter_expert_card_decisions` spine primitive, so a future matchup-feature unit
can extend both gaps together instead of building two separate one-off tools.
