# Search recovered on the ladder (54218335 verdict: search_ran)

## The bet

Submission 54218335 (`submission_search_trolley.tar.gz`) force-loads our own
bundled `cg` under a private module name when the ambient `cg.api` lacks the
`search_*` wrappers, binding the forward model against our own native lib as a
separate instance. Prior search subs (54208986, 54208992) were inert: the
match-time `import cg.api` resolved a shadow with card data but no forward model,
so every decision fell back to the heuristic (bank draws of ~0.02 to 0.04s, never
the search budget; see `ladder_search_inert.md`). The whole recovery resolved on
one number: per-MAIN-decision overage-bank drawdown, ~0.5s if search ran vs
~0.02s if it stayed inert.

## The verdict: search runs, but it does not help

54218335 is COMPLETE. Its publicScore opened at 600.0 off the single validation
game, settled to 585.8 as the first real games accrued, and has now dropped to
431.4 as the sample grew. That is the LOWEST of the three trolley-era subs: the
plain trolley deck (569.6) and the trolley bench-guard (571.9), both the same deck
under the plain heuristic, sit ~140 points ABOVE it. A fresh per-agent pull
(`replays/search_trolley_fresh`, self-play skipped) confirms the score with the
record: 1W/3L, all three losses early_collapse. The recovery is real compute (search
ran; see below), but running it made the agent play WORSE than the heuristic floor
on the same deck. The recovery arc is closed and the outcome is negative.

The first ladder episode (episode-82961967) is a self-play validation game. Run
through the codified verify channel alone it read:

```
games with a searchable decision: 1
total searchable decisions: 6
max per-decision bank draw: 1.059s
verdict: search_ran
```

## Confirmed against real opponents

The doc's open action was to let 54218335 accrue non-self-play episodes and re-run
the channel. Two public ladder games (82962690, 82963490) have since completed and
been pulled. Over all 3 replays the channel now reads:

```
search activity over 3 replays in replays/search_trolley
  games with a searchable decision: 3
  games where search ran (draw >= 0.15s): 3
  total searchable decisions: 60
  max per-decision bank draw: 6.564s
  verdict: search_ran
```

The verdict holds against real opponents: every game searched, on every searchable
MAIN decision (60 total). The heaviest decision now draws 6.564s from the bank, far
above the 1.06s of the quiet self-play game and ~150x to ~300x the inert
heuristic-fallback cost. Determinized lookahead is unambiguously live on the ladder.

## Why tuning cannot rescue it: the offline A/B

The prior open action was to A/B `PTCG_ROLLOUT_DEPTH` offline and submit a config
that beats the current search stack. That plan rested on the search stack being
worth improving. A controlled offline gauntlet (search vs the plain heuristic, both
agents on the SAME deck via a staged `deck.csv`, n=30 each, alternating first seat)
shows it is not:

```
search vs heuristic, trolley deck,   n=30:  15W/15L = 50.0%  (CI 33.2 to 66.8%)
search vs heuristic, baseline deck,  n=30:  17W/13L = 56.7%  (CI 39.2 to 72.6%)
```

On the trolley deck search is a dead coin flip against the heuristic it falls back
to. The modest edge it carries on the baseline deck (56.7%) does not transfer to the
trolley deck at all. So search's offline CEILING on the trolley deck is parity with
the heuristic, and it pays that for nothing: the heuristic reaches the same 50/50 at
~0.02s per decision while search draws up to 6.564s. `PTCG_ROLLOUT_DEPTH` trades
terminal accuracy for more determinizations inside the budget, but no depth setting
can lift a stack whose full-depth ceiling is already only a tie. There is no
offline-validated improvement to submit, and offline self-play cannot even see the
real failure: on the ladder (the diverse field, not our own heuristic) trolley-search
scores 431.4 against the heuristic's 569.6 to 571.9.

The likely mechanism: `determinize` biases the hidden state toward the opponent's
recognized archetype, falling back to the MIRROR prior (assume the opponent runs OUR
deck) when nothing is recognized. Against a varied ladder field that prior is
systematically wrong, so the search optimizes lines for the wrong world and lands
below the assumption-free heuristic. All three fresh losses bucket as early_collapse,
the same empty-bench signature the heuristic hits, so search adds no endgame value
either, only cost and variance.

## Verify-channel defect fixed this iter

`scout.py search-activity` defaulted to `skip_self_play=True`, inherited from the
loss report where a self-play loss is not a real ladder loss. But this channel
measures OUR OWN agent's compute, which is opponent agnostic: a self-play replay
carries our search on both seats and is valid ground truth. With the only pulled
54218335 episode being a self-match, the default silently dropped it and printed
a false `inert` verdict over 0 replays. Changed the default to KEEP self-play
(with a `--skip-self-play` opt-out for the loss-shaped use), so the channel
reports the honest verdict on exactly the evidence a fresh submission first
produces. Regression test added: a self-play replay is kept by default and the
verdict is `search_ran`; opting out drops it to 0 games.

## What this closes

The search-on-the-ladder lever is closed with data. Search was recovered (it runs
in the grader sandbox, 66 searchable decisions over 5 replays, up to 6.564s draws)
but recovering it did not pay: on the trolley deck it only ties the heuristic
offline (50%) and loses to it on the ladder (431.4 vs 569.6 to 571.9). The standing
best agent to keep as the ladder floor is therefore the plain heuristic on the
trolley deck (bench-guard 54215910 at 571.9, plain trolley 54215558 at 569.6), NOT
search. Do NOT A/B `PTCG_ROLLOUT_DEPTH` / `PTCG_SEARCH_DETS` / `PTCG_SEARCH_BUDGET`
to "improve" the search stack (the offline ceiling is a tie, retired here), do NOT
re-submit 54218335 or anything already on the ladder, and do NOT re-walk the closed
analysis levers (deck falsification, bench-ordering, deck_matchup, draw-access). The
one thing that would reopen search is a determinization prior that models the real
opponent field instead of the mirror, which is a from-scratch modeling effort, not a
knob turn; absent that, the heuristic is the policy to defend.
