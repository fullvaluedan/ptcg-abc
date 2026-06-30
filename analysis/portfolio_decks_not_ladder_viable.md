# Portfolio decks collapse less but lose the prize race: not ladder candidates

Phase 4 deck-data. Empty-bench early_collapse (a lone basic active knocked out
with nothing to promote) is our #1 real ladder loss, root-caused to deck
thinness (6 basic Pokemon in 60 in the baseline combo line). The decided next-slot
lever is `trolley.csv`, which patches that line (Mega Signal 4 to 2, plus 2 Ultra
Ball and the Precious Trolley ACE SPEC) and cuts the mirror collapse rate from 80%
to 58% with no win-rate regression.

This iteration tested a different hypothesis: a structurally more consistent deck
(the U11 portfolio foils `aggro.csv` and `control.csv`, built around different
basics and a different energy type) might sidestep empty-bench collapse entirely
and be a stronger ladder candidate than patching the fragile glass cannon. Their
collapse rates had never been measured.

## The collapse-rate test looks like a landslide for the portfolio decks

`tools/collapse_rate.py`, heuristic mirror self-play, n=60 per deck (lower is
better):

| deck      | empty-bench collapse rate | 95% CI         |
|-----------|---------------------------|----------------|
| aggro     | 10.0% (6/60)              | 4.7% to 20.1%  |
| control   | 18.3% (11/60)             | 10.6% to 29.9% |
| trolley   | 58.3% (35/60)             | 45.7% to 69.9% |
| ultraball | 63.3% (38/60)             | 50.7% to 74.4% |
| baseline  | 80.0% (48/60)             | 68.2% to 88.2% |

aggro collapses roughly 6x less than baseline and 6x less than the queued trolley
patch. Read alone this says aggro is the consistency deck to ship.

## The win-rate matrix falsifies it outright

`tools/deck_match.py`, same heuristic policy, n=40 per ordered pairing:

| matchup             | row win rate | W/D/L     |
|---------------------|--------------|-----------|
| baseline vs aggro   | 82.5%        | 33/0/7    |
| baseline vs control | 87.5%        | 35/0/5    |
| trolley vs aggro    | 62.5%        | 25/0/15   |
| trolley vs control  | 92.5%        | 37/0/3    |
| baseline vs trolley | 52.5%        | 21/0/19   |
| aggro vs control    | 32.5%        | 13/0/27   |

Overall win rate (mean across opponents): baseline 74.2%, trolley 71.7%, aggro
35.0%, control 22.5%. Both portfolio decks lose to BOTH competitive decks
decisively. They are far weaker, not stronger.

## Why the two metrics disagree: collapse-rate is only valid within a win family

The portfolio decks collapse less because they LOSE BY OTHER MEANS, not because
they win. Their loss buckets move off empty_collapse and onto bad_determinization,
deck_matchup, and endgame_misplay (aggro's n=60 buckets: bad_determinization 32,
deck_matchup 15, endgame_misplay 7, early_collapse 6). A deck that rarely opens on
a lone basic but cannot close on prizes simply loses a longer, different-looking
game. The empty-bench collapse rate is a meaningful comparison ONLY among decks
that share a win condition (baseline, ultraball, trolley all run the same Mega
Abomasnow ex line); across archetypes a low collapse rate just means the deck
loses some other way. Do not rank decks across win-condition families by collapse
rate alone; gate every collapse-rate claim on a win-rate check.

## Decision: trolley stays the next-slot submission; portfolio decks are not ladder candidates

Among competitive decks, trolley is the only lever that both holds win rate even
with the strongest deck (baseline vs trolley 52.5%, trolley vs baseline 60.0%, CIs
span 50) AND cuts the empty-bench collapse that costs us the most real ladder
games. aggro and control remain Strategy-writeup portfolio pieces (the weakness-
counter two-deck concept) and matchup foils for the gauntlet, not submissions.

## Reproduce

```
.venv/Scripts/python.exe tools/collapse_rate.py decks/baseline.csv decks/trolley.csv decks/aggro.csv decks/control.csv -n 60
.venv/Scripts/python.exe tools/deck_match.py decks/baseline.csv decks/trolley.csv decks/aggro.csv decks/control.csv -n 40
```

Mirror self-play; absolute rates drift run to run (global RNG), but the orderings
(collapse: aggro < control < trolley < ultraball < baseline; win rate: baseline ~
trolley >> aggro > control) are stable.
