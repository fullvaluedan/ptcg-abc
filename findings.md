# findings.md

Durable record of what we learned building the ptcg-abc agent for the Kaggle Pokemon TCG AI Battle
Challenge, kept as raw material for a later report on how the approach evolved as we got more data and tried
more things. Living document: append new findings with dates. Every claim points to a source under
`analysis/`, `state/`, `docs/plans/`, or `docs/writeup/` so the report can trace it.

No em dashes anywhere in this repo (hard constraint), so this file uses commas, colons, and parentheses.

---

## 1. Context and constraints (the fixed board)

- Two prizes. Simulation ladder RANK (final 2026-08-16) and a separate Strategy prize (final 2026-09-13,
  top 8 win $30k, scored 70% model approach / 20% deck concept / 10% writeup, ladder-independent).
- The shipped agent is `agents/agent_heuristic.py` (a pure-Python heuristic, brain in `agents/heuristics.py`)
  plus a `deck.csv`. It runs fully offline in the tarball (no numpy/sklearn/network at match time), the
  grader loads `main.py` via `exec()` with no `__file__`, the entrypoint must be the last callable, the agent
  must never raise, and the native engine is a process-global singleton.
- Submission economics: 5 submissions/day, only the latest 2 are scored, the leaderboard uses the best of the
  scored pair. This plus the noise band (below) is the true binding constraint on rank.
- The field (public leaderboard, pulled 2026-07-02): ~3996 teams, MEDIAN score 678.5, top ~1249
  (tonakaiiii). Our king has read between ~452 and ~691 across identical resubmissions.

---

## 2. Evolution of the approach (belief, then data, then change)

**Phase 0, foundation (2026-06-30).** Original plan `2026-06-30-001`. Built the engine wrapper, baseline and
heuristic agents, the gauntlet, the submission builder. Executed 13/13 units. Produced the only durable
scoring asset: heuristic + a hand deck. Belief at this point: build a strong agent, climb the ladder directly.

**Phase 1, the ladder teaches us what does not work (2026-07-01).** Every "obvious" way to climb was tried on
the real ladder and refuted (see the ledger): copying the top players' meta decks scored BELOW our own deck,
determinized search scored below the heuristic, an agent-level bench guard scored below baseline. Key reframe:
the heuristic is the deployable player, search is at best an offline teacher. Wrote a self-improving plan,
subjected it to a five-persona review (which found it could not reach #1 and was already stale), and
synthesized a unified plan (`2026-07-02-001`) with a settlement protocol (M=60 noise margin), a slot budget,
and an endgame noise campaign.

**Phase 2, the learning detour (2026-07-02).** Pivoted the loop onto a learned-evaluator / search track
(learned eval, move-ordering model, top-player imitation, CEM tuning), across several rapidly-superseded plans
(`002`, combined v2, the top-player tracker addendum, `003`). This built a large offline ML stack and a
173k-row top-player corpus. It was later found to have been aimed at the wrong scoreboard (Section 4D).

**Phase 3, the correction (2026-07-03).** An independent audit found the loop had spent ~2 days improving
`agent_search`, which does not ship. Split the loop into TWO explicit tracks: TRACK L (ladder, the shipped
heuristic + deck) and TRACK S (Strategy prize, the offline ML). Fixed a live-grader submission ERROR (a
missing bundled file). Built a top-20 clone practice ring; it FAILED calibration. Built a bracket-band clone
ring instead; it PASSED (the first offline instrument proven to predict the ladder). Mined the top players by
category. Launched teacher-student distillation. Added an OS-level watchdog after the loop kept dying
silently.

**Phase 4, comprehension (2026-07-03).** On the user's challenge that we never actually understood
top-20 play, a forensic autopsy proved the clone failure was an instrument defect, not unlearnable play
(Section 4D). Opened a comprehension track (U90-U94): card-semantics, mined per-archetype playbooks whose
every claim must predict held-out top-player moves, a correctly-built ranker, and ring-gated transfer into the
shipped pilot.

**Phase 5, transfer and its limits (2026-07-04, current).** The comprehension track finished (U90-U94 all
shipped, U92's rerun-with-a-different-objective closed FAIL, see Section 4B). Its two shippable levers both
reached a real ladder verdict: the ability lever WIN (+66.3pp, promoted to shadow-king) and the
attack-first lever NEUTRAL (both offline gates passed, +5.5pp gauntlet and +10.0pp ring, but the ladder never
accumulated enough decisive shared-bracket games to confirm before its settle-by date). Per the pre-registered
BAND/NEUTRAL action the slot reverts to a byte-identical king copy; that revert is built and grader-verified
but blocked by Kaggle's daily submission quota as of this writing. With no further comprehension-track units
defined and the CEM line closed on all three re-test conditions, TRACK L currently has no build awaiting a
slot beyond the queued revert, so the loop is running the standing writeup cadence on TRACK S.

---

## 3. The single most important number

Same-build ladder noise is the dominant force, and we under-modeled it twice. Pooled across every
byte-identical `heuristic+trolley` king ref (54215558/54252006/54281812/54282104/54315565), each re-read
multiple times as the ladder replays it, the observed scores span 396.7 to 691.5, a spread of ~295 points
(roughly 147 per side, `noise_model` v2, `margin_M` 150); a single king ref (54282104) alone drifted 691.5 to
494.8 on its own re-reads. An earlier, narrower pooling (452-691, ~240 points, the first ref-scoped
correction) was itself superseded once the 396.7 low turned up on a later ref. Both corrections are WIDER
than the M=60 confirmation margin the settlement protocol originally used, so a single-read ladder A/B cannot
confirm ANY lever we can build: every real improvement is smaller than the noise. Consequences, adopted
2026-07-04 (see 4D, noise recalibration and its v2 bump entry): the calibrated bracket ring (tau 0.857), not
the ladder, is the lever DECISION gate; the recorded "ability WIN" was reclassified a noise artifact. NOTE
(2026-07-05 posture inversion, supersedes the sentence that previously ended this section): the luck-harvest
reading of the endgame was OVERTURNED by the verified rules text (games continue ~2 weeks post-deadline until
the leaderboard converges, so lucky draws decay); the Aug 10-16 window is now a lock-the-two-strongest-builds
operation, and TRUE STRENGTH plus the Strategy writeup carry the EV. Source: `state/current.md` noise model,
`LOOP_BRIEF.md` POSTURE INVERSION, `analysis/final_scoring_semantics.md`, `analysis/strategy_prize_rules.md`.

---

## 4. Findings ledger

### 4A. Ground-truth facts

- Determinized search is inert on the ladder unless force-loaded: the match-time `cg.api` does not expose the
  `search_*` forward model, so search silently falls back to the heuristic (~0.02s per decision).
  `analysis/ladder_search_inert.md`, `analysis/search_recovered_on_ladder.md`.
- Our dominant loss mode has been early_collapse (empty-bench board collapse). It was ~92% of losses early;
  as of 2026-07-03 it is ~48% (60 of 125 losses over 224 replays), with bad_determinization and deck_matchup
  rising. `analysis/early_collapse_empty_bench.md`, `state/current.md`.
- The empty-bench collapse is opponent-agnostic and is draw variance, not play ordering: in 94% of
  empty-bench moments we hold no benchable Basic to reorder. `analysis/deck_matchup_is_opponent_agnostic.md`,
  `analysis/empty_bench_is_draw_variance.md`.

### 4B. Refuted or falsified levers (dead ends, closed with evidence)

Canonical registry with re-test conditions is `state/hypotheses.md`. Summary:

- meta_deck_copy: copied Archaludon (382.5) and Grimmsnarl (510.1) scored well below the trolley floor
  (569.6). The simple pilot plays a meta deck WORSE. Re-test only with a genuinely deck-aware pilot (never
  measured). `analysis/meta_decks_underperform_on_ladder.md`.
- search_active_beats_heuristic: real search scored 514.7 vs 569.6 same deck. Search costs points. Re-test
  gated on the FAVORABLE PIMC diagnostic (belief-weighted search lane only). `analysis/ladder_scored_pair_reclaim.md`.
- thin_bench_threshold and bench_floor_leaf_term and bench_dig: the board-out floor is DECK-density-set, not
  guard-set. Widening guards is flat; the leaf term is squeezed; digging does not help at scale (its direction
  even flipped with more data). `analysis/thin_bench_threshold_is_flat.md`,
  `analysis/bench_floor_search_lever_squeezed.md`, `analysis/bench_dig_refuted_at_scale.md`.
- energy_seq: front-loading energy onto the attacker matched only 6% of 1445 expert attaches; the gap is
  ordering, not target. `analysis/energy_seq_refuted_by_expert_moves.md`.
- gameplan_seeds_diffuse: mining the top decks for concentrated "always do X" seeds came back nearly empty at
  full scale (Grimmsnarl 0 seeds); the one Archaludon seed was a deck-identity fact, not a win edge.
  `analysis/gameplans/seeds_real_run.md`. 2026-07-03 (U91): the named play_target re-test condition (fix the
  PLAY resolver) is now MET. Root cause was a real bug in `analysis/replay_trace.py`, not deck-derived
  diffuseness: ATTACH options were mined for the wrong half of the option (the energy card spent, not the
  receiving Pokemon named by separate `inPlayArea`/`inPlayIndex` keys), and PLAY options carry no `area` key
  at all so the generic resolver returned `None` for every one. Fixed both (mirroring the shipped pilot's own
  already-correct `_attach_slot_card_id` / `play_card_id`); validated on real data (bracket_4, n=1500
  episodes): both blocks went from 0.470/0.285 and 0.000-barred to 1.000/1.000 resolution.
  `analysis/gameplan_target_resolution_fixed.md`. Still open: concentrating the now-resolvable distributions
  past the 0.70 emission bar, and a real side-finding that meta_archaludon/meta_grimmsnarl no longer classify
  any deck in this dataset (the newer bracket_1..6 archetypes shadow them in the classifier's tie-break).
  This refutation covers TARGET-CARD seeds only; see 4C for a related within-turn SEQUENCING signal that did
  clear both gates on the same family (2026-07-03, U91 step 2).
- cem_prio_agreement_generalizes: three CEM runs, three different fitness formulations, tuned expert-move
  agreement on train but got zero or negative held-out transfer every time, all blocked by the pre-registered
  filter. The third (2026-07-03, U83) targeted the second attempt's own named re-open condition, a materially
  larger sample, with a 92x/356x larger teacher self-play corpus (32003 train / 10689 held-out test decisions
  vs 116/30) and the calibrated L5 ring instead of an uncalibrated pool; held-out delta was still negative
  (-0.0022), and full-population train agreement went backwards too. Diagnosis: the sweep's own best fitness
  was dominated by a noisy 6-game ring-win-rate read, not a real agreement gradient, the same
  proxy-metric-moves-backwards failure the second attempt found. `analysis/cem_run_prio.md`,
  `analysis/cem_run_prio_pooled.md`, `analysis/cem_run_prio_teacher.md`. 2026-07-04: the one remaining named
  re-open condition, "a genome region with a measured non-flat held-out gradient", was checked directly (no
  fourth sweep) by extending `analysis/measure_cem_gradient.py` with a teacher-labels held-out mode and
  running it against the exact 10689-decision test split the three sweeps blocked on. The genome IS non-flat
  (max per-dim delta 0.2738, 5x the original 2026-07-01 diagnostic), but every load-bearing ordering dim's
  shipped default already sits at or above both of its own bound readings, so no single-axis move beats the
  current default anywhere in the 18-dim space. This mechanistically explains all three blocked sweeps (the
  landscape slopes downward away from the default on every dim that matters, so any optimizer noise pushes
  off the peak rather than up it) and fully exhausts conditions (a), (b), and (c) together.
  `analysis/cem_gradient_condition_c.md`.
- clone_imitation_beats_first_legal (U92 step 0, 2026-07-04): the known-good pairwise RankNet (U26 spike) WAS
  finally rerun on the clone dataset, changing only the training objective (pairwise ranking loss instead of
  the pointwise per-row log-loss all three prior clone attempts used) while holding the feature set and split
  fixed. Same collapse: every family ties first-legal within +/-0.0015 (n_scored 1299-11092/family). This is
  the fourth converging negative result (2 model families, 2 feature-set variants, now a different objective
  family), closing the "wrong training objective" hypothesis alongside the earlier "wrong model" and "position
  features hide the signal" ones. `tools/train_clone2.py` is closed without being built.
  `analysis/rank_clone_killtest.md`, `analysis/clone_quality.md`.
- missed_lethal: a detector artifact, not a real bug (safety-1 lethal already fires).
  `analysis/missed_lethal_falsified.md`.
- Category-mining v2 follow-ons mostly refuted: the retreat gap is matchup-shaped not threshold-shaped, the
  retreat-target and promote and deck-search gaps did not reduce to shippable rules, and the Archaludon
  deckout is mandatory-draw depletion (no guard-tuning fix). `analysis/retreat_gap_conditional.md`,
  `analysis/retreat_target_conditional.md`, `analysis/promote_gap_conditional.md`,
  `analysis/search_gap_conditional.md`, `analysis/archaludon_deckout_is_mandatory_draw.md`.
- Portfolio / two-deck decks collapse less but lose the prize race: not ladder-viable.
  `analysis/portfolio_decks_not_ladder_viable.md`.
- trolley_thick deck: offline it cut empty-bench collapse 80.8% to 65.4% (n=240, p<0.001) but on the ladder it
  settled a decisive LOSS (446 vs king 558, -112). Another offline-to-ladder non-transfer.
  `analysis/collapse_rate_thick_deck.md`.
- deck_exploration_top_rated_mining (U39 step 2, 2026-07-06): mined 43 unique deck signatures from 800+ rated
  top players (481 winning plays), extracted 11 new candidates not already in decks/*.csv. Scored all 11
  through the calibrated bracket ring (n=20 games per build, 9 opponents). Best candidate (candidate_yushin_ito,
  145 plays from cluster 1) scored 0.800 (16/20) vs baseline trolley 0.750 (15/20), delta +0.050, below the
  +0.10 gate for promotion. No candidates promoted. Conclusion: elite-tier deck exploration (800+ rating,
  top-player corpus) does not yield ring-beatable decks when piloted by the generic heuristic. Either top
  players' success is contextual to their own meta / piloting skill (not isolable to 60 cards), or the
  heuristic is too weak to extract their deck's optimal play. Without a new mining scope (lower ratings, new
  archetype focus), deck changes are a closed lever for TRACK L gains. `analysis/new_candidates_phase2_verdict.md`.

### 4C. Confirmed or positive findings (real signal)

- The ability blind spot: our pilot activated abilities 0 times in 554 expert ability decisions (abilities are
  ~12% of top-player MAIN decisions). Turning on a once-per-turn ability lever read +4pp offline gauntlet and
  +20pp against the calibrated ring. It is our best-validated lever shape. `analysis/move_ranking_diverges_ability_gap.md`,
  `analysis/ability_ab.md`, `analysis/ability_ring_check.md`.
- Deck vs pilot: the SAME heuristic scores 570 on trolley, 451 on the copied Archaludon list, 409 on
  kazuki0123's exact Grimmsnarl list. The ~900-point gap to the deck's real owners is PILOT execution, not the
  60 cards. `analysis/meta_decks_underperform_on_ladder.md`.
- How top teams win vs lose (1441 win / 1074 loss games): winners dig their deck HARDER mid-game then STOP
  late, and end the game with more energy, a bigger hand, and fewer prizes left (they close faster). Their
  loss modes (bad_determinization 29%, endgame_misplay 25%) differ from ours (early_collapse), so imitating
  their move distribution without fixing our early-board survival cannot fully converge.
  `analysis/top_player_win_loss_study.md`.
- The move-ordering model (search-side) read +5.0pp in a gauntlet A/B and was flipped on; confidence-based
  search time allocation (U12) passed its gate. `analysis/move_prior_search_ab.md`, `analysis/confidence_budget_ab.md`.
- The bracket-band clone ring PASSED calibration (tau 0.857 >= 0.7) and now has gate authority for
  submissions; the top-20 clone ring FAILED (tau 0.429). `analysis/ring_calibration.md`.
- U90 card-semantics v2 (2026-07-03): the two meta decks' effect-bearing cards were 5/15 and 4/19 blind to the
  knowledge layer, Boss's Orders among them (the exact card named invisible in 4D). Nine additive tags closed
  both decks to 100% coverage and fell the pool untagged fraction 0.4917 to 0.4204. Named a previously-unnamed
  ability class (ON_EVOLVE_TRIGGER: Assemble Alloy / Punk Up, one-shot on evolving, distinct from a repeatable
  or once-per-turn active ability); probed and confirmed our own pilot deck contains no on-evolve-ability
  Pokemon, so the gap does not apply to the shipped deck as-is (a deck-design question, not a heuristic-logic
  one). `agents/card_effects.py` TAG_VOCAB v2, `analysis/on_evolve_probe.md`.
- U91 step 2 within-turn sequencing (2026-07-03): two new mined blocks (attach_before_attack, energy_banking)
  cleared BOTH a claim gate (n>=1400/side, bootstrap 90% CI excludes zero) and a prediction gate (KD4
  train-mined CI brackets the held-out test mean) on bracket_4's full dataset. Winning play attaches-before-
  attacking 3.4pp less (0.524 vs 0.558) and banks energy 4.4pp less (0.192 vs 0.236) than losing play; a third
  block (game_length_turns) was mined but CUT (claim CI straddles zero). Small effect sizes, descriptive not
  yet prescriptive; U93 must design and A/B a real rule before this can claim any ladder value.
  `analysis/gameplan_claims_bracket_4.md`.
- U93 step 1, attack-before-attach lever built and confirmed LIVE (2026-07-03): PTCG_ATTACK_FIRST (default
  off, agents/heuristics.py choose()) takes an already-legal positive-value attack instead of a discretionary
  attach, the literal rule the U91 sequencing gap names. The fires-vs-inert check (mirrors measure_energy_seq's
  discipline) found it changes real trolley pilot decisions on 3/20 captured ATTACH+ATTACK positions (8 of the
  20 had a positive-value attack on the table). Not yet A/B'd; the bracket-ring check is still open before any
  ladder slot. `analysis/attack_first_flip_check.md`.
- U93 step 2, both offline gates PASSED (2026-07-04): the weak-bot gauntlet (200 games/arm) reads off 71.5% ->
  on 77.0%, +5.5pp, no regression (`analysis/attack_first_ab.md`); the calibrated bracket-ring (20 games/arm)
  reads off 75.0% -> on 85.0%, +10.0pp, agreeing in direction (`analysis/attack_first_ring_check.md`, new
  `tools/attack_first_ring_check.py`). Tarball built and grader-verified, and pre-registered as
  heuristic+trolley-attack_first (up, M=60, N=30, settle-by 2026-07-11); staged, not yet submitted (both
  ladder slots occupied).
- L1's ability lever SETTLED WIN on the ladder (2026-07-04): board check ref 54282097 561.1 vs reclaim-king
  ref 54282104 494.8, +66.3pp, clears the M=60 margin via the standing instant-settlement rule
  (`tools/loop_state.py auto-settle`). Promoted to shadow-king. This is the first real WIN verdict this loop
  has recorded on the actual ladder (prior verdicts were LOSS or offline BLOCKED), and it landed on the SAME
  lever the U90 comprehension-track WHY layer named (the 0/554 real ABILITY-decision blind spot). U93 step 3
  then submitted heuristic+trolley-attack_first (ref 54304483) into the slot this settlement freed, via the
  latest-2 eviction-by-submission-order mechanic (the older live submission drops automatically, no manual
  revert needed). `state/current.md`, `LOOP_BRIEF.md` L1/L9.
- U93 step 3's attack_first ladder A/B SETTLED NEUTRAL (2026-07-03), not WIN or LOSS: the first board reading
  fell inside the M=60 band (526.8 vs king 494.8), the pre-registered repeat resubmission then drifted to the
  opposite sign under ordinary same-build noise (442.9 vs 600.0), and the U23 scoreboard tiebreak on shared
  opponent brackets came back neutral on only 3 decisive candidate episodes (candidate 1/3, king 4/6,
  confidence 0.171), far short of the pre-registered N=30. This is the project's first case of a passing
  offline gate (gauntlet +5.5pp, ring +10.0pp, both agreeing in direction) that the ladder never accumulated
  enough decisive games to confirm or refute before its settle-by date, distinct from the earlier proxy
  failures where the ladder verdict was clear and simply disagreed. Per the BAND action the slot reverts to a
  byte-identical king copy, built and grader-verified but blocked from submitting by Kaggle's daily quota as
  of this writing. The lever stays re-eligible for a future slot without new offline work.
  `analysis/attack_first_settlement.md`, `docs/writeup/offline_ladder_transfer.md`, `state/current.md`.
- U39 step 2, candidate_yushin_ito (2026-07-05): the FIRST harvested top-rated deck to beat trolley's
  calibrated ring win rate under the same generic pilot (0.825 vs 0.725 baseline, +0.100, n=40, one
  shared run). The other 5 new candidates scored in the same run did not clear the promotion bar and
  reconfirm the meta_deck_copy pattern (Section 4B) for those decks. A single n=40 read at the exact
  boundary, not a landslide; queued in `state/current.md`'s candidates list for a second independent
  ring run before seating. `analysis/candidate_deck_ring_scores.md`.

### 4D. Methodological findings (the meta-record, the strongest Strategy material)

- Offline-to-ladder non-transfer, the core epistemic failure: 0 of 5 incremental offline-positive levers
  transferred (benchguard, both meta decks, search, trolley_thick). Root cause: the gauntlet opponent pool was
  our own heuristic piloting 8 different decks, a mirror match that answers "does this beat ourselves", not
  "does this beat the field". Fix in progress: the calibrated bracket ring. `docs/writeup/offline_ladder_transfer.md`.
- Measurement discipline held: machine-enforced pre-registration (`tools/loop_state.py`), the M=60 noise
  model, default-deny proxy gates, and held-out AUC filters blocked every bad ship. Six experiment failures
  settled as written-down verdicts (CEM blocked on held-out, U9b archetype gate FAIL, U11 eval-blend FAIL)
  instead of anecdotes. No regression was ever promoted to king.
- The clone autopsy (2026-07-03): the recorded conclusion "top-20 play is too subtle to imitate" was WRONG. It
  generalized an optimizer artifact. Three verified defects: (1) the trainer used a pointwise per-row log-loss
  whose zero-risk optimum IS the first-legal baseline, so both model families picked option 0 in 13019/13019
  then 11092/11092 held-out decisions; (2) the baseline policy (option position) was handed to the model as a
  feature while the gate was margin-over-that-baseline; (3) the features were semantically blind (8 regex
  tags, no card identity, no energy costs, no evolution lines, Boss's Orders invisible). Learnable structure
  sits unexploited: first-of-played-category beats first-legal by 20-27pp on every family, and END_TURN is
  never option 0 yet was the real choice 4.3% of the time. The known-good pairwise ranking objective (U26
  spike) was rerun on the clone data (2026-07-04, U92 step 0): same collapse, see 4B's
  clone_imitation_beats_first_legal entry. `analysis/clone_quality.md`, `analysis/unit_zero_spike.md`,
  and the comprehension track directive in `LOOP_BRIEF.md`.
- Target selection failure: the loop spent ~2 days (roughly 37 consecutive commits) improving `agent_search`,
  which does not ship, after the disqualifying fact was already written into the brief. Corrected by the
  two-track split. This is the largest single process mistake and it was an orchestration error, not a loop
  error.
- Operational reliability: the tmux server died silently more than once (a 12.4h overnight gap, ~28% total
  downtime), and a decisively-lost deck candidate held a scarce scored slot for ~21h while a better build sat
  staged behind it. Fixes: an OS-level scheduled-task watchdog (`watchdog_check.sh`, survives tmux-server
  death) and a settle-the-instant-it-is-out-of-band rule.
- Planning economy: 9 plan docs in 4 days, some abandoned within 2-6 hours; the unified plan's ladder-
  execution units got 0/11 execution before being superseded. Fix: a plan freeze until the next weekly review.
  Narrow, offline plans by contrast executed at or near 100%.
- U94 (2026-07-04): the comprehension track's writeup chapter (`docs/writeup/comprehension.md`) closes the
  loop the autopsy opened: a wrong recorded verdict, the two real mining bugs that caused it, the two-gated
  playbook claims it enabled, the one shipped lever those claims produced, and the final pairwise-RankNet
  kill test that closed the original clone question for good. Its 18-row claims ledger is machine-audited,
  not just written: `tests/test_comprehension_writeup.py` parses the table and asserts every cited source
  path exists on disk, so a future rename or deletion of an analysis file fails a test instead of leaving a
  dangling claim in the writeup.
- Noise recalibration (2026-07-04, `LOOP_BRIEF.md` L9 correction): the observed same-build ladder spread is
  wider than previously modeled, ~452 to 691 on a single king ref (54282104) across its own resubmissions, not
  the ~90-130 the U22 noise model assumed. M=60 is too tight to settle a single-read ladder A/B against that
  spread. Consequence: the recorded `heuristic+trolley-ability` WIN (561.1 vs a 494.8 low king draw, +66.3pp,
  Section 4C) is reclassified as a NOISE ARTIFACT, not a confirmed lever; 561.1 sits mid-range of the king's
  own 452-691 reads. New standing rules: (a) the calibrated bracket ring (tau 0.857) is now the lever DECISION
  gate, not single-read ladder A/Bs; (b) the ability build (ring +20pp) is kept as the scored floor on ring
  evidence, not ladder evidence; (c) stop spending scored slots to confirm sub-band levers (the attack_first
  slots were noise-chasing in hindsight); (d) ladder submissions are now for floor maintenance and the
  2026-08-10/16 endgame variance-harvest campaign only, which becomes the primary rank lever since the noise
  band exceeds any offline build gain available. This does not overturn the ring-gated offline verdicts
  themselves (ability +20pp, attack_first +10pp both still stand as ring evidence); it overturns treating the
  ladder board reading as able to confirm or refute them at n=1.
- Archetype-registry shadowing bug fixed (2026-07-04): `classify_family` broke coverage ties alphabetically,
  and `tools/bracket_decks.py`'s harvested `bracket_N` decks sat in the same signature dict as the named
  meta families. Two of the six harvested bracket decks turn out byte-identical, by signature, to a named
  family (`bracket_4` == `meta_archaludon`, `bracket_1` == `meta_grimmsnarl_tonakaiiii`), and "bracket_"
  sorts before "meta_", so every deck matching that signature silently classified as the bracket name
  instead, making the two named meta families permanently unminable whenever `--decks-dir decks` was used
  (0 appearances, not an error). Fixed by preferring a non-bracket name on exact ties
  (`analysis/expert_cohort.py`). Confirmed on the real 2026-06-30 dataset (400-episode slice): `meta_archaludon`
  and `meta_grimmsnarl` went from 0 to 219 and 13 real episode counts. Bracket decks with no duplicate
  signature (`bracket_2/3/5/6`) are unaffected.
- Noise model bumped to v2 (2026-07-04, board-check iteration): a routine TRACK L board check found the
  plain king-copy revert (ref 54315565) had drifted to a new low of 396.7, below the ~452 floor the L9
  correction had already widened to. Pooling every byte-identical `heuristic+trolley` board reading across
  its full resubmission history (refs 54215558/54252006/54281812/54282104/54315565, each re-read multiple
  times as the ladder keeps replaying the same submitted agent over subsequent days) gives an observed range
  of 396.7 to 691.5, a ~295-point spread. Separately, `state/current.md`'s own machine-readable `noise_model`
  JSON block had never actually been updated by the L9 correction: it still asserted v1 (`margin_M: 60`, the
  stale ~30pt basis) even while the same file's `shadow_king`/`in_flight` prose already described the
  recalibration, so the file's own source of truth contradicted its own narrative. Fixed both: `noise_model`
  is now v2 (`margin_M: 150`, basis text citing the pooled 396.7-691.5 range) and `tools/loop_state.py`'s
  `DEFAULT_MARGIN` constant (the fallback for any future pre-registration's ladder-side margin) moved from
  60 to 150 to match, with its docstring rewritten to cite the real evidence instead of the falsified v1
  basis. This does not retroactively change any already-settled pre-registration (each row carries its own
  hardcoded margin); it only fixes the record and sets a sane default for whatever ladder-side margin a
  future pre-registration might still want, given the ring is now the actual decision gate per L9.
- Age-stratified noise model refit (P4, 2026-07-06): per the P4 directive ("re-derive the true king estimate
  from AGED reads before Aug 10-16 lock decision"), stratified 77 ledger reads by age (<48h fresh vs 48-72h
  mature vs >72h aged, using timestamps from board-check notes). Fresh reads are depressed vs aged: trolley
  422.2 (fresh, n=1) vs 600.0 (aged, n=1), diff -177.8pp; trolley-ability 563.8 (fresh, n=1) vs 570.9
  (mature 48-72h fallback, n=29), diff -7.1pp. Aged sample is tiny (n=1-2), so aged-king-estimate falls back
  to mature (48-72h) for trolley-ability. Recomputed M from mature pooled stats (n=57, stdev=31.2, max_residual
  100.8): M=110 (vs current M=240). The tighter 48-72h band reflects the post-July-2 board-check cycle; the
  longer-term v2 pooling (M=240) included earlier spread from divergent builds and settling phases. For
  Aug 10-16 lock decision, use aged where available (trolley 600.0, locked-in), and ring-gated reconciliation
  for any paired build. Findings: (1) true king estimate is higher when we use aged reads; (2) the M=240 is a
  longer-horizon bound that survived all builds' settling; (3) fresh reads are indeed depressed vs aged,
  confirming P4 hypothesis. `analysis/noise_model_age_stratified.md`.
- Ability-lever confound re-check (2026-07-04): `LOOP_BRIEF.md` L1 had flagged, but never re-validated, that
  the offline gauntlet gate for `heuristic+trolley-ability` (+4.0pp, `analysis/ability_ab.md`) baked
  `PTCG_ABILITY` into a whole subprocess's environment, so both seats (our pilot AND every `deck:<name>`
  opponent, which is the SAME `heuristics.py` module in the SAME process) got the ability lever in the "on"
  arm, not just the pilot under test. `tools/measure_ability_isolated.py` toggles the module-global
  `_ABILITY` per seat instead of per process, making a true "only our pilot has the lever" arm measurable for
  the first time. Result across three independent runs (900 isolated-arm games total): the isolated diff_pp
  oscillates around zero (+2.5, -0.5, -1.3; mean +0.2), and so does the confounded diff_pp it was designed to
  compare against (-4.0, +5.5, -0.7; mean +0.3). Neither arm shows a stable positive effect at any sample
  size tried. Conclusion: the originally reported +4.0pp was noise-dominated at its sample size, independent
  of the mirror-match confound; it should not be read as confirming a real win-rate edge. This does not
  change the shipped shadow-king disposition (per L9 the calibrated bracket ring, not the gauntlet or the
  ladder, is the standing decision gate, and the underlying 0/554 blind-spot motivation for the lever is
  untouched), but it is a second independent instance of this project's central methodological finding: weak
  offline win-rate point estimates at n~200-300 are not trustworthy on their own, confound or no confound.
  `analysis/ability_isolated_confound_check.md`.
- Ring-side ability confound check (2026-07-04): the isolated re-check above only covered the offline
  gauntlet's +4.0pp; L9's actual standing decision gate is the calibrated bracket ring's +20.0pp
  (`analysis/ability_ring_check.md`), which was never checked for the same process-global mirror-match
  confound. Code-traced it instead of re-measuring: the ring's `clone:<family>` opponents resolve to
  `_clone_opponent` (`tools/opponents.py`), which never calls `heuristics.choose()` and so never reads
  `_ABILITY` (the flag is read in exactly one place in `agents/heuristics.py`, inside `choose()`'s
  `_resolve_ability` closure). A new regression test proves it directly
  (`tests/test_opponents.py::test_clone_opponent_ignores_ability_flag_never_reads_it`: a safe ability
  option is picked identically whether `_ABILITY` is `True` or `False`). Conclusion: the ring's +20.0pp
  was already a genuinely one-sided measurement and never needed deconfounding, unlike the gauntlet's
  +4.0pp. This closes an open question rather than reversing a verdict; the ring remains clean evidence
  for the shadow-king disposition. `analysis/ability_ring_confound_check.md`.
- Writeup staleness fix in `docs/writeup/comprehension.md` (2026-07-04, board-check iteration): the claims
  ledger row and closing paragraph still described `PTCG_ATTACK_FIRST` as "staged, not yet submitted", a
  fact that was true when U94 wrote the chapter but was superseded within the same day once the lever was
  actually submitted (refs 54304483/54304681), settled NEUTRAL via the U23 scoreboard tiebreak, and reverted
  to a king copy. Corrected both spots to state the real settled-NEUTRAL outcome and note both offline gates
  (+5.5pp gauntlet, +10.0pp ring) still stand unchanged, so the lever remains re-eligible for a future slot
  without new offline work. Same recurring pattern as the other writeup-drift findings above: a document
  correctly describes a fact at the moment it is written, then the underlying state moves on without every
  citing document being walked back over.
- Board-check "identical reading" streak explained, not just dismissed (2026-07-04): the king-copy ref
  (54315565) had read exactly 423.5 across five consecutive board checks while its sibling scored slot (the
  ability ref 54315802) kept drifting normally. Earlier board-check notes guessed this was "the leaderboard's
  re-scoring cadence running slower than our check cadence" without verifying it. Checked directly with
  `tools/scout.py episodes <ref>`: the king-copy ref's newest completed episode id is 83757916, while the
  ability ref's newest is 83762365 (about 4400 higher, i.e. meaningfully more recent on the shared, monotonic
  cross-competition episode id space). The king-copy submission has simply stopped being scheduled for new
  matches; its score is frozen because no new episodes are landing, not because of a coincidental cadence
  gap. This is the first time this project recorded episode-id freshness per tracked ref (no prior baseline
  existed to compare against), so it cannot yet say whether matchmaking is deprioritizing older submissions
  in favor of newer ones as the deadline approaches, but it gives future board-checks a concrete, checkable
  signal (compare newest episode id across checks) instead of guessing.
- CORRECTION to the above (2026-07-04, next board check after the sixth confirmation): the king-copy ref's
  newest episode id advanced again (83757916 to 83768597) and its score moved for the first time in seven
  checks (423.5 to 443.1). The "stopped being scheduled" diagnosis was right about the moment it was checked
  but wrong to generalize as a stable end state; it was a temporary scheduling gap, not a permanent one. Folded
  into `docs/writeup/offline_ladder_transfer.md` as a direct follow-on paragraph to the original finding: a
  diagnosis confirmed six times in a row can still need revising on the seventh, and the correction uses the
  same discipline (check the concrete signal again) rather than either assuming permanence or distrusting the
  original check.
- Both tracked refs frozen on the SAME check for the first time (2026-07-04): the ability-floor ref (54315802)
  and the king-copy ref (54315565) both read exactly their prior values (603.3 / 443.1) with `tools/scout.py
  episodes` confirming neither played a new game since the last check (newest episode ids unchanged for both:
  83768225 and 83768597). Every prior freeze episode affected only one ref at a time while its sibling kept
  drifting; a simultaneous freeze of both is more consistent with a temporary platform-wide scheduling lull
  than a per-submission issue, but one check is not enough to conclude that, only to flag it as a signal worth
  distinguishing from the earlier per-ref pattern on the next check.
- CONFIRMATION (2026-07-04, next board check): the simultaneous freeze above held a second consecutive time,
  same episode ids (83768225 / 83768597) and same scores (603.3 / 443.1) for both refs. Two checks in a row
  with both refs stalled at the identical episode is stronger evidence for a genuine simultaneous scheduling
  gap than a single observation, though still not proof of cause; will keep comparing episode ids each check
  rather than declaring this settled, per the same discipline the overturned single-ref diagnosis above taught.
- THIRD CONSECUTIVE CONFIRMATION (2026-07-04, next board check again): the same simultaneous freeze held a
  third time in a row, still the exact same episode ids (83768225 / 83768597) and the exact same scores
  (603.3 / 443.1) for both tracked refs. This crosses the threshold the prior two entries set for treating it
  as a standalone methodological finding rather than an ongoing watch item: three checks, spread across
  however many hours of real wall-clock time separate them, with neither submission scheduled for a single
  new game, points at an account-or-platform-wide scheduling gap rather than anything about either submission
  itself (a per-submission cause would be a striking coincidence to hit both refs at once three times running).
  This does not change any lever decision (the calibrated bracket ring stays the decision gate per L9, not
  ladder reads) and does not move either score outside the 396.7-691.5 pooled noise range, so no noise-model
  refit is triggered. The actionable takeaway for future board-checks: a long simultaneous freeze is
  consistent with normal scoring-platform behavior near a competition's slower period and is not, by itself,
  evidence anything is wrong with the submitted builds; keep checking episode ids each time, but stop treating
  each additional simultaneous-freeze confirmation as newsworthy on its own once the pattern is this
  established, and instead watch for the freeze breaking (either ref's newest episode id advancing again).
- Writeup drift caught before it went stale for long (2026-07-04): `docs/writeup/genome_tuning.md` still
  described condition (c) (a genome region with a measured non-flat held-out gradient) as a standing open
  question, even though it had already been directly checked and closed the same day (`2caccac`,
  `analysis/cem_gradient_condition_c.md`): the genome IS non-flat (max per-dim delta 0.2738), but every
  load-bearing dim's shipped default already sits at or above both of its own bound readings, so no
  single-axis move beats the current default anywhere in the 18-dim space. The commit that closed the
  condition touched `findings.md` and `state/*` but not the writeup file, the same "correct when written,
  not walked back over" pattern as the earlier writeup-drift findings in this section. Fixed by adding a
  dedicated subsection to the writeup rather than editing the stale sentence in place, so the record shows
  the open-then-closed arc instead of erasing the original framing.
- Writeup-drift audit run clean (2026-07-04): following up on the genome_tuning.md drift catch above, this
  iteration audited `docs/writeup/learned_evaluator.md` and `docs/writeup/comprehension.md` against the
  latest `findings.md`/`state/current.md` entries (L9 noise recalibration, attack_first NEUTRAL settlement).
  Both were already current: comprehension.md's bottom line already frames the attack_first NEUTRAL correctly
  as low-confidence rather than a refutation, and learned_evaluator.md makes no ladder-state claims that could
  go stale in the first place. No edit made. Worth recording because a drift-audit habit only earns trust if
  it also reports clean passes, not just the one time it found something.
- A self-issued "ring v2" directive was wrong and got caught before any wasted rebuild (2026-07-05):
  after diagnosing a Haiku escalation over U39 step 2, an earlier LOOP_BRIEF note concluded the
  calibrated ring needed rebuilding because it was "calibrated only on same-deck trolley builds." That
  claim was never checked against `analysis/ring_calibration.md` before being written, and it was
  false: the ring's six-build calibration set already includes two deck-changed builds
  (meta_archaludon, meta_grimmsnarl) and correctly ranked both near the bottom. Caught before any
  duplicate ring was built, by re-reading the calibration doc directly rather than trusting the prior
  turn's own summary of it. The real gap (no new deck had ever been SCORED through the existing ring)
  was then executed instead, producing the candidate_yushin_ito finding above. Recorded because
  cross-checking one's own prior directives against the source document, not just against memory of
  it, is exactly the discipline this project's other findings depend on.
- Blindspot audit, 15-agent adversarially-verified (2026-07-06): six parallel evidence readers (own losses,
  top-player learning, pilot capability, lever inventory, data utilization, deck ceiling) fed a completeness
  critic whose 8 proposed missing-levers each got an independent refutation pass against state/hypotheses.md
  and findings.md 4B/4C. Four were KILLED as already tried and closed (move-level blunder mining as proposed,
  deck-space basics/energy sweeps, shipping the four mined decision gaps, re-adjudicating evicted builds by
  resubmission), demonstrating the refutation pass earns its cost: half of what looked missing was actually
  done. Four survived and became LOOP_BRIEF P8 directives U104-U107 plus governance fix U108. The audit's
  three structural conclusions: (1) the pilot's biggest capability hole is threat/prize blindness
  (agents/heuristics.py has zero non-comment prize reads, never reads the opponent bench, and retreats only
  on own HP fraction, so it plays identically at 5-0 up and 0-5 down) while the needed obs fields are proven
  available at match time (search/endgame.py reads them without cg); (2) the loss-bucket narrative driving
  effort allocation ("67% early_collapse, nothing play-addressable") rests on a cumulative replay pool that
  mixes every retired build, decompositions of only 5-17 losses, and no loss-mode measurement of the current
  shadow-king at all; (3) two past evictions violated the project's own noise model (trolley_thick evicted on
  a -112.3 read described as "far exceeds" M=240 when it is inside the band; attack_first reverted on a
  NEUTRAL decided at 3 decisive episodes), so ring-positive levers were discarded by an instrument the
  project itself proved cannot resolve them. Sub-band ladder reads can never evict a ring-positive build
  going forward. `LOOP_BRIEF.md` P8, audit transcript in the session workflow record.
- U108 settlement arithmetic governance fix (2026-07-06): recorded two methodological corrections. (1) trolley_thick settled on ladder at 446 vs king 558 (diff -112.3), which is INSIDE the M=240 band, not a LOSS threshold (LOSS is king - 240 or below, i.e., 318 or below). The build was logged as evicted when the pre-registered filter says BAND settle to a repeat resubmission, then U23 scoreboard; the recorded protocol action (evict) was not the pre-registered filter. Going forward, a ladder read inside the band margin can never evict a ring-positive build (ring evidence is the sole eviction authority per L9). (2) attack_first settled NEUTRAL via the pre-registered U23 scoreboard tiebreak, not a confirmed LOSS: only 3 candidate decisive shared-bracket episodes vs the required N=30 confidence bar, confidence 0.171 vs required 0.90. The NEUTRAL verdict is correct (per the pre-registered action for a scoreboard below threshold), but the settlement record itself is in a two-ref small-sample regime where the lever stays re-eligible for future testing without new offline work. Both cases are recorded in `state/current.md` governance note and pre-registration filters to prevent recurrence. `analysis/attack_first_settlement.md`, `state/current.md`.

---

## 5. Key pivots and decisions (dated)

- 2026-07-01: reframe search from "the player" to "an offline teacher" after the 514.7 vs 569.6 fact.
- 2026-07-02: pivot the loop to the learned-evaluator/search track (later found mis-aimed).
- 2026-07-03: two-track split (ladder vs Strategy) after the value audit; make the ladder track own the
  shipped agent.
- 2026-07-03: reopen "understand the top 20" as a first-class comprehension track after the autopsy reversed
  the "too subtle" verdict.
- Standing decisions: one loop only (rank is quota/slot/noise-bound, parallel loops cannot buy rank); the
  bracket ring is the only calibrated gate; the Aug 10-16 endgame noise campaign is booked.
- 2026-07-04: the episode-freshness staleness diagnosis (4D) reconfirmed stable across six consecutive
  board checks (frozen ref's newest episode id never advances while its sibling keeps climbing); folded into
  docs/writeup/offline_ladder_transfer.md as a small measurement-discipline paragraph alongside the noise-
  model correction story, since both are instances of verifying a repeated explanation instead of repeating it.
- 2026-07-04 (follow-up): the king-copy ref (54315565) that had "resumed play" after its first six-check
  freeze went on to freeze AGAIN, for seven more consecutive checks at 443.1, longer than the original gap.
  Its sibling scored ref (the ability floor, 54315802) broke its own six-check freeze in the same iteration
  the king-copy ref's second freeze was still holding, so the two refs' quiet periods are decoupled, not one
  shared event. Folded into docs/writeup/offline_ladder_transfer.md as a further caveat: a resolved-scheduling
  diagnosis is only true at the moment it is checked, not permanent immunity to re-freezing.
- 2026-07-04: `tools/refit_noise_model.py` built and run against the full ledger (57 pooled same-build reads
  across two families) instead of continuing to eyeball a min/max range every board check. Result: M=150 (v2)
  was itself undersized, since the worst observed residual (235.1, on `heuristic+trolley`'s own mean) exceeds
  it; recommended M=240 (v3, larger of a 2-sigma bound and the worst residual). Applied to
  `state/current.md`'s noise_model block and `tools/loop_state.py`'s `DEFAULT_MARGIN`
  (analysis/noise_model_refit.md). This is the endgame campaign's named prep step ("refit the noise model on
  all accumulated same-build reads"), done early while board-check iterations keep supplying data, rather
  than left until 2026-08-10.
- 2026-07-04: `tools/endgame_stopping.py` built to operationalize U48's final-pair optimal-stopping design
  (docs/plans/2026-07-02-001-feat-unified-number-one-plan.md Phase 4) ahead of the Aug 10-16 window, the same
  early-prep pattern as the noise-model refit above. It reuses `refit_noise_model.py`'s own family stats to
  turn "king-true-estimate" into a real number (the shadow-king build's pooled same-build mean, currently
  569.7 over n=28 reads) and computes stop_target = mean + bonus (609.7 at bonus=40), written into
  `state/current.md`'s new `endgame_campaign` block along with the pair rule, no-roll buffer, and lock date.
  Satisfies U48's own verification requirement ("stop target and pair rule in state/current.md before the
  first re-roll") more than a month before the campaign can start, so the August iterations only need to
  re-run the tool for a fresh mean, not design the rule from scratch under deadline pressure.

---

## 6. Current state and open direction (2026-07-04)

- CORRECTED 2026-07-04 (noise recalibration, see 4D): the "ability WIN" (561.1 vs 494.8) is now understood as
  a noise artifact, not a confirmed ladder result, given the king's own 452-691 same-build read spread. The
  ring-gate result (ability +20pp on the calibrated bracket ring) still stands and is the reason the ability
  build is kept as the scored floor going forward, not the single ladder read.
- The comprehension track (U90-U94) is fully shipped. Its other candidate, attack-first, SETTLED NEUTRAL on
  the ladder at n=1 read (both offline gates passed, +5.5pp gauntlet / +10.0pp ring); per the noise
  recalibration this NEUTRAL read is itself low-confidence evidence, not a refutation of the ring-gated
  offline result. A plain king-copy revert for that slot was submitted 2026-07-04 (ref 54315565, settled
  COMPLETE 476.1) before the recalibration correction landed. FLOOR RESTORED 2026-07-04: the resubmitted
  ability build (ref 54315802, same tarball as 54282097) into that slot cleared PENDING this iteration at
  SubmissionStatus.COMPLETE 600.0, confirming the ring-preferred build now occupies the scored slot instead of
  a plain king copy; this was floor maintenance, not a fresh ladder A/B, and carried no new pre-registration.
  The CEM/genome-tuning line is closed on all three re-test conditions (Section 4B). No further TRACK L unit
  is defined without a plan review (freeze through 2026-08-16); ladder submissions are now for floor
  maintenance and the 2026-08-10/16 endgame variance-harvest campaign only. TRACK L now HOLDS: no further
  submission is planned until the board drifts off the ring-preferred build or the endgame campaign opens.
- Writeup sync 2026-07-04: `docs/writeup/offline_ladder_transfer.md` still described the ability lever's
  ladder read as an unqualified WIN that "the ring, the gauntlet, and the ladder all agreed" on, and gave the
  noise band as the stale ~90-130pt estimate with M=60 presented as sized correctly against it. Both were
  stale claims once the L9 noise recalibration landed (see 4D); corrected the WIN paragraph to note it is now
  read as a mid-band noise artifact, and rewrote the noise-model section to report the ~452-691pt corrected
  band, the M=60 undersizing, and the resulting hand-off of decision authority to the calibrated ring, as an
  explicit in-the-open correction rather than a quiet patch.
- TRACK S: the offline ML stack and the writeup, assembled continuously; this is now the default per-iteration
  action whenever TRACK L has no build awaiting a slot.
- Age-stratified refit (2026-07-05, U4 Item 1): P4 hypothesis (aged reads more accurate than fresh) contradicted by data. Fresh trolley-king reads (437.2, n=29) run LOWER than aged (600.0, n=1), opposite direction; using aged-only estimate was premature. Impact: refit uses pooled estimate (456.4, n=57) as baseline, not aged-only. This reinforces the central finding: same-build noise band (~452-691) is much wider than build-level deltas, so ladder reads at n~30 per arm are not trustworthy for deciding between builds on their own; the calibrated bracket ring (ring test, not ladder points) is the decision gate. (analysis/noise_model_age_stratified.md)
- U100 rules-as-implemented completion (2026-07-06): all 21 game mechanics verified with real game stepping via cg.api engine state extraction. Tests moved from trivial structural checks (e.g. "state exists") to measured real values: damage deltas on attacks, energy counts across turns, prize flow patterns, status flag transitions, evolution detection. The harness can now (1) drive real game states, (2) measure specific mechanic behaviors at each step, (3) verify the engine enforces rules correctly. Unblocks U101 (invariant fuzzer for glitch detection), U102 (card-text divergence audit), U103 (mirror-deck skill benchmark). (tests/test_engine_mechanics.py, docs/rules_as_implemented.md)
- Governance violations and settlement arithmetic fix (U108, 2026-07-06): two past evictions violated the project's own noise model, discovered upon L9's noise recalibration. (1) trolley_thick evicted 2026-07-03 on a -112.3pp ladder read (446.2 vs reclaim-king 558.5): Under the M=240 noise model, a read is BAND if it sits within ±240 of the king. −112.3pp is well inside this band, making this a BAND verdict that required one repeat resubmission + U23 scoreboard settlement before any eviction, not an immediate eviction. Incorrect decision rule applied. (2) attack_first reverted 2026-07-04 on a NEUTRAL verdict decided from only 3 decisive episodes in the U23 scoreboard tiebreak (3 shared bracket episodes out of 6 candidate and 6 king comparisons, yielding n_decisive=3 and confidence=0.171): The M=240 band rule extends to settlement verdicts: a NEUTRAL decided with weak confidence (n<30 decisive) should trigger re-read before eviction, not immediate revert. Instead, slot was immediately reverted to a king copy. Both violations: the project's own pre-registered M=240 band rule (BAND reads require repeat+scoreboard, not eviction) was overridden by implicit tighter thresholds not in any decision rule. Standing correction (P8 POSTURE INVERSION): a ladder read inside the M band can NEVER evict a ring-positive build; ring evidence is the only eviction authority. trolley_thick's offline collapse fix (-15.4pp empty-bench, 55% head-to-head win rate in analysis/collapse_rate_thick_deck.md) is marked for ring-gate re-eligibility if a future ladder slot opens. Corrected state/current.md prose (state/current.md trolley_thick ledger row, superseded_2026_07_05 JSON note).
- Honest outlook: #1 is off the table. Realistic ladder landing with the fixes is the median band
  (~600-700 score, roughly #1500-2200 from ~#2980). The Strategy prize is the stronger bet: the differentiated
  story is the pre-registration machinery, the quantified noise model, the offline-to-ladder transfer record
  (three named proxy failures, then two real levers reaching WIN and NEUTRAL verdicts), and the self-caught
  clone-autopsy reversal.

---

## 7. Source index (for the report)

- Falsification registry: `state/hypotheses.md`. Live ledger and noise model: `state/current.md`.
- Per-finding analyses: `analysis/*.md` (indexed by first heading; see the win/loss study, the ability gap,
  the ring calibration, the transfer record, the clone autopsy inputs).
- Intent evolution: `docs/plans/*.md` (9 plans, 2026-06-30 to 2026-07-03) show what we believed at each step.
- Strategy writeup drafts: `docs/writeup/` (learned_evaluator, offline_ladder_transfer, genome_tuning, and
  comprehension, all four now written; comprehension shipped 2026-07-04 with U94's machine-audited claims
  ledger).
- The audits that produced the meta-findings ran as ephemeral multi-agent workflows this session (loop-value
  audit, engagement report card, clone-failure autopsy). Their conclusions are captured above; if a fuller
  transcript is wanted for the report, they can be re-run.

**Queue item 4: Deck candidate exploration (U39), 2026-07-05 (ESCALATED, CORRECTED 2026-07-06)**. Mined dataset produced 6 candidate decks. Scored through calibrated bracket ring (tau 0.857, n=20 each): candidate_yushin_ito ring +0.100pp vs trolley baseline (ring 90.0% vs 80.0%), stable delta across three independent runs (n=20/40/40, analysis/candidate_decks_ring_gate.md). Submitted ref 54365656 to ladder after error resolution (refs 54362805 ERROR, 54365656 COMPLETE 651.9, drifted to 732.1). Ladder read: candidate settled 496.4 rating / 47.1% win rate (41 fresh episodes) vs trolley revert 520.5 rating / 46.2% win rate (42 fresh episodes), a 24.1-point rating gap. CORRECTION (2026-07-06): that rating gap was originally written up as "the strongest ring-to-ladder transfer failure to date." Checked against the underlying win rates it is not: 47.1% vs 46.2% is a 0.9pp difference, z ~ 0.08 on a pooled two-proportion test, smaller than the ~2.4pp swing a single flipped game produces in a 41-game sample. There is no confirmed transfer failure here, only an inconclusive small-sample ladder read that happened to look dramatic in rating points. This is itself an instance of the exact mistake the M=240 noise recalibration exists to prevent (reading a within-noise rating delta as a real result), caught the same way the earlier "ability WIN was actually noise" finding was caught. The correct conclusion, which still holds: L9 recalibration (2026-07-05) makes the bracket ring the primary decision gate and treats ladder single-reads as too noisy to confirm or refute a ring finding either way; candidate remains ring-promoted and is eligible for future resubmission with a larger episode sample if a real ladder confirmation is wanted. Floor restoration attempt (ref 54366402/54366910 ERROR, 54367075 COMPLETE 442.8) landed to hold the ring-best ability build. (analysis/candidate_decks_ring_gate.md, state/current.md L9 protocol, docs/writeup/offline_ladder_transfer.md section on ring-to-ladder transfer, Attempt 4 corrected 2026-07-06)
- U101 invariant fuzzer campaign (2026-07-06, CRITICAL FINDING): ran tools/invariant_fuzzer.py on 200 fresh games (seed 42, not replay-loaded). All four non-conservation checks passed (HP bounds 0/200, prize bounds 0/200, turn alternation 0/200, energy flags 0/200). Card conservation check: 193/200 violations (96.5%). Pattern is systematic and invariant: Player 0 +6 cards (66 total, expected 60), Player 1 -1 card (59 total, expected 60), net -7 total across both players. Breakdown at game-init: deck+hand+discard+active+bench+prize+tools+energyCards. Fresh-game violations rule out replay-load artifacts as root cause. Likely causes: (a) missing zone in the counting (select.deck, preEvolution, stadium, supporter) - check cg.api observation schema, (b) energy cards miscounted (double-counting or wrong field), (c) systematic engine behavior at init that violates the 60-card invariant. NEXT: inspect cg.api.Observation structure to find missing zones; rerun fuzzer with detailed logging per-card-type to isolate which cards are missing. (analysis/engine_quirks.md, tools/invariant_fuzzer.py)
- U104 stacked ring run (2026-07-06, GATE FAIL): measured three-arm factorized ring run (tools/stacked_ring_run.py) against calibrated bracket ring (tau 0.857). Arm 1 (trolley+ability baseline): 31 wins, win_rate 0.775. Arm 2 (yushin+ability): 30 wins, win_rate 0.75. Arm 3 (yushin+ability+attack_first): 34 wins, win_rate 0.85. Diff_pp (arm 3 minus arm 1) = 7.5pp. Gate requires diff_pp > 10pp for promotion; 7.5pp is FAIL. Result: yushin+ability+attack_first does not beat trolley+ability by sufficient margin in ring measurement. Does not promote to P3 lock-the-strongest-pair selection. The 7.5pp measurement double-checks the recent yushin vs trolley contest (yushin had three +0.100 reads and one +0.050 read, all on deck-specific rings): this fresh ring run puts the delta lower (~7.5pp) and below the promotion threshold. Verdict stands: trolley remains the baseline candidate for the endgame campaign unless a future deck candidate exceeds trolley's ring performance. (analysis/u104_stacked_ring_run.json)
