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

## The verdict

54218335 is COMPLETE. Its publicScore opened at 600.0 off the single validation
game and, as real ladder games accrued, settled to 585.8. That is above the plain
trolley deck (569.6) and the trolley bench-guard (571.9) but slightly below the
inert search on the baseline deck (54208986 at 591.9). So the recovery is real
compute, not yet a clear rating win; the two figures below (only 2 non-validation
games so far) are a small sample.

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

## The tuning input this exposes

6.564s on a single decision is ~13x the 0.5s `PTCG_SEARCH_BUDGET` soft cap. That is
expected, not a bug: the soft cap bounds the search LOOP, but each determinization
rolls out to a terminal `result` uninterrupted (`_ROLLOUT_DEPTH` defaults to None),
and the endgame solver raises the cap on pivotal decisions. So per-decision cost is
dominated by rollout depth against a real (long) game, not by the soft cap. Across
~20 searchable decisions per game the worst case still stays well under the 600s
bank, so this is a throughput/quality lever, not a timeout risk. The concrete tuning
knob is `PTCG_ROLLOUT_DEPTH`: a positive cut-off stops each rollout early and trusts
the board value function, trading terminal accuracy for more determinization samples
inside the same 0.5s. That is the first thing to A/B offline on the trolley deck.

The loss in the 1/0/1 real-game split buckets as early_collapse (empty-bench
self-collapse), a deck-level lever already worked and closed, not a search defect.

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

## What this opens

The verdict is now confirmed against real opponents (above), so the recovery arc is
closed. The next lever is tuning the recovered search stack on the trolley deck,
measured offline first, then submitted on a genuine offline-validated improvement.
The most promising knob given the 6.564s draws is `PTCG_ROLLOUT_DEPTH` (a terminal
cut-off buying more determinizations per decision), with `PTCG_SEARCH_BUDGET` and
`PTCG_SEARCH_DETS` as secondary width knobs. A/B each offline via the gauntlet on
the trolley deck before any submit. Do NOT re-walk the closed analysis levers (deck
falsification, bench-ordering, deck_matchup, draw-access) and do NOT re-submit
54218335 or anything already on the ladder.
