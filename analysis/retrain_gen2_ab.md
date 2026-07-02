# Ladder data A/B: does adding ladder replay rows help the evaluator?

Plan U4 (v2 redo). Two models trained on the same gauntlet training rows,
one with ladder replay rows added, evaluated on the same held-out
gauntlet-only test set so the comparison isolates the effect of the extra
ladder rows rather than measuring a different test distribution.

## Setup

- Gauntlet-only training rows: 112033
- Ladder rows added for the merged variant: 15971
- gauntlet_gen2_batch1 rows added for the merged variant: 1190
- gauntlet_gen2_batch2 rows added for the merged variant: 3624
- gauntlet_gen2_batch3 rows added for the merged variant: 8334
- top_player rows added for the merged variant: 173663
- Merged training rows: 314815
- Held-out gauntlet-only test rows: 26234 (same rows for both models)

## Results

| variant | train rows | test AUC | test accuracy |
|---|---|---|---|
| gauntlet-only | 112033 | 0.8104 | 0.7236 |
| gauntlet+ladder+gauntlet_gen2_batch1+gauntlet_gen2_batch2+gauntlet_gen2_batch3+top_player | 314815 | 0.7795 | 0.6902 |

## Gate

Keep the merged model only if its AUC on the gauntlet-only test set is at
least the gauntlet-only model's AUC. Otherwise keep the gauntlet-only model.

Verdict: **gauntlet-only** wins (gauntlet-only AUC 0.8104, merged AUC 0.7795).
The exported search/eval_model.json is the gauntlet-only model.

## Training weights (--source-weights)

Sample weights applied to the merged fit only (plan U3c):

- top_player: 2.0
- any other source (including gauntlet rows if unlisted): 1.0
