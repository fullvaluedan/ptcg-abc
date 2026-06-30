# Offline collapse-rate test reverses the deck submission order: trolley first

Phase 4 deck-data. The prior iterations established that empty-bench
early_collapse is our #1 real ladder loss (a lone basic active knocked out with
nothing to promote, 17 of 17 classified losses across all three heuristic-family
submissions), root-caused it to deck thinness (6 basic Pokemon in 60), and
staged two consistency decks as the fix:

- `ultraball.csv`: Mega Signal 4 to 2, plus 2 Ultra Ball (Item, discard 2, search
  the deck for any Pokemon). Keeps the Maximum Belt ACE SPEC.
- `trolley.csv`: same Ultra Ball swap, but the ACE SPEC is Maximum Belt to Precious
  Trolley (puts a basic from the deck straight to the bench, free, no discard).

The open question was which to submit first. Self-play win rate could not answer
it: both decks measured EVEN with baseline (the early_collapse upside is against
the diverse ladder field, which a mirror gauntlet cannot show, and it is a
minority of self-play games). The staged plan guessed ultraball first because it
was lower risk, with a note that trolley's free bench-basic might be the stronger
lever since the collapse lands as early as turn 3, before an Ultra Ball
discard-fetch can reliably fire.

## The metric the deck change actually targets is measurable offline

Win rate is the wrong yardstick for a consistency fix. The fix targets a specific
loss bucket, so measure that bucket directly. `tools/collapse_rate.py` runs N
heuristic-vs-heuristic mirror games per deck, reads `env.toJSON`, classifies the
loser of each game with the existing `analysis/loss_classifier.py`, and reports
the fraction of games lost to empty-bench early_collapse.

Caveat on reading the numbers: the mirror over-states the absolute rate, because
both seats pilot the same 6-basic glass cannon, so a lone-active knockout is the
dominant ending (70-plus percent here versus a minority on the ladder). The
signal is the RELATIVE reduction versus baseline, not the absolute level. On the
ladder only our deck carries the fix, so a lower mirror collapse rate means our
own seat collapses less often.

## Result (heuristic self-play, two independent n=80 runs, pooled n=160)

| deck      | run 1     | run 2     | pooled       | vs baseline       |
|-----------|-----------|-----------|--------------|-------------------|
| baseline  | 57/80     | 61/80     | 118/160 73.8%| --                |
| ultraball | 54/80     | 48/80     | 102/160 63.8%| -10.0pp (z ~ 1.9) |
| trolley   | 42/80     | 45/80     |  87/160 54.4%| -19.4pp (z ~ 3.7) |

trolley is lowest in both independent runs. Pooled, the baseline-to-trolley
reduction is highly significant (two-proportion z about 3.7, p < 0.001); the
baseline-to-ultraball reduction is real but only borderline (z about 1.9,
p about 0.05). trolley cuts empty-bench collapse roughly twice as much as
ultraball.

## Why trolley wins this metric

The collapse fires turn 3 to 5 (lone active KO'd, empty bench, deck still ~44
unplayed). Precious Trolley puts a basic on the bench the turn it is played, for
free, so it can answer a thin bench before the knockout. Ultra Ball must first
have two spare cards to discard and then resolve a deck search, which often comes
a turn too late, exactly the timing risk the staged plan flagged. The data
confirms the flag.

## Decision: submit trolley first on the next slot, not ultraball

This reverses the staged "ultraball first" order. trolley is the stronger
early_collapse lever and already measured non-regressing on self-play win rate
(EVEN with baseline, CI spans 50, see deck_design.md). The ACE SPEC trade
(Maximum Belt damage boost to Precious Trolley consistency) is the cost; the
collapse-rate data says the consistency is worth more than the boost against the
empty-bench failure that is costing us the most games.

ultraball stays as a fallback candidate and a Strategy-writeup portfolio piece.
After trolley has ladder episodes, re-pull with `tools/scout.py`, re-classify,
and confirm the live early_collapse bucket shrinks versus the baseline-deck
submissions. Do NOT re-walk the energy-trim or Master Ball / Poffin levers (ruled
out in deck_design.md).

## Reproduce

```
.venv/Scripts/python.exe tools/collapse_rate.py decks/baseline.csv decks/ultraball.csv decks/trolley.csv -n 80
```

Mirror self-play; the absolute rate drifts run to run (global RNG), the ordering
baseline > ultraball > trolley is stable.
