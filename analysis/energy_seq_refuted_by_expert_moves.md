# Energy sequencing (PTCG_ENERGY_SEQ) is refuted by the top players' own attaches

## Finding

The move-ranking breakdown named ATTACH as the experts' most common action and our
second-worst category (lever #2 in analysis/move_ranking_diverges_ability_gap.md:
87/1445 = 6.0% exact-target agreement). The substitution row shows WHY the number is
low in two distinct ways:

```
ATTACH   -> PLAY:538, ATTACK:452, ATTACH:241, EVOLVE:214
```

Of the 1445 real expert ATTACH decisions, our pilot attaches on 241 of them but only
87 hit the exact target the expert chose, so ~154 are wrong-target attaches. The rest
are ordering: we PLAY, EVOLVE, or (on a lethal) ATTACK at the moment the expert front-
loads energy. The `PTCG_ENERGY_SEQ` lever exists precisely for the wrong-target half:
once the active can already pay for its cheapest attack, it steers surplus energy onto
the strongest still-underpowered benched attacker instead of overloading the front line.
The doc said this candidate reordering "can be scored against this same validator before
any slot is spent." It now has been.

## Evidence (analysis/move_ranking_validator.py --breakdown, real dataset, limit 1500)

Same 4524 held-out expert MAIN decisions in 131 of the top players' games, exact-index
top-1 agreement. Baseline is the shipped heuristic (all flags off).

```
                    baseline   PTCG_ENERGY_SEQ=1
  top-1             0.212  ->  0.210   (-0.002)
  ATTACH  87/1445   0.060  ->  0.053   (77/1445, -10 exact matches)
  PLAY              0.263  ->  0.263   (unchanged)
  ATTACK            0.770  ->  0.770   (unchanged)
  EVOLVE            0.570  ->  0.570   (unchanged)
```

The ATTACH substitution row is byte-identical between the two runs: we still attach on
the same 241 decisions. Sequencing did not convert a single ordering miss (PLAY / ATTACK
/ EVOLVE) into an attach, because it only changes the target once we are ALREADY in the
attach branch. And on the 241 we do attach, it moved 10 of them AWAY from the expert's
target (87 -> 77), never toward it.

## Conclusion: refuted, kept off

The top players do NOT redistribute surplus energy onto a bench payoff attacker the way
this lever does. Powering the active first (the default `_choose_attach` behavior) matches
their attaches strictly better than sequencing does. The ~154 wrong-target attaches are
therefore not an active-vs-bench misallocation; whatever drives them (which specific bench
slot, a target the greedy default and the expert both miss), steering energy to the bench
is the wrong correction and makes agreement worse.

This is the same shape as the PTCG_BENCH_DIG refutation: a plausible pilot lever that a
weak-bot gauntlet could have rationalized, killed cleanly by the one distribution we cannot
fake (real top-player decisions) BEFORE it cost a ladder slot. `PTCG_ENERGY_SEQ` stays
default-off and is now documented as refuted; the flag and its measurement (this validator
with the env var set) are kept so the refutation is re-runnable. Every shipped build stays
byte-identical.

## What this leaves for the ATTACH gap

The exact-target ATTACH miss is real (154 wrong-target attaches) but is NOT an active-vs-
bench allocation error. A future lever would have to model WHICH energy type or WHICH
specific slot the top players attach to, scored against this same breakdown before any
ship. The ordering half (538 PLAY + 214 EVOLVE ahead of attach) is largely a single-
decision artifact: attach is once-per-turn and our develop-first order reaches it later in
the same turn, so over a full turn we still attach. The one ship-worthy lever the breakdown
has surfaced remains PTCG_ABILITY (0.212 -> 0.225, ABILITY 0/554 -> 0.139), which stays the
next single-variable ladder A/B once a slot is free.
