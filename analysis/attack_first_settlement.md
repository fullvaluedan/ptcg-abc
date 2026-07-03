# U93/L9 heuristic+trolley-attack_first BAND settlement (U23 scoreboard)

Plan: state/current.md pre_registrations row for `heuristic+trolley-attack_first`. First board
reading (ref 54304483) landed BAND (526.8 vs king 494.8, diff +32.0, inside M=60). Per the
build's own pre-registered BAND action: one byte-identical repeat resubmission (ref 54304681),
then a U23 scoreboard tiebreak (analysis/episode_scoreboard.py) on shared opponent brackets at
~90% binomial confidence; else NEUTRAL and revert to king.

## Why the scoreboard, not just the two ladder numbers

By the time this iteration's board check ran, both readings had drifted from their settle-time
values under the documented same-build noise (state/current.md noise_model, ~90-130pt spread):
ref 54304483 read 442.9 (now BELOW the king's 494.8) and ref 54304681 read 600.0 (well above).
One positive, one negative reading is not a resolvable verdict from ladder points alone, so this
falls through to the pre-registered scoreboard tiebreak rather than being called by eye.

## Method

Downloaded real episode replays via `tools/scout.py pull` for all three refs (candidate's first
reading, candidate's repeat, and the frozen king comparison point):

- ref 54304483 (attack_first, first reading): 2 decisive real-opponent episodes
- ref 54304681 (attack_first, repeat): 1 decisive real-opponent episode
- ref 54282104 (reclaim-king, frozen comparison point): 42 decisive real-opponent episodes

Combined the two byte-identical attack_first refs into one candidate pool (5 games, 3 self-play
excluded automatically by `episode_scoreboard.outcomes_from_dir` -> wait, excluded via
`rows_from_dir`/`opponent_archetype.scan_dir`, leaving 3 decisive rows with a resolved opponent
bracket) and ran `analysis.episode_scoreboard.settlement` against the king's rows.

## Result

```
python -m analysis.episode_scoreboard data/replays_by_build/attack_first_combined data/replays_by_build/king_reclaim
```

- shared brackets (3): Marnie's Grimmsnarl ex, Fezandipiti ex, Mega Starmie ex
- candidate: 1/3 decisive on shared brackets (0.333)
- king: 4/6 decisive on shared brackets (0.667)
- confidence: 0.171 (well under the 0.90 bar)
- favors_candidate: **false**
- verdict: **neutral**

## Verdict and action

NEUTRAL. The scoreboard does not favor the candidate at 90% confidence (nowhere close: 0.171),
and the two raw readings no longer even agree in sign. Sample is small (3 candidate decisive
episodes on shared brackets) because this build had only just started accumulating ladder games;
the scoreboard is nonetheless the pre-registered tiebreak and gives a clean non-favoring read, so
per protocol this settles NEUTRAL rather than waiting for a larger sample the settle-by date does
not budget for.

Per the pre-registered BAND action for `heuristic+trolley-attack_first`: **revert the slot to a
king copy**. heuristic+trolley (shadow-king remains `heuristic+trolley-ability`, ref 54282097,
frozen 561.1) stays the reclaim-king. A byte-identical king-copy tarball was built and
grader-verified (`test_grader_submission.py[heuristic-trolley]`) this iteration
(`agents/agent_heuristic.py` + `decks/trolley.csv` + `_HEUR_EXTRAS`, no env flags), but the
Kaggle daily submission quota was already exhausted for 2026-07-03 UTC (6 submissions that UTC
day: 54281812, 54281824, 54282097, 54282104, 54304483, 54304681; prior loop notes tracking "2/5
used today" undercounted by only looking at the day's later batch). The API confirms: "Your team
has used its daily Submission allowance (5) today, please try again tomorrow UTC." The revert
submission is queued for the next iteration once the quota window resets (~00:00 UTC 2026-07-04).

The attack_first lever itself is not refuted by this NEUTRAL: the offline gauntlet (+5.5pp) and
calibrated bracket-ring (+10.0pp) gates it cleared before spending the slot are still valid
offline evidence. This is a ladder-sample-size NEUTRAL (3 decisive shared-bracket episodes is far
below the pre-registered N=30), not a directional refutation. Re-eligible for a future ladder slot
if the offline gates are re-checked and still hold; does not need new offline work to re-try.
