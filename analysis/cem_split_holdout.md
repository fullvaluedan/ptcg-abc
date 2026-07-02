# CEM agreement channel tunes on the train bucket only; the test bucket stays held out

**Date:** 2026-07-02
**Unit:** P1 / U35 prep (the last correctness gate before the real CEM run)
**Follows:** `analysis/cem_gradient_restored.md` (the genome this run will search) and
`analysis/replay_trace.py` (`split_of`, the one md5 partition every held-out unit shares)

## The hole this closes

`tools/cem_tune.py` scores each genome candidate on two channels: how well it beats
the diverse opponent pool, and how well its `choose()` agrees with the top players'
recorded moves (`analysis/move_ranking_validator.score_replays`). The agreement
channel loaded **every** replay in the source, so a CEM run fit its weights on the
whole dataset, test bucket included. The pre-registered offline filter that gates a
ladder slot is supposed to be measured on the held-out `test` bucket; if the tuner
already saw those episodes, that validation is not held out and the filter reads
optimistically. This is exactly the KD4 held-out discipline the loop brief calls
non-negotiable.

## The fix

`_internal_evaluate` now filters the loaded `(replay, label)` pairs by
`replay_trace.split_of(label)` before scoring, controlled by a new `--split`
argument:

- `--split train` (the default): score only the `train` md5 bucket, leaving `test`
  clean for the pre-registered offline filter. A tuning run defaults to this so a
  contaminated fit can never happen by omission.
- `--split test`: score only the held-out bucket (for measuring the final filter,
  never for fitting).
- `--split all`: no filter, every loaded episode (the old behavior, kept for
  diagnostics like the flat-gradient sweep that are not tuning runs).

The membership rule is `replay_trace.split_of`, the same 25%-test md5 partition used
by `analysis/replay_trace`, `tools/per_archetype_baseline`, and the U26 spike, so the
bucket an episode lands in never drifts between the tuner and the unit that later
validates its output. `split_of` hashes the bare episode id (it strips the `.json`
suffix and any directory), so the label `load_replays` yields (`"12345.json"`) maps
to the same bucket whether read from a zip or a directory.

The pool-match channel is unaffected (it is self-play against the opponent pool, not
replay-derived), so this only tightens the validation channel.

## Behavior guarantee

The default flips the agreement channel from all-episodes to train-only, which is the
intended correctness change; no shipped agent is touched (the tuner is offline-only
and never bundled). `tests/test_cem_tune.py` pins both directions with a stubbed
replay channel:

- `test_internal_evaluate_filters_replays_to_the_requested_split`: with buckets
  `{1:train, 2:test, 3:train}`, `--split train` scores exactly `[1.json, 3.json]`;
  the test episode is dropped.
- `test_internal_evaluate_scores_all_replays_when_split_is_all`: `--split all` scores
  all three, confirming the escape hatch still applies no filter.

Full suite for the tuner: 20 passed.

## What this unblocks

The real `tools/cem_tune.py` PRIO-ordering run (U35) can now execute without
contaminating its own held-out validation. The run fits on `--split train`; the
resulting env-override vector is then measured by the pre-registered offline filter
on `--split test`, and only a filter pass earns a ladder A/B slot (the ladder stays
the sole arbiter, KTD1/KTD4).
