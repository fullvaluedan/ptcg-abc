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

## What three failures in a row actually means

Three different offline designs, of increasing sophistication and cost to build,
have now been checked against the same ladder-truth bar and none has cleared it:
a banned weak-bot pool, a real-move-agreement validator that surfaced a genuine
capability gap but was never itself calibrated as a gate, and a top-player clone
ring built for exactly this purpose that still landed at tau 0.429, little better
than a coin flip at ordering builds correctly. `analysis/ring_calibration.md`
names this directly: "every offline proxy tried so far... has failed to retrodict
the real ladder ordering well enough to be trusted as a gate." The loop's
response was not to lower the bar (drop the threshold, accept a partial pass, or
quietly start trusting a proxy anyway) but to fall back explicitly to ladder-only
judgment for future shipped-agent candidates, with strict slot discipline (at most
2 scored slots, 5 submissions/day) taking the place of an offline pre-filter.

This pattern only has teeth because of a second piece of measurement discipline
built earlier: the same-build noise model. Two byte-identical resubmissions of
the same king build read 600.0 then 594.7 in successive board checks
(state/current.md), and the wider unified plan calibrated a same-build spread of
roughly 90 to 130 points from repeated draws of near-identical builds. Every
pre-registered ladder A/B in this project uses a margin (M=60, roughly half that
band) precisely so that ordinary same-build noise cannot masquerade as a real
result. Without that noise floor already in place, a proxy reading "close enough"
on a handful of ladder games could have been mistaken for a working gate instead
of correctly identified as a failure; the two pieces of discipline (a hard
retrodiction bar for proxies, a hard noise margin for ladder verdicts) work
together to keep a convenient-but-wrong signal from being promoted to a decision
rule.

## Bottom line for the Strategy prize

The differentiated claim here is not "we found a working offline predictor of
ladder rank." We did not, after three attempts of increasing cost and
sophistication. The differentiated claim is that the project built a
machine-enforced rule for admitting that in advance (proxies are refused by
default and earn only the right to block, never promote, and only after clearing
a pre-registered tau bar), applied it consistently across three structurally
different designs, and reported every failure with a named, specific diagnosis
(non-predictive by construction; real but uncalibrated; a same-deck mirror
confound) rather than quietly lowering the bar until something passed. Combined
with the pre-registration protocol and the fitted same-build noise band, this is
the project's account of what does, and mostly does not, transfer from offline
testing to a real competitive ladder, and it is deliberately reported as
evidence in its own right rather than smoothed over on the way to a cleaner
narrative.
