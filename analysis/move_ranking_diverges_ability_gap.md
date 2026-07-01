# The pilot plays like the top players 21% of the time; the biggest gap is ABILITY

## Finding

Run over the real dataset, the U5 held-out move-ranking validator gives the shipped
heuristic pilot a top-1 agreement of **0.212** with the top players across 4524 of
their actual MAIN decisions in 131 of their games. This is the first systematic run
of the validator (it was built in a831d44 but never scored against the dataset); the
only prior number was an incidental "10/76 at SEL_MAIN" from the missed-lethal
investigation, and this confirms that signal at scale.

The new `--breakdown` path (category_confusion) names WHERE the pilot diverges by
labeling both the option the expert played and the one our pilot would choose with
its action category. The result is not diffuse: the disagreement is concentrated in
a few categories, and one of them is a total capability gap.

## Evidence (analysis/move_ranking_validator.py --breakdown, real dataset, limit 1500)

```
expert teams: kazuki0123, tonakaiiii, The Debauchery Tea Party
episodes scored: 131 (skipped 1369)   expert decisions: 4524   top-1 agreement: 0.212

per expert action category (decisions, our agreement):
  ATTACH   n=1445  agree=87    (0.060)
  PLAY     n=1416  agree=372   (0.263)
  ABILITY  n=554   agree=0     (0.000)
  ATTACK   n=439   agree=338   (0.770)
  EVOLVE   n=258   agree=147   (0.570)
  END      n=210   agree=14    (0.067)
  RETREAT  n=202   agree=2     (0.010)

expert chose -> our pilot chose (on all decisions):
  ATTACH   -> PLAY:538, ATTACK:452, ATTACH:241, EVOLVE:214
  PLAY     -> PLAY:683, ATTACK:535, EVOLVE:198
  ABILITY  -> ATTACK:278, PLAY:152, ATTACH:44, END:33, EVOLVE:30, RETREAT:17
  ATTACK   -> ATTACK:341, PLAY:67, EVOLVE:19, ATTACH:6, RETREAT:6
  EVOLVE   -> EVOLVE:183, ATTACK:66, PLAY:9
  END      -> PLAY:84, ATTACK:70, EVOLVE:24, END:14, ATTACH:13, RETREAT:5
  RETREAT  -> ATTACK:106, PLAY:45, END:34, EVOLVE:9, ATTACH:6, RETREAT:2
```

## Ranked levers this names (grounded in real top-player data, not self-play)

1. **ABILITY is a complete blind spot: 0/554 (0.0%).** `heuristics.choose` has no
   OPT_ABILITY branch, so when a MAIN offers an ability the pilot never takes it; it
   attacks (278) or plays a card (152) instead. Abilities are 12% of the top
   players' MAIN decisions and are the draw / search / damage engines of this meta
   (the exact engine our meta-deck copies mispiloted). This is the clearest, most
   defensible next pilot lever: a categorical capability we simply lack, confirmed
   absent on every one of 554 real expert uses, and orthogonal to the bench work
   that has been refuted three times over. It is NOT an index-near-miss artifact:
   the pilot returns a non-ability option every time.

2. **ATTACH under-use: 87/1445 (6.0%), the experts' most common action.** When the
   expert attaches energy, half the time we PLAY (538) or ATTACK (452) instead of
   attaching (241) or evolving (214). The top players front-load energy; our MAIN
   priority (EVOLVE, then PLAY with a bench-thin defer, then ATTACH) reaches ATTACH
   later than they do. A candidate reordering can be scored against this same
   validator before any slot is spent.

3. **RETREAT 2/202 (1.0%) and END 14/210 (6.7%): we over-commit.** Where the expert
   retreats a pinned active or ends the turn, we keep attacking or playing. Lower
   priority than 1 and 2 by volume, but the same tool measures any fix.

ATTACK (0.770) and EVOLVE (0.570) already track the experts well and need no work.

## Caveat (unchanged from the validator's own docstring)

This is a RELATIVE filter, not an absolute skill measure: exact-index agreement is
strict and many options are near-equivalent, and offline agreement is not the ladder
(per meta.md, only the ladder confirms a win). The 0/554 ABILITY number survives the
caveat because it is categorical, not a near-miss: the pilot has no path that returns
an ability at all. Use this validator as the overfit filter for the next pilot change
(measure the agreement delta on this fixed held-out set BEFORE spending a ladder
slot), never as proof on its own.

## Next increment (clearly scoped, flag-guarded, measurable)

Add an ability-activation branch to `heuristics.choose` behind a default-off flag,
then re-run `--breakdown` to confirm it lifts ABILITY agreement off zero without
regressing ATTACK/EVOLVE, and self-play to confirm no crash or timeout. Ship only if
it is a verified improvement and never displaces a stronger live build.
