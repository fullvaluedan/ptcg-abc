# Universal proxy retrodiction gate (U24)

## The rule

No offline proxy may BLOCK a ladder slot until it has retrodicted the ordering of
the builds we already have ladder truth for. The ladder A/B is the sole arbiter;
a proxy earns only the right to BLOCK a candidate (never to promote one), and only
after it reproduces the known rank order. A passing proxy that says "block" is
trusted; every other proxy is refused by default (`loop_state proxy_may_gate`
returns False with no calibration report).

## Ground truth (the five known builds)

| build | ladder | ref |
| --- | --- | --- |
| heuristic+trolley | 569.6 | 54215558 |
| heuristic+benchguard | 554.5 | 54215910 |
| search+trolley | 514.7 | 54218335 |
| meta_grimmsnarl | 510.1 | 54220220 (first read; 489.6 on 07-02) |
| meta_archaludon | 382.5 | 54219892 |

These are the ordering a proxy must reproduce: 569.6 > 554.5 > 514.7 > 510.1 >
382.5. The list is `analysis.proxy_calibration.KNOWN_LADDER`; extend it as new
builds settle so the calibration set grows.

## The test

A proxy assigns each build a scalar (higher = better). We rank-correlate its
scores against the ladder scores over the builds it covers with Kendall's tau
(concordant minus discordant pairs over untied pairs). PASS requires both:

- **coverage** >= 4 of the 5 known builds (`MIN_COVERAGE`). Two points can only be
  perfectly concordant or discordant, so a two-build "calibration" is no evidence.
- **tau** >= 0.8 (`TAU_THRESHOLD`). Over the full five-build set that lets at most
  one of the ten pairs invert (9 concordant, 1 discordant -> tau 0.8). A proxy
  that flips two or more pairs is not predictive enough to kill a candidate.

Ties in either sequence are dropped from the tau denominator, so a proxy is
neither rewarded nor punished for two builds it cannot distinguish.

## How to calibrate a proxy before it gates

1. Score all five known builds with the proxy (offline).
2. `python -m analysis.proxy_calibration --scores '{"heuristic+trolley": ..., ...}'`
   prints the report and exits 0 on PASS / 2 on FAIL.
3. To persist the verdict so the loop honors it:
   `python -m tools.loop_state calibrate-proxy --proxy <name> --scores '{...}'`
   writes the report into `state/current.md` (calibrated_proxies).
4. Before letting any proxy block a slot:
   `python -m tools.loop_state check-gate --proxy <name>` (exit 1 = refused).

## Current status: nothing calibrated (default-deny)

No proxy has been calibrated against the five-build ordering yet, so **every proxy
gate is refused**. This is the correct safe default: proxies BLOCK only, and until
one proves it reproduces the ladder ordering it may not even do that. This closes
review P2-18 (an uncalibrated proxy silently gating a slot).

Two standing consequences:

- The **weak-bot gauntlet is banned from all gates** regardless of any tau it
  posts (loop brief hard constraint): it is non-predictive by construction. Even
  if it retrodicted the ordering, it does not earn a gate.
- The **cloned/deck-diverse gauntlet and move-ranking validator** (the proxies the
  plan wants to eventually gate ML/deck spend, U35/U39/U40/U43) must each publish a
  passing report here before their block counts. Until then they inform but do not
  gate.
