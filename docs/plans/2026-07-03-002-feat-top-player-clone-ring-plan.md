---
title: "feat: top-player clone opponents + calibrated practice ring (ptcg-abc)"
date: 2026-07-03
type: feat
status: ready
depth: standard
origin: Dan's directive (build opponent bots from the top leaderboard players); fixes the audited offline-to-ladder non-transfer (mirror-pool gauntlet)
target_repo: ptcg-abc
---

# feat: top-player clone opponents + calibrated practice ring

## Why

Four ladder results in a row contradicted our offline gauntlet (benchguard, both meta copies, search,
trolley_thick). Root cause: the practice pool is OUR OWN heuristic piloting different decks, a mirror match
that does not resemble the real field. Fix: opponent bots that imitate the TOP LEADERBOARD TEAMS' recorded
play, each paired with that team's harvested deck, and a CALIBRATION gate proving the new ring actually
predicts known ladder outcomes before it is trusted. Clone bots are offline tools only: they never ship in
the submission tarball, so they may use numpy/sklearn freely and carry no grader constraints.

## Hard constraints (inherited)

- No em dashes anywhere. Competition data stays isolated under gitignored data/; derived corpora too.
- Clone bots and their weights are dev-side artifacts; commit code and small JSON weights, never replay data.
- One loop; ladder slots stay governed by TRACK L pre-registration. This ring GATES candidates; it never
  spends slots itself.

## Data reality (verified)

- The episode dataset holds 2,041 games by the top-20 teams (win AND loss sides) plus full decklists.
- analysis/move_ranking_validator.iter_expert_decisions already yields (state, chosen-option) pairs for any
  seat; analysis/expert_cohort.py classifies archetype families; agents/imitation_features.py (committed WIP)
  featurizes (state, option) pairs as ranking groups.
- tools/opponents.py already resolves deck:<name> opponents; clone:<name> slots in beside it.

## Implementation units

### U70. Top-player decision dataset (per team and per archetype family)
- **Goal:** the training table for cloning: one ranking group per top-team MAIN decision (features per legal
  option + which option the team actually chose), tagged by team, archetype family, and won/lost.
- **Files:** tools/clone_dataset.py, tests/test_clone_dataset.py.
- **Approach:** iterate the episode dataset's top-team seats (BOTH their wins and losses; how they respond
  under pressure is part of the imitation), reusing iter_expert_decisions + imitation_features. Split
  held-out by EPISODE. Output ragged npz under data/training/clones/ (gitignored).
- **Tests:** synthetic replays produce correctly shaped groups; episode-level split holds; draws and
  malformed episodes skipped; no test touches real competition data.
- **Verification:** per-family group counts reported; at least the Grimmsnarl and Archaludon families reach
  trainable size (census says they do).

### U71. Clone policy training + export
- **Goal:** a shallow option-scoring policy per archetype family (pooled top-team play), the clone's brain.
- **Files:** tools/train_clone.py, agents/clone_policy.py, tests/test_clone_policy.py.
- **Approach:** pairwise/listwise logistic ranking over the U70 groups (sklearn dev-side is fine; inference
  numpy-only for speed). Export weights JSON per family. Report held-out top-1 agreement per family and
  against a random/first-legal baseline; record honestly in analysis/clone_quality.md. A clone only
  qualifies as a ring opponent if it beats the first-legal baseline by a wide margin on held-out decisions.
- **Tests:** training on synthetic groups recovers a planted preference; export round-trips; scorer never
  raises and falls back to first-legal on malformed states.
- **Verification:** analysis/clone_quality.md shows per-family held-out agreement and which families qualify.

### U72. clone:<family> opponents in the gauntlet pool
- **Goal:** the ring itself: each qualified clone pilots its own family's harvested top deck.
- **Files:** tools/opponents.py, tests/test_opponents.py.
- **Approach:** register clone:<family> names resolving to an agent that picks the family's harvested
  decklist at deck-select and scores options with agents/clone_policy.py at decisions, guaranteed-legal
  fallback throughout. The RING = the set of qualified clones plus the existing harvested-deck opponents.
- **Tests:** clone opponent plays a full legal match; unknown family degrades to the deck:<name> behavior;
  pool listing includes clones only for exported weight files present on disk.
- **Verification:** a gauntlet run against the ring completes with zero invalid moves.

### U73. CALIBRATION GATE: does the ring predict the real ladder?
- **Goal:** trust or reject the ring based on evidence, never vibes.
- **Files:** tools/ring_calibrate.py, analysis/ring_calibration.md, tests/test_ring_calibrate.py.
- **Approach:** run every historical build with a KNOWN ladder score (trolley 569.6, benchguard 554.5,
  search 514.7, grimmsnarl 510.1, archaludon 382.5, plus thick 446.2) through the ring at fixed N; compare
  ring win-rate ordering to the known ladder ordering (rank correlation). DECISION RULE, pre-registered
  here: correlation >= 0.7 means the ring becomes the OFFLINE GATE for every future TRACK L candidate
  (replacing the mirror pool); below that, record the failure honestly and keep the ladder as sole judge.
- **Tests:** the correlation math on planted orderings; ties handled; a build set smaller than 4 refuses to
  conclude.
- **Verification:** analysis/ring_calibration.md states the correlation, the verdict, and (if passing) the
  new gate threshold a candidate must beat.

### U74. Re-gate the live levers through the ring
- **Goal:** immediate payoff: score the staged ability build and the next deck candidates against the ring.
- **Files:** analysis/ability_ring_check.md (plus ledger updates).
- **Approach:** only if U73 passes: run ability-on vs ability-off and any queued deck candidates against the
  ring; record whether the ring agrees with the pending ladder A/B once it settles (a free predictiveness
  data point either way). Ring results NEVER veto an already-pre-registered ladder A/B; they gate FUTURE
  candidates.
- **Verification:** the ledger notes ring-vs-ladder agreement for every candidate that reaches the board.

## Sequencing and priority

U70 -> U71 -> U72 -> U73 -> U74, one unit per loop iteration. This series is the loop's TOP PRIORITY after
TRACK L's staged actions (evict thick, submit ability), because every future ladder decision depends on a
gate that actually predicts the ladder. It also feeds TRACK S directly (the clone ring and its calibration
are strong Strategy-writeup material: an honest, validated evaluation methodology).

## Risks

- Clones may imitate weakly (shallow model, June data). Mitigation: the U71 qualification bar and the U73
  calibration gate; a failed calibration is recorded, not rationalized.
- The field drifts; June clones age. Mitigation: weekly tracker refresh already exists; retrain clones on
  refresh.
- Ring games are slower than mirror games. Mitigation: tools/parallel_gauntlet.py (U60) already fans out
  across cores.
