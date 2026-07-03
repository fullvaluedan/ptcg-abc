# Clone policy training (plan U71)

tools/train_clone.py fits two model kinds per archetype family over
agents/imitation_features's per-option feature vector, target is the
option the top team actually played, held out by EPISODE (the split
tools/clone_dataset.py already assigned): a standardized logistic
regression ("linear") and a shallow gradient-boosted tree ranker
("tree", TREE_MAX_DEPTH-deep, TREE_N_ESTIMATORS rounds). Whichever has
the larger held-out margin over the first-legal baseline is reported
and, if it clears the gate, exported; the losing kind's read is also
shown so a family where both kinds tie the baseline is visible as such,
not silently hidden behind the winning kind's number.

## Gate

A family qualifies as a ring opponent only if its held-out top-1
accuracy beats the FIRST-LEGAL baseline (always picking option 0) by
at least 15%, with at least 20 scored held-out
decisions (below that the read is too noisy to trust either way).

| family | model | train rows | test rows | decisions scored | accuracy | first-legal baseline | margin | qualified | other kind's margin |
|---|---|---|---|---|---|---|---|---|---|
| meta_archaludon | linear | 30404 | 10637 | 1469 | 0.4534 | 0.4534 | +0.0000 | NO | +0.0000 (tree) |
| meta_grimmsnarl | linear | 386248 | 138495 | 13019 | 0.4307 | 0.4307 | +0.0000 | NO | +0.0000 (tree) |
| meta_grimmsnarl_tonakaiiii | linear | 28835 | 11108 | 1299 | 0.3918 | 0.3903 | +0.0015 | NO | +0.0000 (tree) |
| other | linear | 55957 | 17431 | 1353 | 0.3296 | 0.3296 | +0.0000 | NO | -0.0007 (tree) |

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

## Diagnosis (2026-07-03, model-family retry): a shallow gradient-boosted tree
## ties the SAME baseline the linear model tied -- the bottleneck is not model
## capacity

Implemented the nonlinear candidate the prior diagnosis proposed:
tools/train_clone.py now fits a shallow GradientBoostingClassifier
(TREE_MAX_DEPTH=2, TREE_N_ESTIMATORS=50, TREE_LEARNING_RATE=0.1) per family
alongside the linear model and keeps whichever has the larger held-out
margin over first-legal (agents/clone_policy.py gained a matching pure-python
tree-walk scorer, "model_type": "gbdt", verified to reproduce
model.decision_function(X) exactly via tests/test_train_clone.py's round-trip
test). A tree can express conditional logic a linear model structurally
cannot ("usually trust position, but override it when content signal X is
unusually strong in this specific situation") -- exactly the capability gap
the prior diagnosis flagged as the leading hypothesis for why the linear
model collapsed to the baseline.

Result on the same regenerated dataset: the tree ties or loses too, for
every family (meta_archaludon +0.0000, meta_grimmsnarl +0.0000,
meta_grimmsnarl_tonakaiiii +0.0000, other -0.0007 -- see the table above,
"other kind's margin" column). Checked decision-by-decision on
meta_grimmsnarl again (13019 held-out decisions, same family the linear
diagnosis used): the tree's top-1 pick equals "option 0" in 13019/13019
cases too (100%), identical to the linear model's collapse. Its
feature_importances_ confirm why: opt_index_norm alone accounts for 89.5% of
total importance; every other feature (is_ability, attack_x_turn,
attach_x_no_energy_yet, is_attack, ...) sits below 2% each. Even though the
tree is structurally capable of branching on content before falling back to
position, boosting never found a split worth keeping, because on this
dataset position is apparently such an overwhelming predictor that no
residual pattern in the remaining ~10.5% of importance was strong or
consistent enough across held-out decisions to ever flip a single top-1
pick.

Implication: this rules out "linear models can't express conditional logic"
as the root cause -- a genuinely nonlinear, branching-capable model hit the
exact same wall. The leading hypothesis now shifts from "wrong model family"
to "the option list's OWN ORDER is already such a strong proxy for what top
players do that our current feature set has ~0 marginal information beyond
it, for either model family." Two live candidates for whoever resumes this
unit: (a) inspect how the game engine / tools/clone_dataset.py's option
enumeration actually orders legal options for a MAIN decision -- if the
engine itself sorts options by some heuristic-adjacent criterion (as
opposed to, say, insertion order or card-id order), that would fully explain
why "first" is so predictive and turn this from a modeling problem into a
labeling artifact; (b) if the ordering is confirmed to carry no artificial
information, treat first-legal as a genuinely strong opponent baseline in
its own right and consider whether the ring even needs a trained clone
model per family, versus a first-legal-plus-safety-fallback opponent that
plays the family's harvested deck without imitation weights at all.

A cheap first look at candidate (a), on the same 13019 meta_grimmsnarl
held-out decisions: option 0's action-category distribution is PLAY 8728,
ATTACH 2283, EVOLVE 988, ABILITY 537, ATTACK 401, RETREAT 82, and END_TURN
0 (never once first). The played category distribution across the same
decisions is PLAY 6268, ATTACH 2483, ABILITY 1210, EVOLVE 1087, ATTACK 1006,
END_TURN 556, RETREAT 409. Two things follow: the option list is not
insertion-order-arbitrary, it looks CATEGORY-grouped with a fixed category
order (PLAY-type actions always enumerated before ATTACH/EVOLVE/ABILITY/
ATTACK/RETREAT, and END_TURN always last, never first) -- which alone
explains why an END_TURN decision (556 of 13019 real choices) can never
register as "played index 0" no matter how good a model is, since the
option representing it is never at index 0. And PLAY is both the most
common option-0 category (67%) and the most common played category (48%),
so category-grouping plus "PLAY is usually right" together account for a
large share of the baseline's 43% without yet explaining the full 100%
top-1 agreement -- the WITHIN-category sub-ordering (e.g. which specific
card a PLAY-type option's slot 0 refers to) still needs its own look before
(a) can be called closed.
