# Noise model refit: M=150 (v2) was itself undersized

Source: `tools/refit_noise_model.py`, run 2026-07-04 against `state/current.md`'s
full per-build ledger.

## Why this needed doing

The v2 noise model (M=150) was set by eyeballing a single min/max range on a
handful of same-build reads ("396.7 to 691.5"). Since then, TRACK L has spent
many board-check iterations resubmitting the same two byte-identical builds
(the trolley king and the ability floor build) purely to hold scored slots.
Those repeat reads are exactly the data a same-build noise model needs, and by
2026-07-04 the ledger held 30 reads of `heuristic+trolley` and 27 of
`heuristic+trolley-ability`, far more than the v2 basis. The endgame-campaign
plan already names "refit the noise model on all accumulated same-build reads"
as required prep work; this refit does that now, ahead of the 2026-08-10
deadline, while the data keeps accumulating.

## Method

1. Group ledger rows into families by the build name up to its first
   parenthetical (`family_key`), since resubmission notes like "(king-copy
   revert, 2026-07-04)" and "(reclaim)" describe the same tarball, not a
   different build.
2. For each family with >= 3 numeric reads, compute its own mean and stdev.
3. Pool the residuals (`reading - family_mean`) across qualifying families, so
   a genuine mean difference between two different builds (the ability build
   reads ~112pt higher on average than the plain king) is never counted as
   noise.
4. Recommend M as the larger of a 2-sigma bound on the pooled residuals and the
   single worst observed residual, rounded up to the nearest 10. Taking the max
   (not just 2-sigma) matters here: the tail is heavy enough that a pure
   Gaussian bound would not have covered the worst point actually observed.

## Result

| family | n | mean | stdev | range |
| --- | --- | --- | --- | --- |
| heuristic+trolley | 30 | 456.4 | 59.2 | [423.5, 691.5] |
| heuristic+trolley-ability | 27 | 568.5 | 43.9 | [470.1, 603.3] |

Pooled residuals: n=57, stdev=52.0, worst observed residual=235.1 (the
691.5 read on `heuristic+trolley`, 235.1 above that family's own mean).

2-sigma bound = 104.0. Worst observed residual = 235.1. Recommended
M = ceil(235.1 / 10) * 10 = **240**.

## What this means

- M=150 (v2) would NOT have covered the worst point actually observed in the
  ledger (235.1 > 150): a real WIN/LOSS/BAND verdict computed at M=150 against
  a read that far off-mean could have been a false signal, not a real lever
  effect. The refit corrects this before it causes a bad call, not after.
- The two families' means differ by ~112 points (568.5 vs 456.4). That gap is
  real (the ability build is the ring-preferred floor for a reason) and must
  not be folded into the noise estimate, which is why residuals are computed
  per-family before pooling rather than against one shared pooled mean.
- Per L9, the calibrated bracket ring, not a single ladder read, is still the
  actual lever decision gate. This refit only matters for a future
  pre-registration that still wants a ladder-side WIN/LOSS/BAND margin (or for
  the 2026-08-10/16 endgame campaign's optimal-stopping model), not for
  today's board-check cadence.

`tools/loop_state.py`'s `DEFAULT_MARGIN` and `state/current.md`'s
`noise_model` block (now v3) were both updated to M=240 with this analysis as
basis. Re-fit again by 2026-07-18, or sooner if the endgame campaign's own
pre-work calls for it.
