# CEM gradient restored: pilot category-ordering weights give the genome a channel to climb

**Date:** 2026-07-01
**Unit:** P2 / U6 (unblocks the CEM verification run)
**Follows:** `analysis/cem_signal_flat.md` (the flat-gradient finding this fixes)

## What changed

`analysis/cem_signal_flat.md` showed the CEM optimizer had almost no gradient:
over 11 genome dims the expert-move agreement moved by at most 0.0049, and 8 of 11
dims moved it exactly 0.0000. The root cause was structural: the dominant driver of
the pilot's MAIN decisions, `agents/heuristics.choose`'s fixed category priority
ladder (lethal -> rare-candy -> evolve -> play -> attach -> ability -> retreat ->
attack -> end), was hard-coded and not in the genome, while 7 of the 11 dims were
`search/eval.py` teacher knobs that never enter the shipped pilot's `choose()`.

This iteration converts that fixed ladder into a **genome-scored ordering**. Each
action category now carries a CEM-tunable priority weight (`PTCG_W_PRIO_CANDY`,
`_EVOLVE`, `_PLAY`, `_ATTACH`, `_ABILITY`, `_RETREAT`, `_ATTACK`); `choose()` takes
the highest-priority category that yields a legal move. The lethal knockout
(safety-1) stays hard-first and END stays the last fallback; neither is tunable.

**Ship guarantee preserved.** The shipped priority defaults descend in the exact
order of the old fixed ladder (6.0 > 5.0 > ... > 0.0), so an un-tuned build is
byte-identical: every `PTCG_W_PRIO_*` is unset and returns its default, the
defaults reproduce the old order, and `weight_space.vector_to_env` emits nothing.
Loop-safety is order-independent: every category is resource-consuming
(evolve/play/attach) or turn-ending (attack), and only a once-per-turn ability is
ever taken, so any ordering still terminates the turn.

## The gradient is now non-flat (same harness, same held-out sample)

`python -m analysis.measure_cem_gradient replays_cem_holdout --limit 40`, 40
held-out expert-seat episodes (1427 real MAIN decisions), baseline agreement
0.2292:

```
dim                              low->agr   high->agr    delta
PTCG_W_PRIO_ATTACK                 0.2292      0.1766   0.0526
PTCG_W_PRIO_ATTACH                 0.2235      0.2495   0.0259
PTCG_W_PRIO_PLAY                   0.2460      0.2348   0.0112
PTCG_W_PRIO_RETREAT                0.2292      0.2186   0.0105
PTCG_W_PRIO_EVOLVE                 0.2313      0.2278   0.0035
PTCG_W_PRIO_CANDY                  0.2278      0.2292   0.0014
PTCG_W_PRIO_ABILITY                0.2292      0.2292   0.0000
... (the 4 threshold + 7 eval dims unchanged from cem_signal_flat.md)

9/18 dims move agreement at all; max delta = 0.0526
```

Read it straight:

- **Max delta rose from 0.0049 to 0.0526, over 10x.** The five ordering dims that
  move the signal are all new, and they now sit at the top of the leverage table.
  CEM finally has a channel it can climb.
- **A concrete above-baseline direction exists.** Raising `PTCG_W_PRIO_ATTACH`
  above its default rank lifts agreement to 0.2495, above the 0.2292 default: a
  candidate that orders ATTACH earlier than the shipped ladder matches the top
  players' moves BETTER. That is exactly the kind of ordering improvement the flat
  genome could not reach.
- **Directions are sane.** Raising `PRIO_ATTACK` DROPS agreement (0.2292 -> 0.1766):
  the experts do not attack over developing, confirming the shipped default (attack
  lowest) is right and warning CEM off the degenerate attack-first pilot.
- **`PRIO_ABILITY` reads 0.0000 here** only because the ability lever (`PTCG_ABILITY`)
  is default-off, so no ability option is ever taken in this sweep. Its leverage
  appears once the ability flag is on (validated separately in the unit tests).

## Next

The U6 gate is now honestly passable: the engine can move the pilot. The next
increment is a real CEM run against the pool (U4) and the held-out validator (U5)
to produce a tuned priority vector, offline-filter it, and gate the winner on
ladder A/B (the sole arbiter). The `PRIO_ATTACH`-earlier direction is the first
hypothesis the run should confirm or refute.

## Reproduce

```
python -m analysis.measure_cem_gradient replays_cem_holdout --limit 40
```

The competition replays stay gitignored (`replays_*/`, `data/`); only this writeup
and the diagnostic tool are committed.
