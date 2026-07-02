# Early-turn archetype classifier training (plan U9b)

tools/train_archetype.py fits a standardized one-vs-rest logistic
regression over analysis/early_archetype_features's early-turn vector,
target is the collapsed archetype label from U9a's silver-label rows,
split by GAME (never by row) into train/held-out sets.

## Setup

Label counts (all rows, before any train/test split):

- other: 75
- Mega Abomasnow ex: 18
- Dragapult ex: 15
- Mega Lucario ex: 9
- Archaludon ex: 8
- Mega Starmie ex: 8
- Meowth ex: 7

n=140 total games (2026-07-03 ladder replay pool) is small enough that
one 28-game held-out split can flip PASS/FAIL on a 1-2 game swing, so
the gate is decided on the MEAN margin across several independent
splits (DEFAULT_SEEDS), not a single arbitrary seed. Per-seed detail:

| seed | train games | held-out games | accuracy | baseline | margin |
|---|---|---|---|---|---|
| 0 | 112 | 28 | 0.4286 (12/28) | 0.3571 ('other') | +0.0714 |
| 1 | 112 | 28 | 0.6429 (18/28) | 0.6071 ('other') | +0.0357 |
| 2 | 112 | 28 | 0.5357 (15/28) | 0.4286 ('other') | +0.1071 |
| 3 | 112 | 28 | 0.5357 (15/28) | 0.5357 ('other') | +0.0000 |
| 4 | 112 | 28 | 0.4643 (13/28) | 0.4643 ('other') | +0.0000 |

## Gate

Mean held-out top-1 accuracy across every seed's split must beat the
mean majority-class baseline (always predict the label most common in
that seed's TRAINING games) by at least 5%.

- mean held-out top-1 accuracy: 0.5214
- mean majority-class baseline: 0.4786
- mean margin: +0.0429 (need >= 0.0500)

Verdict: **FAIL**.

This is a valid negative result (same posture as U8b/U65): only 2/5 individual seeds clear the margin on their
own, so any one of them would have been a cherry-picked,
non-generalizing PASS. The model is NOT exported, and U9c does not
wire an unproven model into search.
