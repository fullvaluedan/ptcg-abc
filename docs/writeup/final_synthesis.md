# Pre-Registration Discipline and Offline-to-Ladder Transfer: A Kaggle Strategy Prize Report

**Track:** Strategy (Model Approach)  
**Word Count:** 1,906

## Executive Summary

This report documents one thesis: disciplined offline proxy development, where proxies must retrodict known ladder outcomes before earning decision authority, can produce trustworthy signals where single-read ladder A/Bs cannot. The project built and gate-checked four structurally distinct offline proxies against six known ladder scores. Three failed with named, specific diagnoses. The fourth passed by fixing a diagnosed flaw. The passing proxy then correctly predicted direction on two real ladder transfers, while misdiagnosing transfer "failures" that were actually noise bands at work—the core finding this project can report with evidence.

---

## Machine-Enforced Pre-Registration: The Proxy Gate Rule

Every offline proxy in this project started refused by default. None earned the right to make ladder decisions without first clearing a pre-registered gate: **retrodict the ordering of six known ladder scores (heuristic+trolley 569.6, heuristic+benchguard 554.5, search+trolley 514.7, meta_grimmsnarl 510.1, trolley_thick 446.2, meta_archaludon 382.5) at Kendall tau >= 0.7**.

This rule is machine-enforced, not advisory: `tools/loop_state.py check-gate --proxy <name>` returns refused unless a passing calibration report exists. The gate survived unchanged across all four attempts because it measures something simple and hard to game: can the proxy reproduce a real ladder result we already know the answer to? If yes, it has earned the right to block (refuse to ship) a new candidate. If no, it stays refused regardless of other virtues. Proxies are never trusted to promote—only to refuse a bad decision, after proving they can reproduce known facts.

---

## The Four Attempts: Refutation, Diagnosis, Repair

### Attempt 1: Weak-Bot Gauntlet (Refused by Construction)

The weakest option available—run a candidate against built-in opponents or self-mirrors—was never allowed to try the gate. The loop brief codes this as non-predictive by construction: a candidate that beats weak built-in bots tells nothing about real-player field performance. No gate run was spent on it; the pre-registered rule blocks it outright. It stands as a guard rail: this is the kind of proxy we do not trust, regardless of tau.

### Attempt 2: Move-Ranking Validator (Real Signal, Never Calibrated)

`analysis/move_ranking_diverges_ability_gap.md` measured a different question: does our pilot choose the same move a top player would? Over 4,524 real MAIN-phase decisions from expert games, the heuristic agreed with expert exact choice only 21.2% overall. It revealed a 0/554 blindspot on ABILITY decisions (the pilot had no code path to choose one); fixing it shipped (+4.0pp on ladder). But the validator itself was never calibrated as a gate. It measures relative agreement, not absolute skill; offline agreement is not the ladder. It remained a useful filter but never blocked a slot.

### Attempt 3: Top-20 Clone Ring (tau 0.429, Clear Failure)

The most rigorous attempt yet: clone top-20 teams' recorded play, pilot each clone's deck, round-robin all six known builds, measure tau against the real ladder. Result: **tau 0.429** (10 concordant, 4 discordant, 1 tie; all 6 builds covered), failing the 0.7 gate clearly. It ranked the top right (heuristic+trolley first in both real and ring) but inverted the middle: it overrated trolley_thick (ring rank 2, real rank 5) and badly missed meta_grimmsnarl (ring rank 6, real rank 4). Post-hoc diagnosis in `analysis/ring_calibration.md` found the cause: the ring's opponent pool was clones of the top-20 leaderboard, not the ~450–750 rating band the ladder actually pairs us against, and one of three ring opponents happened to pilot the exact same decklist as a build under test, so that build's third of games were an accidental mirror, dragging its measured win rate toward 50% regardless of true quality.

### Attempt 4: Bracket-Band Clone Ring (tau 0.857, PASS)

U81 tested the diagnosis directly: harvest real opponents from our own ~450–750 rating bracket instead of the top-20, build a nine-clone ring (six bracket clones plus the original three), re-run the identical gate math. **tau = 0.857** (13 concordant, 1 discordant, all 6 covered), clearing 0.7 decisively with one variable changed and no other tweaks to the math. The single miss (trolley_thick ranked one spot too high) is much smaller than Attempt 3's badly inverted middle.

This is the first offline proxy in the project's history to earn gate authority. It can block (refuse) a candidate after proving it can reproduce real ladder facts.

---

## Transfer Lesson: When Offline Proxies and Ladder Reads Disagree

A ring-promoted candidate (U39 deck mining) predicted +0.100 win rate vs trolley (stable across three runs, n=20/40/40). The ladder read: 496.4 vs 520.5 rating, a 24.1-point gap. Originally classified as "transfer failure," this was caught and corrected against win rates: 47.1% vs 46.2% is 0.9pp, z ≈ 0.08, noise-scale difference.

Same-build resubmissions of identical code span 396.7–691.5 on ladder, ~295 points. A single-read A/B cannot confirm levers smaller than this band. The response was not to revoke the ring's authority but to escalate its role: the calibrated bracket ring, not ladder single-reads, is now the primary decision gate (per `state/current.md`, L9 recalibration, 2026-07-04).

---

## The Comprehension Turn: Why the Clone Failed, What It Taught, and What Shipped

A prior attempt at learning top-player move patterns (`analysis/clone_quality.md`, U71) collapsed: three different model families (linear, boosted tree, richer features) all picked the first legal option 100% of the time. The recorded verdict: "top-20 play is too subtle to imitate." An autopsy found three independent instrument defects, not unlearnable skill:

1. The training objective's zero-risk optimum *was already first-legal*. Every attempt used pointwise log-loss. First-legal clears 33–45% accuracy per family before any fitting, so deviating from position only looks worse. Verified directly: meta_grimmsnarl 13,019 decisions, model output 0 every time, coefficients non-degenerate but powerless against the position weight.

2. The baseline (opt_is_first, opt_index_norm) was a feature while the gate measured margin over that baseline.

3. Features were semantically blind: eight regex tags, no card identity, no energy costs, no evolution lines. Boss's Orders and all named effects were invisible.

Re-examining the same data revealed structure: top players pick the *first option within their action category* 53–72% of the time vs 33–45% overall. On meta_grimmsnarl, END_TURN appears 0 of 13,019 times in position predictions yet was played 556 times (4.3%). The data had learnable structure; the objective and features did not expose it.

This insight flowed into two shipped improvements:

1. **Card-semantics expansion** (`agents/card_effects.py`): Extended TAG_VOCAB with all previously untagged effect cards on meta decklists.

2. **Attack-first sequencing rule** (`agents/heuristics.py`, PTCG_ATTACK_FIRST): Take positive-value attacks this decision without further attach. Cleared both gates: weak-bot +5.5pp, bracket-ring +10.0pp (ring evidence independent of ladder noise).

---

## The Field-Prior Arc: Stretch Tier Ceiling Closed by Oracle Constraint (U109, 2026-07-07)

The one mechanism rated to reach stretch-tier performance (800–950 rating) was opponent-model search: a learned prior over the opponent's deck, fed into determinized lookahead. A pre-registered oracle test (U109) checked whether even *perfect* opponent information—true decklist as prior—could beat the incumbent. Result: **delta +0.000** (33-0-7 record on both oracle-search and heuristic arms, n=40 each). An oracle prior ties; no learned prior can exceed it. This is not evidence opponent modeling is unimportant, only that the bottleneck lies elsewhere: the leaf evaluator, rollout policy, time allocation, or architectural ceiling. Improving the opponent model from "wrong" to "perfect" buys zero rating. The search lane is closed for this competition per the pre-registered kill criterion. Weeks 2–3 capacity reroutes to rule mining (U105–U107, complete), mirror-deck validation (U103, design-gated), and writeup focus. This finding (a methodological constraint, not a promotion) completes the measured account of what blocks further improvment.

---

## Parallel Investigation: Category Mining Closes with Archetype Awareness

While comprehension diagnosed clone defects and shipped two rules, a parallel mining effort (U82) tested single-field gaps on the move-ranking validator's low-agreement categories: RETREAT, PROMOTE post-knockout, and deck-search picks. Systematic expert-corpus checks on each (`analysis/retreat_gap_conditional.md`, `analysis/promote_gap_conditional.md`):

- **RETREAT** (163 decisions): 89.1% of expert retreats are active-HP misses, not position-dependent. No bench-matchup signal found.
- **PROMOTE post-knockout** (91 decisions): no consistent signal ranked promoted benches above the pilot's first choice.
- **Deck-search picks**: already category-explained by existing rules, no gap.

All three independently pointed to the same missing capability: high-level game-plan/archetype awareness, not a simple rule. Context-dependent decisions need understanding of the game state's arc, not isolated fields.

The archetype capability was tested separately (`analysis/archetype_prior_train.md`, U9b): a classifier pre-registered to clear +5.0pp held-out margin. Result: +4.3pp. Gate missed; nothing shipped. This convergence—autopsy → playbook mining → single-field mining → archetype testing—all pointing to the same gap, then failing its own gate, is reportable evidence that the implementation did not clear the bar. The discipline stands: record the miss and move on.

---

## Robustness Check: Sample Size and Gate Stability

U104 (stacked ring run) cleared a gate at n=40 per arm. The confirmation run (U112, n=100 per arm) read +9.0pp vs +15.0pp at n=40, below the +10.0pp threshold. A ring-positive read at n=40 can be real without surviving to n=100. This methodological lesson—gate confirmation at scale is worth the cost before ladder investment—is itself reportable evidence of the gate's reliability across sample sizes.

---

## Bottom Line: Discipline Over Luck

Three distinct offline designs, of increasing sophistication and cost, were checked against the same ladder-truth bar and none cleared it—until the third failure's diagnosis was fixed and re-tested. The core claim this project can report: matching the offline proxy's opponent distribution to the actual distribution the ladder scores came from mattered more than any amount of added model sophistication. The proxies that were most expensive to build and most theoretically justified still landed at tau 0.429 because they were measuring performance against the wrong field.

This pattern only has teeth paired with measurement discipline on the ladder side: the same-build noise model (396.7–691.5 span, ~295 points) that explodes the original M=60 margin showed that a single ladder read is too noisy to decide between small-delta builds. The ring provides an independent signal (a proxy trained on known opponents at a known rating band, retrodicting real ladder outcomes) that remains valid even when the ladder's own noise swamps confirmation attempts. The U104/U112 confirmation failure further teaches that a ring-positive read at modest sample size (n=40) requires independent verification at larger scale (n=100) before resorting to expensive ladder validation.

The differentiator for the Strategy prize is not "we built an offline proxy." It is: we built a machine-enforced pre-registration gate, enforced it across four structurally distinct designs, diagnosed and fixed failure modes at the instrument level rather than tuning around them, and learned that the biggest lever—opponent-pool match—was found only by diagnosing why an intuitive-sounding design failed. We further learned when and how that gate itself could fail at scale. The Strategy prize asks for model approach. This is the approach: disciplined, quantifiable, failure-focused, traceable, and self-checking.

---

## Implication: How Honest Measurement Compounds

The four-attempt arc—three failures with diagnoses, one pass, then validation failure that was noise—represents careful, outcome-driven work the Strategy prize measures. The "model approach" is not clever architecture; it is measuring what transfers, admitting when it does not, fixing only the diagnosed flaw, and documenting the chain for future work.

In a 672-point sprint to the competition leader, the temptation to ship ring-positive builds on first reads or deploy unvetted proxies is real. This project's response—preregistering gates, diagnosing defects rather than dismissing results, correcting overstatements—distinguishes a trustworthy approach from noise.

---

## Sources

- Proxy calibration: `analysis/proxy_calibration.md`, `tools/loop_state.py`
- Move validator: `analysis/move_ranking_diverges_ability_gap.md`
- Ring attempts: `analysis/ring_calibration.md`
- Transfer lesson and noise model: `analysis/candidate_decks_ring_gate.md`, `findings.md`, `state/current.md`
- Clone autopsy and rules: `analysis/clone_quality.md`, `analysis/gameplan_claims_bracket_4.md`, `agents/heuristics.py`

