# Pair Pre-Registration Prep: E[max] Arithmetic for the Aug Final Pair (U10 / R7)

**Date:** 2026-07-10
**Plan:** docs/plans/2026-07-10-001-feat-improvement-push-plan.md, U10 (U116 + U117). Requirement R7.
**Purpose:** Everything Dan needs to sign the August pair-submission decision by Aug 5. This is the
arithmetic and evidence half; the minute-by-minute lock procedure is the sibling half in
docs/lock_rehearsal_checklist.md.

## TL;DR recommendation

**Submit two byte-identical copies of the ring-leading build. Do NOT hedge with a second, different
build.** There is no runner-up whose ring read overlaps the leader this round (U4 surfaced no
promotable new deck; U5 confirmed no gate got stuck), so a diverse hedge has nothing to hedge
against, and the E[max] arithmetic shows a hedge is strictly dominated by identical copies whenever
the leader's true skill is even marginally higher than the runner-up's.

- **Leader:** `heuristic+yushin+ability+threat_retreat`, ring win rate **0.910** (n=100, U2).
- **Max-of-two lift from using both slots (identical copies):** `sigma / sqrt(pi)` =
  **+20.9 rating points** over a single submission, at U7's residual sigma = 37.0
  (range **+14.7 to +26.5** across U7's 90% CI [26.0, 46.9]).
- **Best hedge alternative:** none qualifies. Every mechanically different build measured this push
  sits well below the leader on the ring (nearest different-deck read is ~9-11pp lower), so no ring
  CI overlaps the leader.
- **Open item (DAN-1 / Rules 2.2.b):** still unresolved. The recommendation is invariant to the
  answer (identical copies of the leader under both readings); only the roll-count and lock
  discipline change. See the DAN-1 section.

---

## 1. The current leader and the ring shortlist (U2 / U4 / U5)

The ring is the decision authority for build composition (L9); ladder reads do not gate lever
decisions. The strongest ring-measured build this push is the yushin-deck stack:

| Build | Ring win rate | n | Source | Verdict |
| --- | --- | --- | --- | --- |
| `heuristic+yushin+ability+threat_retreat` | **0.910** | 100 | analysis/u105b_threat_retreat_ring_ab.md (U2) | PASS, +6.0pp over yushin+ability |
| `heuristic+yushin+ability+attack_first` | 0.875 | 40 | analysis/u104_stacked_ring_pass_run.md (U104) | PASS, +15.0pp over trolley+ability |
| `heuristic+yushin+ability` (baseline) | 0.800-0.850 | 40-100 | U104 arm 2 / U2 off-arm | baseline |
| `heuristic+trolley+ability` | 0.725 | 40 | U104 arm 1 | weaker deck |

- **U2 (threat-retreat A/B, banked):** threat_retreat ON 0.910 (91-0-9) vs OFF 0.850 (85-0-15),
  diff **+6.0pp**, gate bar > +5.0pp, **PASS** at n=100, same-run, alternating seats. The lever is
  banked into the leader. (analysis/u105b_threat_retreat_ring_ab.md.)
- **U4 (wave-2 deck candidates):** all five mined wave-2 decks FAILED the +0.10 screen against the
  `candidate_yushin_ito` baseline (0.825). Best was `candidate_bluezlee_w2` at 0.800, delta **-0.025**
  (below baseline, wrong direction). **No promote, no new deck.** (analysis/wave2_ring_scores.md.)
- **U5 (hard ring):** NOT NEEDED NOW. Neither U2 nor U4 produced a stuck verdict (>= 0.85 baseline
  AND a compressed/ambiguous delta). Both resolved cleanly on the standard calibrated ring, so no
  harder ring is required to trust the ordering. (analysis/u110_hard_ring_decision.md.)

**Note on the leader's exact composition.** attack_first (U104) and threat_retreat (U2) are two
independently ring-PASSED levers on the same yushin+ability base. They were not co-measured in a
single n=100 run, so this doc uses the highest co-measured read, 0.910 (yushin+ability+threat_retreat,
U2), as the defensible leader anchor. Whether the final tarball also stacks attack_first is a
build-composition detail for Dan to confirm at lock time; it does not change the pair arithmetic
below (identical copies of whichever single strongest tarball Dan settles on).

**There is no runner-up.** No mechanically different build measured this push comes within read
noise of the leader. The nearest different-deck read (`candidate_yushin_ito` at 0.825, or
`bluezlee_w2` at 0.800) is ~9-11pp below the leader's 0.910; at n=100 a two-arm standard error near
these win rates is ~4.6pp, so a 9-11pp gap is roughly 2+ standard errors, a real separation rather
than noise. Per the plan, when U4 does not surface a promotable new deck with a real overlapping
ring CI, the pair defaults to the identical-copies branch. That is exactly this round.

---

## 2. E[max] arithmetic (reproducible, hand-checkable)

### 2.0 The model

Per analysis/final_scoring_semantics.md, only the latest 2 submissions are scored, both keep playing
independent episodes, and the leaderboard shows the **max** of the two. So the final score is
`max(X1, X2)`, where each copy's converged rating `Xi` is a draw from a Gaussian centered on that
build's true skill `mu_build` with residual convergence noise `sigma`. Two submitted copies play
separate episodes, so `X1` and `X2` are **independent**. U7 gives `sigma = 37.0` rating points
(the end-of-window residual sigma; caveats in Section 3).

Two roles, do not confuse them:
- **Ring win rate** selects *which build is the leader* (Section 1). Units: win-rate proportion.
- **U7's sigma** is the *convergence noise on the final leaderboard rating* and drives the E[max]
  math below. Units: rating points.

### 2.1 Branch A -- two identical copies (RECOMMENDED)

Both copies are the leader `L`: `X1, X2` iid `N(mu_L, sigma^2)`.

```
E[max(X1, X2)] = mu_L + sigma * E[max(Z1, Z2)],   Zi iid N(0,1)
E[max of two standard normals] = 1 / sqrt(pi) ~= 0.56419
=> E[max identical] = mu_L + sigma / sqrt(pi)
```

Compared to spending a single slot (or two perfectly-correlated copies), `E[best single] = mu_L`.
So the **value of putting both slots on identical copies** is the max-of-two lift:

```
lift = sigma / sqrt(pi)
     = 37.0 / 1.772454 = +20.9 rating points        (at sigma = 37.0)
     = 26.0 / 1.772454 = +14.7   (sigma at CI low, 26.0)
     = 46.9 / 1.772454 = +26.5   (sigma at CI high, 46.9)
```

Hand check: `1 / sqrt(pi) = 0.56419`; `37.0 x 0.56419 = 20.875`. Confirmed.

### 2.2 Branch B -- a hedge with two DIFFERENT builds (the road not taken)

Copy 1 is the leader `L` (`mu_L`); copy 2 is a different build `R` with true skill `mu_R = mu_L - d`,
`d >= 0` the true-skill gap, same sigma, independent. For two independent normals with common sigma:

```
theta = sqrt(sigma^2 + sigma^2) = sigma * sqrt(2)
a     = (mu_L - mu_R) / theta = d / theta
E[max hedge] = mu_L * Phi(a) + mu_R * Phi(-a) + theta * phi(a)
             = mu_L - d * Phi(-a) + theta * phi(a)
```

where `Phi` is the standard normal CDF and `phi` its PDF.

Sanity check at `d = 0` (a perfect skill tie): `a = 0`, `Phi(0) = 0.5`, `phi(0) = 0.39894`,
`theta = sigma*sqrt(2)`, so `E[max hedge] = mu_L + sigma*sqrt(2)*0.39894 = mu_L + sigma/sqrt(pi)` =
exactly Branch A. A perfectly-tied different build adds **nothing** over identical copies.

Worked hedge examples at `sigma = 37.0` (leader mean set to `mu_L` for readability; the table shows
`E[max] - mu_L`):

| true gap d (rating pts) | E[max hedge] - mu_L | E[max identical] - mu_L | hedge minus identical |
| --- | --- | --- | --- |
| 0  | +20.875 | +20.875 | 0.000 (tie) |
| 10 | +16.255 | +20.875 | -4.620 |
| 20 | +12.382 | +20.875 | -8.493 |
| 40 | +6.694  | +20.875 | -14.181 |
| 60 | +3.272  | +20.875 | -17.603 |

**Every positive gap makes the hedge worse.** Even a runner-up only 20 rating points below the
leader (well inside the 37-point read noise) costs ~8.5 rating points of expected max versus two
identical leaders.

### 2.3 The dominance result (why identical wins)

Define `g(d) = E[max hedge] - E[max identical] = theta*[phi(d/theta) - phi(0)] - d*Phi(-d/theta)`.
For `d > 0`, `phi(d/theta) < phi(0)` (the normal PDF peaks at 0), so the first term is negative, and
`d*Phi(-d/theta) > 0`, so the second term is subtracted. Hence `g(d) <= 0` for all `d >= 0`, with
equality only at `d = 0`. **Under equal sigma and a leader whose true skill is at least the
runner-up's, two identical copies of the leader weakly dominate every hedge, strictly for any real
skill gap.**

This dominance is **sigma-independent**: `g(d) <= 0` holds for any `sigma > 0`. Sigma only scales the
*size* of the max-of-two lift, not the identical-vs-hedge choice. That is why U7's sigma being a
proxy (Section 3) does not threaten the recommendation.

### 2.4 When would a hedge actually be justified?

The fixed-known-mu model above says: never, as long as you know which build is better. The plan's
hedge trigger ("runner-up's ring CI overlaps the leader's AND U7's sigma makes E[max of two
different builds] beat E[best single]") is really an **epistemic** condition: it fires only when the
ring reads overlap enough that you *cannot tell which build has the higher true mu*, so the "leader"
label itself is uncertain and submitting both covers the risk of having picked wrong. That is a
strictly stronger requirement than mere sampling noise, and it is **not met** here: U2 cleanly ranks
threat-ON above threat-OFF (+6.0pp, clean at n=100), U4's candidates all fail by wide margins, and
U5 confirms no verdict got stuck. No epistemic overlap exists, so the hedge does not fire.

### 2.5 Reproduce the arithmetic

```python
import math
def Phi(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
def phi(x): return math.exp(-x*x/2)/math.sqrt(2*math.pi)
def emax(m1, m2, s):
    theta = s*math.sqrt(2); a = (m1-m2)/theta
    return m1*Phi(a) + m2*Phi(-a) + theta*phi(a)
mu, s = 600.0, 37.0
print("identical lift:", emax(mu, mu, s) - mu)         # 20.875 == s/sqrt(pi)
for d in (0, 10, 20, 40, 60):
    print("d=", d, "hedge-identical:", emax(mu, mu-d, s) - emax(mu, mu, s))
```

Run with any `mu` (the lift is translation-invariant). Output matches Section 2.1-2.2 exactly.

---

## 3. U7's residual sigma, caveats carried forward honestly

- **Value:** end-of-window residual **sigma = 37.0**, 90% CI **[26.0, 46.9]**, **n = 60**.
  Source: analysis/convergence_sigma.md (U7 / U115).
- **This is a PROXY, not a direct measurement.** U7's preferred covariate is each read's real
  episode count (reconstructed from the ref's episode list). That reconstruction was unavailable
  (no kaggle CLI in that environment), so U7 used an **age-hours fallback** covariate instead. The
  37.0 is a proxy for the 200-350 game convergence window, not a measured 200-350 game sigma.
- **Coarse buckets.** Note fields carry a date, not a timestamp, so age-hours resolves only to whole
  days; most reads bunch into one or two buckets. The curve is real but coarse.
- **Fresh-read correction had nothing to exclude this run** (0 of 61 dated reads within 48h of the
  reference date), because the ledger has fully aged into the converged regime, not because the
  correction stopped applying.
- **Why the caveat does not move the recommendation.** Section 2.3: the identical-vs-hedge ordering
  is sigma-independent. Sigma only sets the size of the max-of-two lift, which ranges +14.7 to +26.5
  rating points across the CI. Dan should read "+20.9 (roughly +15 to +26)" and treat the point
  estimate as a proxy, not a promise. If a real episode-count sigma is ever reconstructable before
  the lock, re-run the one-liner in 2.5 with it; the branch choice will not change, only the lift
  magnitude.

---

## 4. DAN-1 (Simulation Rules 2.2.b): OPEN, both branches stated

**Status: unresolved.** Per LOOP_BRIEF.md, Simulation Rules 2.2.b says teams "may select up to two
Final Submissions," while the overview/FAQ say only the latest-2 are auto-tracked. Dan is to check
the logged-in Submissions page for a selection UI before August (the DAN-1 escalation). No selection
UI has been confirmed, so both readings are live:

- **Branch (i) latest-2-auto** (overview/FAQ; corroborated by our own eviction probe in
  analysis/final_scoring_semantics.md): only the latest 2 submissions are scored, there is no manual
  selection, and there is no best-ever safety net. Operational consequence: **strict no-roll
  discipline** -- any submission after the intended lock evicts a good draw with no way to get it
  back. Submit the identical-copies pair, then freeze. This is the branch the lock-rehearsal
  checklist and final_scoring_semantics assume.
- **Branch (ii) manual-select-two** (the literal 2.2.b text): if a selection UI exists, Dan could
  roll **more than two** copies of the leader across the window and hand-pick the best two converged
  draws at the end. `max` over `k > 2` independent draws is `>=` the max over 2, so if selection
  exists the optimal tactic shifts from "two copies, freeze" to "roll several copies of the leader,
  select the best two."

**Invariance:** under both branches the *build choice is unchanged* -- every copy is the leader; a
hedge is never justified (Section 2). Only the roll-count and freeze discipline differ, and that is
a checklist-tactics tuning, not a pair-decision change. The draft row (Section 5) is written for the
invariant part. Resolving DAN-1 only tells Dan whether to roll-and-select (branch ii) or submit-two-
and-freeze (branch i). Recommended default until DAN-1 resolves: **branch (i)**, the conservative
no-roll reading, because it is safe under both (submitting exactly two identical copies and freezing
is valid whether or not a selection UI exists).

---

## 5. The draft pre-registration row

A DRAFT row for the leader has been staged in state/current.md via the canonical writer
(`tools/loop_state.py prereg-draft`, which calls `upsert_draft_prereg`). It is written to the
`draft_pre_registrations` list, **not** to the live `pre_registrations` gate, and is stamped
`status = "DRAFT"`. This is deliberate:

- A draft is validate-clean (it passes `validate_prereg` with zero problems) but is **not** a
  submission authorization. `submission_allowed(build)` still returns BLOCK for it, because only a
  human moving the row into `pre_registrations` finalizes it. Only Dan's confirmation does that.
- The JSON STATE block is the source of truth; the prose "Draft pre-registrations" section is a
  rendered view. The row was never hand-edited into the JSON.

Draft row fields (all validate-clean):

| field | value |
| --- | --- |
| build | `heuristic+yushin+ability+threat_retreat` |
| direction | up |
| margin M | 240 (the U108 noise band; matches the checklist's M) |
| N (episode floor) | 200 (low end of U7's 200-350 game convergence window) |
| settle_by | 2026-08-30 (leaderboard-final, ~2 weeks after the Aug 16 deadline) |
| status | DRAFT |
| filters | ring evidence from U2/U4/U5 + the E[max] identical-copies selection (full citation in the row) |
| WIN / LOSS / BAND | locked-pair actions: no eviction after the Aug 16 lock; ring evidence is the only eviction authority (U108) |

**To finalize (Dan only):** after signing, promote the row from `draft_pre_registrations` into
`pre_registrations` (e.g. re-issue it through `tools/loop_state.py prereg ...` with the same fields),
which flips `submission_allowed` to ALLOW for the build. Until then the gate stays closed.

---

## 6. Consistency with the lock-rehearsal checklist (sibling half)

Cross-checked against docs/lock_rehearsal_checklist.md (the U117 half):

- **M = 240** here matches the checklist's "Noise band (M) = 240 points" (U108 settlement arithmetic).
- **U108 standing rule** (a ladder read inside the M-band never evicts a ring-positive build; ring
  evidence is the only eviction authority) is referenced identically in the draft row's WIN/LOSS/BAND
  actions.
- **Pair composition** ("Build 2 Submission (Hedge or Identical Copy)") is resolved by this doc to
  the **identical-copy** branch, which the checklist already lists as a supported option.
- The checklist's load-bearing pre-submission gate, `tests/test_grader_submission.py`, exists in the
  tree. Nothing in this doc contradicts the checklist.

---

## Appendix: source docs

- analysis/u105b_threat_retreat_ring_ab.md -- U2 verdict, threat-retreat PASS +6.0pp at n=100.
- analysis/wave2_ring_scores.md -- U4 verdict, no promote for all five wave-2 candidates.
- analysis/u110_hard_ring_decision.md -- U5 verdict, hard ring not needed now.
- analysis/convergence_sigma.md -- U7 residual sigma 37.0, 90% CI [26.0, 46.9], n=60 (age-hours proxy).
- analysis/final_scoring_semantics.md -- latest-2 max scoring rule (the E[max] model).
- analysis/u104_stacked_ring_pass_run.md -- U104 stacked ring pass (yushin+ability+attack_first 0.875).
- docs/lock_rehearsal_checklist.md -- the sibling U117 lock procedure.
- LOOP_BRIEF.md -- DAN-1 / Rules 2.2.b escalation, U108 governance.
