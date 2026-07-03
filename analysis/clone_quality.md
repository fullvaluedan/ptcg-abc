# Clone policy training (plan U71)

tools/train_clone.py fits one standardized logistic regression per
archetype family over agents/imitation_features's per-option feature
vector, target is the option the top team actually played, held out by
EPISODE (the split tools/clone_dataset.py already assigned).

## Gate

A family qualifies as a ring opponent only if its held-out top-1
accuracy beats the FIRST-LEGAL baseline (always picking option 0) by
at least 15%, with at least 20 scored held-out
decisions (below that the read is too noisy to trust either way).

| family | train rows | test rows | decisions scored | accuracy | first-legal baseline | margin | qualified |
|---|---|---|---|---|---|---|---|
| meta_archaludon | 49815 | 17285 | 2452 | 0.2883 | 0.4356 | -0.1472 | NO |
| meta_grimmsnarl | 331381 | 123386 | 11092 | 0.2248 | 0.3957 | -0.1709 | NO |
| meta_grimmsnarl_tonakaiiii | 28835 | 11108 | 1299 | 0.2433 | 0.3903 | -0.1470 | NO |
| other | 55957 | 17431 | 1353 | 0.2217 | 0.3296 | -0.1079 | NO |

Qualified families (0): (none).

Qualified families' weights are exported to agents/clone_weights/; every
other family is a valid negative result (same posture as U8b's
move-prior gate), not exported, and does not join the ring (U72).

## Diagnosis: every family loses to the first-legal baseline, not just falls short

Every family's fitted accuracy is BELOW its first-legal baseline (negative
margin), not merely under the qualification threshold. Checked directly
against the U70 dataset (data/training/clones/clone_groups_1783043310.npz,
61406 groups, avg 10.3 options/group, median 9): "always pick option 0"
scores 39.3% overall, far above the 14.5% a truly random pick would get
(mean 1/n_options). The option list the engine hands the agent is not
arbitrarily ordered; something about its construction correlates strongly
with what a top team actually plays, and agents/imitation_features.py's
per-option feature vector has NO feature that encodes an option's raw
position in that list. A content-only ranker therefore cannot access the
single strongest signal in this data, so it loses to a baseline that
exploits list order for free. This is a featurizer gap, not a training bug
(the same trainer recovers a planted preference cleanly on synthetic data,
see tests/test_train_clone.py) and not specific to U71 (search/move_prior.py,
U8b/U8c, reads the same featurizer and inherits the same blind spot). Fixing
it (an explicit option-position feature, a FEATURE_VERSION bump, and
re-validating every consumer of imitation_features against the new layout)
is out of scope for this unit; recorded here for whoever revisits either the
clone ring or the move-prior model next.
