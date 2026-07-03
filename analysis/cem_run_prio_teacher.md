# U83 re-test: teacher-corpus scale (10-92x larger sample) also fails to generalize

**Date:** 2026-07-03
**Unit:** L7 / U83, condition (a) from `analysis/cem_run_prio_pooled.md`
**Follows:** `analysis/cem_run_prio.md` (agreement-only, held-out delta -0.067, BLOCKED) and
`analysis/cem_run_prio_pooled.md` (pooled win-rate+agreement, held-out delta exactly 0, BLOCKED)
**Run artifact:** `analysis/cem_runs/u83_teacher_ring_seed0.json`,
`analysis/cem_runs/u83_teacher_ring_seed0.log`

## What ran

`tools/cem_tune.py --population 16 --elite 4 --iterations 6 --injected-variance 0.05
--ring-matches 6 --pool-matches 0 --teacher-labels data/training --limit 4000 --split train`
(seed 0), over the same 18-dim PRIO genome. Two things differ from the first two attempts,
both closing the re-test conditions the pooled-run writeup left open: the fitness blends
move-ranking agreement with **calibrated L5 ring win rate** (`--ring-matches 6`, tau 0.857,
`analysis/ring_calibration.md`) instead of the old uncalibrated U4 pool, and the label source
is the U83 teacher self-play harvest (`data/training/teacher_labels_corpus.jsonl` +
`teacher_labels_harvest_20260703.jsonl`) rather than the 116/30 real-replay sample. Best
training-side fitness: 0.8940 (best-so-far after CEM iteration 2 of 6, flat for the last 4
iterations, `analysis/cem_runs/u83_teacher_ring_seed0.log`).

## Held-out evaluation (ship-faithful, same protocol as the first two attempts)

`tools/cem_held_out_gate.py --result analysis/cem_runs/u83_teacher_ring_seed0.json
--teacher-labels data/training` scores the default (ship) vector and this run's best vector
separately on the clean `test` md5 bucket. Unlike the first two attempts, the teacher corpus
is large enough to report full-population sizes, not a 30-decision sample:

| vector | split | n scorable MAIN decisions | move-ranking agreement |
| --- | --- | --- | --- |
| default (ship) | train | 32003 | 0.8077 |
| tuned (this run) | train | 32003 | 0.8049 |
| default (ship) | test | 10689 | 0.8210 |
| tuned (this run) | test | 10689 | 0.8189 |

(counts via `analysis.teacher_labels.load_records` + `split_of` over `data/training`, the
same source the gate itself reads; roughly 92x the train and 356x the held-out-test decision
count of the first two attempts' 116/30 real-replay sample.)

Held-out delta (tuned - default): **-0.0022** (0.8189 - 0.8210). `cem_held_out_gate.py`
verdict: **BLOCKED**.

## What is new and notable versus the first two attempts

1. **The scale objection is answered, not sidestepped.** The pooled-run writeup's open
   re-test condition (a) was explicitly "a materially larger expert-move sample"; this run
   used a corpus roughly two orders of magnitude larger on both splits and still landed a
   negative held-out delta of essentially the same size as attempt 1's small-sample negative
   delta (-0.0022 here vs -0.067 there, both negative; the earlier magnitude was itself noisy
   at n=30). More data did not turn the sign positive.
2. **The tuned vector is also worse than default on its own held-out-clean TRAIN split**
   (0.8049 vs 0.8077, -0.0028), not just on held-out test. This is a stronger negative
   signal than either prior attempt produced: the earlier runs at least improved train
   agreement (the metric the CEM was directly selecting on) before failing to transfer.
   Here, full-population train agreement did not improve either.
3. **The mechanism is now diagnosable and matches attempt 2's failure shape.** The CEM
   sweep's own reported best fitness (0.8940) blended `--ring-matches 6` win rate with
   agreement over only the first `--limit 4000` train records, not the full 32003-decision
   train split evaluated above. Six ring matches is a high-variance win-rate read (roughly
   +-20pp binomial SE per candidate). The optimizer's selection pressure was therefore
   dominated by ring-win-rate noise rather than a genuine agreement signal, the same
   proxy-metric-moves-backwards failure attempt 2 found with the U4 pool's win rate: a
   larger, better-calibrated opponent pool did not fix the underlying problem that a few
   games per candidate is not enough signal to select a genome on, and agreement itself
   carries no exploitable gradient at this genome's dimensionality either (full-population
   train agreement also went the wrong way).

## Verdict

BLOCKED, same as the first two attempts. Held-out delta is negative (KTD1/KTD4: block on
any non-positive read). No ladder A/B; ship stays byte-identical.

## Plateau accounting

This is CEM candidate **3 of 3** non-WIN reads under three materially different
configurations: agreement-only at small scale (attempt 1), pooled win-rate+agreement at
small scale (attempt 2), ring win-rate+agreement at 10-92x scale (attempt 3, this run). The
one concretely re-open condition attempt 2 left standing, "(a) a materially larger
expert-move sample," is now closed: it was tried, at large scale, and the delta stayed
negative. The only remaining stated re-open condition from the pooled-run writeup is
"(c) a genome region with a measured non-flat held-out gradient", still untried. Per the
LOOP_BRIEF plan-freeze rule this is recorded here and in `state/hypotheses.md` /
`state/current.md` for the next weekly plan review, not acted on unilaterally; no further
CEM sweep over this same 18-dim PRIO genome is planned without either condition (c) or a new
weight-space region to try it against.

## Re-test condition

Do not re-run this configuration, or a larger population/iteration count at the same genome
and label source; the bottleneck the last three attempts have converged on is not search
thoroughness or sample size, both of which were increased across attempts 2 and 3 without
changing the sign of the held-out delta. Re-open only with (c) a genome region (a different
weight subset, or the U91/U92 playbook-mined levers once available) with an observed
non-flat held-out gradient measured BEFORE a full sweep is spent on it.
