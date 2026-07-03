# The RETREAT gap is not an injury threshold: 76% of missed retreats are at full HP

## Finding

`analysis/move_ranking_diverges_ability_gap.md` named RETREAT the pilot's worst
category (2/202, 1.0% exact-target agreement). This is the first conditional
mining of WHY: `analysis/retreat_gap_miner.py` runs the shipped pilot AND the
shipped `should_retreat` HP-ratio rule (agents/heuristics.py) directly against
the real board state at every expert RETREAT decision, isolating whether the
low number is an ordering artifact, an HP-threshold miscalibration, or
something the current rule cannot model at all.

## Evidence (analysis/retreat_gap_miner.py, 2026-07-02 dataset, limit 1500)

```
expert teams: kazuki0123, tonakaiiii, The Debauchery Tea Party
real expert RETREAT decisions scored: 689
  agree           16    (2.3%)
  preempted       59    (8.6%)
  threshold_miss  614   (89.1%)

threshold_miss active hp ratio at decision time (0.1-wide bins):
  0.3-0.4: 23
  0.4-0.5: 29
  0.5-0.6: 44
  0.6-0.7: 26
  0.7-0.8: 14
  0.8-0.9: 14
  0.9-1.0: 464
```

(This run's decision count, 689, is larger than the earlier 202 because it
reads the newer 2026-07-02 dump rather than the dataset behind the original
`move_ranking_diverges_ability_gap.md` reading; the shape of the finding, not
the exact count, is what matters here.)

Only 8.6% of the miss is ordering (`should_retreat` already agrees, a
higher-priority develop category ran first that same decision, and the retreat
would still land later the same turn -- the same benign artifact
`energy_seq_refuted_by_expert_moves.md` found for ATTACH). The overwhelming
majority, 89.1%, is a genuine threshold_miss: `should_retreat` says False on
the real state, so the pilot never even considers retreating.

The threshold_miss bucket itself breaks in an unexpected way: **464 of 614
(75.6%) happen when the active is at 90-100% of its max HP**, i.e. barely
damaged or fully healthy. Splitting the pilot's actual pick by HP band:

```
high-HP (>=0.9) threshold_miss, n=464:
  ATTACK:162  END:128  PLAY:127  ATTACH:26  EVOLVE:21

lower-HP (<0.9) threshold_miss, n=150:
  ATTACK:108  PLAY:29  END:7  ATTACH:5  EVOLVE:1
```

## Interpretation

`RETREAT_HP_RATIO` (default 0.34) encodes "retreat when hurt", and the small
lower-HP threshold_miss tail (150/614, the 0.3-0.8 bins) is the part that
knob could plausibly reach by raising the ratio. But raising the ratio cannot
touch the dominant 464/614 case: these are top players retreating a Pokemon
that is barely hurt at all. That is not an injury decision, it is a **tempo /
matchup swap**: bringing in a specific bench attacker (a favorable
type matchup, a Pokemon that can now score a knockout the active cannot, or
one whose ability/attack the current board state calls for) regardless of the
active's health. `should_retreat`'s only two inputs (own HP ratio, "is any
bench mon at higher raw HP") cannot represent this by construction: a full-HP
active with a full-HP bench has no HP-based reason to ever consider retreating
in that model, no matter how bad its current matchup is.

## Why this is not a shippable lever yet

Unlike the ABILITY gap (a total capability hole, one clean flag) or the
confirmed-refuted ATTACH sequencing lever, this finding does not yet name a
specific, cheap rule: "swap to a better matchup" requires type
effectiveness / weakness-resistance knowledge and a notion of "which bench
attacker is better against the current opponent active" that the heuristic
does not have today. Shipping a guess here risks the same shape of refutation
`energy_seq_refuted_by_expert_moves.md` already hit once. The concrete next
step (not yet built) is to mine what changes on the bench-vs-opponent matchup
across these 464 decisions (weakness/resistance flags, attack damage deltas)
to see whether a cheap, well-defined "promote the better matchup" rule exists
before any flag is written.

## Conclusion

RETREAT is confirmed a real, large, and previously uncharacterized category
gap, but it is a matchup-awareness gap, not a threshold-tuning gap. Recorded
here so a future unit does not waste a lever on `RETREAT_HP_RATIO` (it would
touch at most ~24% of the miss) and instead scopes a matchup-based retreat
rule against this same miner before any ladder-facing change.

**Update (analysis/retreat_target_conditional.md):** the matchup-swap theory
above was a plausible read of the HP-band shape but had not actually been
measured against WHICH bench mon top players bring in. Once measured
directly (the `SelectContext.SWITCH` target decision, via the new
`analysis/retreat_target_miner.py`), it is refuted: only 22.9% of high-HP
retreat targets actually have a better type matchup than the outgoing
active. The 89.1% MAIN-decision gap this doc characterizes is still real and
still open; its cause is not yet identified.
