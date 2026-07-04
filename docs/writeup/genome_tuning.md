# CEM genome tuning of the shipped heuristic's PRIO weights (Strategy prize writeup, U35)

This section is a companion to [offline_ladder_transfer.md](offline_ladder_transfer.md):
that section is about whether an offline *proxy* can be trusted to predict ladder
rank; this one is about whether an offline *optimizer* can be trusted to improve
the shipped agent at all. Unlike the learned evaluator in
[learned_evaluator.md](learned_evaluator.md), the genome tuned here is not
quarantined to the unshipped search agent: `agents/heuristics.py`'s
`PRIO_ATTACK`, `PRIO_ATTACH`, `PRIO_EVOLVE`, `PRIO_ABILITY`, `PRIO_RETREAT`
(and the leaf-eval shaping weights) are read directly by the agent that actually
ships on the ladder. A genome improvement here would be a real, low-risk ladder
lever: no new code path, just re-ordered priorities inside logic that already
runs. That is exactly why it was worth testing carefully rather than skipped as
out of scope.

## What CEM tunes and how it is scored

`tools/cem_tune.py` runs the cross-entropy method over an 18-dimensional weight
vector (`tools/weight_space.py`): sample a population of candidate genomes from a
Gaussian, score each one, keep the elite fraction, refit the Gaussian to the
elite mean and variance (with an injected-variance floor so the search does not
collapse to a point before it has explored), repeat. Two independent fitness
channels are available: **agreement**, how often the candidate's `choose()`
picks the same MAIN decision a real top player did, scored by the same
move-ranking validator used in the transfer-problem writeup; and **pool win
rate**, how often the candidate wins a fresh gauntlet match against the U4
diverse 8-deck opponent pool. Every score is measured on a held-out-clean
**train** md5 bucket of the harvested replay data, with a separate **test**
bucket the tuner never touches during search, mirroring the row-level and
game-level leakage controls already described for the learned evaluator.

The gate a tuned genome must clear before it earns a ladder A/B is the same
shape as the U24 proxy-retrodiction rule: a **non-negative held-out agreement
delta**. A genome that only improves the bucket it was fit on is exactly what
overfitting looks like, and the whole point of a held-out check is to catch
that before it costs a scarce ladder slot.

## Attempt 1: agreement-only fitness (2026-07-02)

The first real run (`analysis/cem_run_prio.md`, seed 0, `--split train`,
`--pool-matches 0`) searched purely on move-ranking agreement. `best_fitness`
was flat at 0.2759 across all 12 iterations, meaning the population's very
first sample already contained the best candidate found and the search never
improved on it, a first warning sign that the agreement channel has little
climbable gradient on this genome. The best genome it did find moved several
priorities substantially: `PRIO_ATTACK` 0.0 -> 3.13, `PRIO_ATTACH` 3.0 -> 3.74,
`PRIO_EVOLVE` 5.0 -> 3.41, `PRIO_ABILITY` 2.0 -> 1.33, `PRIO_RETREAT` 1.0 ->
0.07.

| genome | train agreement | held-out test agreement |
|---|---:|---:|
| default (ship) | 0.2155 (25/116) | 0.2333 (7/30) |
| best tuned | 0.2759 (32/116) | 0.1667 (5/30) |

The tuned genome gained 7 more correct decisions on the 116 it was allowed to
see, and lost 2 of the 7 it had been getting right on the 30 it had never
seen. Train up, test down, in opposite directions, is the textbook shape of
overfitting rather than a real improvement. Verdict: **BLOCKED**, no ladder
A/B, ship stays byte-identical.

## Attempt 2: pooled fitness, a re-test with a fix behind it (2026-07-03)

The first run's own re-test menu named a specific, concrete follow-up:
turn on the second fitness channel (`--pool-matches > 0`) so a real win-rate
signal regularizes the agreement fit instead of leaving agreement to overfit
alone. That re-test only became possible after an unrelated bug fix: an
earlier attempt at this exact run had silently produced a zero-byte log,
because `tools/cem_tune.py`'s `_parse_evaluator_output` was reading the first
line of the evaluator subprocess's stdout instead of the last, so every
pool-match score came back as `-inf` without raising an error. Fixing that
parser (a one-line change, its own small commit) is what let this second
attempt run for real instead of quietly measuring nothing.

With both channels blended at equal weight (`--w-pool 0.5 --w-val 0.5`), at a
reduced search scale stated plainly up front (population 6-8 instead of the
default 50, 3-4 iterations instead of 20-plus, because each fitness
evaluation pays a roughly 14-second fixed subprocess cost and a full-scale
sweep would run several hours, past what one loop iteration can spend), the
held-out read (`analysis/cem_run_prio_pooled.md`) came back like this:

| vector | split | pool win rate | move-ranking agreement |
|---|---|---:|---:|
| default (ship) | train | 0.700 (21/30) | 0.2155 (25/116) |
| default (ship) | test | 0.633 (19/30) | 0.2333 (7/30) |
| tuned (this run) | train | 0.567 (17/30) | 0.2500 (29/116) |
| tuned (this run) | test | 0.633 (19/30) | 0.2333 (7/30) |

This time the held-out agreement did not just move in the wrong direction, it
did not move at all: 7 out of 30 held-out decisions matched under both the
default and the tuned genome, the identical count, meaning the 4 decisions
the tuning changed on the train bucket (25 -> 29) had literally zero overlap
with anything in the unseen bucket. And the half of the fitness function this
run was actually optimizing for, pool win rate, moved backwards on its own
training-side read (0.700 -> 0.567, a 13-point drop) rather than forward.
Verdict: **BLOCKED** again, for a second, independent reason: a flat-zero
transfer this time rather than a small negative one, on a genome candidate
whose own optimized objective went the wrong way even on the data it was fit
to.

## Why two failures in a row is being treated as a signal, not a shrug

The project's unified plan pre-registered a specific tripwire for exactly this
situation: if two consecutive CEM candidates both fail to clear the held-out
filter, that is read as evidence the current approach to this lever (agreement
and/or pool-win fitness, on the current expert-move sample size, over this
genome's dimensions) has plateaued, and the tripwire's stated response is to
stop spending dedicated ladder-adjacent effort on more variations of the same
fix and instead redirect that effort toward deck-space changes and hand-coded
levers, retaining CEM only for genuinely new weight spaces it has not yet been
tried against. Both attempts above are non-WIN candidates under that rule
(a negative delta, then a flat delta), so the two-candidate condition was met
on 2026-07-03, a few days ahead of the plan's own ~July 15 calendar checkpoint
for reviewing it. Per the project's standing plan-freeze rule (no unilateral
re-pointing outside a scheduled weekly review), this was recorded plainly in
`state/hypotheses.md` and `state/current.md` for that review to act on, rather
than declaring CEM tuning dead, or quietly trying a third variant, on the spot.

Two structurally different failure shapes both point the same direction: a
small negative held-out delta, and then a flat, exactly-zero one under a
different fitness formulation. Neither is proof the PRIO weight space is
permanently untunable; the honest read is narrower, that at the current
expert-move sample (116 train decisions, 30 held-out test decisions) this
genome and these two fitness formulations carry no signal that survives
contact with unseen data. The two concretely stated re-test conditions still
open are a materially larger expert-move sample from a future dump, or a
different region of weight space with an observed non-flat held-out gradient;
a third attempt at the same configuration and sample size is explicitly not
expected to change the answer and is not planned.

## Attempt 3: teacher-student distillation at scale (2026-07-03, BLOCKED)

The prior section named two concrete re-test conditions and explicitly ruled
out a third attempt at the *same* configuration and sample size. This attempt
is not that: it targets re-open condition (a) directly, a materially larger
expert-move sample, using a different data source than the real-ladder replay
dump the first two attempts were capped by.

Instead of waiting for more real ladder games (rate-limited by the 5/day
submission quota and the opponents' pace, not by us), U83 builds a **teacher**:
the full search-stack build (determinized lookahead plus the learned evaluator
and move prior, all gates already green) at a generous per-move budget, playing
self-play games against the L5 bracket ring's opponents, the same ring
`tools/ring_calibrate.py` measured at tau 0.857 against real ladder scores.
`analysis/teacher_labels.py`'s `TeacherLogger` records every scorable MAIN
decision the teacher makes, win or lose, in the same `agreement()` contract
the real-replay move-ranking validator already used, so the CEM fitness
channel needed no new scoring logic, only a new label source.
`tools/teacher_selfplay.py` runs this harvest, and
`run_teacher_selfplay_parallel` splits it across worker subprocesses (default
`min(20, cpu_count)`, one native-engine singleton per process) rather than a
thread or multiprocessing pool, matching the L7 plan's "20-core parallel
gauntlet" line. `tools/harvest_status.py` tracks progress the correct way,
counting distinct games rather than decision rows, since one long game can
produce dozens of rows: by the time the CEM sweep below was launched, the
harvest had reached 1157 train-split games and 398 held-out test-split games,
roughly ten times the 116/30 real-replay sample the first two attempts were
limited to.

Two more pieces closed out before spending this larger sample on a real sweep,
both because the first two attempts' honest failures set a higher bar for the
third. First, `tools/cem_tune.py` gained a `--ring-matches` fitness channel
that plays the candidate genome against the same calibrated L5 ring (via the
existing `run_gauntlet` call, just a different opponent list) instead of the
older, uncalibrated U4 diverse pool the pooled-fitness attempt used, so the
win-rate half of the fitness function now points at the one proxy this project
has actually validated against ladder outcomes. Second,
`tools/cem_held_out_gate.py` automates the exact verdict rule the first two
attempts applied by hand, including the strictly-positive-not-merely-
non-negative reading of "non-negative held-out delta" that attempt 2's own
exactly-zero case forced: it runs the default and tuned genomes separately
against the held-out test split and returns WIN only on a strictly positive
agreement delta, BLOCKED otherwise, removing the chance of a third attempt
being graded more leniently than the first two just because a human was
tired of writing the same by-hand diff a third time.

A real sweep (`tools/cem_tune.py --population 16 --elite 4 --iterations 6
--injected-variance 0.05 --ring-matches 6 --pool-matches 0 --teacher-labels
data/training --limit 4000 --split train`, seed 0) ran to completion
(`analysis/cem_runs/u83_teacher_ring_seed0.json`, best training-side fitness
0.8940). `tools/cem_held_out_gate.py --result
analysis/cem_runs/u83_teacher_ring_seed0.json --teacher-labels data/training`
scored it against the clean held-out test split, now 10689 scorable MAIN
decisions (versus the first two attempts' 30): default agreement 0.8210,
tuned agreement 0.8189, delta **-0.0022**. Verdict: **BLOCKED**, the same
result as the first two attempts, this time at roughly two orders of
magnitude more data on both splits.

This is a materially stronger negative than it looks at first glance. The
pooled-run writeup (attempt 2) left one concrete re-open condition standing
for a future attempt: "(a) a materially larger expert-move sample." This run
was built specifically to answer that condition, not sidestep it, and the
answer came back negative: a ten-to-ninety-times larger corpus did not turn
the held-out sign positive, and the tuned vector was also worse than default
on its own held-out-clean full train split (0.8049 vs 0.8077), a result the
first two attempts did not even produce (they at least improved train
agreement, the metric being directly selected on, before failing to
transfer). The diagnosed mechanism matches attempt 2's own failure shape:
the CEM sweep's reported "best fitness" blended a high-variance 6-game ring
win rate with agreement over only a 4000-decision slice, so the optimizer's
actual selection pressure was dominated by opponent-noise rather than a
real, generalizing agreement gradient, the same proxy-metric-moves-backwards
problem a calibrated ring and a larger corpus did not fix. Full detail and
the source numbers are in `analysis/cem_run_prio_teacher.md`.

## Bottom line for the Strategy prize

This is the same discipline demonstrated in the offline-to-ladder transfer
writeup, applied to an optimizer instead of a proxy: a pre-registered,
non-negotiable held-out gate (fit on train, judged on test the tuner never
saw), applied three times, to three different fitness formulations and label
sources (small-sample agreement-only, small-sample pooled win-rate, then a
calibrated-ring win-rate blend at 10-92x the data scale), over a genome that
is a real, live, shipped-agent lever rather than an academic exercise. All
three attempts failed that gate cleanly, and each failure was named with a
specific mechanism (overfitting to a small train bucket; a fitness channel
moving backwards on its own training data; opponent-noise-dominated selection
pressure surviving a 92x data increase) rather than absorbed into a vague
"needs more tuning" note. The shipped heuristic's `PRIO_*` weights remain at
their hand-set defaults as a direct result: not because tuning was never
tried, but because three independent, honestly-reported attempts to improve
on them, including one specifically built to answer the prior attempt's own
named re-open condition, did not survive the same held-out bar every other
offline claim in this project has to clear.

The one re-open condition still standing, per `analysis/cem_run_prio_teacher.md`,
was a genome region with a measured non-flat held-out gradient, checked before a
full sweep is spent on it rather than assumed. At the time this was written the
comprehension track (U90-U94) was still open and named as the project's live
source for a candidate lever that might supply one; that track has since run to
completion (`docs/writeup/comprehension.md`) without surfacing one. Its two
shippable levers (the once-per-turn ability guard, the attack-first sequencing
rule) both went in as hand-coded, flag-gated `agents/heuristics.py` rules with
their own offline gates and ladder A/Bs, not as a new region of the 18-dim PRIO
vector, so neither one is a re-test case for CEM. Separately, U92's kill test
(same writeup, "The final answer on the objective itself") answered the
adjacent question of whether a different training objective could recover
signal from the harvested clone dataset, and it also came back negative.

### Condition (c) closed directly, not just left unanswered (2026-07-04)

Rather than wait for a new lever to supply a testable genome region, the
condition was checked head-on: `analysis/measure_cem_gradient.py` (the same
per-dim leverage probe that discovered the PRIO genome in the first place) was
extended with a `--teacher-labels`/`--split` mode so it could run against the
exact held-out `test` split (n=10689) the three CEM sweeps blocked on, instead
of a smaller, different sample. Result: the genome IS non-flat on this split
(max per-dim delta 0.2738, over 5x the original small-sample diagnostic's
0.0526), so "the genome has no signal at all" is ruled out as the explanation
for three straight BLOCKED verdicts. But every one of the four load-bearing
ordering dims (`PRIO_ATTACK`, `PRIO_ATTACH`, `PRIO_PLAY`, `PRIO_EVOLVE`) has
its shipped default sitting at or above both of that dim's bound readings, so
no single-axis move anywhere in the 18-dim space beats the current default.
This is a stronger result than another failed optimizer run: it explains the
mechanism (the held-out landscape slopes downward away from the shipped
default along every dim that matters, so any noisy optimizer is more likely to
step off the peak than climb it further) rather than just adding a fourth
data point to "still blocked." Full detail: `analysis/cem_gradient_condition_c.md`.

Conditions (a), (b), and (c) are now all closed. No further sweep over this
genome is planned; a fourth CEM attempt would need a genuinely new weight-space
region this genome does not currently express (e.g. a card-identity- or
archetype-aware weight), not a re-run of the existing 18 dims.
