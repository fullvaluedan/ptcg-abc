# Fetch a Basic onto the bench before a hand-disrupting play (heuristic)

## The gap this closes

`choose_play` already benches a Basic first when the bench is thin, but only when
a Basic Pokemon is in hand to bench directly. The dominant early_collapse loss is
exactly the case where it is NOT: a lone active is knocked out with an empty bench
and no benchable Basic in hand. In that case the old code fell through to
`play_opts[0][0]`, the first PLAY option in whatever order the engine listed it.

That order matters when the hand also holds a deck-search that benches Basics
(Precious Trolley: "Search your deck for any number of Basic Pokemon and put them
onto your Bench"). Within a turn `choose()` exhausts PLAY options before END, so
in the simple case the Trolley is played anyway. But a hand-disrupting play kept
ahead of it can strand it: Lillie's Determination shuffles the whole hand,
including the Trolley, back into the deck, and Ultra Ball's discard-2 can burn it.
Played first, those leave the empty bench unfilled for the turn.

## The change

When the bench is thin and no Basic is in hand to bench directly, prefer a PLAY
that searches the deck and benches a Basic (`_benches_basic_from_deck`, read from
the effect text so Precious Trolley qualifies and any Nest Ball style basic-to-
bench search generalizes; Mega Signal / Cyrano / Ultra Ball, which only fetch to
hand, are excluded). This deploys the bench-fixer before a hand-shuffling
Supporter can strand it. Placed after the direct-bench-a-Basic step and only in
the non-deckout branch, so a healthy board and the near-deckout milling guard are
untouched.

## Offline measurement (why this is kept but NOT submitted)

Mirror collapse_rate on the trolley deck, heuristic self-play, n=160 each:

- current heuristic: 119/160 early_collapse (74.4%, 95% CI 67.1% to 80.5%)
- with fetch-priority: 132/160 early_collapse (82.5%, 95% CI 75.9% to 87.6%)

No reduction; the two intervals overlap heavily. The mirror is the wrong
instrument for a one-sided policy change: both seats carry the fix, so a
symmetric improvement does not lower the loser-collapse fraction (someone still
loses each decided game). Instrumenting the path directly over 80 self-play games:
the fetch-priority branch activated 35 times and actually REORDERED the pick only
13 times, about one reorder per twelve player-games, and only a fraction of those
sit behind a hand-disrupter that would have stranded the Trolley. The behavioral
delta is real but below the TrueSkill ladder noise band (score swings of ~130 pts
are routine here), so the mirror cannot detect a benefit and neither would the
ladder on any near-term sample.

Decision: keep the change (it is a strict correctness refinement that deploys the
bench-fixer earlier and never regresses a legal play; full suite 183 pass,
gauntlet vs random 89.0% with 0 invalid) but do NOT spend a slot on it. A new
submission would displace the current second-scored agent (benchguard 611.8) from
the latest-2-scored pair, so shipping an offline-undetectable change risks
lowering the standing for no measured gain. This closes the last named
ladder-executing lever (draw-access, dig a Basic when bench thin and hand holds
none) with data: the card pool's only direct-bench fetch is already deployed by
the heuristic; sequencing it earlier is correct but not slot-worthy.
