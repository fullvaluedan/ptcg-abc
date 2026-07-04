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

Same-build ladder noise is the dominant force, and we under-modeled it. The byte-identical king has scored
452, 476, 494, 507, 534, 558, 600, 648, and 691 across resubmissions of the SAME code, a spread of ~240 points
(roughly 120 per side), and a single king ref (54282104) alone drifted 691 to 494 on its own re-reads. That is
WIDER than the M=60 confirmation margin the settlement protocol used, so a single-read ladder A/B cannot
confirm ANY lever we can build: every real improvement is smaller than the noise. Consequences, adopted
2026-07-04 (see 4D, noise recalibration): the calibrated bracket ring (tau 0.857), not the ladder, is the
lever DECISION gate; the recorded "ability WIN" was reclassified a noise artifact; and because 5/day +
latest-2 scoring lets us keep the luckiest draw, repeated resubmission of the best build (the Aug 10-16 endgame
variance campaign) is the PRIMARY source of rank, ahead of any build improvement. Source: `state/current.md`
noise model, `LOOP_BRIEF.md` L9, `analysis/final_scoring_semantics.md`.

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
  `analysis/cem_run_prio_pooled.md`, `analysis/cem_run_prio_teacher.md`.
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
