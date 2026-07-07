# U109 Oracle Bound Test, FAIL (2026-07-07)

## Summary

Same-run two-arm ring measurement against the calibrated 9-opponent bracket ring
(`tools/ring_calibrate.ring_names()`: bracket_1..6 plus meta_archaludon,
meta_grimmsnarl, meta_grimmsnarl_tonakaiiii). Arm A is the U112-confirmed
stacked incumbent (heuristic+yushin+ability+attack_first). Arm B is a
determinized search agent given each ring opponent's ACTUAL true decklist as
`opponent_prior` in `search/determinize.py`'s `determinize`, the best possible
opponent model an oracle rather than a learned approximation, selected per
matchup before the match starts. **Result: GATE FAIL.** The oracle-search arm
does not beat the stacked incumbent at all, let alone by the pre-registered
margin.

## Setup

- Tool: `tools/oracle_ring_test.py`.
- n = 40 games per arm, both arms measured in the same script invocation
  against the same 9 ring opponents, round-robin, alternating starting seat
  (`swap_first`) exactly like `tools/stacked_ring_u104.py` and
  `tools/ring_calibrate.py`.
- Arm A (stacked incumbent): pilots `decks/candidate_yushin_ito.csv` through
  `agents/heuristics.py` with `_ABILITY=True` and `_ATTACK_FIRST=True`, the
  exact build confirmed at n=100 in `analysis/u112_stacked_ring_confirmation.md`
  (arm 3, 0.860 win rate there).
- Arm B (oracle-search): also pilots `decks/candidate_yushin_ito.csv` (so the
  only difference from arm A is the opponent model available to search, not
  the deck), and at every searchable MAIN decision calls
  `search/rollout.py`'s `search_decision` with `opponent_prior` forced to the
  true 60-card decklist of whichever ring opponent it is currently facing,
  loaded from `decks/<family>.csv` via `tools/opponents.py`'s own
  `_read_deck_csv` (the same source of truth the opponent itself plays). This
  deliberately bypasses `agents/agent_search.py`'s own archetype-guessing
  prior (`analysis/archetype.py`'s `opponent_prior`): the whole point of an
  oracle test is the unfair advantage of the true decklist, not a better
  guess. The round-robin loop selects and rebuilds the oracle agent per
  opponent before each match, since a single static agent has no legitimate
  way to know its opponent's identity from observations alone.

## Results

| Arm | Config | Win Rate | W-D-L | n |
|-----|--------|----------|-------|---|
| A (incumbent) | heuristic+yushin+ability+attack_first | 0.825 | 33-0-7 | 40 |
| B (oracle-search) | search+yushin+oracle opponent_prior | 0.825 | 33-0-7 | 40 |

## Gate Decision

- **Delta (arm B - arm A)**: +0.000 = **+0.0pp**
- **Gate threshold**: >+0.05 (+5.0pp), per `docs/ROADMAP-30D.md` section 1's
  U109 row and section 6's Jul 13 kill criterion.
- **Verdict**: **FAIL** (delta does not exceed threshold; delta is exactly
  zero, not merely under the bar).

## Interpretation

1. **The ceiling test is unambiguous.** This project has a documented history
   of same-comparison ring deltas swinging with sample size (U104 read
   +15.0pp at n=40, then +9.0pp at n=100 in `analysis/u112_stacked_ring_
   confirmation.md`). A result close to the +0.05 gate would call for an
   n=100 rerun before concluding anything. This result is not close: both
   arms landed on the identical win-loss-draw record (33-0-7) at n=40, an
   exact tie with zero separation. Even under this project's own
   demonstrated ~5-9pp run-to-run noise band, a true positive delta of
   +0.05 or more essentially never produces a dead-even same-run tie. This
   is a clean falsifier, not an ambiguous read, so per the task's own
   instruction (only escalate to a larger n if the result is genuinely
   ambiguous or promising) no n=100 rerun is warranted.

2. **Handing search the oracle prior bought nothing measurable.** Search
   with the best possible opponent model available (the true decklist, not
   a learned or guessed one) still could not separate itself from the pure
   heuristic stack even by a single game's margin across 40 games per arm.
   This directly answers the question U109 was built to ask: the failure of
   determinized search on the real ladder (`analysis/search_recovered_on_
   ladder.md`, 431.4 vs 569.6) was NOT primarily an opponent-modeling
   problem. Fixing the opponent-modeling problem all the way to omniscience
   changes nothing.

3. **A learned field prior cannot exceed an oracle prior.** The oracle prior
   used here is strictly better information than any prior weeks 2-3's
   field-calibrated determinization work (U113a) could ever produce, since a
   learned posterior over decklists is, at best, an approximation of the
   true decklist this test already handed to search directly. If the oracle
   ceiling is at or below the current heuristic incumbent, the learned-prior
   version can only be at or below that same ceiling too. There is no
   mechanism by which spending weeks 2-3 building U113a/b/c narrows this gap.

4. **Search's cost in this test is not opponent-model uncertainty.** Since
   the opponent model was perfect and the result still did not move, the
   remaining candidate explanations for search's ladder underperformance are
   elsewhere in the search stack (the leaf evaluator, the rollout policy
   being the same heuristic it is being compared against so wins over
   heuristic play require the search LOOKAHEAD itself to add value beyond
   what the heuristic already picks, time-budget allocation, or a genuine
   ceiling limit of the search architecture given a strong heuristic rollout
   policy). None of those are addressed by a better opponent prior, so none
   of them are unlocked by weeks 2-3's planned field-prior work either.

## Gate Math

- Threshold: delta > +0.05.
- Observed: delta = +0.000.
- +0.000 is not greater than +0.05: **FAIL**, and by the full +0.05 margin,
  not a near-miss.

## Implication for the Roadmap

Per `docs/ROADMAP-30D.md` section 6's Jul 13 kill criterion: "U109 oracle
fails to beat the stacked incumbent by +0.05 => the search lane is DEAD for
this competition (the ceiling was never there); weeks 2-3 capacity reroutes
to U106-driven rule mining, U103, and U102." This result meets that criterion
early (2026-07-07, six days before the Jul 13 deadline) and with a clean,
unambiguous margin. The search lane (U113a field prior, U113b eval upgrade,
U113c integrated build) should be closed now rather than waiting for the
kill date, and the freed weeks 2-3 capacity should redirect to U106
(state-matched expert lookup), U103 (mirror ladder), and U102 (differential
audit), per the roadmap's own reallocation plan.

## Next Queue Items

1. Close the search lane now (LOOP_BRIEF.md updated alongside this file) so
   the unattended loop does not spend future iterations on U113.
2. Redirect Week 2-3 compute-session capacity to U106/U103/U102 per
   `docs/ROADMAP-30D.md` section 2.
3. U110 (hard ring) and U105 (threat/prize rules) remain independently
   queued Week-1 items, unaffected by this result.
4. No Dan escalation is required for a FAIL verdict (the roadmap's kill
   criterion is pre-registered and self-executing); Dan escalation is
   reserved for the PASS branch, which did not occur here.

---
*Gate failed 2026-07-07 at n=40/arm (33-0-7 both arms, delta +0.000).*
