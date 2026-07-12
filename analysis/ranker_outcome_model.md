# Outcome-labeled per-option policy ranker: the chosen-option outcome model

Task B part 1 of the ML-review prescription (analysis/ml_expert_review.md, "OPEN,
the one untested deployable ML cell"): train and ship, flag-gated and off by
default, an outcome-labeled per-option policy ranker (PTCG_RANKER). This doc
documents the exact data formulation, the training result, the export, the
match-time integration, and the fires-vs-inert check. No em dashes anywhere in
this repo.

## The design decision: the chosen-option outcome model

Every prior policy dataset in this repo is an IMITATION target.
tools/replays_to_rows.py's move_rows_from_replay labels every legal MAIN option
(chosen and not) with is_chosen, restricted to the eventual WINNER's seat only,
so the label answers "what would the winner do here" regardless of whether that
seat's play was actually strong at this particular decision. Every value model
in the repo (search/learned_eval.py's eval_model.json) scores a BOARD STATE, not
an option, and match-time value-plus-lookahead is structurally closed (the
grader withholds the forward model; analysis/ml_expert_review.md source list).

The prescribed cell instead asks a different question: P(win | this option's
features, actually taken), estimated directly from realized game outcomes
rather than from imitating the winner. The row builder for this
(tools/replays_to_rows.py's new `outcome_rows_from_replay`) makes one explicit
design choice, named here as it is named in code: the **chosen-option outcome
model**.

- Walk BOTH seats of every replay (not winner-only), so both win-labeled (1)
  and loss-labeled (0) rows exist. A seat's own final result (from `rewards`)
  labels every row that seat produces.
- For every qualifying MAIN decision (a `agents/imitation_features.
  decision_features(obs)` ranking group of >=2 legal options), keep **exactly
  one row: the option that was actually chosen**, with is_chosen 1 written for
  QA/schema-comparison but constant (and therefore dropped from the feature
  matrix at training time: it carries no variance and no signal in this
  dataset by construction).
- A **non-chosen** option is never labeled with the outcome. There is no
  counterfactual evidence that a different pick would have changed the result;
  folding an untaken option into the outcome-labeled set would attribute a
  game-level result to an action that never happened, injecting pure label
  noise into every multi-option decision (a decision with 9 options would
  contribute 8 mislabeled rows and 1 correctly-labeled row under the naive
  "label everything" alternative). Restricting to the chosen option keeps every
  training row causally connected to the label it carries: this seat, at this
  decision, picked this option's features, and this seat's game ended in this
  result.

The resulting model is a Monte-Carlo credit-assignment estimate over played
actions (chosen-option features -> eventual outcome), not a counterfactual
value function. It cannot tell you what would have happened had a different
option been played; it can only say "options with these features tend to
appear more often on the winning side of realized games than the losing side."
That is the honest scope of what real replay data (chosen actions plus a
terminal result, no simulator) can support without search, and it is exactly
the arithmetic-cheap check the review calls for: "closes the ML question
honestly either way."

At match time (search/learned_ranker.py, agents/heuristics.py's PTCG_RANKER
resolver) the same trained scorer is applied to EVERY currently-legal option
(whether or not it was ever "chosen" in training), and the argmax is taken.
This is the standard way a Monte-Carlo-evaluated action model is used for
control: the training distribution is over played actions across many games
and both outcomes; scoring an unplayed-but-legal option asks the model to
generalize from the feature vector alone, the same generalization every
supervised policy/value model in this repo already relies on.

A `state_eval_p` column also rides along on every row: the existing
search/learned_eval.py board-state win-probability estimate for the decision's
state (identical across every option within one decision, since it is a
function of state, not option identity). It cannot rank options against each
other, but it is reported as the "if comparable" baseline the plan asked for
(see Results).

## Data

Source: real top-team Kaggle episodes, extracted directly from
data/episodes/*.zip (tools/build_outcome_dataset.py), not the pre-existing
data/replays/*.json corpus (which is our own submission's self-play ladder
games, a different corpus tools/replays_to_rows.py's move_rows_from_replay
already serves). The elite-weighted core is data/derived/top50_harvest.json's
713 unique episode ids (the top-50 leaderboard teams' harvested recent games,
tools/top50_harvest.py). Every dump member is named `<episode_id>.json`
(verified directly against a sample), so extraction is a single namelist()
pass per dump (10 dumps, ~52,000 episodes total, cheap: reads only the central
directory) followed by targeted zf.read + json.loads for the 713 wanted
members only.

Result: **713/713 episodes found, 0 missing**. 3 episodes contributed 0 rows
(a draw, or no qualifying >=2-option MAIN decision), leaving **710 games**
and **44,024 rows** (`data/training/outcome_rows_top50_1783845441.csv`). Class
balance: 50.47% win / 49.53% loss, near-exactly balanced by construction (every
game contributes one win-labeled seat and one loss-labeled seat).
`tools/build_outcome_dataset.py --widen` is implemented (uncapped per-team
episode pull via `tools.top50_harvest.scan_all_dumps`, same 50 team names, no
games-per-team=20 cap) but was not exercised for this run: 44k rows across 710
games already gives a comfortable train/test split for a 44-feature linear/
small-MLP fit, and widening is explicitly optional ("if time allows") in the
task brief.

Split: **game-level**, 80/20, `tools.train_eval.game_split` (reused as-is,
never row-level: the repo convention everywhere else in this file's siblings).

## Training and results

`tools/train_ranker.py`, sklearn 1.9.0 (already present in .venv; no install
needed), on `agents/imitation_features.FEATURE_NAMES` (44 features: the U26
spike core, U71's position/local-rank features, and the TAG_VOCAB multi-hot).

| model | held-out AUC | n |
|---|---|---|
| LogisticRegression (standardized) | **0.5424** | test rows 9,080 (train 34,944), games 710 |
| MLPClassifier(hidden_layer_sizes=(64,), relu, early_stopping) | 0.5380 | same split |
| baseline: first-legal only (`opt_is_first`, single-feature LR) | 0.5173 | same split |
| baseline: eval_model.json state prize-diff heuristic (`state_eval_p`, unfit) | 0.5887 | same split |

Both trained models beat the first-legal-only baseline (0.5424 and 0.5380
vs 0.5173): the per-option feature content adds real, if modest, signal over
option position alone, closing the "does it beat first-legal" question the
U71 finding raised for the imitation featurizer.

The state-level `eval_model.json` baseline reads HIGHER (0.5887) than either
per-option model. This is expected, not a failure of the per-option approach:
`state_eval_p` predicts the eventual winner from the CURRENT BOARD STATE
(prize differential, HP, deck counts), a much more direct signal for "who is
ahead right now" than the identity of one option just chosen at that state.
It is also, by construction, identical across every option at a given
decision, so it cannot rank sibling options against each other at all; it is
reported here only as the comparability check the plan asked for, not as a
competing ranker. The per-option models answer a narrower, option-specific
question (does THIS option's own feature profile skew toward the winning
population), which is the one PTCG_RANKER actually needs to rank sibling
options within one decision.

**LogisticRegression wins on held-out AUC (0.5424 > 0.5380)** and is the
exported model.

## Export

`search/ranker_model.json` (LogisticRegression: `feature_names`,
`feature_version` = `agents.imitation_features.feature_version()` =
`("3", card_effects.TAGS_VERSION)`, `mean`, `std`, `coef`, `intercept`),
following the `search/eval_model.json` template exactly. `search/
learned_ranker.py` is the pure-Python loader/scorer (no sklearn/numpy
dependency, mirrors `search/learned_eval.py`'s load/cache/never-raise
contract), supporting both `model_type: "logreg"` (this export) and
`model_type: "mlp"` (one ReLU hidden layer plus a sigmoid output unit,
matching sklearn's `MLPClassifier` binary-classification layout) so a future
retrain that picks the MLP needs no scorer changes.

Unlike `learned_eval.predict_win_probability` (0.5 neutral fallback used
unconditionally everywhere), `learned_ranker.score_option` returns **None**
on any load or scoring failure. A per-option score participates in an argmax
against sibling options at the same decision; a fabricated neutral 0.5 would
silently tie every option and pick an arbitrary one (whichever sorts first)
rather than signaling "no valid model" to the caller.

## Match-time integration (agents/heuristics.py)

`PTCG_RANKER` (default off, `os.environ.get("PTCG_RANKER", "0") != "0"`).
When on, `choose()`'s ladder gains one resolver, `_resolve_ranker`, at fixed
priority `float("inf")` (above every CEM-tunable `PRIO_*`, so it wins the
ladder sort whenever it returns a non-None pick):

1. Ranks every **L2/L3-safe** legal MAIN option
   (`_ranker_safe_indices`, new) by `search/learned_ranker.score_option` and
   takes the argmax.
2. Sits strictly **below the L1 lethal FORCE**: `choose()` checks lethal
   unconditionally before the ladder (and therefore before `_resolve_ranker`)
   is ever consulted, unchanged by this work.
3. **Re-derives L2 and L3 itself** rather than trusting the scorer to have
   learned them: `_ranker_safe_indices` excludes (a) a repeatable
   (non-once-per-turn, or unresolvable) ABILITY option, mirroring
   `_once_per_turn_ability`'s stateless-loop guard, and (b) near a
   self-deckout, a PLAY option that provably drills the deck (or whose card id
   cannot be resolved, treated conservatively as a potential driller),
   mirroring `choose_play`'s near-deckout branch. A trained scorer that never
   saw those constraints during training can therefore never violate them.
4. Is free to override **L4/L5 and the CEM-tuned PRIO_\* category order**:
   those are strategic heuristics, not safety guards, and improving on them is
   the point of the ranker.
5. Degrades safely: fewer than two safe candidates, a `None` decision-features
   result, or every candidate scoring `None` (missing/stale/corrupt model) all
   fall through to the historical category ladder untouched, never picking an
   arbitrary tied option.
6. **Byte-identical when off**: `_resolve_ranker`'s first line returns `None`
   before building any candidate set or importing `imitation_features` /
   `learned_ranker`, so a shipped build with the flag unset never even touches
   the new code path. `tests/test_ranker.py::
   test_ranker_off_never_builds_a_candidate_set` locks this by monkeypatching
   `_ranker_safe_indices` to raise and confirming it is never called.

`agents/imitation_features` and `search/learned_ranker` are imported lazily
(inside `_resolve_ranker`, not at module top level) specifically to avoid a
circular import: `agents/imitation_features.py` already imports `agents/
heuristics.py` at module scope, so a top-level `heuristics -> imitation_
features` import would cycle. `tests/test_grader_submission.py`'s
`_HEUR_EXTRAS` (and therefore `_SEARCH_EXTRAS`, which splats it) now also
bundles `imitation_features.py` and `search/learned_ranker.py`: this is a
static AST check on the ImportError-fallback shape, not a runtime-reachability
one, on purpose, so a future build that flips `PTCG_RANKER` on is already
covered rather than discovering the gap the way ref 54281824 discovered a
missing `card_effects.py`.

## Unit tests

- `tests/test_learned_ranker.py` (8 tests): committed-model load/bounds,
  wrong-length vector, missing/stale/corrupt/unknown-type model file (all
  return `None`, never raise), a hand-built logreg round-trip and a hand-built
  MLP round-trip (both pure-Python forward passes checked against a known
  monotone response).
- `tests/test_ranker.py` (16 tests):
  - **flag-off byte-identity**: `_RANKER` defaults `False`;
    `_ranker_safe_indices` is proven unreachable when off (a monkeypatch that
    raises is never triggered); choose() is unaffected even when the scorer is
    mocked to prefer a different option, because the flag being off means it
    is never consulted.
  - **non-mocked scoring on real card data**: `decision_features` +
    `learned_ranker.score_option` end to end on real card ids, using the
    actually-committed `search/ranker_model.json` (no mocking); a full
    `choose()` pass with `_RANKER` on, real card ids, real model.
  - **ranker preference flip on a constructed pair of options**: with the
    scorer mocked to strongly prefer RETREAT vs strongly prefer ATTACH on the
    same three-option decision, `choose()`'s pick flips to match, proving the
    argmax wiring (not a hardcoded index).
  - Safety-guard interaction: lethal FORCE always wins even when the scorer
    is mocked to hate the lethal attack; a repeatable ability and a
    deckout-drilling PLAY are excluded from the candidate set even when the
    scorer is mocked to love them (`_ranker_safe_indices` unit tests plus
    full-`choose()` integration tests for both); fewer-than-2-candidates and
    all-`None`-scores both degrade to the historical ladder without ever
    calling the scorer needlessly.

`tests/test_heuristic.py`, `tests/test_endgame_play.py`, and
`tests/test_safety.py` (124 tests) all still pass unmodified: the new resolver
adds one ladder tuple entry that no-ops when the flag is off.

## Fires-vs-inert with positive control (candidate_yushin_ito)

`tools/measure_ranker.py`, mirroring `tools/measure_endgame_play.py`'s
template exactly (n=25 real captured positions on `decks/
candidate_yushin_ito.csv` + 1 synthetic positive control), per the repo's
`tools/measure_*` standard.

- **Real positions**: heuristic-vs-random self-play on yushin, capturing MAIN
  decisions where the ranker's structural precondition holds (>=2 L2/L3-safe
  candidate options, via `_ranker_safe_indices`), toggling `_RANKER` off/on
  with the REAL committed `search/ranker_model.json` (never mocked for these
  rows) and comparing `choose()`'s pick.
- **Positive control**: a hand-built three-option decision (RETREAT / ATTACH /
  END, all L2/L3-safe) with `learned_ranker.score_option` mocked to strongly
  prefer RETREAT (an option the historical ladder does not pick here: ATTACH
  wins off). This checks the WIRING (`_RANKER` -> `_ranker_safe_indices` ->
  `decision_features` -> `score_option` -> argmax -> `choose()`), not the
  trained model's judgment, so it is expected to flip regardless of what the
  real model thinks about real yushin positions.

Result:

```
positions captured (>=2 L2/L3-safe candidates): 25
PTCG_RANKER flipped the pilot decision on 17/25 real yushin positions

positive control (synthetic, scorer mocked to prefer RETREAT):
  off_type=8 (ATTACH) on_type=12 (RETREAT) flip=True
```

**Positive control flipped** (the wiring is sound) and **17/25 real yushin
positions flip** (the trained model is LIVE, not inert, on the ring deck). Per
the U105 lesson, this only clears the CAN-fire/DOES-fire precheck: the next
honest step is the pre-registered powered elite-ring gate (analysis/
ml_expert_review.md's own prescription: ~710/arm for a +5pp gate, ~195/arm for
+10pp, at 80% power, one-sided alpha 0.05, run on the parallelized harness).
That gate run is explicitly out of scope for this task ("Do NOT run the ring
gate yet, the parallel harness lands in a sibling task") and is not run here.

## Files

- `tools/build_outcome_dataset.py` (new): zip-based episode extraction +
  `--widen` option.
- `tools/replays_to_rows.py` (extended): `outcome_rows_from_replay`,
  `write_outcome_csv`.
- `tools/train_ranker.py` (new): LR + MLP(64) training, baselines, export.
- `search/learned_ranker.py` (new): pure-Python scorer.
- `search/ranker_model.json` (new, exported): the committed LogisticRegression
  model.
- `agents/heuristics.py` (extended): `PTCG_RANKER`, `_ranker_safe_indices`,
  `_resolve_ranker`, one ladder entry.
- `tools/measure_ranker.py` (new): fires-vs-inert + positive control.
- `tests/test_learned_ranker.py`, `tests/test_ranker.py` (new).
- `tests/test_grader_submission.py` (extended): `_HEUR_EXTRAS` covers the new
  flat-layout imports.
- `data/training/outcome_rows_top50_1783845441.csv` (generated, gitignored
  training data, not committed): 44,024 rows, 710 games.
