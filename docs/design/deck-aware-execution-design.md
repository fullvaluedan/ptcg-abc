# Deck-Aware Pilot Execution: Design Digest (canonical record)

Source: 6-agent design fan-out (5 architect memos + adversarial critique), 2026-07-02.
Scope: hybrid data-first deck-awareness for the cabt pilot. Contains only derived design
content, no competition data (no replay payloads, no team handles, no episode content).

Verdict up front: individually strong memos that do NOT yet compose into one buildable
system. Hold a reconciliation pass on ~8 forked contracts, add the missing seeds-consumer
and unit-zero-spike units, THEN build. Details in the Critique section.

---

## Memo 1: dataset-pipeline (expert-decision imitation dataset)

Core move: each expert MAIN decision is a RANKING GROUP (one feature row per legal option,
label = within-group offset of the played option), not a fixed-class classification.

Key decisions (decision: rationale):
- Ranking groups over classification: option indices are unstable card identities; scoring featurized (obs, option) pairs and argmaxing within the group is index-invariant and matches match-time use.
- ONE ship-safe featurizer shared verbatim between extraction and inference (agents/imitation_features.py, FEATURE_VERSION asserted everywhere): train/serve skew is the number one BC failure mode.
- Ragged npz per (archetype, split) with jsonl manifest sidecar (data/imitation/<archetype>/train.npz, test.npz, manifest.jsonl): one np.load for a numpy-only trainer, manifest covers auditability.
- Split by EPISODE via md5(episode_id) mod 100 (85/15): decisions within a game are correlated; md5 is deterministic across runs and machines.
- Filter: winning seats whose 60-card list matches the target archetype signature (overlap >= 0.8), outcome columns stored so filtering can soften later without re-extract.
- Scope v1 to MAIN single-pick decisions; sel_type/sel_context columns exist NOW so sub-selects (CARD fetch/discard) are a filter change, not a schema change.
- Global card vocab from card_index(): stable across archetypes and rebuilds, no vocab file to sync.
- Isolation: stream zips, write only derived floats under gitignored data/imitation/, extractor refuses out-paths outside data/.

Units (files):
- U1 featurizer: agents/imitation_features.py, tests/test_imitation_features.py (F~55 features, never raises, stdlib at emit time)
- U2 episode filter (win + archetype gate): analysis/imitation_filter.py, tests/test_imitation_filter.py
- U3 extractor CLI: tools/imitation_extract.py, tests/test_imitation_extract.py
- U4 npz writer/loader (the schema contract): analysis/imitation_dataset.py, tests/test_imitation_dataset.py
- U5 stats and QA gate (volume/balance/baseline floors): tools/imitation_stats.py, tests/test_imitation_stats.py
- U6 ship-side round-trip guard + build version gate: tests/test_ship_featurizer.py, tools/build_submission.py

Top risks:
- Volume starvation (one archetype, wins only, maybe a few thousand decisions): U5 hard count gate before training; relief valves are lower overlap, no-require-win weighting, more daily zips.
- Train/serve featurization drift: single module + version handshakes + bit-for-bit round-trip test.
- Near-duplicate episode leakage across the split: accepted; final gate is never the test split, it is move_ranking_validator plus the ladder.
- Cloning winner mistakes: ranking labels are soft; won/turn/prize columns allow later weighting; hand-coded guards cap the blast radius.

## Memo 2: card-effect-features (agents/card_effects.py knowledge layer)

Core move: a stdlib-only card-knowledge layer keyed by cardId/attackId, three layers:
text-level tag rules (tag_text -> frozenset over fixed TAG_VOCAB), cached card-level API
with explicit degradation (UNKNOWN_CARD / UNTAGGED_EFFECT / empty), and fixed-order
feature vectors (FEATURE_NAMES, TAGS_VERSION) for the learned scorer.

Key decisions (decision: rationale):
- Pure card-knowledge layer, zero observation parsing: reusable by pilot rules, scorer, archetype inference, and trivially testable; obs shape churn cannot break it.
- heuristics.py keeps _card_text and passes TEXT in: preserves ~6 monkeypatch test seams and avoids a circular import; all ~60 existing tests pass unmodified.
- Three-state degradation (UNKNOWN_CARD, UNTAGGED_EFFECT, empty): novel effects fail loudly, not silently vanilla; consumers branch conservatively per their current fail direction.
- TAG_VOCAB fixed order + TAGS_VERSION + digest drift test: an untracked rule tweak must not silently skew shipped weights; mismatch degrades to the pure ladder.
- Behavior freeze by golden equivalence over the FULL real card pool (old helper bodies vs new delegation): the charter requires byte-identical default behavior.
- Stdlib-only (re, functools), lazy table build: import-cheap under the grader, no numpy needed.
- heuristics imports card_effects in try/except with None fallback: a mis-built tarball degrades to today's conservative defaults, never crashes.
- Vocabulary grown from reality via a coverage audit tool with a ratcheting untagged fraction: new regex phrasings drafted from the real pool text dump, never guessed.

Units (files):
- U1 tag rules + vocabulary: agents/card_effects.py, tests/test_card_effects.py
- U2 card-level API + degradation: agents/card_effects.py, tests/test_card_effects.py
- U3 heuristics refactor, behavior-frozen: agents/heuristics.py, tests/test_card_effects.py, tests/test_heuristic.py
- U4 coverage audit + ratchet: tools/tag_coverage.py, tests/test_card_effects.py
- U5 ship integration + grader safety: tools/build_submission.py, tests/test_grader_submission.py, tests/test_build_submission_env.py
- U6 versioned feature vectors for the scorer: agents/card_effects.py, tests/test_card_effects.py

Top risks:
- Regex drift during the move changes shipped behavior: golden pool-wide equivalence test before deleting old code.
- New-tag regexes guessed, not matched to real pool phrasing: U4 dump-first drafting plus named-card spot checks and the ratchet.
- Rule changes after training silently skew the multi-hot: TAGS_VERSION gate, loader degrades on mismatch.
- Tarball missing the module: None fallback + negative grader-exec test demanding a legal move.

## Memo 3: execution-seam-and-policy (the injection seam and learned ranker)

Core move: ONE module-global option-scorer hook in agents/heuristics.py (default None,
byte-identical unset), installed when PTCG_POLICY=1 is baked. MAIN flow becomes four
layers: hard FORCE/VETO guards > confident learned argmax (softmax margin >= tau) >
existing ladder with score tiebreaks > END/_first_legal.

Key decisions (decision: rationale):
- Single seam via heuristics.set_option_scorer: all three call sites (agent_heuristic, agent_search fallback, search/rollout.py _policy) inherit deck-awareness with zero caller edits.
- Guards, then confident override, then tiebreak (all three, layered by confidence): only a full-decision argmax can fix the category-level ability gap, but unguarded cleverness loses ladders.
- Loop-safety ability VETO outranks the ranker unconditionally: a confident repeatable-ability preference would hang a stateless choose() loop.
- Per-archetype linear weight blocks in one policy_weights.npz, selected by signature overlap (own deck lazily, opponent via infer_belief): sample-efficient, auditable, clean fallback chain to generic then pure ladder.
- Linear conditional-logit ranker, pairwise trained (sklearn offline), tiny-MLP upgrade in the same npz only if linear plateaus: validated small steps beat big unvalidated ones.
- Thin guard layer formalized as ordered FORCE/VETO list (lethal, ability veto, deckout drill veto, thin-bench force, archetype-keyed Rare Candy force): all already-validated behaviors, repositioned above the scorer.
- Ship via existing build_submission --extra and --env, loader mirrors _read_deck with no-__file__ guard: zero build-tool code changes, grader-crash class de-risked.
- Rollout tie-in free by construction (rollouts route through choose), opponent conditioning behind PTCG_POLICY_OPP: same weights serve pilot, gauntlet foil, and cloned rollout opponent.

Units (files):
- U-E1 seam + layered MAIN flow: agents/heuristics.py, agents/agent_heuristic.py, agents/agent_search.py, tests/test_heuristic.py
- U-E2 archetype resolution both seats: agents/policy.py, analysis/archetype.py, tests/test_policy.py
- U-E3 weight loading + ranking inference: agents/policy.py, agents/features.py, tests/test_policy.py
- U-E4 FORCE/VETO guard layer: agents/heuristics.py, tests/test_heuristic.py, tests/test_safety.py
- U-E5 offline trainer -> policy_weights.npz: tools/train_policy.py, analysis/move_ranking_validator.py, tests/test_train_policy.py
- U-E6 grader-safe bundling + weights regression: tests/test_grader_submission.py, tools/build_submission.py
- U-E7 rollout/cloned-opponent verification: search/rollout.py (verify only), agents/policy.py, tools/opponents.py, tests/test_search.py, tests/test_opponents.py

Top risks:
- Train/serve skew clearing the confidence gate as noise: one shipped featurizer, version handshake, composed-pilot gate on held-out episodes.
- Tau miscalibrated (never engages, or overrides good ladder play): CEM-tunable, swept offline; guards are tau-independent.
- Offline agreement up, ladder flat (already lived twice): guards-only build ships first; weights build only after clearing the held-out baseline; grader regressions kill the crash failure mode.
- Scorer cost in the rollout hot loop: <5ms featurizer budget test, time-bank guards, search build can ship without the flag.

## Memo 4: deck-understanding (target selection and game-plan mining)

Core move: two products: (1) an archetype-family target selector ranking families by
expert-winning-replay volume times expert win rate (not raw wins, which are a popularity
artifact); (2) a game-plan miner over winning expert replays producing six stat blocks
(openings, evolution timing, sequencing, energy targeting, win condition, deckout
avoidance) that feed BOTH a human game-plan doc and a thresholded machine seeds JSON.

Key decisions (decision: rationale):
- Two-level deck identity (families for learning, exact 60 for shipping): per-signature counts are too thin for stable stats; a submission still needs one exact legal list.
- Mastery score = expert wins times expert win rate: raw-win ranking rewards popularity and yields noisy imitation labels; execution learning needs strong-pilot wins.
- One shared decision spine: lift iter_expert_decisions/OPT_CATEGORY into analysis/replay_trace.py with resolution of option index to card/attack/target; miner, BC dataset, and validator all consume the same population, so human-readable stats sanity-check BC features.
- Mine wins, contrast against losses: load-bearing behaviors show up as win/loss deltas and strengthen the writeup.
- Seeds are conservative, thresholded, versioned (0.70 share, 0.80 timing, 0.95 unanimity): mechanical thresholds keep the hand-coded layer thin; weak signals emit nothing.
- Isolation: per-decision traces live under gitignored data/derived/; committable artifacts are aggregates and public card names only; seeds bake as dict constants at build time (no runtime file IO).
- Predict but do not hardcode the target (Grimmsnarl family expected primary, Archaludon the volume hedge): the selector must be free to disagree; a confident prior was already refuted once.

Units (files):
- DU1 family clustering + target selector: tools/archetype_select.py, analysis/target_selection.md, analysis/gameplans/targets.json, data/derived/target_episodes.jsonl (gitignored), .gitignore
- DU2 shared resolved-decision trace: analysis/replay_trace.py, analysis/move_ranking_validator.py (re-export refactor), data/derived/traces/ (gitignored), tests/test_replay_trace.py
- DU3 game-plan miner: analysis/gameplan_mine.py, analysis/gameplans/<family>.md, tests/test_gameplan_mine.py
- DU4 seeds emitter (--seeds mode): analysis/gameplan_mine.py, analysis/gameplans/<family>_seeds.json, tests/test_gameplan_seeds.py, build_submission bake point
- DU5 pilot-vs-expert gap probe: analysis/gameplan_gap.py, analysis/gameplans/<family>_gap.md, tests/test_gameplan_gap.py

Top risks:
- Expert identification is a proxy (no ladder ratings in replays): anchor on the handles already tied to leaderboard positions, require ranking stability across anchor-only and threshold-expanded cohorts.
- Incomplete option resolution silently poisons stats and seeds: per-block resolution_rate; blocks under 0.90 flagged UNRELIABLE and mechanically barred from seeding.
- Seeds rot as the meta shifts: dated provenance, deterministic emitter for reviewable diffs, env-gated levers.
- Validator refactor breaks the anti-overfit gate: lift-and-re-export, existing tests as the acceptance gate.
- Target still cannot beat the trolley floor: DU5 gap probe must move before any ladder slot is spent.

## Memo 5: measure-sequence-risk (gates, sequencing, fallbacks)

Core move: the ladder A/B is the SOLE arbiter; every offline metric is a pre-registered
filter that can block a submission but never promote one. Three phases: A = pre-ML fast
wins plus a two-step attribution A/B (meta+aware vs meta+generic, then vs trolley);
B = learned scorer behind leakage/permutation/latency gates; C = rollout policy and
cloned opponent, weights handed to the CEM loop.

Key decisions (decision: rationale):
- Ladder-only promotion: the project already lived offline-does-not-transfer twice; one epistemology across plans.
- Two-step attribution: the headline comparison confounds deck and pilot; step 1 isolates the pilot factor so a failed headline still teaches which factor failed.
- Pre-registered margins in state/current.md BEFORE candidates run: post-hoc thresholds invite promotion of noise; ladder noise margin calibrated from same-build resubmission variance.
- Double gate: build-time lever (PTCG_DECK_AWARE, default OFF) plus runtime signature-match confidence gate: instant fleet rollback and a structurally always-live generic ladder.
- One model, three roles (pilot tiebreaker, gauntlet foil, rollout opponent): two clones would double the leakage surface and fork the plans.
- Weak-bot gauntlet banned from all gates (smoke tests only): known non-predictive; cloned or deck-diverse pools only, with per-opponent breakdowns.
- Hard safety rungs permanently outrank the scorer (lethal > deckout guard > scorer > ladder > _first_legal): the unattended loop cannot babysit a learned policy; deckout is the proven top leak.
- Phase B go/no-go = Phase A attribution result, not its headline: if hand-coded awareness moves nothing, pause before ML spend.

Units (files):
- MSR-1 per-archetype expert-agreement pre-gate: analysis/move_ranking_validator.py, tools/deck_harvest.py, analysis/archetype.py, tests/test_move_ranking_validator.py
- MSR-2 deck-execution loss buckets: analysis/loss_classifier.py, tests/test_loss_classifier.py
- MSR-3 effect-tag coverage meter + 100% target-deck gate: analysis/effect_coverage.py, tests/test_effect_coverage.py, agents/heuristics.py
- MSR-4 gate ledger + pre-registration + slot protocol: tools/loop_state.py, state/current.md, state/hypotheses.md, autoloop_status.md, tests/test_loop_state.py
- MSR-5 cloned-opponent gauntlet wiring + per-opponent rows: tools/opponents.py, tools/gauntlet.py, analysis/opponent_policy.py, tests/test_opponents.py, tests/test_gauntlet.py
- MSR-6 latency + grader-safety bench: tools/gauntlet.py, tools/measure_latency.py, search/timebudget.py, tests/test_grader_submission.py, tests/test_safety.py
- MSR-7 overfit/leakage sentinels (obs-only, permutation invariance, split integrity, shuffled-label control): tests/test_bc_dataset.py, tests/test_featurizer.py, analysis/move_ranking_validator.py
- MSR-8 always-on deckout guard above the scorer: agents/heuristics.py, tests/test_safety.py, tests/test_heuristic.py

Top risks:
- Imitation does not transfer to the ladder (already-realized risk class): ladder-only arbiter, filters block slot spend, trolley incumbent holds a slot, default-off lever for one-rebuild rollback.
- Index-instability and label leakage: permutation-invariance and obs-only sentinels, episode-level frozen split, mandatory shuffled-label control before any real training.
- Latency blows the think bank or rollout budget: pre-registered caps, soft-cap bailout to the generic ladder (degraded play, never a timeout loss).
- Cloned-opponent circularity: the clone must itself beat the generic heuristic on expert agreement before its gauntlet counts.
- Protocol drift in the unattended loop: machine-checked margins, incomplete ledger rows cannot reach the ladder, refutations re-tested through the hypothesis registry.

---

## Critique: high-severity gaps

1. Card-effect layer never reaches the learned model: memo 1's featurizer (F~55) contains ZERO of card_effects' TAG_VOCAB multi-hot, despite memo 2 stating the featurizer calls into it. The hybrid plan's core premise (effect awareness feeds the engine) is unimplemented. Fix: append card_effects feature vectors per option, record TAGS_VERSION next to FEATURE_VERSION, make card-effects U1/U2/U6 a hard featurizer dependency.
2. Featurizer contract forked three ways: agents/imitation_features.py (lists, int version, stdlib) vs agents/features.py (ndarray, str version, numpy) vs memo 5's third test-file set. The most-cited technical risk (train/serve skew) is realized organizationally. Fix: one module path, one signature, one integer version, one test file, before any code.
3. Model contract fork: memo 1 pins scores = X @ w + embed[card_vocab_idx] (listwise, embedding table); memo 3 pins pairwise logistic with s = X @ W + b and an npz with no embedding block. The dataset contract and the shipped scorer do not compose. Fix: pick one (recommend the plain linear W,b) and update both schemas.
4. Seeds JSON has an emitter but NO consumer: DU4 defines the seeds, U-E4 only formalizes existing behaviors, so Phase A's advertised hand-coded deck-aware layer is unowned. Fix: add a unit that bakes the seeds as a build-time dict constant and applies them in attach/bench/fetch resolution and the deckout floor, with an explicit owner.
5. Rollout seat-identity mechanism unresolved: U-E2's own text trails off self-contradicting; hand-presence and yourIndex tests both fail in determinized rollouts, so per-seat weight selection (the whole U13 tie-in) cannot be implemented as written. Fix: record the real player index at install time or thread a seat tag through the search Observation, as a testable contract before U-E7.
6. W_generic has no training data: memo 3's fallback chain needs a pooled all-archetype dataset that memo 1's archetype-filtered extractor cannot produce. Fix: drop W_generic (fallback = pure ladder) or add an --archetype all extractor mode; decide now, it changes the schema.
7. No cheap end-to-end signal check before ~26 units are built: the central bet (a linear ranker over these features beats the 0.212 top-1 and reorders categories like the 0/554 ability gap) is untested until everything lands. Fix: a 1-2 day unit-zero spike (hack extract, ~20 features, sklearn pairwise, per-category held-out agreement) gates the whole pipeline build.

Notable medium gaps: duplicate-option label noise caps both training and every agreement gate (collapse feature-identical options or add multi-positive labels in v1); Phase A ignores the known PTCG_ABILITY lever (+0.013 top-1, ability 0 to 0.139) which should be a named fast-win A/B; three different expert-cohort definitions across memos (one cohort module needed); three memos restructure move_ranking_validator differently (land DU2's lift first); memo 3's loader checks feature_version but not TAGS_VERSION (one combined version tuple); the 0.212 gate number is global and not transferable to a per-archetype scorer (gate against MSR-1's recomputed baselines).

Key contradictions to reconcile (one decision each): featurizer contract; model equation; deckout guard default (MSR-8 always-on vs U-E4 lever-gated); holdout split definition (md5 mod 100 vs even/odd vs unspecified hash); lever name (PTCG_POLICY vs PTCG_DECK_AWARE); first target archetype (Grimmsnarl vs Archaludon); expert cohort; version gating; card-effect integration; duplicated coverage tooling (tools/tag_coverage.py vs analysis/effect_coverage.py).

Missing units: seeds consumer; SEL_CARD fetch/discard handling (at minimum a seeded fetch-priority rule); pooled generic dataset extraction; featurizer/version unification; shared split-authority module; PTCG_ABILITY Phase A A/B; unit-zero spike; a pre-registered kill criterion / timebox for the whole deck-aware bet.

Sequencing advice (condensed): (0) unit-zero spike plus the ~8 reconciliation decisions; (1) DU2's replay_trace lift lands first, then MSR-1 and the extractor build on it; (2) heuristics.py changes serialize under one owner (card_effects delegation, then the seam and guards, then MSR-8 rung order), full test suite green after each; (3) Phase A ships the pieces that actually change ladder behavior (seeds consumer, PTCG_ABILITY, deckout guard) before any training; (4) weights enter a scored slot only after the spike passes and step-1 attribution shows recovery; (5) rollout/opponent conditioning waits for the seat-identity contract and the budget-hold test. Calibrate the ladder noise margin (possibly via a deliberate same-build resubmission) before the first ladder claim.

Critique top risks: execution ceiling (trolley's edge may be deck-vs-field fit, and there is no kill criterion bounding slot spend); linear ranker insufficiency untested until the end; organizational train/serve skew from the forked contracts; duplicate-option noise hiding a metric ceiling; Phase A under-delivery (mostly byte-identical refactors, the behavior-changing pieces unowned); slot economics unaccounted (two-step A/B times margin calibration under 5/day); isolation's one soft spot (per-tool out-path guards should live in one shared helper, or the next quick tool becomes the leak vector).

Verdict: individually strong memos that do not yet compose into one buildable system. The measurement/gating design and isolation posture are solid, and ranking-over-featurized-options is the right formulation for index instability. But three load-bearing forks (featurizer, model equation, guard/lever defaults), an unowned Phase A deliverable, a data-less W_generic, an unspecified rollout seat mechanism, and an untested central bet mean: run the reconciliation pass, add the seeds-consumer and unit-zero-spike units, then proceed. Without that, parallel implementation produces train/serve skew and an empty first A/B.
