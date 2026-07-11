# Path above 1000: the honest assessment and the staged plan (2026-07-11)

From an 11-agent strategic audit (5 investigators, opus synthesis, 5 adversarial verifiers). Two
investigators RAN the missing diagnostics live rather than speccing them; every load-bearing number
below was reproduced against the repo. No em dashes anywhere in this repo.

## Verdict

We do not have a plan for 1000+. The current plan is a plan for 650-700 converged. The reason is
structural: every lever is promoted or killed by the calibrated bracket ring, whose opponents are
cloned from OUR OWN 450-750 band, which saturates at 0.875-0.91, and on which the live stack already
reads 0.910. The remaining headroom on that instrument is worth roughly zero rating. 1000 is the top
~1.6% of the field (68 of 4351 teams above 1000; p95 is 951).

Honest probabilities even if every stage below works: 1000+ by Aug 16 under 5%; 800+ roughly 25-35%;
a converged 700-750 is the most likely outcome (55-65%). The Strategy prize (70% model approach,
Sep 1) is served by this plan regardless of the rating outcome.

## The four verified gaps (framings adversarially checked; facts reproduced)

1. NO HIGH-BAND INSTRUMENT. We have never measured win rate against strong play. The one signal we
   have: the current stack wins only 72.7-78.8% against the 3 hardest ring clones vs 85-91% overall,
   and the threat_retreat lever that PASSED the aggregate gate actually loses MORE against the
   genuine top-team clone (27.3% vs 21.2%, analysis/u105b_n100_run.log). The saturated ring can point
   the wrong way. A real high-band ring is near-free: tools/top_player_tracker.py already accepts
   --top-n 200 (hardcoded 20), the 7.0GB of episode dumps are on disk, the archetype classifier
   generalizes, and clones need no new design.
2. THE SHIPPED PILOT WAS NEVER MEASURED AGAINST EXPERTS. agents/heuristics.py reads its flags from
   the environment at import time, and every expert-agreement run ever done measured the FLAGS-OFF
   pilot. The audit ran the corrected diagnostic live (1082 games, 33,295 expert decisions, 131s,
   one core) and found a new lever candidate no prior analysis flagged: PLAY-category agreement drops
   10.9pp in near-endgame states and accounts for 41% of all close-game disagreement.
3. BROAD DECK SEARCH IS VIRGIN (survived adversarial verification untouched). The 2026-07-02 plan's
   own goal line says "search deck space instead of copying it" and the unit silently substituted
   mining. Only 3 narrow basics/energy probes on one lineage were ever closed. No genome/population
   code exists. Measured throughput 1.7-1.9 games/s: a 10k-game overnight search costs ~90 min to 4h.
   Open problem: fitness noise at small n, and fitness MUST be the high-band ring or the search
   inherits the saturation ceiling.
4. THE MIRROR DIAGNOSTIC RUNS TODAY. deck:meta_grimmsnarl vs clone:meta_grimmsnarl with a
   per-decision divergence log ran live at 1.84s/game with a ~10-line wrapper. The 21.6% U103
   baseline cited in LOOP_BRIEF is stale (n=116, pre-ability). A 4.5-min per-archetype baseline rerun
   gives the honest current number.

## The staged plan (every stage on-request, no unattended loops)

S1. HIGH-BAND RING: harvest top-68-to-200 decklists from the on-disk dumps, register clone families,
    score the current stack. Gate: stable n>=100 reads and a materially-below-0.910 score (the
    headroom signal). Cost: one short LLM unit, near-zero compute. Kill: too few decklists at top-N.
S2. COUNTERFACTUAL DIVERGENCE AT SCALE, LIVE FLAGS: the proven Pack-2 code over the high-band roster
    with prize-proximity weighting; refresh the stale baseline first. Gate: reproduce the
    PLAY-endgame gap and rank the categories. Cost: 3-5h LLM, under 3 min compute. Kill: if
    agreement vs high-band play is already high, the deficit is structural, not rule-shaped.
S3. CONVERT TOP DIVERGENCES TO FLAG LEVERS, GATED ON THE HIGH-BAND RING (the exact pattern that
    produced PTCG_ABILITY, the only lever that ever transferred from expert mining). Gate: category
    agreement improves AND >=+10pp on the HIGH-BAND ring at n=100. Kill: any lever that wins on the
    saturated ring but not the high-band ring (the threat_retreat trap).
S4. (parallel, lower priority) OVERNIGHT DECK SEARCH against the high-band ring with two-stage
    noise-robust selection and deck_validate as the legality operator. Gate: >=+10pp over yushin on
    the high-band ring at n=100.

## Stop doing

Promotion decisions on the saturated calibrated ring (keep it as a cheap regression guard only);
anything in the search/imitation lanes (oracle-dead and 4-way closed); single-axis deck grids;
process/calibration infrastructure framed as rating work; treating convergence as the bottleneck;
re-scoring the ~37 unscored mined decks on the saturated ring as a strategy.

## Sources

analysis/u105b_n100_run.log, analysis/ring_calibration.md, analysis/clone_quality.md,
analysis/expert_census.md, tools/top_player_tracker.py, tools/opponents.py, tools/deck_validate.py,
docs/reviews/2026-07-02-self-improving-plan-review.md, docs/plans/2026-07-02-001 (U39 goal vs
approach), findings.md 4B/4D, the audit workflow record (session, 2026-07-11).
