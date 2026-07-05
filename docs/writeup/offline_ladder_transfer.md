# The offline-to-ladder transfer problem (Strategy prize writeup)

This section is the honest-measurement chapter: every offline proxy this project
built to predict real Kaggle ladder outcomes, and what happened when each one was
checked against the ladder truth we actually have. It is a companion to
[learned_evaluator.md](learned_evaluator.md), which covers the model itself; this
section covers the harder, less flattering question of whether any offline signal
can be trusted to make ladder decisions for us.

## Why this needed a rule at all

Early in the project it would have been easy to build an offline gauntlet, watch a
candidate build win it, and ship the candidate on that basis alone. The risk is
that an offline proxy can look informative while measuring something the real
ladder does not reward: a gauntlet of weak built-in bots, for instance, rewards raw
aggression that a diverse field of real players punishes. So the project adopted a
single standing rule before trusting any proxy with a ladder decision
(analysis/proxy_calibration.md, U24): **no offline proxy may block a ladder slot
until it has retrodicted the ordering of builds we already have ladder truth for**,
scored by Kendall's tau against five (later six) known, real ladder results. A
proxy that passes earns the right to BLOCK a candidate; it is never trusted to
promote one. Every proxy starts refused by default. This is machine-checked, not a
guideline: `tools/loop_state.py check-gate --proxy <name>` returns refused unless a
passing calibration report exists.

The ground truth it must reproduce, as of this writing (analysis/proxy_calibration.md,
analysis/ring_calibration.md):

| build | ladder score |
|---|---:|
| heuristic + trolley | 569.6 |
| heuristic + benchguard | 554.5 |
| search + trolley | 514.7 |
| meta_grimmsnarl | 510.1 |
| trolley_thick | 446.2 |
| meta_archaludon | 382.5 |

## Attempt 1: the weak-bot mirror gauntlet, banned by construction

The first and cheapest offline signal available, built-in bots or self-mirrors,
was never even allowed to try. The loop brief treats it as non-predictive by
construction: a candidate that beats weak built-in opponents or its own mirror
tells you almost nothing about how it will do against the diverse field of real
players and decks on the ladder. `analysis/proxy_calibration.md` codifies this as
a standing exclusion: "the weak-bot gauntlet is banned from all gates regardless
of any tau it posts." No calibration run was ever spent on it, because the
project judged in advance that no plausible tau from that design would be worth
trusting.

## Attempt 2: the move-ranking validator, a real signal that still never gated

`analysis/move_ranking_validator.py` measures something different: not "does a
build win games" but "does our pilot choose the same move a real top player would,
decision by decision." Run over 4,524 real MAIN decisions from 131 top-player
games, the shipped heuristic agreed with the expert's exact choice only 21.2% of
the time overall, and the breakdown was not diffuse: it found a categorical blind
spot (0/554, 0.0% agreement on ABILITY decisions, because the pilot had no code
path that could ever choose one) alongside a strong ATTACK/EVOLVE agreement
(0.770 and 0.570) that needed no work (analysis/move_ranking_diverges_ability_gap.md).
That ABILITY finding was real and led directly to a shipped ladder change (L1,
the `PTCG_ABILITY` A/B, +4.0pp in its own offline gauntlet). But the validator
itself was never calibrated against the five/six-build ladder ordering above, and
its own docstring says why it should not be trusted to gate on its own: it is
"a RELATIVE filter, not an absolute skill measure... offline agreement is not the
ladder." It has always been used as an overfit filter on candidate changes, never
as a pass/fail gate on a ladder slot.

## Attempt 3: the calibrated clone ring (U70-U73), the most rigorous attempt yet

The clone ring was built specifically to fix what the first two attempts could
not: opponents cloned from real top-20 teams' recorded play (U70-U71), each
piloting that team's own harvested deck (U72), round-robined against the six
known builds above and graded with the same Kendall-tau math as the U24 rule,
at a slightly relaxed threshold (tau >= 0.7 instead of 0.8, pre-registered to
account for the ring's own match-count noise on top of any true signal).

The result, run twice independently for a robustness check: **tau = 0.429** on
the first reading (10 concordant, 4 discordant, 1 tie dropped, 6 of 6 builds
covered) and **tau = 0.286** on a second, independent set of match draws
(analysis/ring_calibration.md). Both fail the 0.7 bar clearly; this was not a
borderline call decided by one unlucky draw. The ring got the top of the
ordering right (heuristic+trolley ranked first in both real and ring scores) but
badly inverted the middle: it overrated trolley_thick (ring rank 2, real rank 5)
and badly underrated meta_grimmsnarl (ring rank 6, real rank 4). The
meta_grimmsnarl miss has a diagnosed structural cause, not just noise: one of the
three ring opponents happened to pilot the exact same decklist as the build under
test, so a third of its games were an accidental mirror match, which drags any
build's measured win rate toward 50% regardless of true quality. That is a
concrete, fixable bug in ring construction (exclude a build's own-deck clone from
its own ring), but it was diagnosed only after the gate had already failed, which
is itself the point: a plausible-looking proxy can fail for a specific, discoverable
reason, and finding that reason after the fact is not the same as trusting the
proxy in advance.

## Attempt 4: the bracket-band clone ring (U81), the first proxy to pass

Three different offline designs, of increasing sophistication and cost to build,
had been checked against the same ladder-truth bar and none had cleared it: a
banned weak-bot pool, a real-move-agreement validator that surfaced a genuine
capability gap but was never itself calibrated as a gate, and a top-player clone
ring built for exactly this purpose that still landed at tau 0.429, little better
than a coin flip at ordering builds correctly. `analysis/ring_calibration.md`
named this directly at the time: "every offline proxy tried so far... has failed
to retrodict the real ladder ordering well enough to be trusted as a gate."

The U73 postmortem had already named a specific, fixable cause for that failure:
the ring's opponents were clones of the top-20 leaderboard, not the ~450-750
rating band the ladder's matchmaking actually pairs us against, and one of the
three opponents happened to mirror a build-under-test's own decklist, dragging
that build's win rate toward 50% regardless of true quality. U81 tested that
diagnosis directly rather than assuming it: `tools/bracket_decks.py` harvested
decklists from real opponents in our own rating band, `tools/bracket_select.py`
built a nine-clone ring from them (six bracket clones plus the original three
meta clones), and the same U73 gate math (`tools/ring_calibrate.py`, unchanged)
was re-run at N=20 games/build against the same six known ladder scores. Result:
**tau = 0.857** (13 concordant pairs, 1 discordant, all 6 builds covered), clearing
the 0.7 bar with the single opponent-pool variable changed and nothing else
(analysis/ring_calibration.md). The one miss (trolley_thick ranked one spot too
high) is a much smaller error than U73's badly-inverted middle of the ordering.

This is now the first offline proxy in the project's history to earn gate
authority: per the pre-registered rule, it can BLOCK (never promote) future
TRACK L candidates. It has since been used twice, with two different ladder
outcomes, both instructive.

U74 re-scored the already-staged `PTCG_ABILITY` lever through the ring
(20 games/arm) and got the same directional answer as the original weak-bot
gauntlet, off 65.0% vs on 85.0% (+20.0pp), agreeing in direction with the
gauntlet's own +4.0pp reading and with the pending pre-registered ladder A/B
(analysis/ability_ring_check.md). That ladder A/B first read as a **WIN**,
561.1 vs the 494.8 king, +66.3pp, clearing the M=60 margin cleanly
(state/current.md). A subsequent noise recalibration (below) reclassified that
single reading as inconclusive, not confirming: 561.1 sits mid-range of the
same king build's own 452-691 read spread, well inside noise. The ring and the
gauntlet still agree with each other; the ladder single-read cannot add or
subtract from that agreement, and is no longer treated as if it could.

Both offline signals were later checked for a specific measurement flaw: the
`PTCG_ABILITY` flag is a single process-global, and every gauntlet
`deck:<name>` opponent runs the SAME heuristics module in the SAME process, so
the "on" arm's opponents played with the ability lever too, not just our
pilot. Deconfounding the gauntlet (`analysis/ability_isolated_confound_check.md`,
900 isolated-arm games) found its +4.0pp was noise-dominated regardless, mean
diff_pp near zero either confounded or not. Checking the ring for the same flaw
found something different: its clone opponents never call the module's
decision function at all, so they structurally never read the flag,
confounded or not (`analysis/ability_ring_confound_check.md`, code-traced and
regression-tested). The ring's +20.0pp was already a clean, one-sided
measurement; it is the gauntlet reading, not the ring reading, that turned out
to be the unreliable one.

U93's `PTCG_ATTACK_FIRST` lever was checked the same way before it spent a
slot: gauntlet +5.5pp, ring +10.0pp, same direction
(analysis/attack_first_ring_check.md). Its ladder A/B did not confirm that
agreement, but it did not contradict it either: the first board reading fell
inside the M=60 noise band, the pre-registered repeat resubmission then
drifted to the opposite sign under ordinary same-build noise (one reading
below the king, one well above), and the fallback tiebreak (a shared-
opponent-bracket scoreboard, analysis/episode_scoreboard.py) came back
NEUTRAL on only 3 decisive candidate episodes, far short of the N=30 the
pre-registration budgeted for (analysis/attack_first_settlement.md). The
honest reading is that this is a sample-size NEUTRAL, not a case where a
proxy that agreed offline was then refuted on the ladder: the ladder never
accumulated enough decisive games to outvote its own noise floor before the
settle-by date. The ring's job was only ever to predict direction, not to
substitute for the N=30 the ladder verdict itself still requires, and this is
the project's first concrete example of that gap: a passing offline gate does
not guarantee the ladder produces a confirming sample in time.

## What four attempts, three failures and one pass, actually mean

The loop's response to the first three failures was not to lower the bar (drop
the threshold, accept a partial pass, or quietly start trusting a proxy anyway)
but to fall back explicitly to ladder-only judgment for future shipped-agent
candidates, with strict slot discipline (at most 2 scored slots, 5 submissions/
day) taking the place of an offline pre-filter, while diagnosing exactly what
each failed proxy got wrong. That diagnostic discipline is what made the fourth
attempt possible: U81 did not build a fundamentally new or more sophisticated
ring, it changed exactly the one variable the U73 postmortem had already named
as the likely cause of failure (which opponents the ring uses) and re-ran the
identical gate math. The lesson this project can now report with real evidence
behind it is that matching the offline proxy's opponent distribution to the
actual distribution the ladder score was earned against mattered more than any
amount of added model sophistication; the three earlier, cheaper designs never
had a chance regardless of how the gate math itself was computed, because they
were all measuring performance against the wrong field.

This pattern only has teeth because of a second piece of measurement discipline
built earlier: the same-build noise model, and that model itself went through an
honest correction worth reporting alongside the four proxy attempts above.

The original estimate, from two byte-identical resubmissions of the same king
build (600.0 then 594.7 in successive board checks), put the same-build spread
at roughly 90 to 130 points, and every pre-registered ladder A/B in this project
used a margin (M=60, roughly half that band) sized to that estimate. As more
same-build resubmissions of a single king ref (54282104) accumulated, the true
spread turned out to be far wider: 452, 507, 534, 558, 600, 648, 691, a range of
roughly 452 to 691 on byte-identical code (the first, ref-scoped correction,
`noise_model` v1-corrected). M=60 was too tight by close to an order of
magnitude; a same-build build can drift more than 200 points on its own without
any code change at all. The concrete cost of the underestimate showed up
immediately: the recorded ABILITY lever "WIN" above (561.1 vs a 494.8 king
draw, +66.3pp) cleared the old M=60 margin easily but sits squarely inside the
corrected 452-691 band, so it is now read as a noise artifact rather than a
confirmed result. A further board check then pushed the estimate wider still:
pooling every byte-identical `heuristic+trolley` reading across its FULL
resubmission history (five different refs, not just 54282104) rather than one
ref's own readings, the observed spread is 396.7 to 691.5 (`noise_model` v2,
`margin_M` 150, `state/current.md`). The direction of the correction has been
consistent both times, wider rather than narrower, which is itself informative:
this project's same-build noise has been underestimated on every attempt to
pin it down so far, not just the first one.

The standing response was not to keep patching M upward and re-trusting single
ladder reads at a wider margin, but to change which instrument gets to decide:
the calibrated bracket ring (tau 0.857, Attempt 4 above), not a single ladder
board reading, is now the gate that lever decisions defer to. Ladder
submissions still matter, but for two narrower jobs: holding the best
ring-supported build in the scored floor slot, and, from 2026-08-10 to 08-16,
an explicit endgame variance-harvest campaign that treats the wide same-build
band as the cheapest source of rank points remaining, rather than something to
fight with tighter margins. Without the ring already existing as an
independently calibrated backstop, this correction would have left the project
with no trustworthy way to decide lever questions at all; the two pieces of
discipline (a hard retrodiction bar for proxies, and being willing to admit a
hard-won noise margin was still wrong and re-point decision authority
accordingly) together keep a convenient-but-wrong signal from being promoted to
a decision rule.

The same discipline (check the instrument instead of trusting a convenient guess)
surfaced once more in routine board-checking. The scored king-copy slot
(ref 54315565) read an identical 423.5 across six consecutive board checks
while its sibling scored slot kept drifting normally. The first-pass guess was
that the leaderboard's re-scoring cadence for that ref had simply fallen out of
step with the check cadence. That guess was never verified until it had to be
repeated a fourth time; at that point `tools/scout.py episodes <ref>` was used
to compare the newest completed episode id per tracked ref, a monotonic counter
shared across the whole competition. The frozen ref's newest episode id had not
moved at all across six checks, while the sibling ref's kept climbing (roughly
2200 higher at the time of the check, later confirmed still climbing on a
seventh check). The submission had simply stopped being scheduled for new
matches; the frozen score is a mechanical consequence of that, not a scoring
lag. This is a small finding on its own, but it is the same pattern as the
proxy-ring story above at a much smaller scale: an unverified explanation that
sounded reasonable was allowed to stand for several iterations before someone
checked it against a concrete, checkable signal instead of repeating it.

A correction to that finding followed almost immediately, and is itself
worth recording: on the next board check after six unchanged reads, the same
ref's newest episode id had advanced again (from the frozen 83757916 to
83768597), and its score moved for the first time (423.5 to 443.1). The
"stopped being scheduled" diagnosis had been correct about what was happening
at the time, but wrong about permanence; it described a temporary scheduling
gap, not a stable end state for that submission. The lesson is one level up
from the one above: verifying an explanation against a concrete signal makes
the explanation trustworthy at the moment it is checked, not trustworthy
forever. A diagnosis that has held for six checks in a row can still need
revising on the seventh, and the fix is the same discipline applied again
(re-check the concrete signal) rather than either assuming permanence or
distrusting the original check.

That correction itself needed a further caveat a few checks later: the same
ref (54315565) went on to freeze at 443.1 for seven MORE consecutive board
checks, its newest episode id unmoved the entire time, a longer stretch than
the original six-check gap that had just resolved. Meanwhile its sibling
scored slot (the ability-floor ref, 54315802) kept climbing normally, then
also froze for six checks of its own before resuming play, breaking its
freeze at the exact moment the king-copy ref's second freeze was still
holding. The two refs' quiet periods do not move together: a submission can
stop being scheduled, resume, and stop again, independently of whatever a
scored sibling submission is doing at the same time. "Resolved" only ever
means resolved at the moment it was checked, not resolved permanently; the
concrete signal (newest episode id per ref) has to be re-checked every time,
not assumed to hold just because it held once before.

The king-copy ref's second freeze (443.1, starting after the 423.5/443.1
transition above) ran for ten consecutive board checks before this section was
last updated, longer than its own first freeze (six checks) and longer than
the ability-floor ref's one observed freeze (six checks, then resumed). There
is no evidence yet of a fixed or predictable freeze length for either ref;
each quiet period has so far ended up a different duration than the last one
observed. The operational takeaway is narrow but load-bearing for anyone
reading a single board check as a signal: a static reading of any length,
including a fairly long one, is not on its own evidence that a submission has
permanently stopped scoring, only that it was not scheduled for a new match
between the two checks being compared.

## A parallel thread: category mining converges on archetype awareness, and a gate closes it

Attempt 2's move-ranking validator (analysis/move_ranking_diverges_ability_gap.md)
did not just surface the ABILITY blind spot; analyzing the same 4,524 real top-
player decisions, it also named RETREAT and the post-knockout PROMOTE decision
as low-agreement categories (0.0% and 0.4% vs the 0.770 ATTACK agreement),
worth root-causing to check whether they hid a cheap, shippable rule the way
ABILITY did. U82 (analysis/category_mining_v2.md) chased both, along with a
deck-search-pick check, against the real expert corpus to see whether any of
them could be explained by a single pilot-missing decision rule. None could,
and each was closed for a specific, measured reason rather than abandoned on a
hunch:

- **RETREAT** (analysis/retreat_gap_conditional.md, 163 real expert decisions
  analyzed): 89.1% of expert retreat decisions are a genuine threshold-miss on
  active HP, not an ordering artifact, and 75.6% of those happen when the
  active is at 90-100% HP (barely hurt), a condition the pilot checks correctly.
  A plausible follow-on theory, that top players swap to a better bench matchup
  regardless of active HP, was measured directly: when experts retreat a high-HP
  active, they bring in a new active only 22.9% of the time with a better type
  matchup than the outgoing one (analysis/matchup_delta.py). The missing signal
  is not a simple energy/HP/matchup field but something about the game state
  context the five measurable fields do not capture.

- **PROMOTE** (analysis/promote_gap_conditional.md, 91 post-knockout decisions):
  the pilot has no rule for promotion after opponent knockout (pure `_first_legal`).
  Six candidate signals (type matchup, bench energy, combined energy-then-matchup,
  immediate-knockout check, and others) were checked against real expert picks.
  The best of them (energy-then-matchup) explains only 40.7% of real choices,
  not a majority, and the immediate-knockout check never applies (0/91 decisions
  in this dataset). Like the RETREAT miss, the gap is not a single measurable field
  but something about the decision context.

- **Deck-search picks** (analysis/category_mining_v2.md): checked whether the
  pilot's card-pick decisions during deck-construction differ from expert plays,
  a potential gap if experts have a game-plan-aware search strategy. Analysis
  found the picks were category-explained by the pilot's existing weighted-random
  search logic rather than revealing a distinct gap; no further mining was needed.

Every one of these threads independently converged on the same diagnosis: the
pilot lacks high-level awareness of the current game plan or archetype the hand
is building toward, and tries to solve context-dependent decisions (which bench
to promote, which active to retreat) with isolated state fields (HP, energy,
matchup) instead. The missing capability is not in any individual card mechanic
but in state aggregation at the game-plan level. U9a/U9b
(docs/plans/2026-07-03-addendum-u9-archetype-detection-v1.md) tested this idea
head-on: building an early-turn archetype classifier that could feed game-plan
state to higher-level decisions, trained on 140 real ladder games labeled with
the deck family they were playing (analysis/archetype_prior_train.md). The
pre-registered gate required the held-out accuracy margin over a majority-class
baseline to clear +5.0 percentage points, averaged across five held-out splits;
it landed at **+4.3 points**, a narrow, unambiguous miss.

Per the addendum's own rule, a failed gate blocks downstream work: no archetype-
prior model was exported, and nothing was wired into the search on the strength
of it. This closes the specific, most-obvious version of the "teach the pilot
the game plan" idea that mining independently converged on; it is not evidence
that the general idea is wrong, only that this implementation (a shallow
classifier trained on 140 games) did not meet the bar that was set for it.
Future work on this capability would need a different approach: more training
data, a richer feature set, or a fundamentally different state-aggregation
architecture, each of which would require a fresh pre-registration and gate.

## Bottom line for the Strategy prize

The differentiated claim is not "we tried three times and none of them worked,"
though that remains an honest part of the record. It is: the project built and
enforced a machine-checkable discipline for proxy development (proxies refused
by default, earning only the right to block and only after clearing a
pre-registered tau >= 0.7 retrodiction bar against known ladder outcomes),
and applied it consistently across four structurally distinct proxy designs.
The first three failed with named, specific diagnoses:

1. **Attempt 1**: Weak-bot gauntlet, refused by construction (non-predictive
   before any gate was even attempted).
2. **Attempt 2**: Move-ranking validator, a real signal of expert play
   agreement but never calibrated as a gate (and explicitly documented why it
   should not be trusted as one).
3. **Attempt 3**: Top-20 clone ring, the most rigorous attempt yet, still
   landing at tau 0.429, failing clearly. Post-hoc diagnosis: the ring's
   opponents were clones of the top-20 leaderboard, not the ~450-750 rating
   band the ladder actually pairs us against; one opponent happened to mirror a
   build-under-test's own deck, dragging that build's win rate toward 50%
   regardless of true quality.

On the **fourth attempt**, the project fixed exactly the diagnosed flaw: instead
of top-20 clones, harvested real opponents from our own ~450-750 bracket
(tools/bracket_decks.py, tools/bracket_select.py), built a nine-clone ring,
re-ran the identical gate math, and passed at **tau 0.857**, clearing the 0.7
bar decisively (analysis/ring_calibration.md). This is the first offline proxy
in the project's history to earn gate authority: it can block a candidate
(refuse to ship it) but never promote one, and only after real Kaggle matches
confirm or refute the ring's ranking.

In parallel, a second, independent discipline line (U82 category mining followed
by U9a/U9b's archetype classifier) applied the same "hard gate, no lowering the
bar" rule to a well-motivated capability hypothesis. Every named single-field
gap the move-ranking validator surfaced (RETREAT, PROMOTE, deck-search picks)
was chased to its root; each analysis converged on the same missing capability:
game-plan awareness at the archetype level, not any individual card mechanic.
U9a trained an early-turn archetype classifier on 140 real ladder games;
U9b's pre-registered gate required +5.0pp held-out accuracy margin over
majority-class baseline, averaged across five splits. Result: **+4.3pp**, a
narrow, unambiguous miss. Per the addendum's rule, nothing was shipped, and the
gate blocks U9c unless future work approaches the idea differently (more data,
richer features, different architecture). This is not evidence the idea is
wrong, only that this implementation did not meet its own bar.

Combined with the pre-registration protocol and the same-build noise band
(itself openly re-fit when real resubmission data showed the initial estimate
was roughly five times too narrow), this is the project's account of what does
and does not transfer from offline testing to a competitive ladder:

- **Offline proxies are not predictors by default**: Most fail, and failing is
  not evidence they are measuring the wrong thing; they may be measuring
  something real but under the wrong conditions (weak bots, wrong opponent
  pool, wrong sample size).
- **Diagnosis of failure often names a fixable flaw**: The top-20 clone ring
  failed not because cloning was the wrong idea but because the ring used the
  wrong bracket; fixing that one variable made the same ring structure pass.
- **A hard-won noise model can itself turn out wrong**: The initial same-build
  spread estimate (90-130 points) was roughly five times too narrow. Correcting
  it in the open, instead of quietly patching tighter margins into the protocol,
  is itself reportable evidence about how robust the noise estimate is.
- **A well-motivated capability idea can miss its own gate**: U9b did not fail
  because archetype awareness is not important, only because this specific
  implementation, trained on this much data, did not clear the bar. Future work
  remains possible, just contingent on a different approach and a fresh gate.

Each of these outcomes—three failures with diagnoses, then a pass, then an
honest gate-FAIL on a capability hypothesis—is reported as evidence rather than
smoothed over toward a cleaner narrative. The Strategy prize criterion (70%
model approach) is not whether the model is perfect, but whether the project's
approach to testing and admitting failure is trustworthy; that is what the
record demonstrates.
