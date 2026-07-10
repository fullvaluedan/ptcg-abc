# U110 (plan U5): hard-ring decision -- NOT NEEDED NOW

Plan: docs/plans/2026-07-10-001-feat-improvement-push-plan.md, U5/U110. Requirement R5:
decide whether to build the enriched "hard ring" (a harder opponent pool for ring evaluation)
or close the question with evidence, using only this push's own gate data from U2 and U4. No
speculation; real data only.

**Verdict: NOT NEEDED NOW.** No gate in U2 or U4 saturated in the sense the decision rule
requires (off-arm/baseline win rate >= 0.85 *combined with* a compressed delta that made the
verdict genuinely ambiguous). Neither gate needed resolution above 0.875 to reach a confident
verdict. The standard calibrated ring (tau 0.857, analysis/ring_calibration.md) resolved both
questions cleanly. The hard ring is not built now; the precise re-open trigger is recorded
below. No code files are produced, per the plan's own test-scenario note for the NOT-BUILT
branch (U5 "Test scenarios": "If NOT built: test expectation: none, decision doc only").

## The decision rule (from the plan, U5 Approach)

> Did any gate in U2/U4 actually saturate (off-arm at or above 0.85 with a compressed delta)?
> If no gate needed resolution above 0.875, close U110 as not needed now with the trigger
> condition recorded. If yes, build the enriched arm ... the hard ring earns gate authority
> only by correctly ordering builds the standard ring already orders.

Saturation, per this rule and the KTD "U105b runs on the standard ring with saturation
routing," is not merely "a high win rate appeared." It is operationally defined by its *effect
on the verdict*: an off-arm/baseline at or above 0.85 whose companion delta is compressed
enough that a PASS/FAIL call cannot be trusted, so the honest move is to escalate to a harder
ring rather than declare a FAIL on a delta the saturated ceiling squeezed flat. The hard ring
exists to un-stick a stuck verdict. If no verdict got stuck, there is nothing for it to resolve.

## Evidence from U2 (analysis/u105b_threat_retreat_ring_ab.md)

Real n=100/arm gate run, same-run, alternating seats, on the calibrated bracket-band ring
(raw log analysis/u105b_n100_run.log, machine-readable block confirmed):

| Arm | Win rate | W-D-L | n |
|---|---|---|---|
| threat_retreat OFF (baseline) | 0.850 | 85-0-15 | 100 |
| threat_retreat ON | 0.910 | 91-0-9 | 100 |

diff_pp (on minus off) = +6.0. Gate bar: strictly more than +5.0pp. **Verdict: PASS.**

Read against the rule:

- The off-arm landed at **exactly 0.850**, which meets the numeric ">= 0.85" half of the
  saturation trigger. This is the one place either gate touched the saturation threshold, and
  it is the delegated judgment call U2's own doc flagged for U5.
- The delta was **+6.0pp, not compressed**. It cleared the +5.0pp bar by a full point (1.2x
  the bar), and the arms are cleanly separated (85 vs 91 wins at n=100; a ~4.9pp two-arm
  standard error puts the +6.0pp gap comfortably outside noise of the bar). The verdict was
  reached with full confidence on the standard ring.
- Therefore the *conjunction* the rule requires -- ">= 0.85 AND a compressed/ambiguous delta"
  -- is **not** satisfied. The first clause is met; the second is not. The gate did not need a
  harder ring to reach its verdict, and it did not need resolution above 0.875 (the off-arm is
  0.85, below 0.875; the on-arm 0.910 is a *result*, not a value the gate math had to reach
  past a saturated band to trust).

### Judgment call on the exactly-0.850 off-arm

U2's doc asks U5 to weigh whether a clean pass at exactly the threshold is "saturation that
blocked a verdict" or "a threshold value that happened not to compress anything this time, but
signals rising risk for the next lever." **My call: it is the latter, decisively.**

Reasoning. Saturation earns the hard ring only through its effect, and here it had none: the
delta was clean, the verdict confident, the standard ring did exactly the job it was
calibrated for. Building a hard ring "because a number touched 0.85" would be building it on a
threshold coincidence, not on a blocked verdict -- and the plan is explicit that the hard ring
earns authority only by first reproducing the standard ring's ordering on builds the standard
ring already orders correctly. There is no stuck ordering here to un-stick. To treat this as
saturation-that-blocked-a-verdict would be to manufacture the very speculation R5 forbids.

But the 0.850 read is a genuine, real-data early warning, and it must be recorded as one, not
waved off. The standard ring's known ceiling is 0.875-0.91 (KTD; analysis/u105b doc). Two facts
compound:

1. The off-arm baseline is already at 0.850, only ~6pp below the top of the saturation band.
2. Because U2 PASSED, threat-retreat is banked, so the **new** best build (yushin+ability+
   threat) now sits at **0.910 -- at the very top of the saturation band**. The next lever
   tested as a same-run A/B from this banked baseline starts with an off-arm essentially at the
   ceiling, with almost no headroom above it to express a positive delta.

That is rising, real, quantified saturation risk for the *next* gate. It is not saturation that
blocked *this* gate. The correct response is to record the trigger and watch for it, which is
exactly what "NOT NEEDED NOW" plus a re-open condition delivers -- not to pre-build on a risk
that has not yet materialized into a stuck verdict.

## Evidence from U4 (analysis/wave2_ring_scores.md)

Real screen run, n=40 each, calibrated bracket ring, baseline candidate_yushin_ito:

| Build | Win rate | W/L | Delta vs baseline | Cleared +0.10 screen? |
|---|---|---|---|---|
| candidate_yushin_ito (baseline) | 0.825 | 33/40 | -- | -- |
| candidate_bluezlee_w2 | 0.800 | 32/40 | -0.025 | No |
| candidate_third_ptcg_club_w2 | 0.475 | 19/40 | -0.350 | No |
| candidate_henka_no_sho_zoroark_w2 | 0.400 | 16/40 | -0.425 | No |
| candidate_kashiwashira_w2 | 0.400 | 16/40 | -0.425 | No |
| candidate_zoroark190_w2 | 0.375 | 15/40 | -0.450 | No |

Read against the rule:

- The **baseline is 0.825, below the 0.85 trigger**. U4 never entered the saturation band at
  all, so its numeric precondition is not even met.
- The verdict (no-promote for all five) was reached by **wide, unambiguous margins**: the best
  candidate missed the +0.10 screen bar in the *wrong direction* (-0.025), and the confirm
  stage was correctly never triggered. There is no compressed delta and no ambiguity anywhere
  in this gate -- the separation between the field and the baseline is large and clear.
- Nothing here needed resolution above 0.875. A harder ring would only push these already-
  decisively-failing candidates further down; it cannot change a single verdict.

## Verdict rationale, in one line

Both gates reached confident verdicts on the standard ring. U2's off-arm touched 0.850 but its
+6.0pp delta was clean, not compressed; U4's baseline was 0.825 with all candidates failing by
wide margins. The conjunction the rule requires (>= 0.85 AND an ambiguous, compressed delta)
occurred in **neither** gate, and neither needed resolution above 0.875. Per the rule, **close
U110 as NOT NEEDED NOW.**

## Re-open trigger (watch this in future gates)

Re-open U110 and build the enriched hard ring when a future ring gate produces **both** of the
following in the same run:

1. The off-arm (or baseline) win rate reads **>= 0.85** on the standard calibrated ring, AND
2. The delta is **compressed into ambiguity** -- concretely, either
   (a) the on-arm bumps the ring's ceiling (~0.91) while the off-arm sits >= 0.85, so the ring
       has no headroom left to express the lever's true effect; or
   (b) the delta lands close enough to the +5.0pp gate bar that the PASS/FAIL side cannot be
       confidently called at the run's n (as a rule of thumb, |diff_pp - 5.0| within about one
       two-arm standard error at that n, i.e. roughly +/-5pp at n=100/arm), so the verdict is
       genuinely a coin-flip against the bar rather than a clean clear or a clean miss.

**Most likely first trigger:** the next same-run A/B lever tested against the now-banked
yushin+ability+threat baseline. That baseline is already at 0.910, at the top of the
0.875-0.91 saturation band, so the very next lever's off-arm starts with almost no headroom. If
that run's on-arm cannot separate from ~0.91 and the delta lands ambiguously near +5pp, that is
condition (2a) firing and is the signal to build the hard ring.

When the trigger fires, build per the plan's approach: hardest clones plus 800+-rated harvested
decks piloted by the stacked build, with the **U73 mirror-drag guard** (the opponent list must
exclude any clone piloting the build-under-test's own deck -- docs/writeup/offline_ladder_
transfer.md), and the hard ring earns gate authority **only after** an ordering-check test
reproduces the standard ring's ordering on two known builds. Until the trigger fires, the
standard calibrated ring remains the sole offline gate, and the U2 secondary metric (loss rate
vs. the three hardest clones: off-arm 0.212, on-arm 0.273 this run) is the running canary to
watch alongside it.
