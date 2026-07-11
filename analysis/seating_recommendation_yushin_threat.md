# Seating recommendation: heuristic+candidate_yushin_ito+ability+threat_retreat

Build under review: the project's strongest measured build, heuristic pilot on the
candidate_yushin_ito deck with PTCG_ABILITY and PTCG_THREAT_RETREAT on. Ring chain:
yushin+ability beats trolley+ability by +8.0pp at n=100 (analysis/u112_stacked_ring_confirmation.md,
arm 2 0.850 vs arm 1 0.770), and threat_retreat adds +6.0pp on top at n=100 same-run
(analysis/u105b_threat_retreat_ring_ab.md, off 0.850 vs on 0.910, gate PASS >+5.0pp). Pre-registered
as heuristic+candidate_yushin_ito-threat_retreat (state/current.md).

## Recommendation

Seat ONE copy of the threat_retreat build on 2026-07-18, right after the yushin candidate's
pre-registered settle-by closes and the M=240 noise model is re-fit (both dated 2026-07-18 in
state/current.md). Do it as a Dan-gated interactive submission, not on the ladder now and not held to
the Aug 12-13 lock. Accept that under latest-2 auto-eviction the single submission drops the OLDER
slot, which is the yushin candidate (ref 54365656), not the weaker ability floor (ref 54367075) that
intuition points at; that is fine, because the threat_retreat build (ring 0.910) strictly dominates
both live slots, so best-of-2 rises from yushin's 0.850-ring to 0.910-ring regardless of which slot
is mechanically evicted. Refresh the pre-registration settle_by to ~2026-07-28 first (section 3), and
do not react to any within-M=240 first-week board read (section 4).

## 1. Which slot: the eviction order is the whole point

The two live refs and their ages (repo-confirmed, not guessed):

- 54365656 = yushin candidate, last read ~626.4, pre-registered settle-by 2026-07-18. Submitted
  FIRST: findings.md queue item 4 records "Submitted ref ... 54365656 COMPLETE 651.9", then the
  floor restoration "54367075 COMPLETE 442.8 ... landed to hold the ring-best ability build" AFTER
  it. Kaggle refs are monotonic integers, and 54365656 < 54367075, so yushin is the OLDER slot.
- 54367075 = ability floor restoration, last read ~530.5. Submitted SECOND, so it is the NEWER slot.

Eviction rule (analysis/final_scoring_semantics.md, corroborated live): "we only track the latest 2
submissions", and "a 3rd submit evicts the 3rd-newest". The current pair, newest to oldest, is
[54367075 ability-floor, 54365656 yushin]. A 3rd submission therefore evicts the 3rd-newest =
54365656 = the yushin candidate.

Consequence, stated precisely: submitting threat_retreat once leaves the pair
[threat_retreat (newest), 54367075 ability-floor 530.5]. It evicts yushin, the STRONGER of the two
live slots, and keeps the weaker ability floor. You cannot selectively evict the ability-floor slot
with a single submission; latest-2 eviction is age-ordered, not score-ordered.

This is acceptable because threat_retreat is ring-superior to BOTH occupants (0.910 vs yushin+ability
0.850 vs the trolley+ability ability floor), so replacing either strictly improves the scored pair,
and this is exactly the U108 / P3 authorized move (the ring-positive stack replaces a ring-inferior
slot occupant; docs/ROADMAP-30D.md U112 row, LOOP_BRIEF.md P8 U108).

If Dan wants to KEEP yushin as an interim hedge second slot (a 0.850-ring hedge beats a
trolley-ability hedge), it takes TWO ordered submissions of the 5/day quota: submit a fresh yushin
copy first (evicts the old yushin 54365656, pair becomes [yushin_new, ability-floor]), then submit
threat_retreat (evicts ability-floor, pair becomes [threat_retreat, yushin_new]). This is only an
interim question: the endgame lock pair is two byte-identical threat_retreat copies (state/current.md
draft PAIR-U10, E[max] identical, hedge strictly dominated), so the second slot ends as another
threat_retreat regardless.

## 2. When: 2026-07-18, not now, not the Aug 12-13 lock

- Not before 2026-07-18. The yushin row's own pre-registered BAND action is "hold through settle-by;
  pooled aged reads vs king true estimate decide; no eviction on any within-band read per U108"
  (state/current.md). Seating threat_retreat before Jul 18 evicts yushin (the older slot) mid-window,
  aborting a pre-registered settlement for no governance gain, since the seating decision is
  ring-gated and the yushin ladder verdict cannot change it. Jul 18 also aligns with the noise re-fit
  ("re-fit by: 2026-07-18"), so the new build's first board reads are read under a fresh M.
- Waiting for the Jul 18 yushin settlement buys the settlement verdict on pooled AGED reads, but that
  verdict is non-decisive by design: yushin currently reads BAND (within M=240), U108 forbids any
  eviction on a within-band read, and the ring is the sole authority. The settlement will close
  yushin as ring-eligible with no forced action. So Jul 18 is the clean boundary, not a dependency.
- Not the Aug 12-13 lock. P3 (LOOP_BRIEF.md, docs/ROADMAP-30D.md section 4) sets Aug 12-13 as the
  LATEST lock date, chosen so the pair still accrues convergence episodes before the post-Aug-16
  convergence window finalizes the leaderboard. Newer refs play much more frequently
  (analysis/final_scoring_semantics.md). Seating the ring-leader ~4 weeks early on Jul 18 banks those
  convergence episodes for one eventual lock-pair member at near-zero risk (U108 caps the downside).

## 3. Pre-registration row (approve before any submission)

A row for this build already exists in state/current.md with settle-by 2026-07-25, which predates the
recommended 2026-07-18 submission. Refresh its settle_by to ~10 days post-submission (2026-07-28)
before spending the slot, so the settlement clock is honest. Row for Dan to approve:

```json
{
  "build": "heuristic+candidate_yushin_ito-threat_retreat",
  "hypothesis": "PTCG_THREAT_RETREAT on (opponent threat-aware retreat) improves win rate on the yushin+ability baseline; ring-gated +6.0pp at n=100 same-run (analysis/u105b_threat_retreat_ring_ab.md) on top of yushin+ability +8.0pp over trolley+ability (analysis/u112_stacked_ring_confirmation.md). Seated as the ring-leading scored floor; ring evidence is the sole decision authority per L9/U108.",
  "direction": "up",
  "margin": 240,
  "n": 30,
  "settle_by": "2026-07-28",
  "actions": {
    "win": "promote heuristic+candidate_yushin_ito-threat_retreat to shadow-king; reclaim-king stays heuristic+trolley",
    "loss": "evict threat-retreat, revert slot to a king copy",
    "band": "hold through settle-by; pooled aged reads vs king true estimate decide; no eviction on any within-band read per U108"
  }
}
```

Writing (or refreshing) this row via tools/loop_state.py is the mechanical submission-authorization
step (check-submit BLOCKS without a complete row). It happens ONLY on Dan's go. This memo does not
write it; the orchestrator commits nothing on my behalf here.

## 4. Risk table

| Risk | Evidence | Why it is not a stop | Action if it fires |
| --- | --- | --- | --- |
| Ring-to-ladder transfer is lossy | 0 of 5 offline-positive levers ever transferred (findings.md 4D) | threat_retreat is gated on the calibrated bracket ring at n=100, the most reliable gate; ladder reads are governance-non-decisive (L9) | none; hold |
| First-week reads swing wildly | yushin's OWN trajectory 651.9 -> 732.1 -> 496.4 -> 626.4 on one unchanged build (findings.md queue item 4), a ~236pt range | M=240 is sized to a worst residual of 235.1 (state/current.md); this swing is expected noise, not signal | none; do not revert |
| Edge compresses vs top opponents | u105b: on-arm loses MORE to the 3 hardest clones (0.273 vs 0.212 off-arm) despite winning more overall (analysis/u105b_threat_retreat_ring_ab.md) | the lever trades contested endgames vs the strongest opponents for a population-wide win-rate gain; the net +6.0pp still passed | monitor loss vs strongest opponents; do NOT revert on it |
| Ring saturation under-reads ceiling | off-arm 0.850 sits exactly at the 0.875-0.91 saturation band (analysis/u105b_threat_retreat_ring_ab.md) | this gate still cleared cleanly (+6.0pp, not a compressed delta); saturation only threatens the NEXT lever, not this one | treat further levers from this baseline as needing the hard ring (U110) |
| Wrong-slot eviction footgun | latest-2 evicts the OLDER slot = yushin, not the ability floor (section 1) | the build dominates both slots, so best-of-2 improves either way | if preserving yushin matters, use the 2-submission reorder (section 1) |

Worst-case first-week read: under M=240 the threat_retreat build can plausibly print anywhere from
roughly 450 to 730 while its true rating is unchanged, exactly as yushin did. A sub-500 print must NOT
trigger a panic revert. U108 is explicit that a ladder read inside the M band can never evict a
ring-positive build, and a reflex revert would itself be the governance error that trolley_thick and
attack_first suffered (LOOP_BRIEF.md P8 U108, findings.md 4D). The ring PASS (+6.0pp) is the only
eviction authority; nothing on the board in the first week can overturn it.

## Sources

state/current.md (pre_registrations, in_flight, M=240, ledger, draft PAIR-U10);
analysis/final_scoring_semantics.md (latest-2, 3rd-newest eviction, best-of-2);
analysis/u112_stacked_ring_confirmation.md (yushin +8.0pp n=100);
analysis/u105b_threat_retreat_ring_ab.md (threat_retreat +6.0pp n=100, hardest-clone, saturation);
findings.md queue item 4 (yushin trajectory, ref order) and 4D (U108, transfer-failure record);
LOOP_BRIEF.md P3/P8; docs/ROADMAP-30D.md sections 4-6 (endgame dates, kill criteria).
