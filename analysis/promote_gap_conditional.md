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
  expert picked the best type-matchup option: 39.6%
  expert picked bench index 0:                36.3%
```

(n=91 is the real promote-decision population found across the entire
2026-07-03 dump, not a `--limit`-truncated sample; this decision only fires
once per knockout with a non-empty bench, so it is naturally rarer than
ATTACH/RETREAT/ABILITY.)

## Interpretation

Four candidate signals were checked against the real expert pick, each
independently: bench index 0 (what `_first_legal` already produces for free),
the bench option with the highest current HP ratio, the bench option with the
most energy attached, and (added this unit) the bench option with the best
type matchup against the opponent's active, via the new shared
`analysis/matchup_delta.py` primitive (`matchup_score`, lifting
`agents/heuristics.py`'s `effective_damage` weakness/resistance rule to a
symmetric, attack-independent per-Pokemon comparison, exactly the follow-on
this doc named below). **None of the four clears even 40%.** Type matchup is
the best of the four (39.6%, edging out the 36.3% agree/energy/index-zero
tie), but that margin is small enough (3.3pp on n=91) to not be a real signal
on its own, and it is nowhere near a majority. Note `agree` and
`played_is_index_zero` are identical by construction (the injected/default
pilot's answer literally is index 0 every time), confirming the pilot is not
doing anything beyond first-legal today.

Unlike the RETREAT gap, where a clear majority (75.6% of misses) shared one
property (near-full HP, pointing at a matchup-swap story), no single simple
per-candidate feature here explains anywhere near a majority of real picks,
and that now includes type matchup: checked directly (not just theorized),
it still tops out at 39.6%. This does not mean the decision is random: it
means HP ratio, raw energy count, and type matchup, each checked one at a
time, are not the (or not the only) governing signal. Plausible remaining
candidates not yet checked: whether a bench mon can score an immediate
knockout on promotion, retained Prize-card implications, or some combination
of the fields already checked (e.g. matchup AND energy together) rather than
any single field alone.

## Why this is not a shippable lever yet

At n=91 with no candidate signal (including the newly-added type matchup)
clearing 40%, there is not yet a concrete, well-supported rule to write
(unlike ABILITY, a clean capability flip). Coding "promote highest HP",
"promote most energy", or "promote the best matchup" against this evidence
would be guessing at the same strength as the current arbitrary
`_first_legal`, and risks the same shape of refutation the ATTACH
energy-sequencing lever already hit when it was shipped on intuition instead
of measurement. The concrete next step (not yet built) is to check whether a
combined signal (e.g. best matchup among only the max-energy candidates, or
an immediate-knockout-on-promotion check) explains a majority, since no
single field examined so far does.

## Conclusion

PROMOTE is a confirmed, previously-unmeasured, currently-unruled category (the
pilot's answer here is pure `_first_legal`, not even the thin-bench Basic-fetch
logic other CARD contexts get). Type-matchup awareness, once actually measured
(not just theorized), turned out NOT to be the missing piece here either: it
is the strongest of four candidate signals but still explains under 40% of
real picks alone. Recorded here, with the new general-purpose
`iter_expert_card_decisions` spine primitive and the new general-purpose
`analysis/matchup_delta.py` (`matchup_score`), so a future unit can (a) re-run
the RETREAT gap's own matchup-swap theory through the same tested primitive
(not yet done, see `analysis/retreat_gap_conditional.md`) and (b) try combined
signals here instead of guessing at a single-field promote rule.
