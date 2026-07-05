# Engine Quirks: invariant fuzz findings (U101)

Method: tools/fuzz_invariants.py plays games through the local cabt engine,
intercepting every observation on both seats via the gauntlet wrapper pattern,
and evaluates state invariants at each observed state. Because zone accounting
is subtle (attached energyCards/tools/preEvolution, facedown prizes as None,
opponent hand as handCount only), each run first CALIBRATES the subtle
quantities over its first K clean games (I1 own-side card conservation, keyed
per seat and per plain-vs-effect-resolution context, and the I7
duplicate-serial baseline), then ENFORCES the calibrated relations plus the
hardcoded invariants (I2 HP bounds, I3 prize monotonicity, I4 bench size,
I5 non-negative deck count, I6 turn/result monotonicity) over the rest.

Standing observations from building the tool (verified against raw env steps):
- A card mid-resolution legally sits in no zone: own-side totals read 59
  instead of 60 exactly when the select carries an effect/contextCard. The
  context-keyed calibration turns that from noise into a sharp invariant.
- The final recorded env step holds stale per-seat observation copies and no
  recorded observation ever exposes result != -1, so only live observations
  are scanned.

Violations stream one compact JSON line each (no raw state dumps) to
analysis/engine_quirks_fuzz.jsonl. A clean run is also a result: every run
appends its games and states scanned below.


## Run 2026-07-05T11:33:48+00:00 (shard 0)

- command: `tools/fuzz_invariants.py --games 30 --agents mixed --seed 0 --shard 0 --calibrate 5`
- games: 30 requested, 30 completed (5 calibration, 25 enforced), 0 crashed
- states scanned: 1161, checker internal errors: 0, duration: 7.9s
- calibration: I1 own-side totals per seat {'seat0/effect': {59: 8, 60: 13}, 'seat0/plain': {60: 79}, 'seat1/effect': {59: 17, 60: 4}, 'seat1/plain': {60: 77}}; I1 skips {'looking_active': 8}; I7 benign duplicate serials none
- verdict: CLEAN, 0 violations over 25 enforced games (1161 states scanned)

## Run 2026-07-05T11:34:10+00:00 (shard 1)

- command: `tools/fuzz_invariants.py --games 10 --agents random --seed 7 --shard 1 --calibrate 5`
- games: 10 requested, 10 completed (5 calibration, 5 enforced), 0 crashed
- states scanned: 818, checker internal errors: 0, duration: 5.1s
- calibration: I1 own-side totals per seat {'seat0/effect': {59: 30, 60: 18}, 'seat0/plain': {60: 173}, 'seat1/effect': {60: 25, 59: 23}, 'seat1/plain': {60: 174}}; I1 skips {}; I7 benign duplicate serials none
- verdict: CLEAN, 0 violations over 5 enforced games (818 states scanned)
