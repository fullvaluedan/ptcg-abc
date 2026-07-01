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

54218335 is COMPLETE at publicScore 600.0, the new best on the board (prior best
was the inert search 54208986 at 591.9, and the plain trolley deck at 569.6).

The first ladder episode for it (episode-82961967) is a self-play validation
game. Run through the codified verify channel it reads:

```
games with a searchable decision: 1
games where search ran (draw >= 0.15s): 1
total searchable decisions: 6
max per-decision bank draw: 1.059s
mean per-decision draw:      0.409s
verdict: search_ran
```

The private forward-model load survived the grader sandbox: determinized search
actually ran on the ladder, drawing 1.06s from the overage bank on its heaviest
MAIN decision, ~20x to ~50x the inert heuristic-fallback cost. The recovery is
real.

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

The next lever is tuning the recovered search stack on the trolley deck
(`PTCG_SEARCH_BUDGET`, determinization width), measured offline first, then
submitted on a genuine offline-validated improvement. Do NOT re-walk the closed
analysis levers (deck falsification, bench-ordering, deck_matchup, draw-access)
and do NOT re-submit 54218335 or anything already on the ladder. Let it accrue
non-self-play episodes and re-run `scout.py search-activity` to confirm the
verdict holds against real opponents.
