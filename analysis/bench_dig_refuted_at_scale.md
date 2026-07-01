# Digging for a Basic when the bench is thin does not cut our board-out (refuted at scale)

## Question
`analysis/empty_bench_is_draw_variance.md` retired bench-ORDERING as an
early_collapse lever: in the ladder replays that collapsed, in 94% of the
empty-bench decision moments we held NO benchable Basic to reorder onto the bench,
so a guard that benches a Basic you already hold has nothing to bench. That finding
pointed at the OTHER half of the collapse: when the bench is thin and we hold no
Basic and no direct bench-fetch trainer (Precious Trolley), could DIGGING for one
this turn (playing a draw/search trainer to find a Basic) cut the board-out that
ordering cannot? It is a distinct mechanism (dig when you hold none, vs reorder one
you hold), so it deserved its own measurement rather than inheriting the ordering
refutation.

## The lever
`heuristics.choose_play`, the not-near-deckout thin-bench branch, gated on
`_BENCH_DIG` (env `PTCG_BENCH_DIG`, default off, ships byte-identical). After the
existing steps (bench a Basic from hand; else Precious Trolley direct to bench), if
neither is available it prefers a draw/search trainer that drills the deck
(`_drills_deck`: Ultra Ball, Cyrano, a draw Supporter) to find a Basic, before
spending the thin-bench turn on an energy attach or a non-digging item.

## Method
`tools/measure_bench_dig.py`, the same controlled single-seat design as
`measure_benchguard`: both seats pilot the same deck with the same heuristic, the
OPPONENT seat's dig lever is pinned off (the shipped default), and only OUR seat's
lever is toggled off vs on. Only OUR seat's losses are classified, so the opponent
pressure is identical across the two runs and the only variable is our own dig
lever. A claim is made only when the two Wilson intervals do not overlap. Mechanical
board-out measurement, not a win-rate claim (offline mirror play is not
ladder-predictive, meta.md).

## Result: a small-n mirage that reversed at scale
```
n=120 (symmetric mirror, both seats dig, collapse_rate): 82.5% -> 77.5%  (-5.0pp)
n=160 (single-seat, opponent pinned off):                40.6% -> 33.1%  (-7.5pp)  CI overlap
n=360 (single-seat, opponent pinned off):                37.5% -> 39.4%  (+1.9pp)  CI overlap
```
At n=120 and n=160 the direction looked favorable (-5 to -7.5pp) and tempting. But
the Wilson intervals overlapped the whole way, and at the larger, more reliable
n=360 sample the effect REVERSED to +1.9pp (dig slightly worse). Our total losses
were flat too (168 off vs 172 on at n=360). The early favorable point estimates were
sampling noise, not signal.

## Conclusion
REFUTED. The dig lever does not mechanically reduce our empty-bench board-out at
reliable n. This is the third independent confirmation of the same axis:
- bench ORDERING (bench a Basic you hold) has no purchase (draw-variance finding);
- raising THIN_BENCH is on the flat part of the curve
  (`analysis/thin_bench_threshold_is_flat.md`);
- DIGGING for a Basic when you hold none is null at scale (this file).

All three agree with the mechanism: the empty-bench collapse is a DECK draw/density
problem, not a pilot play-access problem. When the trolley glass cannon boards out,
in roughly half the games there is no second Basic in the reachable deck to find, so
no amount of digging or reordering can produce one. The lever that moves this metric
is deck basic-density (`decks/trolley_thick.csv`, Kyogre 2->4, measured -15pp
collapse), not another pilot guard.

The lever stays gated off permanently (`test_shipped_config.py` pins
`heuristics._BENCH_DIG is False`). The measurement tool and the reproducible flag are
kept so the refutation is re-runnable, and so no future iteration spends a scarce
daily ladder slot re-testing a pilot-side answer to a deck-side problem.

## Measurement-discipline note (for the writeup)
This is a clean example of why the loop reads CONTRASTS with Wilson intervals and
raises n before claiming a lever: a -7.5pp point estimate at n=160 would have looked
like a win and could have burned a submission slot, but it was inside the noise and
inverted at n=360. Small-n favorable, large-n null is the exact trap the oracle-poor
measurement discipline is built to catch.
