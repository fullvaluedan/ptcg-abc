# The endgame_misplay losses were empty-bench collapses

## Context

Fresh larger-sample pull (07-01, UTC ~01:06) of the two board leaders, which had
accrued more ladder games since the prior n=6 pull. Isolated dirs, one seat per
replay from info.TeamNames.

| Agent | ref | Record | early_collapse | endgame_misplay | Board |
|-------|-----|--------|----------------|-----------------|-------|
| benchguard | 54215910 | 5W/3L (n=8) | 2 | 1 | 679.2 (best) |
| trolley | 54215558 | 8W/6L (n=14) | 5 | 1 | 677.9 |

The guard's edge over the deck-only fix held a second time: benchguard still
leads on record (62.5% vs 57.1%) and on the raw early_collapse rate, consistent
with the prior pull. Scores stay effectively tied inside the TrueSkill drift band.

## Finding

An `endgame_misplay` bucket appeared once on each leader, which the standing NEXT
would read as a genuine second (search/judgement) lever. Walked both at the card
level. Both are empty-bench:

- benchguard ep 82944784: turn 13, my_prize 2, opp_prize 3, deck 17, **bench 0**
- trolley ep 82939817: turn 7, my_prize 2, opp_prize 6 (opp took ZERO prizes,
  we were far ahead), deck 32, **bench 0**

Both ended with our lone active knocked out and nothing to promote: the same
empty-bench collapse as every other loss, not search slipping a winnable endgame.
They were labeled `endgame_misplay` only because `classify_loss` ran the near-win
(`my_remaining <= close_remaining`) gate BEFORE the empty-bench gate, so a
collapse that happened to land two prizes short of the win was miscredited to
judgement.

This is the same misbucketing pattern already fixed for `bad_determinization`
(f2a8ffb) and the late empty-bench cases (b9c356b): the empty-bench signature is
the real proximate cause regardless of when in the prize race it fires.

## Fix

`classify_loss` now runs the `my_bench_end == 0 -> early_collapse` gate BEFORE the
`endgame_misplay` near-win gate (still after `deckout` and `deck_matchup`, which
are distinct end states). Genuine endgame misplays keep a bench (bench > 0 or
None, never observed), so they still reach the near-win gate. Two tests lock both
directions: an empty-bench near-win loss buckets early_collapse, a near-win with a
standing bench stays endgame_misplay. 173 tests pass (was 171).

Reclassified on the real pulls: benchguard endgame_misplay 1 -> 0 (early_collapse
2 -> 3), trolley 1 -> 0 (early_collapse 5 -> 6). Every loss on both leaders is now
the one empty-bench signature: 3/3 and 6/6.

## Consequence

There is NO endgame_misplay lever and no developed-board second lever. 100% of
losses on both board leaders are the empty-bench consistency ceiling the card pool
cannot thin (bench_fetcher_survey.md, empty_bench_is_draw_variance.md). This
forecloses a phantom lever rather than opening a new one; it does not change the
submitted artifacts. benchguard 54215910 stays the standing best / preferred
artifact and no re-submit is warranted (it is already up and leading).
