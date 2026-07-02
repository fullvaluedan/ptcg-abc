# Ladder data A/B: does adding ladder replay rows help the evaluator?

Plan U4 (v2 redo). Two models trained on the same gauntlet training rows,
one with ladder replay rows added, evaluated on the same held-out
gauntlet-only test set so the comparison isolates the effect of the extra
ladder rows rather than measuring a different test distribution.

## Setup

- Gauntlet-only training rows: 112033
- Ladder rows added for the merged variant: 15971
- Merged training rows: 128004
- Held-out gauntlet-only test rows: 26234 (same rows for both models)

## Results

| variant | train rows | test AUC | test accuracy |
|---|---|---|---|
| gauntlet-only | 112033 | 0.8104 | 0.7236 |
| gauntlet+ladder | 128004 | 0.8079 | 0.7174 |

## Gate

Keep the merged model only if its AUC on the gauntlet-only test set is at
least the gauntlet-only model's AUC. Otherwise keep the gauntlet-only model.

Verdict: **gauntlet-only** wins (gauntlet-only AUC 0.8104, merged AUC 0.8079).
The exported search/eval_model.json is the gauntlet-only model.

## U3c: top-player training weights

tools/train_eval.py gained --source-weights (plan U3c, addendum v2): a comma
separated source=weight list applied as sklearn sample weights during fit.
Chosen defaults: top_player=2.0, every other source (gauntlet, ladder, or a
csv with no source column) stays at 1.0. This is a hook only here, wired
through fit_standardized and compare_gauntlet_vs_merged with tests
(tests/test_train_eval.py); the actual combined gauntlet+ladder+top_player
retrain that exercises it for real is U6, not this unit. When --ladder-csv is
given, only the "gauntlet" and "ladder" keys affect the merged fit above; a
future combined CSV that carries a real source column (gauntlet/ladder/
top_player rows concatenated) can pass --source-weights directly to the
single-csv fit path instead.
