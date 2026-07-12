# Powered four-arm flag-config experiment

The n=100 same-run read (analysis/top50_flag_config.md) found plain (config 1, both
flags off) reading best on both the elite and calibrated rings for
decks/candidate_yushin_ito.csv, and that read was the stated basis for the 2026-07-12
reseat of ref 54592012 as plain (state/current.md, in_flight.note). Per
analysis/ml_expert_review.md's own power prescription (required n at 80% power,
one-sided alpha 0.05, for a 5pp gate: about 710/arm), this doc reruns the same four-arm
comparison at power using the committed parallel harness (tools/parallel_ring.py,
FOUR_CONFIG_ARMS), the same harness and shard-timeout methodology the PTCG_RANKER gate
used (analysis/ranker_gate.md).

Four arms, all piloting decks/candidate_yushin_ito.csv: plain (both flags off),
+PTCG_ABILITY, +PTCG_THREAT_RETREAT, +PTCG_ABILITY+PTCG_THREAT_RETREAT ("both", the live
submission's stack). Same-run within each ring: one script execution, round-robin across
the full ring, alternating seats, identical opponent order for every arm.

## Method and honest achieved n

Both rings ran via `tools/parallel_ring.py`, jobs=16 (default_jobs on this 20-core box),
`--shard-timeout 240` (the exact value analysis/ranker_gate.md's elite-ring gate used,
"about 4x a normal shard's 50-90s" for its 2-arm run; this run stacks 4 arms per shard, so
per-shard work is roughly double that precedent run's, and the timeout margin is tighter
in consequence).

- **Elite ring** (35 clone:top50_* opponents), requested n=700/arm, seed=0: 8 of 16 shards
  (2, 3, 5, 6, 7, 12, 13, 14) hit the 240s timeout and were killed, the same
  pathological-single-game-trajectory failure mode documented in analysis/ranker_gate.md
  (not a deadlock; each killed shard's process tree was pinned near 100% CPU). Landing
  **n=351/arm actual (50.1% of the 700 requested)**, wall clock 240.5s
  (analysis/flag_config_powered_elite.json).
- **Calibrated ring** (9 clone:<family> opponents), requested and achieved **n=200/arm**,
  zero shard timeouts, wall clock 45.4s (analysis/flag_config_powered_calibrated.json).

The elite-ring shortfall is reported honestly rather than patched by rerunning with a
longer timeout or topping up games: the failure mode is a specific pathological game
trajectory that (per ranker_gate.md's own characterization) burns 800+ CPU-seconds per
occurrence, not a slow-but-finishing shard, so a materially longer timeout would mostly
just extend wall clock without reliably recovering those shards. At n=351/arm the
per-arm-vs-plain delta SE is about 3.3pp (95% CI half-width about 6.5pp), so this read
can resolve differences of roughly 7pp or more; it is not the full n=700 power target, and
that limitation is carried into the verdict below rather than glossed over.

## Elite ring results (n=351/arm achieved)

| arm | W-D-L | win rate | SE | same-run delta vs plain | 95% CI |
|---|---|---|---|---|---|
| plain (baseline) | 255-1-95 | 0.7265 | 0.0238 | +0.0pp | -6.60 to +6.60 |
| ability | 264-0-87 | 0.7521 | 0.0230 | +2.56pp | -3.93 to +9.06 |
| threat_retreat | 268-0-83 | 0.7635 | 0.0227 | +3.70pp | -2.74 to +10.15 |
| both | 258-0-93 | 0.7350 | 0.0236 | +0.85pp | -5.71 to +7.42 |

No arm's 95% CI vs plain excludes zero. threat_retreat reads highest, plain reads lowest,
of the four arms at this n.

## Calibrated ring results (n=200/arm achieved, full)

| arm | W-D-L | win rate | SE | same-run delta vs plain | 95% CI |
|---|---|---|---|---|---|
| plain (baseline) | 174-0-26 | 0.8700 | 0.0238 | +0.0pp | -6.59 to +6.59 |
| ability | 172-0-28 | 0.8600 | 0.0245 | -1.00pp | -7.70 to +5.70 |
| threat_retreat | 181-0-19 | 0.9050 | 0.0207 | +3.50pp | -2.68 to +9.68 |
| both | 179-0-21 | 0.8950 | 0.0217 | +2.50pp | -3.81 to +8.81 |

No arm's 95% CI vs plain excludes zero here either. threat_retreat reads highest again;
plain drops to third of four (ability is lowest).

## Comparison against the n=100 / n=50 reads

Elite ring, n=100 (analysis/top50_flag_config.md) vs n=351 (powered, this doc):

| config | n=100 win rate | n=351 win rate | change |
|---|---|---|---|
| plain | 0.850 | 0.7265 | -12.35pp |
| ability | 0.690 | 0.7521 | +6.21pp |
| threat_retreat | 0.720 | 0.7635 | +4.35pp |
| both | 0.740 | 0.7350 | -0.50pp |

Ranking at n=100: plain > both > threat_retreat > ability. Ranking at n=351: threat_retreat
> ability > both > plain. **The ranking inverted top to bottom**: the config that read best
at n=100 (plain, 0.850) reads worst at n=351 (0.7265); the config that read worst at n=100
(ability, 0.690) reads second-best at n=351 (0.7521).

Calibrated ring, n=50 (analysis/top50_flag_config.md) vs n=200 (powered, this doc), given
as additional context since the calibrated ring was a secondary regression guard in the
original experiment too:

| config | n=50 win rate | n=200 win rate | change |
|---|---|---|---|
| plain | 0.940 | 0.870 | -7.00pp |
| ability | 0.780 | 0.860 | +8.00pp |
| threat_retreat | 0.900 | 0.905 | +0.50pp |
| both | 0.860 | 0.895 | +3.50pp |

Ranking at n=50: plain > threat_retreat > both > ability. Ranking at n=200: threat_retreat
> both > plain > ability. plain drops from first to third; threat_retreat moves into first.

## Verdict: the n=100/n=50 conclusion did not hold, and reversed in point estimate

Plain does not read best at power on either ring. On the elite ring the point-estimate
ranking flipped end to end (plain: 1st of 4 at n=100, 4th of 4 at n=351). On the calibrated
ring plain fell from 1st to 3rd of 4. threat_retreat reads best on *both* powered rings,
which it did not at n=100/n=50 on either ring.

That said, this is a reversal in point estimate, not a statistically resolved one: every
same-run delta vs plain on both rings has a 95% CI spanning zero (largest observed delta
is +3.70pp elite / +3.50pp calibrated, against a delta SE of about 3.3pp on both rings).
The honest statistical read is that **all four arms are statistically indistinguishable at
the achieved n** (n=351/arm elite is itself under the ~700/arm power target, on top of
that). The most defensible conclusion is not "threat_retreat is actually best," it's
"the n=100/n=50 read's apparent plain advantage does not survive a properly powered
re-read, and was very likely small-sample noise" -- consistent with this repo's own
standing caution elsewhere that single small-n reads "swing inside ~450-730 and decide
nothing" (state/current.md, U108).

## What this means for the Aug lock pair

The live pair is ref 54592012 (plain) and ref 54555716 (the "both" / ability+threat_retreat
flags stack), reseated 2026-07-12 on the n=100/n=50 finding that plain was the clear
elite-ring winner. That stated basis is not supported by this powered read:

- plain vs both (the two configs actually in the live pair): elite delta +0.85pp (95% CI
  -5.71 to +7.42), calibrated delta +2.50pp (95% CI -3.81 to +8.81). Neither ring shows a
  significant difference between the pair's two live configs, and both point estimates
  now favor "both" over plain, the opposite of the direction the reseat assumed.
- Neither live-pair config (plain, both) is the single best point-estimate performer on
  either powered ring: threat_retreat alone is, on both rings, and it is not represented
  in the live pair at all.

Per this project's own standing rule (ring evidence, not a single ladder/small-n read, is
the decision authority -- U108, state/current.md), the powered read argues against treating
plain as a proven upgrade over the flags stack: nothing here clears significance in either
direction, so there is no statistical case to reseat again on this evidence alone. The one
actionable signal worth flagging before the Aug 16 lock is that threat_retreat-only
(config 3, neither live-pair member) reads numerically ahead of both current pair members
on both rings; if a tie-break is wanted before lock, a targeted top-up read on config 3
specifically (recovering elite-ring power past the 351/700 achieved here) would be the
next step, not a unilateral reseat. This is a recommendation only, per this project's
existing convention (analysis/top50_flag_config.md) -- the submission stays Dan's call.

## Files

- `analysis/flag_config_powered_elite.json` (raw `run_parallel_ring` output, elite ring,
  n=351/arm achieved, generated, not hand-edited).
- `analysis/flag_config_powered_calibrated.json` (raw `run_parallel_ring` output,
  calibrated ring, n=200/arm achieved, generated, not hand-edited).
