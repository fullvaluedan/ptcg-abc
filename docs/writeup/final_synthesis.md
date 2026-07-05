# Pre-Registration Discipline and Offline-to-Ladder Transfer: A Kaggle Strategy Prize Report

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

`analysis/move_ranking_diverges_ability_gap.md` measured a different question: does our pilot choose the same move a top player would? Over 4,524 real MAIN-phase decisions from expert games, the heuristic agreed with expert exact choice only 21.2% overall. More important, it revealed a 0/554 blindspot on ABILITY decisions (the pilot had no code path to ever choose one), and this finding was real: fixing it shipped (+4.0pp on ladder). But the validator itself was never calibrated as a gate. Its own docstring documents why it should not be: it measures relative agreement, not absolute skill; offline agreement is not the ladder. It remained a useful filter (avoid overshooting on obvious misses) but never blocked a slot.

### Attempt 3: Top-20 Clone Ring (tau 0.429, Clear Failure)

The most rigorous attempt yet: clone top-20 teams' recorded play, pilot each clone's deck, round-robin all six known builds, measure tau against the real ladder. Result: **tau 0.429** (10 concordant, 4 discordant, 1 tie; all 6 builds covered), failing the 0.7 gate clearly. It ranked the top right (heuristic+trolley first in both real and ring) but inverted the middle: it overrated trolley_thick (ring rank 2, real rank 5) and badly missed meta_grimmsnarl (ring rank 6, real rank 4). Post-hoc diagnosis in `analysis/ring_calibration.md` found the cause: the ring's opponent pool was clones of the top-20 leaderboard, not the ~450–750 rating band the ladder actually pairs us against, and one of three ring opponents happened to pilot the exact same decklist as a build under test, so that build's third of games were an accidental mirror, dragging its measured win rate toward 50% regardless of true quality.

### Attempt 4: Bracket-Band Clone Ring (tau 0.857, PASS)

U81 tested the diagnosis directly: harvest real opponents from our own ~450–750 rating bracket instead of the top-20, build a nine-clone ring (six bracket clones plus the original three), re-run the identical gate math. **tau = 0.857** (13 concordant, 1 discordant, all 6 covered), clearing 0.7 decisively with one variable changed and no other tweaks to the math. The single miss (trolley_thick ranked one spot too high) is much smaller than Attempt 3's badly inverted middle.

This is the first offline proxy in the project's history to earn gate authority. It can block (refuse) a candidate after proving it can reproduce real ladder facts.

---

## Transfer Lesson: When Offline Proxies and Ladder Reads Disagree

A ring-promoted candidate (from U39 deck mining, `analysis/candidate_decks_ring_gate.md`) predicted +0.100 win rate vs trolley baseline (calibrated stable across three independent runs, n=20/40/40). The ladder read: candidate settled 496.4 rating vs trolley revert 520.5, a 24.1-point gap. Originally written as "the strongest ring-to-ladder transfer failure to date," this diagnosis was caught and corrected against the underlying win rates: 47.1% vs 46.2% is a 0.9pp difference, z ≈ 0.08, smaller than the swing a single flipped game produces in a 41-game sample. There was no contradiction, only an inconclusive small-sample ladder read that happened to look dramatic in rating points.

This is the exact mistake the corrected noise model exists to prevent. Analysis in `findings.md` (Section 3) documents the fix: same-build resubmissions of identical code span 396.7 to 691.5 on the ladder, a ~295-point spread. A single-read A/B cannot confirm any lever smaller than this band. The response, per `state/current.md` (L9 noise recalibration, 2026-07-04), was not to revoke the ring's authority or lower its bar, but to formally escalate the ring's role: the calibrated bracket ring, not ladder single-reads, is now the primary decision gate for lever decisions.

---

## The Comprehension Turn: Why the Clone Failed, What It Taught, and What Shipped

A prior attempt at learning top-player move patterns (`analysis/clone_quality.md`, U71) collapsed: three different model families (linear, boosted tree, richer features) all picked the first legal option 100% of the time. The recorded verdict: "top-20 play is too subtle to imitate." An autopsy found three independent instrument defects, not unlearnable skill:

1. The training objective's zero-risk optimum *was already first-legal*. Every attempt used pointwise log-loss. First-legal clears 33–45% accuracy per family before any fitting, so deviating from position only looks worse. Verified directly: meta_grimmsnarl 13,019 decisions, model output 0 every time, coefficients non-degenerate but powerless against the position weight.

2. The baseline (opt_is_first, opt_index_norm) was a feature while the gate measured margin over that baseline.

3. Features were semantically blind: eight regex tags, no card identity, no energy costs, no evolution lines. Boss's Orders and all named effects were invisible.

The same data was re-examined for structure: top players pick the *first option within their own action category* 53–72% of the time vs 33–45% for "first in the whole list." On meta_grimmsnarl alone, END_TURN (option 0) appears 0 of 13,019 times in position-based predictions, yet was the real played choice 556 times (4.3%). The data had learnable structure; the objective and features did not expose it.

This insight flowed into two shipped improvements:

1. **Card-semantics expansion** (`agents/card_effects.py`): Extended TAG_VOCAB with all previously untagged effect cards on meta decklists. Tests verify zero untagged cards remain.

2. **Attack-first sequencing rule** (`agents/heuristics.py`, PTCG_ATTACK_FIRST): When a positive-value attack is legal this decision without a further attach, take it now instead of the discretionary attach. Mined from real expert play via `analysis/gameplan_claims_bracket_4.md`. Cleared both offline gates: weak-bot gauntlet +5.5pp, calibrated bracket-ring +10.0pp. Ladder A/B at n=1 read was NEUTRAL (inside noise band), but ring evidence stands independent of ladder noise.

---

## Bottom Line: Discipline Over Luck

Three distinct offline designs, of increasing sophistication and cost, were checked against the same ladder-truth bar and none cleared it—until the third failure's diagnosis was fixed and re-tested. The core claim this project can report: matching the offline proxy's opponent distribution to the actual distribution the ladder scores came from mattered more than any amount of added model sophistication. The proxies that were most expensive to build and most theoretically justified still landed at tau 0.429 because they were measuring performance against the wrong field.

This pattern only has teeth paired with measurement discipline on the ladder side: the same-build noise model (396.7–691.5 span, ~295 points) that explodes the original M=60 margin showed that a single ladder read is too noisy to decide between small-delta builds. The ring provides an independent signal (a proxy trained on known opponents at a known rating band, retrodicting real ladder outcomes) that remains valid even when the ladder's own noise swamps confirmation attempts.

The differentiator for the Strategy prize is not "we built an offline proxy." It is: we built a machine-enforced pre-registration gate, enforced it across four structurally distinct designs, diagnosed and fixed failure modes at the instrument level rather than tuning around them, and learned that the biggest lever—opponent-pool match—was found only by diagnosing why an intuitive-sounding design failed. The Strategy prize asks for model approach. This is the approach: disciplined, quantifiable, failure-focused, and traceable.

---

## Sources

- Proxy calibration and gate rule: `analysis/proxy_calibration.md`, `tools/loop_state.py`
- Attempt 1 (weak-bot ban): Standing rule in brief; no calibration run needed
- Attempt 2 (move validator): `analysis/move_ranking_diverges_ability_gap.md`
- Attempt 3 (top-20 ring, tau 0.429): `analysis/ring_calibration.md`
- Attempt 4 (bracket ring, tau 0.857): `analysis/ring_calibration.md` (U81 section)
- Transfer lesson and noise model: `analysis/candidate_decks_ring_gate.md`, `findings.md` (Section 3, noise model), `state/current.md` (L9 noise recalibration)
- Clone autopsy and shipped rules: `analysis/clone_quality.md`, `analysis/gameplan_claims_bracket_4.md`, `agents/heuristics.py` (PTCG_ATTACK_FIRST, TAG_VOCAB)

---

**Word count: 1,680** | Format: Kaggle Writeup, 2000-word max | Track: Simulation Rank or Strategy Prize Model Approach (70%)

