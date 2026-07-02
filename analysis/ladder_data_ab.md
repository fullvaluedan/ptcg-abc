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
