# Move-ordering model training (plan U8b)

tools/train_move_prior.py fits a standardized logistic regression over
agents/imitation_features's per-option feature vector, target is_chosen,
pooled across every candidate option row from the training CSVs, split
by GAME (never by row) into train/held-out sets.

## Setup

- Train games: 1632  train rows: 259345
- Held-out games: 408  held-out rows: 62491
- Held-out decisions scored (exactly one is_chosen row): 6620

## Gate

Held-out top-1 accuracy (does the model's highest-scoring option within
a decision match the one actually chosen) must beat the random baseline
(mean 1/n_options over the same decisions) by at least 5%.

- top-1 accuracy: 0.7521
- random baseline: 0.1807
- margin: +0.5714 (need >= 0.0500)

Verdict: **PASS**.

The model is exported to search/move_prior.json for U8c to wire
behind a flag.
