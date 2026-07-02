# Final scoring semantics: the rules that fix U48 (plan U29)

**Answer: the latest-2 model is confirmed by the official rules, verbatim, and
corroborated by our own board evictions. Only your most recent 2 submissions are
tracked and used for final scoring; the leaderboard shows the best of those 2.
Submitting a 3rd agent drops the 3rd-newest out of the scored pair. There is no
best-ever safety net.** This resolves review deferred Q2 and fixes the U48
optimal-stopping design (KD8): every re-roll evicts the older scored submission,
so the pre-registered stop rule stands unchanged. This unit gates U48.

Source: the competition overview / submission-and-scoring section of
https://www.kaggle.com/competitions/pokemon-tcg-ai-battle (fetched 2026-07-02 via
a JS-rendering proxy; the raw page is client-rendered so a plain fetch returns
only the title). Corroborated by the observed eviction behavior on our own
Submissions page (the cheap probe U29 authorizes).

## Verbatim rules text

On which submissions count:

> "To reduce the number of agents playing and increase the number of episodes
> each team participates in, we only track the latest 2 submissions and use those
> for final submissions. On the leaderboard only your best scoring agent will be
> shown, but you can track the progress of all of your submissions on your
> Submissions page."

On continued play:

> "Every agent submitted will continue to play episodes until the end of the
> competition, with newer agents playing a much more frequent number of
> episodes."

On the deadline and final evaluation window:

> "At the submission deadline on August 16, 2026, additional submissions will be
> locked. From August 16, 2026 for approximately two weeks, we will continue to
> run games ... the leaderboard is final."

On the daily limit:

> "Each day your team is able to submit up to 5 agents to the competition."

On the rating model:

> Skill Rating "modeled by a Gaussian N(mu, sigma^2) where mu is the estimated
> skill and sigma represents the uncertainty"; after each episode "we'll update
> the Rating estimate" and "reduce the sigma terms relative to the amount of
> information gained"; "Newly submitted agents will be given an increased rate in
> the number of episodes run."

## The one ambiguity, resolved

Two sentences appear to conflict: "we only track the latest 2 submissions and use
those for final submissions" versus "every agent submitted will continue to play
episodes until the end." The decisive clause is **"use those for final
submissions"**: older agents keep playing some episodes (so their displayed mu can
still drift), but only the latest 2 are USED FOR FINAL SCORING. The
"best scoring agent" shown on the leaderboard is therefore the best of your latest
2, not the best you ever submitted. A good draw that falls out of the latest-2 no
longer counts. There is no freeze-and-keep-forever safety net.

Empirical corroboration (the U29 cheap probe): our own board shows exactly this.
Submitting the reclaim king (54252006) "evicts the oldest active meta copy
(archaludon 387.0)" and submitting trolley_thick (54252291) "evicts the below-floor
meta copy grimmsnarl 489.6." Each new submission drops one older agent out of the
scored set, and the set stays at size 2. This is precisely the "only the latest 2"
rule, observed live, not inferred.

## What this fixes for U48 (optimal-stopping final-pair campaign)

1. **KD8's core assumption holds.** "Every re-roll evicts the older scored
   submission" is literally true: a 3rd submission drops the 3rd-newest out of the
   scored pair, and that draw is gone. So the pre-registered stop rule is correct
   as written: **never roll past a good draw**, because rolling forward discards
   the older half of the pair.

2. **The final pair is two independent draws and the leaderboard takes the max.**
   Because both latest-2 keep playing and the shown score is the best of the two,
   the final pair is not forced to be two identical king copies. Two mechanically
   different builds of near-equal true skill give two independent samples from the
   rating distribution, and max(two independent good draws) beats a single draw. A
   within-M, mechanically different hedge therefore has positive expected value.
   This confirms the plan's U48 approach unchanged: **default = two copies of the
   strongest settled build; a diverse hedge only if the runner-up is within M and
   mechanically different.** No design change; the rules validate it.

3. **The two-week post-deadline window shrinks sigma, not mu.** After Aug 16 no
   new submissions are accepted and games continue for ~2 weeks purely to reduce
   rating uncertainty on the locked latest-2. More episodes means sigma keeps
   contracting, so a genuinely strong pair converges upward toward its true mu and
   a lucky-but-weak pair regresses down. This favors locking a genuinely good pair
   over a high-variance late gamble, and it means the Aug 15 lock (with a full day
   of slack) loses almost nothing to the extra convergence that happens anyway.

4. **No-roll buffer is confirmed sound.** Hard no-roll buffer from Aug 14 12:00
   UTC, final pair locked by Aug 15: this sits safely inside the Aug 16 23:59 UTC
   deadline. Because only the latest 2 count and there is no best-ever net, the
   buffer is not optional caution but a correctness requirement: any submission
   after the intended lock evicts a good draw with no way to get it back.

5. **Daily budget is 5 submissions/day** (matches the loop's quota rule). The
   binding resource remains settled verdicts, not slots; the 5/day cap is not the
   constraint.

## Residual uncertainty and re-probe condition

The rules text does not spell out, to the letter, whether a deactivated agent's
displayed mu is frozen or keeps drifting on the reduced episode rate. This does
not affect any U48 decision above, because only the latest 2 are used for final
scoring either way. If a future unit ever needs the deactivated-agent drift
behavior (it does not today), re-probe by watching an older submission's score on
the Submissions page across two board checks after it leaves the latest-2. Recorded
2026-07-02; not revisited unless a U48 decision comes to depend on deactivated-mu
drift.

## Default if this had been unresolved

The plan's conservative default (two copies of the king, locked by Aug 15) would
have held. It is not needed: the rules resolved cleanly, and the resolution keeps
that default as the U48 base case while explicitly permitting the within-M
mechanically-different hedge.
