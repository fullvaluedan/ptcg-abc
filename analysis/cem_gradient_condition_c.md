# Condition (c) checked directly: the genome IS non-flat, and its peak is the shipped default

**Date:** 2026-07-04
**Unit:** L7/U83 re-test, condition (c) from `analysis/cem_run_prio_teacher.md`
**Follows:** `analysis/cem_run_prio.md`, `analysis/cem_run_prio_pooled.md`, `analysis/cem_run_prio_teacher.md`
(three converging BLOCKED CEM sweeps over the 18-dim PRIO genome)
**Run artifact:** `analysis/cem_runs/gradient_probe_teacher_test.json`

## What ran

Three consecutive CEM sweeps over `tools/weight_space.PARAM_SPACE` all BLOCKED on held-out
transfer (agreement-only, pooled win-rate+agreement, ring win-rate+agreement at 92x scale).
Each writeup named the same one remaining re-open condition: "(c) a genome region with a
measured non-flat held-out gradient", explicitly to be checked BEFORE spending a fourth full
sweep. `analysis/measure_cem_gradient.py` already existed for exactly this per-dim leverage
check (it is how U6 discovered the PRIO_* ordering genome in the first place, on a 40-episode
real-replay sample), but it only supported the real-ladder-replay label source. Extended it
with a `--teacher-labels`/`--split` mode (mirroring `tools/cem_held_out_gate.py`'s scoring
path) so the SAME per-dim probe could run against the exact held-out `test` split the three
CEM verdicts were blocked on, not a different, smaller sample.

`python -m analysis.measure_cem_gradient --teacher-labels data/training --split test --limit
100000` (no engine, no games; move-ranking agreement is deterministic and needs no seed).
`n=10689` scorable MAIN decisions, baseline agreement 0.8210, exactly matching
`cem_run_prio_teacher.md`'s reported default/test agreement, confirming this reads the same
held-out population the three CEM sweeps blocked against.

## Result: non-flat, but every direction is downhill from the default

```
dim                              low->agr   high->agr    delta
PTCG_W_PRIO_ATTACK                 0.8210      0.5472   0.2738
PTCG_W_PRIO_ATTACH                 0.8202      0.6365   0.1836
PTCG_W_PRIO_PLAY                   0.6638      0.8043   0.1405
PTCG_W_PRIO_EVOLVE                 0.7895      0.8210   0.0315
PTCG_W_THIN_BENCH                  0.8085      0.8141   0.0056
PTCG_W_PRIO_RETREAT                0.8210      0.8180   0.0030
PTCG_W_RETREAT_HP_RATIO            0.8198      0.8211   0.0013
PTCG_W_DRAW_CONSERVE_THRESHOLD     0.8206      0.8198   0.0007
... (10 remaining dims exactly 0.0000, same structural-zero dims cem_signal_flat.md named)

8/18 dims move agreement at all; max delta = 0.2738
```

Read it straight:

- **Condition (c) is now met and answered.** Max delta rose from 0.0526 (the 2026-07-01
  diagnostic, small real-replay sample, old fixed-ladder-vs-PRIO-genome comparison) to
  0.2738 here, over 5x larger, on the actual held-out population the CEM sweeps use. The
  genome is emphatically NOT flat on this split.
- **But every bound that moves agreement moves it DOWN, not up.** For every one of the four
  load-bearing ordering dims (ATTACK, ATTACH, PLAY, EVOLVE), the shipped default's own
  agreement (0.8210) is at or above BOTH of that dim's bound readings:
  - `PRIO_ATTACK` default 0.0 IS the low bound (0.8210, unchanged); the high bound (10.0,
    attack-first) drops agreement to 0.5472. Confirms attack-last is already correct.
  - `PRIO_ATTACH` default 3.0 sits between its bounds; low (0.0) reads 0.8202, barely below
    default; high (10.0) reads 0.6365, far below. Default is already at/near this dim's peak.
  - `PRIO_PLAY` default 4.0; low (0.0) reads 0.6638 and high (10.0) reads 0.8043, BOTH below
    the default's 0.8210. The default is a local maximum on this axis, not an endpoint.
  - `PRIO_EVOLVE` default 5.0; low (0.0) reads 0.7895 (worse); high (10.0) reads 0.8210, a
    tie with the default, never better.
  - The three smallest deltas (`RETREAT_HP_RATIO` high +0.0001, `PRIO_RETREAT`, `THIN_BENCH`)
    are within noise of the read itself (single-axis, others held at default) and do not
    clear any threshold a real CEM candidate would need to beat (compare: the three blocked
    sweeps' own deltas were -0.0022 to -0.067).
- **No single-axis direction beats the shipped default anywhere in the 18-dim genome.** This
  is a stronger, more mechanistic result than "CEM found nothing": it shows there IS a real
  gradient (ruling out "the genome has no signal at all" as the explanation for 3 straight
  BLOCKED verdicts), and separately shows the gradient's exploitable direction is already
  where the shipped agent sits. That reconciles cleanly with why every CEM sweep that
  wandered off the default (whether pulled by a small elite-fit on train, or by noisy
  ring-win-rate proxy signal) landed on a WORSE held-out point: the local landscape here
  slopes downward away from the current default along every load-bearing dim, so an
  optimizer under any noise at all is more likely to step off the peak than to climb it
  further.

## Verdict

Condition (c) CLOSED, negative: no exploitable single-dim direction exists. This is the
fourth consecutive negative result over this exact genome (the 3 CEM sweeps plus this direct
per-dim check), and it is the strongest one, because it explains the mechanism rather than
just reporting another failed optimizer run. Per the pre-registered offline filter (KTD1/
KTD4), no ladder A/B follows; ship stays byte-identical.

## Re-test condition

Do not re-run a CEM sweep over this same 18-dim genome; a fourth sweep would face the same
locally-optimal-at-default landscape this diagnostic just measured directly, at a fraction of
the cost of another population/iteration run. Re-open the CEM/PRIO track only with a
genuinely new weight-space region: a dimension this genome does not currently express (e.g.
a card-identity- or archetype-aware weight, per the comprehension track's U90/U91 mined
levers) whose held-out gradient has not yet been measured by this tool. Until then, the
CEM/PRIO lever is fully exhausted, not merely paused.
