# U35 re-test: pooled fitness (win_rate + agreement) also fails to generalize

**Date:** 2026-07-03
**Unit:** P1 / U35 re-test, condition (b) from `analysis/cem_run_prio.md`
**Follows:** `analysis/cem_run_prio.md` (the agreement-only run, held-out delta -0.067, BLOCKED)
and the `fix(cem)` commit that fixed `_parse_evaluator_output` (the stray 0-byte
`cem_run_prio_pooled_seed0.log` from an earlier attempt never produced a valid score
because of the stdout-parsing bug; that fix is what makes this run possible).
**Run artifact:** `analysis/cem_runs/cem_run_prio_pooled_seed0.json`

## What ran

A real `tools/cem_tune.py` run over the same 18-dim PRIO genome
(`tools/weight_space.py`; two dims, `PTCG_W_PRIO_ATTACK` and `PTCG_W_BENCH_TARGET`,
are absent from the best vector's env map because the best candidate happened to
land on the shipped default cast value for those two dims), this time with
**both** fitness channels on:
`--pool-matches 10` (win rate vs the U4 diverse pool) and `--w-pool 0.5 --w-val 0.5`
(equal blend with the U5 move-ranking agreement channel), fit on the held-out-clean
**train** md5 bucket (`--split train`), seed 0.

**Reduced scale, stated up front:** `--population 8 --elite 2 --iterations 4` (later
re-run at `--population 6 --elite 2 --iterations 3` after the first attempt exceeded
the loop iteration's time budget; each fitness evaluation spawns a fresh subprocess
that pays a ~14s fixed startup cost plus ~0.25s per pool match, so a full-scale
population-50/iterations-20 sweep would run several hours). This is a materially
smaller search than U35's agreement-only run (population 50 default, 12 iterations
before the injected-variance floor stopped improving `best_fitness`), so a negative
result here is weaker evidence that the whole PRIO axis is dead and stronger evidence
only against this specific reduced configuration. Recorded honestly as a scale
caveat, not smoothed over.

## Held-out evaluation (ship-faithful, same protocol as U35)

Both the default (ship) vector and the run's best vector, evaluated fresh via the
`--evaluate` subprocess seam (env baked exactly like a real build) on both the train
and the held-out test md5 buckets, `--pool-matches 30` for a less noisy win-rate read
than the tuning run itself used:

| vector | split | pool win_rate | move-ranking agreement |
| --- | --- | --- | --- |
| default (ship) | train | 0.700 (21/30) | 0.2155 (25/116) |
| default (ship) | test | 0.633 (19/30) | 0.2333 (7/30) |
| tuned (this run) | train | 0.567 (17/30) | 0.2500 (29/116) |
| tuned (this run) | test | 0.633 (19/30) | 0.2333 (7/30) |

Two things stand out:

1. **Zero held-out transfer.** The tuned vector's held-out test agreement is
   `7/30`, byte-for-byte identical to the default's `7/30` (same count, not just a
   coincidentally close ratio). The tuned genome changed a real MAIN decision on
   4 of the 116 train-bucket decisions (25 -> 29) but changed **none** of the 30
   held-out test decisions. This is a cleaner and more legible negative than U35's
   (a small negative delta, -0.067): it is exactly flat, meaning whatever pattern
   the tuner fit on train carries literally zero signal onto unseen expert moves.
2. **The train-bucket pool win rate got WORSE, not better** (0.700 -> 0.567,
   -13.3pp), even though this run's own fitness function was blending pool win rate
   in at equal weight with agreement. `win_rate` has no genuine train/test split
   concept the way `agreement` does (the pool gauntlet is not filtered by replay
   membership), so the train-vs-test win_rate columns above are two independent
   noisy draws of the same stochastic 30-game gauntlet for each vector, not a
   held-out check; read them only as "does win rate look better for the tuned
   vector," and the honest answer at n=30 each (~9pp binomial SE per read) is no.

## Verdict

BLOCKED, same as U35. The pre-registered offline filter needs a **non-negative**
held-out agreement delta before a candidate may spend a ladder slot; a delta of
exactly zero is not evidence of a real generalizing improvement (KTD1/KTD4: block,
never promote on a non-positive read), and the pool-win-rate half of this run's own
fitness moved in the wrong direction on the very data it was fit on. No ladder A/B;
ship stays byte-identical.

## Plateau accounting

This is CEM candidate **2 of 2** in the plan's plateau contingency ("~Jul 15: CEM
plateau rule live (two consecutive non-WIN candidates)",
`docs/plans/2026-07-02-001-feat-unified-number-one-plan.md`). Both U35
(agreement-only) and this run (pooled) are non-WIN: U35 was a small negative
held-out delta, this run is a flat (zero) held-out delta with a worse train-side
win rate on the metric it optimized for. The count condition (two consecutive
non-WIN candidates) is met **today, ahead of the ~Jul 15 calendar checkpoint**.

Per the LOOP_BRIEF plan-freeze rule (no re-pointings outside a weekly review), this
finding is recorded here for that review to act on rather than unilaterally
declaring CEM dead or redirecting the dedicated CEM ladder budget this iteration.
The honest summary to carry into that review: at the current expert-move sample
size (116 train / 30 held-out test MAIN decisions) and reduced search scale, the
PRIO genome axis has now failed to generalize twice, under two different fitness
formulations, in two different held-out-failure shapes (small negative, then flat
zero). The remaining untried U35 re-test conditions are (a) a materially larger
expert-move sample (mid-July zip harvest) and (c) a genome region with a measured
non-flat held-out gradient; this run exhausts condition (b) (`--pool-matches > 0`)
without success.

## Re-test condition

Do not re-run this exact configuration; it will not produce new information at this
sample size. Re-open only with (a) a larger expert-move sample, or (c) a materially
different genome region / different weight-space subset with an observed non-flat
held-out gradient. A full-scale (population 50, iterations 20) run at the SAME
sample size is not expected to change the verdict (the held-out bucket, not search
thoroughness, is the bottleneck at n=30) and is not worth the multi-hour cost until
one of (a) or (c) is available.
