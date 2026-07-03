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
| meta_archaludon | linear | 44104 | 13886 | 1951 | 0.4464 | 0.4454 | +0.0010 | NO | +0.0000 (tree) |
| meta_grimmsnarl | linear | 331381 | 123386 | 11092 | 0.3957 | 0.3957 | +0.0000 | NO | +0.0000 (tree) |
| meta_grimmsnarl_tonakaiiii | linear | 28835 | 11108 | 1299 | 0.3903 | 0.3903 | +0.0000 | NO | +0.0000 (tree) |
| other | linear | 55957 | 17431 | 1353 | 0.3289 | 0.3296 | -0.0007 | NO | -0.0007 (tree) |

Table reflects the latest retrain (feature_version 3, dataset
clone_groups_1783047584.npz, opt_local_rank_norm / opt_is_local_first
added). See "Diagnosis (2026-07-03, local-rank featurizer fix)" below for
the read on why the seam found in the prior diagnosis still did not move
the gate.

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

## Diagnosis (2026-07-03, within-category sub-order): a real seam, not yet
## exposed to either model -- local rank inside the category block beats
## global position by a wide margin

Closed the open thread from the prior diagnosis: does the WITHIN-category
sub-order also collapse to "always first," or does it carry independent
signal our current features cannot see? Read the same committed dataset
(clone_groups_1783045002.npz) directly rather than re-deriving from
replays: each option row's category is recoverable from its own
is_play/is_attach/.../is_end one-hot (feature indices 0-6), and a group's
option order is already preserved row-by-row, so no engine or replay
access was needed for this check.

First confirmed the option list really is laid out as contiguous
category blocks (PLAY, then ATTACH, EVOLVE, ABILITY, ATTACK, RETREAT,
END, in that fixed order whenever a category is present at all --
verified by checking that the sequence of first-occurrences per group
never revisits a category already closed out; e.g. `('PLAY', 'ATTACK',
'RETREAT', 'END')` and `('PLAY', 'ABILITY', 'ATTACK', 'RETREAT', 'END')`
are the two most common full-group patterns on meta_grimmsnarl). Given
that, computed each decision's PLAYED option's rank WITHIN its own
category block (0 = first option of that category, 1 = second, ...) and
asked how often that local rank is 0.

Result, held-out test split, all four families:

| family | local-rank-0 (played option is first-of-its-category) | global first-legal baseline |
|---|---|---|
| other | 53.1% (718/1353) | 32.96% |
| meta_archaludon | 72.1% (1059/1469) | 45.34% |
| meta_grimmsnarl | 66.9% (8708/13019) | 43.07% |
| meta_grimmsnarl_tonakaiiii | 70.8% (920/1299) | 39.03% |

This is the seam candidate (b) asked for. "First option within whichever
category the player picked" is a dramatically stronger predictor (53-72%)
than "first option overall" (33-45%) on every family, roughly +20 to +27
points. That gap cannot be explained by category-grouping alone (which is
already baked into the global-first number via PLAY being both the most
common opt-0 category and the most common played category) -- it says
that ONCE you know (or predict) which category a top player is about to
act in, which specific option within that category they pick is itself
highly first-biased, and this is a completely different signal than the
global opt_index_norm / opt_is_first pair currently in FEATURE_NAMES.
Those two features only see an option's position across the WHOLE list,
so a PLAY option sitting at global index 3 (because it is the 4th card
in a 5-card PLAY block that starts at index 0) looks nowhere near "first"
to the model even though, within its own category, it is exactly the
kind of option a top player is very likely to pick.

This resolves the open question from the prior diagnosis: the within-
category sub-order is NOT another collapse to "first is right by
definition" (it is well below 100%, so it is not a labeling artifact the
same way category-grouping is), and it is NOT flat/uninformative either
(53-72% is far above chance for blocks that are often 2-8 options wide).
It is a real, exploitable, previously-invisible seam. Candidate (a) from
the prior diagnosis (treat first-legal as the ceiling and drop trained
imitation entirely) is not the right call yet -- there is more signal on
the table than either model family got to see.

Implication for the next U71 attempt: add an explicit within-category
position feature (e.g. `opt_local_rank_norm` and `opt_is_local_first`,
mirroring the existing `opt_index_norm` / `opt_is_first` pair but computed
over just the options sharing this option's category) to
agents/imitation_features.py, bump FEATURE_VERSION, regenerate the
dataset, and rerun the U71 gate. This is a real, separately-scoped
featurizer change (new feature computation, a FEATURE_VERSION bump, a
drift-test update, a dataset regen, a retrain) and should be sized and
started fresh next iteration rather than squeezed in here.

## Diagnosis (2026-07-03, local-rank featurizer fix): the new feature landed
## and got large weight, but the gate still ties -- the models never needed
## the seam because they already max out held-out accuracy without it

Implemented the fix the prior diagnosis specified: `opt_local_rank_norm`
and `opt_is_local_first` added to agents/imitation_features.py
(FEATURE_VERSION bumped 2 -> 3, N_FEATURES 33 -> 35), computed as this
option's rank among only the options sharing its own `type`, mirroring the
existing global opt_index_norm / opt_is_first pair. Regenerated the U70
dataset under feature_version 3 (data/training/clones/clone_groups_
1783047584.npz, 60033 groups; the team-episode sample shifts slightly
run-to-run since it re-pulls the live leaderboard, so this is not
directly comparable to the prior run's 65870, but the same four families
are present) and reran tools/train_clone.py (both the linear and tree
kinds, per family).

Result: still GATE FAIL, all four families, and the margins did not
materially move from the pre-fix (feature_version 2) read -- meta_
grimmsnarl and meta_grimmsnarl_tonakaiiii both stayed at exactly +0.0000,
other stayed at -0.0007, meta_archaludon moved from +0.0000 to +0.0010
(still noise at n=1951). The tree kind ties or loses identically to the
linear kind on every family, same as before the fix.

Diagnosed why directly (meta_grimmsnarl, 11092 held-out decisions,
refit standalone): the fitted logistic regression's top-1 pick still
equals GLOBAL option 0 in 11092/11092 held-out decisions (100%), the
identical total collapse the two prior diagnoses found before this
feature existed. The new features did get real weight -- the top 4
standardized coefficients by magnitude are now opt_is_local_first
(+0.69), opt_index_norm (-0.67), opt_local_rank_norm (+0.56), and
opt_is_first (+0.24), each larger than the top content weight
(attach_x_no_energy_yet, -0.19) -- but this is not useful signal, it is
redundancy: the first option in the whole list is, by construction,
always also the first option of its own category (a category block that
starts the list cannot have anything ahead of it within itself), so
opt_is_local_first is 1.0 on exactly the same rows opt_is_first is 1.0
on the top-predicted row of every decision. Giving the model a second,
third, and fourth way to say "this is position 0" did not give it a new
reason to ever pick something else; it gave the same conclusion more
routes to the same answer.

This is a materially different (and more concerning) finding than "the
seam wasn't visible yet": the seam FROM the read-only analysis (53-72%
local-rank-0 accuracy vs 33-45% global-first) is real on the DATA, but it
never gets exercised inside a decision the model is uncertain about,
because both model families (linear and shallow GBDT, log-loss trained
over every decision) find that defaulting to "always predict global
option 0" already achieves the SAME held-out top-1 accuracy as the
first-legal baseline by definition, with zero risk of ever being wrong
in a way the loss function penalizes more than the reward for occasionally
using content. Put plainly: the training objective has no incentive to
ever deviate from copying position, because deviating can only look worse
on this metric when it disagrees with the (frequently correct) baseline,
even though the local-rank seam shows there exist real decisions where
content plus local rank would predict better than global position alone.
Neither model family here can be pushed to actually use a feature just
because it is theoretically informative in the population -- both
converge on the same degenerate, zero-risk policy.

Two live candidates now, and neither is "try yet another feature or model
family blind," since three separate attempts (linear, tree, richer
features) have converged on the literal identical collapse: (a) retrain
with the global opt_index_norm / opt_is_first pair EXCLUDED entirely, to
directly measure whether a content-plus-local-rank-only model can beat
first-legal without a global-position escape hatch available at all (this
tests the local-rank seam honestly, instead of letting the model default
back to the cheaper global signal); (b) accept, after three converging
negative results, that first-legal is very likely the practical ceiling
for a per-decision imitation model on this feature/label setup, and move
U72 to a first-legal-plus-safety-fallback opponent (plays the family's
harvested deck, uses the existing heuristic's safety guards, no trained
per-option weights) instead of a trained clone. (a) is the cheaper, more
honest next step and should be tried before falling back to (b).

Tests: `python -m pytest tests -q`, 860 passed (up from 858), 0 failed;
+2 new tests in tests/test_imitation_features.py covering the local-rank
feature's within-category grouping and its single-option-group zero case.
