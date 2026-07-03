# U92 step 0: pairwise-RankNet kill test on the clone dataset

tools/rank_clone_killtest.py fits analysis.unit_zero_spike's
PairwiseLinearRanker (RankNet, plan U26) per archetype family on the
same clone_groups_*.npz dataset and train/test split tools/train_clone.py
already gated (analysis/clone_quality.md), changing ONLY the training
objective (pairwise ranking instead of per-row log-loss) to test whether
the objective, not the data, was the reason every prior attempt collapsed
to exactly the first-legal baseline.

## Verdict rule

PASS (worth building tools/train_clone2.py) if the ranker beats the
first-legal baseline by at least +0.03 on some family with at
least 20 scored held-out decisions. Otherwise FAIL: a
fourth converging negative result, closing the objective-change
hypothesis alongside the three tools/train_clone.py attempts.

| family | train groups | test groups | decisions scored | ranker accuracy | first-legal baseline | margin | verdict |
|---|---|---|---|---|---|---|---|
| meta_archaludon | 6234 | 1951 | 1951 | 0.4439 | 0.4454 | -0.0015 | FAIL |
| meta_grimmsnarl | 30567 | 11092 | 11092 | 0.3956 | 0.3957 | -0.0001 | FAIL |
| meta_grimmsnarl_tonakaiiii | 3284 | 1299 | 1299 | 0.3903 | 0.3903 | +0.0000 | FAIL |
| other | 4253 | 1353 | 1353 | 0.3282 | 0.3296 | -0.0015 | FAIL |

Overall: FAIL (no family cleared the margin).

## Diagnosis: the fourth converging negative result, objective-change hypothesis closed

`analysis/clone_quality.md` documents three straight attempts to clone a top
team's real MAIN decision, all of which collapsed to the exact same behavior:
the model's top-1 pick equals option 0 (the FIRST-LEGAL option) on 100% of
held-out decisions, tying the first-legal baseline to the digit. The three
attempts varied the model (standardized logistic regression, then a shallow
gradient-boosted tree) and the feature set (adding a within-category local-rank
feature, then excluding the global-position features entirely), but every one
of them shared the same TRAINING OBJECTIVE: a per-row, pointwise binary
log-loss over "is this the option that was played." The U90 comprehension-track
autopsy named that objective itself as a live suspect, because its zero-risk
optimum is provably "always predict whatever the baseline already predicts"
whenever the baseline clears non-trivial accuracy on its own -- exactly first-
legal's situation here (33-45% baseline accuracy per family).

This kill test changed only that one variable: same dataset
(`clone_groups_1783047584.npz`, feature_version 3), same per-family train/test
split (episode-level, already fixed at U70 dataset-build time), same feature
set (the full `agents.imitation_features.FEATURE_NAMES`, position features
included), but a pairwise-logistic RankNet objective (`analysis.
unit_zero_spike.PairwiseLinearRanker`, plan U26) instead of per-row log-loss.
A RankNet loss is fit over chosen-vs-every-sibling difference vectors within a
decision, so "always agree with the baseline" is not a free, zero-risk optimum
the same way it is for a per-row classifier -- if position still fully
dominates under this genuinely different objective, that is strong evidence
the collapse is a property of the DATA (engine list order already carries
almost all of the discriminating signal over top-player MAIN decisions), not
an artifact of the specific objective `tools/train_clone.py` happened to use.

Result: every family's margin is within +/-0.0015 of dead zero (n_scored
1299-11092 per family, not a small-sample artifact) -- the RankNet reproduces
the identical collapse the pointwise classifiers hit. `PairwiseLinearRanker`
needed one small, backward-compatible generalization to run this test at all:
`analysis/unit_zero_spike.py`'s `fit()` previously hard-coded the weight
vector's width to the module's own 20-feature `N_FEATURES` constant rather
than reading it from the data, which would have silently broken (or silently
truncated) on `imitation_features`'s 35-wide rows; it now infers width from
the training rows themselves, so the class is reusable over any caller's
feature vectors, not just its own original spike (covered by the existing
`tests/test_unit_zero_spike.py` suite, unchanged, since real usage there
always already passed 20-wide rows).

Conclusion: the objective-change hypothesis is CLOSED, negative, alongside
the three tools/train_clone.py attempts. This is the fourth (linear, tree,
richer/ablated features, now a different objective family entirely)
independent way of asking "is there a model that can beat first-legal on
this dataset" and the fourth time the answer is no. U92's later steps
(building `tools/train_clone2.py` with a groupwise objective, quarantined
position features, and U90 semantic features) are NOT worth building on top
of this evidence: the missing ingredient was never the model or the
objective, and the earlier ablation in `analysis/clone_quality.md` already
showed that removing the position escape hatch makes every model WORSE than
first-legal, not better. U92 is closed for good pending a genuinely new lever
(a different label scheme, e.g. per-turn or per-game rather than per-decision,
or a feature source outside imitation_features entirely) rather than another
model/objective swap over the same data. The comprehension track (L8) now
ships as U90 + U91 + U93 + U94, skipping U92.

Tests: `python -m pytest tests -q`, all passing; +10 new tests in
`tests/test_rank_clone_killtest.py` (harness correctness, a planted-preference
recovery proving the harness itself can detect real signal before trusting it
on real data, and an end-to-end `main()` report/verdict check for both the
PASS and FAIL paths) plus the `PairwiseLinearRanker.fit()` width generalization
in `analysis/unit_zero_spike.py`.
