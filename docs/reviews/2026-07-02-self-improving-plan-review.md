# Review findings: 2026-07-01-001 self-improving agent plan (2026-07-02)

Five-persona review (coherence, feasibility, product-lens, scope-guardian, adversarial) of
docs/plans/2026-07-01-001-feat-self-improving-agent-plan.md, judged against the stated goal:
FIRST on the Simulation ladder (final 16 Aug 2026), which the owner holds requires (1) the best
all-around deck and (2) a pilot that executes complex skills and move sets. Strategy prize
(top 8, 70/20/10, final 13 Sept 2026) is the parallel track.

Verdict: the plan cannot reach #1 by its own numbers. In-scope phases cap at ~900 vs a ~1300 top;
the only in-plan #1 path (P3 search revival) is gated and may be skipped with no contingency.
The deck-execution deferral rests on evidence that never tested a deck-aware pilot. The plan is
also one day behind its own autoloop execution.

## Already applied (mechanical fixes)
- Phased Delivery table now lists U12, U13, U14 (P2 row).
- U14 phase label corrected to P2; U13 added to U14 dependencies (verification gate).
- Benchguard harness path corrected to tools/measure_benchguard.py.

## P0
1. (error, Scope Boundaries) Deck-execution deferral cites Archaludon 401 / Grimmsnarl 409 vs 570,
   but that experiment only tested the GENERIC pilot on meta decks. A deck-aware pilot was never
   measured, so the refutation does not reach the deferred work. The revisit gate (U13 search
   revival) conflates an opponent model with pilot skill and sits behind a possibly-skipped P3.
   Fix direction: rewrite the deferral to what the evidence supports; make deck-aware execution an
   active parallel track with a cheap direct test (deck-conditioned imitation pilot in the gauntlet).
2. (omission, Phased Delivery) No path to #1 if U7 is unfavorable: P3 skipped means the plan tops
   out ~900 vs ~1300 with no named contingency. Fix direction: define the deck-aware execution
   track as the explicit U7-unfavorable branch with its own gate and ceiling estimate.

## P1
3. (error, Problem Frame) Root cause stated as "a piloting gap, not a deck gap" but the cited
   source analysis/meta_decks_underperform_on_ladder.md concludes it is a JOINT deck-and-pilot gap.
   Fix: restate as joint; add a deck-space exploration unit (150 harvested decks + CEM/gauntlet).
4. (error, Ground-Truth/Units) Plan is stale: U1, U2, U3, U5, U6, U12 and U4's deck pool already
   landed (commits on 2026-07-01); ground-truth #5 (empty opponent pool) is no longer true;
   U14(b) energy-preservation was implemented and REFUTED (analysis/energy_seq_refuted_by_expert_moves.md).
   Fix: per-unit status lines (landed / partial / refuted / not started, with commit or analysis ref).
5. (error, U6) The specified CEM genome/fitness was measured FLAT (analysis/cem_signal_flat.md):
   pool win rate saturates at 1.0; 8 of 11 dims have zero leverage. Working fix (PTCG_W_PRIO_*
   priority-order weights, analysis/cem_gradient_restored.md) is absent from the plan. Fix: rewrite
   U6 genome around pilot priority weights; expert-move agreement is the discriminating fitness.
6. (error, Phased Delivery) U7 diagnostic has zero unmet dependencies yet is sequenced after the
   whole P2 build. Fix: run U7 now, in parallel; its verdict steers the pivot while calendar remains.
7. (error, U10) Dependencies offer "or the tuned pilot" but the approach requires search values at
   nodes; as written U10 cannot run if P3 is skipped. Manual call: gate U10 on a search worth
   distilling, or redefine labels as outcome-only.
8. (omission, Phased Delivery) No calendar or submission budget vs 16 Aug (~230 slots at 5/day;
   arbiter resolves ~2 decisions/day; CEM generates candidates faster than the arbiter can judge).
   Fix: slot budget per phase gate, latest-start dates, size the engine to the arbiter.
9. (omission, KTDs) Load-bearing A/B facts (514.7 vs 569.6) sit inside a ~130-point noise band per
   the plan's own source. No gate states sample size, margin, or settlement criterion. Fix: an A/B
   decision protocol (settle after N episodes, minimum win margin, repeat rule inside the band);
   re-confirm the search-costs-points fact under it.
10. (omission, Units) "Best all-around deck" has no serving unit: U3 is a defensive density tweak;
    no unit searches deck space. Fix: deck-optimization unit reusing the pool/gauntlet/CEM machinery.
11. (omission, Units) U13's behavior-cloned policy is never trialed as the deployable pilot on a
    complex deck, the cheapest direct test of the deck-execution requirement. Fix: add BC-as-pilot
    (and BC-blended heuristic) as a gauntlet-then-ladder candidate.

## P2
12. (error, U4) Replaying recorded plays as opponents is infeasible (actions are option indices
    into a diverging state). Fix: decks piloted by heuristic now, U13 clone later.
13. (error, KTD3) "Embarrassingly parallel" contradicts the sequential singleton engine; CEM
    iterations are hours, parallel only across subprocesses. Fix: honest throughput math in U6.
14. (error, KTDs/Units) "Oracle" names two systems (search teacher vs cloned opponent). Manual:
    adopt "offline teacher" for search; reserve "oracle" for the U13 measurement policy.
15. (error, Problem Frame) Engine bundled into the goal ("the hackathon story") though its own
    ceiling read prices it ~100-150 points over hand-iterated P1; engine ran ahead of P1's ladder
    gate. Manual: split ladder goal from Strategy-prize narrative; gate FURTHER engine investment
    on P1 ladder confirmation.
16. (omission, U8/U13) Both build analysis/opponent_policy.py with no cross-link. Fix: U8 consumes
    U13's model; U8's new work is reach-weighting plus archetype-biased deal prior.
17. (omission, U4) Frozen snapshot mechanism undefined and conflicts with env-at-import weights.
    Manual: define snapshot as a self-contained module copy with baked constants.
18. (omission, U5/U13) Validators asserted ladder-correlated, never calibrated. Fix: require each
    proxy to retrodict the known ladder ordering (trolley 569.6 > search 514.7 > meta copies)
    before it gates slots.

## FYI (advisory)
- U11 training framework unnamed; jax 0.10.2 already in .venv.
- Strategy-prize story weakens if P3/P4 are skipped; build the writeup on every-branch components.
- The ~1300 target is a moving field; the bar rises until 16 Aug.

## Residual concerns
- "Top of ladder wins via complex-deck piloting" is plausible but unverified; the episode dataset
  can answer it directly.
- U1 reclaim gate not yet confirmed live (quota-locked at last status).
- First benchguard build scored 554.5 vs 569.6 baseline; P1's ladder gate may not yet be met.
- Latest-two-scored portfolio strategy (hedge two diverse builds vs two copies of best) unresolved.

## Deferred questions
- How many top-player MAIN decisions per archetype does the dataset hold? A 40-file sample found
  only 3 expert episodes (116 decisions). This sizes U13, U5, AND any deck-aware imitation work.
- Does the 16 Aug final freeze and re-score submissions?
- How do this plan and the deck-aware-execution track share the 5/day quota?
- Numpy or jax for U13 training; where do coefficients live vs the no-__file__ constraint?
- Which artifact is authoritative per-unit status: the plan, LOOP_BRIEF.md, or state/current.md?
- Cut U10/U11 outright given the deadline?
