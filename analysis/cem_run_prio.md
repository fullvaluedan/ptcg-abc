# U35 real CEM run over the PRIO genome: train gain does not survive held-out test

**Date:** 2026-07-02
**Unit:** P1 / U35 (the engine's first real gear, on the restored gradient)
**Follows:** `analysis/cem_gradient_restored.md` (the genome grown so CEM has a gradient)
and `analysis/cem_split_holdout.md` (the `--split train` fix that keeps `test` clean)
**Run artifact:** `analysis/cem_runs/cem_run_prio_train_seed0.json`

## What ran

A real `tools/cem_tune.py` run over the 18-dim PRIO genome
(`tools/weight_space.py`), agreement channel only (`--pool-matches 0`, `--w-val 1.0`),
fit on the held-out-clean **train** md5 bucket (`--split train`) of
`data/episodes/pokemon-tcg-ai-battle-episodes-2026-06-30.zip`, seed 0. The
move-ranking agreement channel is the U5 validator (`analysis/move_ranking_validator`)
scoring the pilot's `choose()` against the top players' recorded MAIN decisions.

The first-hypothesis direction (PRIO_ATTACH earlier) landed inside a broader
re-ordering: the best genome raises PRIO_ATTACK 0.0 -> 3.13 and PRIO_ATTACH 3.0 ->
3.74 while lowering PRIO_EVOLVE 5.0 -> 3.41, PRIO_ABILITY 2.0 -> 1.33, and
PRIO_RETREAT 1.0 -> 0.07 (the leaf-eval shaping dims moved little).

## The result: overfit to train, blocked by the held-out filter

`best_fitness` is **flat at 0.2759 across all 12 iterations** (the iteration-0
population already held the best candidate; CEM never beat it, though the elite mean
climbed 0.2586 -> 0.2759 and the injected-variance floor kept `std_mean` ~0.23-0.26,
so exploration never froze). That flatness is the first warning: the agreement
channel has little gradient for CEM to climb even on the genome grown to restore one.

The pre-registered offline filter is measured on the **held-out test** bucket, never
the bucket the tuner saw. Evaluating the default (byte-identical ship) genome and the
best tuned genome on both buckets, ship-faithful (env baked, fresh `--evaluate`
subprocess, agreement only):

| genome | train agreement | test (held-out) agreement |
| --- | --- | --- |
| default (ship) | 0.2155 (25/116) | 0.2333 (7/30) |
| best tuned | 0.2759 (32/116) | 0.1667 (5/30) |

The tuned genome **gains +0.060 on train (25 -> 32 matched decisions) but loses
-0.067 on the held-out test bucket (7 -> 5 matched decisions)**. This is textbook
overfitting: the CEM fit the train bucket's expert moves and generalized worse than
the un-tuned default to unseen ones. (Reproduction check: the tuned train agreement
0.2759 matches the run json's `best.fitness` 0.27586 exactly, confirming the artifact
is a genuine agreement-only train fit at `--w-val 1.0`.)

## Verdict

The pre-registered offline filter requires a **non-negative** held-out move-ranking
agreement delta before a candidate may spend a ladder slot (loop brief rule 4; U35
"a tuned candidate passes filters and gets one pre-registered A/B"). The held-out
delta here is **negative (-0.067)**, so the tuned genome is **BLOCKED**: no ladder
A/B, and the ship stays **byte-identical** (the default vector, `vector_to_env` empty
map). The offline filter did exactly its job (block, never promote; KTD1/KTD4).

The held-out test bucket is small (30 MAIN decisions), so this is a weak-signal
refutation, not a strong one; but the direction is clear (a train gain that inverts
on held-out data) and the flat `best_fitness` corroborates a weak agreement gradient.

## Plateau accounting

Per the plan's CEM PLATEAU contingency (two consecutive candidates fail filters or
settle neutral, first read ~Jul 15): this is the **first** CEM candidate to fail the
offline filter (1 of 2). CEM is not yet plateaued. A second failing/neutral candidate
trips the rule and moves the dedicated CEM ladder budget to deck-space and hand-coded
levers (CEM then retained only to tune new levers).

## Re-test condition

The agreement channel overfits at this expert-move sample. Re-open the PRIO CEM run
only with (a) a materially larger expert-move sample (a mid-July zip harvest per the
census plan), or (b) the two-channel fitness turned on (`--pool-matches > 0`, so the
diverse-pool win rate regularizes the agreement fit), or (c) a genome change with a
measured non-flat agreement gradient on held-out data. Recorded as the
`cem_prio_agreement_generalizes` lever in `state/hypotheses.md`.
