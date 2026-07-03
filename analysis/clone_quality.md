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
| meta_archaludon | 30404 | 10637 | 1469 | 0.4534 | 0.4534 | +0.0000 | NO |
| meta_grimmsnarl | 386248 | 138495 | 13019 | 0.4307 | 0.4307 | +0.0000 | NO |
| meta_grimmsnarl_tonakaiiii | 28835 | 11108 | 1299 | 0.3918 | 0.3903 | +0.0015 | NO |
| other | 55957 | 17431 | 1353 | 0.3296 | 0.3296 | +0.0000 | NO |

Qualified families (0): (none).

Qualified families' weights are exported to agents/clone_weights/; every
other family is a valid negative result (same posture as U8b's
move-prior gate), not exported, and does not join the ring (U72).

## Diagnosis (rerun after the featurizer fix): the fix closed the negative-margin
## gap, but the linear model still ties, never beats, first-legal

Retrained on a freshly regenerated dataset (data/training/clones/clone_groups_
1783045002.npz, feature_version 2, opt_is_first / opt_index_norm present).
Three of four families now score margin +0.0000, exactly equal to the
first-legal baseline rather than below it; the fourth (grimmsnarl_tonakaiiii)
reads +0.0015, noise at n=1299. This is real progress over the prior run
(every family lost outright), but the 15pp gate needs a positive margin, and
ties are not progress toward it.

Checked directly why the tie is exact, not approximate (meta_grimmsnarl,
13019 held-out decisions): the fitted logistic regression's predicted top-1
option equals "option 0" in 13019/13019 held-out decisions (100%), even
though the fitted coefficients are NOT degenerate -- opt_is_first (+0.51) and
opt_index_norm (-0.44) are the two largest standardized weights, but real
content weights survive fitting too (attach_x_no_energy_yet -0.25, is_attack
+0.23, attach_to_active +0.19, is_ability +0.15). The position weights are
just large enough, relative to the typical magnitude of every other feature
combined, that no held-out decision's content ever overcomes the score gap
in favor of a later option. A purely additive (linear) model cannot express
"usually trust the engine's ordering, but override it when content signal X
is unusually strong" without an explicit interaction term; it can only trade
off position against content at one fixed global rate, and the fitted rate
makes position always win.

Implication: the featurizer fix was necessary and worked (proven by the
negative-to-zero margin swing), but a per-family standardized logistic
regression is very likely the wrong model family for this data now that
position is in play -- it structurally cannot let content ever override
order. A nonlinear model (shallow gradient-boosted trees, still dev-only and
sklearn-fine per the plan's constraints) or an explicit
position-as-tiebreaker-only scoring scheme are the two live candidates for
the next U71 attempt; recorded here, not yet implemented, for whoever
resumes this unit next.
