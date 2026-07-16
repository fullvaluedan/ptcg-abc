# HANDOFF: ptcg-abc (Pokemon TCG AI Battle Challenge)

Written 2026-07-12. Branch `feat/phase3-followon` (also fast-forwarded to `main`),
HEAD `c342cf5`. No em or en dashes anywhere in this repo (a commit-msg hook enforces it).

## Bottom line up front

We are not making ladder progress, and it is structural, not effort. The honest
picture, verified repeatedly this month:

- Our true rating is ~570 to 630. The field median is 676, p95 is 951, and the
  leader is 1242. We sit around the 35th to 40th percentile of 4351 teams.
- The one genuine improvement all month was the DECK (candidate_yushin_ito over
  the old trolley shell, a real +8pp ring effect). Every behavioral flag we
  shipped (ability, threat-retreat, the stack) DISSOLVED when finally measured at
  proper statistical power: at n=351 to 700 per arm, all four flag configurations
  are statistically indistinguishable on both rings (`analysis/flag_config_powered.md`).
- The best analysis we have (`analysis/path_above_1000.md`) puts the current plan's
  converged ceiling at 650 to 700, and 1000+ at under 5% even if every remaining
  idea works. Nothing currently in the repo reaches 1000.

If the goal is the Simulation ladder rank, we have mostly hit the wall of what a
hand-coded rule-ladder pilot scored on a band-local instrument can do. If the goal
is prize money, the Strategy prize ($30k, judged 70% on model approach, ladder
independent) is the winnable one, and its writeup is finished and submission-ready
(see "The two decisions only Dan can make").

## Current live state

Kaggle scored pair (latest-2 semantics, best-of-pair counts), read 2026-07-12:

| ref | build | last read | pre-registered settle-by |
|---|---|---:|---|
| 54592012 | yushin PLAIN (no flags) | 539.3 | 2026-07-22 |
| 54555716 | yushin + ability + threat_retreat | 572.0 | 2026-07-25 |

Both are drifting inside the M=240 noise band. Per U108, no single read inside the
band decides anything; only pooled aged reads near the settle-by dates matter. The
powered flag experiment says these two configs are within noise of each other, so
there is no statistical case to reseat either way before the lock.

Nothing is running in the background. Verified: the tmux server has no sessions;
all unattended LLM loops were stopped 2026-07-10 on Dan's directive (autoloop,
ce-work push, and the `ptcg-watchdog` scheduled task, which is Disabled). The only
scheduled machinery is `ptcg-data-refresh` (daily 09:00, `tools/daily_refresh.py`,
pure Python, no LLM). Do not restart any loop or re-enable the watchdog without an
explicit ask (memory: `ptcg-abc-loops-stopped`).

## Calendar

- 2026-07-22: plain-yushin (54592012) settle-by. Decide from pooled aged reads.
- 2026-07-25: flags-stack (54555716) settle-by.
- 2026-08-05: pair pre-registration package due (Dan signs). Prep exists in
  `analysis/seating_recommendation_yushin_threat.md` and the E[max] logic; the
  convergence sigma input is `analysis/convergence_sigma.md` (sigma ~37).
- 2026-08-12 to 08-13: lock the final pair EARLY so it accrues convergence games.
  Checklist: `docs/lock_rehearsal_checklist.md`. Ops guard: every tarball passes
  `tests/test_grader_submission.py`, confirm COMPLETE before the next roll, submit
  nothing after Aug 13 that has not already scored COMPLETE under an identical hash.
- 2026-08-16 23:59 UTC: Simulation deadline, then ~2 weeks of continued games until
  the leaderboard converges (lucky reads decay; only true strength survives).
- 2026-09-01: Dan's self-imposed writeup submit target (12-day buffer).
- 2026-09-13 23:59 UTC: hard Strategy writeup deadline. Team-merger deadline 09-06.

## The honest scorecard: what worked, what did not

WORKED (real, replicated, banked):
- The yushin deck over trolley: +8pp on the calibrated ring at n=100, replicated
  (`analysis/u112_stacked_ring_confirmation.md`). This is the only lever that moved
  the needle and survives scrutiny.

DID NOT WORK (dissolved under proper measurement, all honestly closed):
- The behavioral flags (ability, threat_retreat, the stack): the n=100 reads that
  motivated shipping them were underpowered; at power they are within noise of plain
  (`analysis/flag_config_powered.md`). The threat lever's original +6pp was a lucky
  n=100 read, exactly the failure mode the ML expert panel predicted
  (`analysis/ml_expert_review.md`).
- The outcome-labeled option ranker (the one untested deployable-ML cell): trained
  weak (AUC 0.542 vs 0.517 baseline) and FAILED its powered gate catastrophically,
  -51pp elite / -45pp calibrated (`analysis/ranker_gate.md`). ML on the action
  policy is now closed honestly, not by assumption.
- The endgame-PLAY rule: designed from real divergence evidence, then killed at the
  fires-vs-inert step (0 fires on yushin, positive control fired). The evidence came
  from Dudunsparce draw decks that hold 19-card hands; yushin never does
  (`analysis/endgame_play_gate.md`).

## Why we are not making progress (the structural diagnosis)

Two walls, both verified from multiple angles:

1. THE PILOT CLASS. The shipped agent is a hand-coded priority ladder
   (`agents/heuristics.py`). Learning a better policy was closed four independent
   ways on the agreement objective (`analysis/clone_quality.md`), and the one
   outcome-labeled ML cell just failed its gate. Search that would use the 600s
   time bank is dead because the grader engine withholds the forward model, and even
   an ORACLE opponent prior tied the heuristic exactly (`analysis/u109_oracle_bound_test.md`).
   The rule ladder is near its ceiling and the obvious ML upgrades are closed.

2. THE INSTRUMENT. Our decision gate (the calibrated ring) is built from clones of
   our OWN 450-750 band and saturates at 0.875 to 0.91. We already read 0.85+ on it,
   so it has almost no headroom left to reward anything, and it demonstrably rewards
   levers that do not transfer (the flags). We built the 35-clone ELITE ring this
   month to see high-band play for the first time, and on it our stack reads ~0.69 to
   0.73 against elite decks, far from the 0.91 the old ring showed. The measuring
   stick we optimized against could not see the thing that matters.

The compounding process failure the ML panel named: we obsessively modeled ladder
noise but never computed the required sample size for the ring gate we made the sole
authority. n=100 gates for +5pp effects run at ~26% power, so most "wins" were noise
excursions that later reversed. That is now fixed in infrastructure (`tools/parallel_ring.py`
runs powered gates in minutes via 16-worker sharding) but the fix arrived after most
levers were already spent.

## What is CLOSED (do not reopen without a genuinely new mechanism)

Read `state/hypotheses.md` and `findings.md` section 4B for the full registry. The
big ones and what EXACTLY was closed:
- Match-time search / determinization: oracle-dead (`analysis/u109_oracle_bound_test.md`).
  Forward model withheld at match time; force-loading our own cg scored 431 vs 570.
- Imitation / clone learning: 4 converging attempts on the agreement objective
  (`analysis/clone_quality.md`).
- The outcome-labeled option ranker: -51pp powered gate (`analysis/ranker_gate.md`).
- Whole-meta-deck copying: below the trolley floor under our pilot.
- Narrow deck grids (basics/energy on the trolley lineage): 3 probes, all negative.
- CEM weight tuning: 3 conditions exhausted.
- The behavioral flags as rating levers: within noise at power.
- prize_close, bench_dig, energy_seq, endgame_play: inert or refuted.

## What is GENUINELY open (the only remaining real moves, honestly priced)

None of these is likely to reach 1000. They are the honest remaining surface, in
rough order of expected value. All are on-request only, no loops.

1. BROAD DECK SEARCH SCORED ON THE ELITE RING (S4 of `analysis/path_above_1000.md`).
   Genuinely virgin: no genome/population/mutation code exists; U39 substituted
   mining for the search it was chartered to do. `tools/deck_validate.py` gives a
   legality operator; `tools/parallel_ring.py` gives fast fitness. Fitness MUST be
   the elite ring, not the saturated calibrated ring, or it inherits the ceiling.
   Cost: ~1 to 2 days to build the GA, overnight-scale compute. This is the highest
   EV move because the deck was the one thing that ever worked, and its neighborhood
   was never searched, only sampled.
2. THE T2 GRIND-DEFENSE RULE (`analysis/beat_the_meta_plan.md`). Aimed at the
   Alakazam-style grind predators that dominate elite kills. Never built. Must gate
   on the elite ring at PROPER POWER (n~700/arm now that it is cheap), and must pass
   a fires-vs-inert check with a positive control first (the U105 lesson). Cost: ~half
   a day. EV: low to moderate; most single rules dissolve at power.
3. THE ~37 UNSCORED MINED DECKS. On disk, never scored. Cheap screen on the elite
   ring. EV: low (wave-2 already went 0-for-5), but nearly free as a batch job.
4. U102 CARD-TEXT EXPLOIT AUDIT. Entirely unrun. Fat-tailed, low-median: the fuzzer
   found zero real engine violations over 2400 games, but two candidate anomalies sit
   unattributed in `docs/rules_as_implemented.md`. Cost: ~half a day capped. EV: a
   small chance of a real edge, otherwise writeup material.

Do NOT confuse "open" with "promising." The gap-calibration math says the sum of all
of these is unlikely to clear +100 rating.

## The two decisions only Dan can make

1. SUBMIT THE STRATEGY WRITEUP. It is finished, 1978 words, submission-ready:
   `docs/writeup/final_synthesis.md`. Kaggle has NO API for hackathon writeups, so it
   must be pasted into the site editor logged in as Dan. The exact click-path and a
   pre-submission checklist are in `docs/writeup/SUBMISSION.md`. A draft does not
   count; the final Submit click is required. This is the single highest-value action
   remaining in the whole project, because the Strategy prize is real money and the
   writeup is genuinely strong (the honest-instrumentation story is exactly what the
   70%-model-approach judging rewards). Target Sep 1, hard deadline Sep 13. A future
   session can drive Dan's Chrome to paste the fields and stop before the final click.
2. THE AUG 12-13 LOCK PAIR. Sign the pre-registration by Aug 5. Given the powered
   flag result (the two live configs are within noise), the honest default is to lock
   two copies of the strongest single build rather than a hedge, unless a deck-search
   winner (open item 1) has by then cleared the elite ring at power. Decide from
   pooled aged reads, never single reads.

## Strategic recommendation (my honest read)

Stop trying to move the ladder rank with more pilot levers. That lane is closed and
each new lever costs real effort to reach a within-noise result. Two things are worth
doing, in this order:

1. Submit the writeup (Dan, 5 minutes, highest EV in the project).
2. If anyone wants to keep pushing the rank, spend it on the ONE thing that ever
   worked and was never properly explored: broad deck search scored on the elite ring
   (open item 1). It is the only move with a non-trivial chance of a real gain, and
   even a win there is more likely to reach 720 to 780 than 1000.

Everything else is either closed, within noise, or writeup material. The project's
real, defensible achievement this month is not a rating; it is the measurement
discipline itself (pre-registration, the noise model, the audits that killed our own
false wins, the power correction). That is the story the writeup tells, and it is the
honest one.

## Operational notes for a future session

- Delegation: on Fable-model sessions, orchestrate and delegate execution to
  Opus/Sonnet/Haiku subagents (memory: `fable-delegation-rule`). Ranking/measurement
  jobs are compute, run them as Python via subagents, never as an LLM loop.
- No unattended loops (memory: `ptcg-abc-loops-stopped`). Interactive and on-request
  only, plus the daily data refresh.
- Powered evals: `tools/parallel_ring.py` (16-worker sharding, shard_timeout, real
  Windows process-tree kill). Use n~700/arm for +5pp gates, n~200/arm for +10pp.
  Some elite-ring shards hang on pathological game trajectories; the timeout excludes
  them, report achieved n honestly.
- Pre-registrations and live_refs are written ONLY through the JSON STATE block via
  `tools/loop_state.py` (prose is a rendered view; hand edits have been silently
  destroyed). Submission is gated by `loop_state.py check-submit`.
- Hard rules: no em/en dashes anywhere (commit hook); never `git add -A`; never
  discard foreign working-tree changes; wait for `.git/index.lock` before git ops.
- Key docs to read first: this file, `analysis/path_above_1000.md`,
  `analysis/ml_expert_review.md`, `findings.md` (sections 3 to 5), `state/current.md`
  (live board and pre-registrations), `docs/writeup/SUBMISSION.md`.
