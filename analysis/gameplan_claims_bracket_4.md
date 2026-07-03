# Game-plan claim/prediction gate results, bracket_4 (U91 step 2)

## What this is

`analysis/gameplan_claim_gate.py` (U91 step 2) puts the three new within-turn
blocks (plan U91, comprehension track) through two honesty gates before any
result counts as a finding:

- **CLAIM GATE**: winning and losing splits each carry >= 200 qualifying
  observations, and a bootstrap 90% CI on mean(win) - mean(loss) excludes
  zero (the gap is real, not sampling noise, on the data it was mined from).
- **PREDICTION GATE**: the same pattern, mined on the KD4 TRAIN split only,
  must have its winning-side estimate replicate on the KD4 TEST split (the
  test split's point estimate must fall inside a bootstrap CI built from
  train alone). A pattern that only describes the training slice is cut.

A block's verdict is CONFIRMED only when both gates pass.

## Target and command

`bracket_4` was chosen because U91 step 1 already validated the fixed
attach/play resolvers reach 1.000 resolution on this family (the two named
meta families, meta_archaludon/meta_grimmsnarl, still cannot be mined at all
under the current decks/ directory; see the still-open archetype-registry
shadowing note below). Signatures must be built with `--decks-dir decks` so
the bracket_1..6 archetypes actually load; the plain `build_signatures(None)`
default silently mines zero appearances (a real footgun, worth noting for
whoever runs this next).

```
.venv/Scripts/python.exe -m analysis.gameplan_claim_gate \
    data/episodes/pokemon-tcg-ai-battle-episodes-2026-06-30.zip bracket_4 \
    --decks-dir decks --out gameplan_claims_bracket_4.json
```

Full dataset, no `--limit`: 1561/1699 winning/losing appearances on the KD4
train split, 530/587 on the KD4 test split.

## Results

| block | claim gate | prediction gate | verdict |
| --- | --- | --- | --- |
| attach_before_attack | n=1472/1446, win 0.524 vs loss 0.558, CI (-0.064, -0.003) | train_ci (0.503, 0.545) brackets test_mean 0.510 | **CONFIRMED** |
| energy_banking | n=1822/1892, win 0.192 vs loss 0.236, CI (-0.066, -0.022) | train_ci (0.177, 0.208) brackets test_mean 0.200 | **CONFIRMED** |
| game_length_turns | n=1561/1695, win 1.905 vs loss 1.972, CI (-0.145, 0.014) | train_ci brackets test_mean, but claim already failed | CUT (claim gate fails, CI straddles zero) |

## Reading the two confirmed blocks

- `attach_before_attack` is a per-turn flag, true only on turns with BOTH an
  ATTACH and an ATTACK that same turn, true when the ATTACH came first.
  Winning bracket_4 play attaches-before-attacking on 52.4% of such turns
  vs 55.8% on losing turns, a real but modest (~3.4pp) gap: winners lean
  very slightly more toward attacking first (or skipping the same-turn
  attach) than losers do. Small effect, but it clears both gates at n>1400
  per side and replicates on 473-591 held-out turns the pattern was never
  mined from.
- `energy_banking` is a per-turn flag, true on ATTACH turns with NO attack
  that same turn (energy attached ahead rather than spent immediately).
  Winning play banks energy on 19.2% of its ATTACH turns vs 23.6% for
  losing play, a larger (~4.4pp) and same-direction gap: winners bank energy
  LESS often than losers. This replicates too (test mean 0.200 sits inside
  the train CI).
- `game_length_turns` (a per-episode count, not per-turn) shows winners
  finish in slightly fewer turns (1.905 vs 1.972) but the gap does not clear
  the claim gate (CI straddles zero, -0.145 to +0.014) even at n>1500 per
  side. Cut. Note bracket_4 games are short overall (median ~2 turns per
  seat in this slice), so the timing signal may simply be too compressed on
  this family to separate; not re-tested on a longer-game family this
  iteration.

## Caveats before this feeds U93 (ladder transfer)

- Both effect sizes are small (3-4 percentage points). They are real
  (gates passed) but not necessarily large enough to move the ladder; U93's
  own gate (bracket-ring A/B >= +5pp) is the next honest check, not this
  claim/prediction pair.
- These are DESCRIPTIVE (what winners do more/less often), not yet
  PRESCRIPTIVE (whether nudging our own pilot toward the winning-side
  behavior actually helps it win). Correlation in the mined data does not
  by itself establish that if our pilot banked energy less, it would win
  more; bracket_4 opponents who bank energy less may simply be ahead on
  board already for unrelated reasons (attacking is available because they
  are winning, not the reverse). U93 must design the flag-gated rule and
  A/B it, not just port the correlation directly.
- Still open from step 1: meta_archaludon/meta_grimmsnarl cannot be mined
  end to end (the bracket_1..6 archetype csvs shadow them alphabetically in
  `classify_family`'s coverage tie-break, see
  `analysis/gameplan_target_resolution_fixed.md`). This run used bracket_4
  as a stand-in family; a like-for-like re-mine of the two named meta
  families is still blocked on that registry fix.

## Tests

`tests/test_gameplan_claim_gate.py`: bootstrap primitives pinned on
hand-built data (constant input collapses the CI to a point, empty input
returns `(None, None)`, same seed reproduces), `claim_gate`/`prediction_gate`
exercised on synthetic categorical/timing blocks (below-min_n fails even with
a clean separation, enough-n-plus-real-gap passes, identical win/loss
distributions fail on a straddling CI), and a live wiring test over a tiny
synthetic replay directory confirming the KD4 train/test split is read off
`replay_trace.split_of` (the same partition every other held-out number in
this project uses) and that `run_gates` reports a verdict per `CLAIM_BLOCKS`
entry. Full suite: 1109 passed.
