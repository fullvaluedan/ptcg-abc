# Raising THIN_BENCH does not cut our board-out: the guard threshold is flat

## Question
The brief leaves a decision branch open: if empty-bench early_collapse persists on the
live agent, "the thin-bench deferral is not firing enough (raise THIN_BENCH / more
aggressive bench-fetch)." THIN_BENCH is the width our develop-first guard insists on
before it stops forcing a Basic onto the bench, and it is also the threshold at which
the search agent DEFERS the whole MAIN decision to that heuristic guard. So raising it
does two things at once: the heuristic benches more turns, and search hands off more
turns. The open question is purely mechanical (does board-out drop), so it does not
need the ladder to answer.

## Method
`tools/measure_benchguard.py --sweep`. Our seat pilots the trolley deck at each swept
THIN_BENCH value against a fixed opponent whose guard is pinned at the shipped 2, so
the field is identical across settings and the only variable is our own guard width.
Only OUR seat's losses are classified (loss_classifier), so the empty-bench bucket is
attributable to our play alone. Read the CONTRAST across thresholds, not the absolute
level: mirror play over-states board-out (meta.md), and this is a board-out MEASUREMENT,
not a win-rate claim.

## Result (n=120/setting)
```
THIN_BENCH=1  early_collapse 46/120 (38.3%)  CI95 (0.301, 0.473)
THIN_BENCH=2  early_collapse 49/120 (40.8%)  CI95 (0.325, 0.498)   <- shipped
THIN_BENCH=3  early_collapse 48/120 (40.0%)  CI95 (0.317, 0.489)
```
A wider n=60 sweep of 0..4 agrees: every threshold sits at ~40% with heavily
overlapping Wilson intervals, and THIN_BENCH=3 was the WORST point estimate there
(53.3%), not the best.

## Conclusion
The threshold is on the FLAT part of the curve. No THIN_BENCH value in 0..4 does
mechanically better than the shipped 2; the differences are inside the sampling noise
at this n, and raising it trends the wrong way if anything. The ~40% board-out floor on
the glass-cannon trolley deck is set by the deck's basic density and the opponent's
pressure, NOT by how wide we insist the bench gets before developing something else.

This REFUTES the "raise THIN_BENCH" branch: the next iteration should not spend a
submission slot on THIN_BENCH=3. The bench-development guard (off vs on, 0 vs 2) already
buys its reduction (measured separately, ~43->34% our-seat, commit a0ac641); pushing the
same knob further is spent. If empty-bench collapse still dominates our ladder losses,
the remaining levers are the DECK (basic density / bench-fetch card count, a deck-level
change) or a stronger pilot that does not trade INTO the knockout in the first place,
not a higher deferral threshold.
