# CEM cannot tune the pilot: both fitness channels are near-flat over the genome

**Date:** 2026-07-01
**Unit:** P2 / U6 (blocks the CEM verification run)
**Verdict:** The CEM optimizer as wired (`tools/cem_tune.py` over
`tools/weight_space.PARAM_SPACE`) has almost no gradient to climb. Running it now
would return the shipped default vector (an empty override map, a byte-identical
build) and burn a ladder slot for no change. The genome must grow the levers that
actually drive the pilot's decisions before a CEM run is worth a slot.

## What the engine needs and what it has

CEM scores each candidate weight vector by two offline filters:

1. **Pool win rate (U4):** the heuristic pilot vs the diverse deck pool
   (`tools/opponents.pool`).
2. **Held-out expert-move agreement (U5):** how often the pilot's `choose(obs)`
   picks the option a top player actually played, on real replay decisions.

For CEM to climb, at least one signal must MOVE as the genome changes. Neither does.

### Channel 1: pool win rate saturates at 1.0

The pilot beats the deck pool essentially every game (4/4 in a smoke gauntlet, and
the pool opponents are the same heuristic on different decks, so the mirror is a
coin-flip-to-win, not a discriminating test). A signal pinned near 1.0 gives CEM
no ordering over candidates. This is the exact "offline weak-bot gauntlets are not
predictive" finding the plan is built on (KTD4), now measured on the U4 pool.

### Channel 2: expert-move agreement barely responds to the genome

Measured with `analysis/measure_cem_gradient.py` over 40 held-out expert-seat
episodes (1427 real MAIN decisions by kazuki0123 / tonakaiiii / The Debauchery Tea
Party). Each row moves ONE genome dim to its low then its high bound, holding the
other ten at the shipped default, and reports the top-1 agreement of that build:

```
baseline agreement: 0.2292 (n=1427)

dim                              low->agr   high->agr    delta
PTCG_W_THIN_BENCH                  0.2292      0.2242   0.0049
PTCG_W_RETREAT_HP_RATIO            0.2313      0.2278   0.0035
PTCG_W_DRAW_CONSERVE_THRESHOLD     0.2292      0.2263   0.0028
PTCG_W_DECKOUT_THRESHOLD           0.2292      0.2292   0.0000
PTCG_W_PRIZE_SHAPING               0.2292      0.2292   0.0000
PTCG_W_HP_SHAPING                  0.2292      0.2292   0.0000
PTCG_W_ACTIVE_HP_WEIGHT            0.2292      0.2292   0.0000
PTCG_W_BOARD_SHAPING               0.2292      0.2292   0.0000
PTCG_W_ENERGY_SHAPING              0.2292      0.2292   0.0000
PTCG_W_BENCH_FLOOR_SHAPING         0.2292      0.2292   0.0000
PTCG_W_BENCH_TARGET                0.2292      0.2292   0.0000

3/11 dims move agreement at all; max delta = 0.0049
```

Read it straight: **8 of 11 genome dims have exactly zero leverage**, and the three
that move the signal move it by at most half a percentage point, all DOWNWARD from
the default. The shipped default vector is already the agreement-maximizing point
inside this genome.

## Why the genome is inert (structural, not noise)

- **7 of 11 dims are `search/eval.py` shaping weights** (`PRIZE_SHAPING`,
  `HP_SHAPING`, `ACTIVE_HP_WEIGHT`, `BOARD_SHAPING`, `ENERGY_SHAPING`,
  `BENCH_FLOOR_SHAPING`, `BENCH_TARGET`). These tune the offline TEACHER's leaf
  value. They never enter the shipped pilot's `choose()`, so they cannot move the
  pilot's move agreement. This is a hard zero: correct by construction, and it says
  those seven dims are simply not part of the same optimization problem as the pilot
  channel. They belong to the teacher (label generation, P3 search), not the player.
- **The 4 pilot knobs are narrow thresholds.** `THIN_BENCH`, `RETREAT_HP_RATIO`,
  `DECKOUT_THRESHOLD`, `DRAW_CONSERVE_THRESHOLD` only change the outcome of a small
  slice of decisions (which play to bench when the bench is thin; whether to retreat
  a low active; whether to skip a draw trainer near deckout). On the broad expert
  decision set most decisions never touch those branches, so the aggregate agreement
  moves under a hundredth.
- **The dominant driver is NOT in the genome.** `agents/heuristics.choose` is a
  fixed category priority ladder: lethal -> rare-candy -> evolve -> play -> attach
  -> ability -> retreat -> attack -> end. That ORDER decides the overwhelming
  majority of MAIN decisions, and it is hard-coded, not a tunable weight. The
  category-level move-ranking work already showed where the pilot diverges from the
  experts (the ABILITY gap, EVOLVE ordering); those are order/branch decisions, not
  threshold values. CEM over the current genome cannot reach them.

## Implication for P2 (this is the gate, honestly stated)

- A CEM run today returns the default and ships nothing new. Do NOT spend a ladder
  slot on it. That the default is already agreement-optimal inside the genome is a
  small positive (the current pilot is not overfit away from the experts on its
  tunable axes), but it is not a climb.
- To make the CEM engine actually improve the ladder-relevant pilot, the genome has
  to include parameters that drive the pilot's real decisions. The highest-leverage
  candidate is to convert the fixed category priority ladder into a scored ordering
  whose **per-category weights** (and a few branch gates like the ability/evolve
  ordering the breakdown flagged) are genome dims. Then agreement has something to
  climb, and the same weights are what the ladder A/B ultimately judges.
- Until that genome exists, the eval-weight half of the vector should be understood
  as the TEACHER's knobs (relevant to P3 search leaf tuning, U8/U9), not the
  player's. Splitting the genome into a pilot-genome and a teacher-genome would stop
  CEM wasting 7 of its 11 search dims on a channel that cannot see them.

## Reproduce

```
# extract a small held-out expert sample (gitignored, never committed):
#   40 expert-seat episodes -> replays_cem_holdout/
python -m analysis.measure_cem_gradient replays_cem_holdout --limit 40
```

The competition replays stay gitignored (`replays_*/`, `data/`); only this writeup
and the diagnostic tool are committed.

## Next

Two clean options for the next iteration, both offline (quota was 5/5 on 07-01,
resets 00:00 UTC 07-02):

1. **Grow the pilot genome** (make U6 able to climb): add per-category ordering
   weights to `agents/heuristics.choose` and to `PARAM_SPACE`, re-run this
   diagnostic to confirm the gradient is now non-flat, then a real CEM run.
2. **Advance to P3 / U7** (the Long et al. determinization diagnostic), which does
   not depend on the CEM channel and is the gate for reviving search.

Recommended: option 1, because it keeps P2 honest (the engine must be able to move
the pilot before we call P2 done) and because the category-ordering levers are
exactly where the expert breakdown says the pilot diverges.
