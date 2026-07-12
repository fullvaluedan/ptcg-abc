# PTCG_ENDGAME_PLAY gate: Step 0 STOP (inert on the ring deck)

Design: `analysis/endgame_play_rule_design.md`. Implementation: `agents/heuristics.py`
(`_ENDGAME_PLAY`, `ENDGAME_HAND`, `_opp_prize_count`, the EVOLVE-priority demotion
in `choose()`'s ladder). Probe: `tools/measure_endgame_play.py`.

No em or en dashes in this file.

## Step 0 (mandatory, pre-registered): fires-vs-inert with positive control

Per the design (section 6), Step 0 runs BEFORE any ring compute is spent: a zero
from a subsumed or broken probe is indistinguishable from a zero from a lever
that is genuinely inert, so the probe must be shown to work (the positive
control) before a real-deck zero is trusted.

`tools/measure_endgame_play.py -n 25` on `decks/candidate_yushin_ito.csv`
(heuristic-vs-random self-play, positions captured where both `OPT_PLAY` and
`OPT_EVOLVE` are legal, the rule's structural precondition):

| metric | result |
|---|---|
| positions captured (PLAY+EVOLVE both legal) | 25 |
| positions where the full trigger fires (near-endgame, hand >= 10, both legal) | 0/25 |
| decisions flipped (EVOLVE with flag off -> PLAY with flag on) | 0/25 |
| positive control (synthetic: our_prizes=2, hand=12, both legal) | fires=True, off=EVOLVE, on=PLAY, **flip=True** |

The positive control flips, so the probe itself is correct: it is not a broken
measurement returning a false zero.

## Due-diligence extension (beyond the pre-registered n=25)

Before accepting the n=25 zero, the capture methodology was stress-tested for a
specific bias risk: `measure_endgame_play.py` stops as soon as it captures 25
positions satisfying only the *structural* precondition (both categories legal),
and that precondition is common early in a match, so a greedy early-stop could
systematically under-sample the later, near-endgame states the rule actually
targets, producing a misleadingly clean zero. Three additional, unfiltered
diagnostic runs (same deck, same heuristic-vs-random self-play, no early stop on
the weaker precondition) checked this directly:

| run | matches | full-trigger fires observed |
|---|---|---|
| unfiltered, all MAIN decisions logged | 40 | 2 decisions had both-legal + hand>=10 simultaneously; near-endgame alone occurred on 29 decisions, both-legal alone on 33, but the full AND of all three conditions was rare |
| unfiltered, unbounded per-match budget | 150 | 1 decision (turn 12, hand 10) |
| unfiltered, unbounded per-match budget (independent re-run) | 200 | 0 decisions |

Across roughly 390 additional heuristic-vs-random matches beyond the official
25-position capture, the full trigger (near-endgame AND hand >= `ENDGAME_HAND`
AND both `OPT_PLAY`/`OPT_EVOLVE` legal, simultaneously) fired on at most one
decision. This confirms the n=25 zero is not a sampling artifact of the
early-stop: the full trigger is genuinely rare, well under 1% of MAIN decisions,
on `candidate_yushin_ito` against a random opponent.

## Verdict: INERT on the ring deck. STOP. No ring compute spent.

Per the design's own pre-registered kill criterion (section 6, Step 0): "if
flips == 0 on yushin across the captured decisions (and the positive control DID
flip, proving the probe works), the lever is inert on the ring deck... Do NOT
spend ring compute; record the honest inert result and stop." Both conditions
hold here (0/25 flips, control flips), so Step 1 (top-50 elite ring, n=100/arm)
and Step 2 (calibrated ring, n=50/arm regression guard) are **not run**.

This is exactly the risk the design's own section 7 named up front: "the ring is
piloted on `candidate_yushin_ito`, whose evolution (Staryu -> Mega Starmie ex) IS
the win condition" and "Probe subsumption (U105)... the rule could be inert on
the ring deck if yushin rarely reaches near-endgame with a 10-plus hand and both
categories legal." The measurement confirms that concern rather than the
transfer-validity concern (tempo cost to the mega evolution): the rule mostly
never gets the chance to fire on this deck against a weak opponent, not that it
fires and loses.

## Disposition

`PTCG_ENDGAME_PLAY` stays implemented and flag-gated, default OFF, exactly as
`PTCG_THREAT_RETREAT` and `PTCG_PRIZE_CLOSE` were left after their own U105
inert findings (`analysis/u105_threat_prize_inert_check.md`): the code is
correct and unit-tested, but not eligible for ring validation or a ladder slot
on the current ring deck. No change to `agents/heuristics.py`'s shipped
(default-off) behavior. Re-eligible for retest if a future deck change makes
`candidate_yushin_ito` (or a replacement ring deck) actually reach the
near-endgame-plus-bloated-hand-plus-both-categories-legal state with useful
frequency, or if the rule is retargeted at a deck that runs a
Dudunsparce-style non-finisher draw engine (the cluster A evidence deck shape,
section 1 of the design).
