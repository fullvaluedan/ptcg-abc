# ML expert review: what we are doing wrong, and what an expert would do (2026-07-12)

From a fact-checked expert panel (evaluation/statistics and ML-systems seats; every load-bearing
claim verified against the repo, with three miscited numbers in the first draft corrected by the
fact-check pass). No em dashes anywhere in this repo.

## The headline verdict

Exemplary measurement DISCIPLINE bolted onto structurally underpowered measurement INSTRUMENTS.
The project modeled one error source obsessively (same-build ladder noise, M refit 60 to 150 to
240) while never characterizing the sampling error of the instrument it promoted to sole decision
authority. At n=100/arm and p~0.85 the two-arm difference SE is ~5pp, so a +5pp gate is read at
roughly one standard error: ~26-32% power. The n=40 screens are worse (~15%). The whipsaw history
(U104 +15pp at n=40 collapsing to +9pp at n=100; ability +4.0pp at n=200 collapsing to ~0 under
isolation; the retracted 0.9pp "transfer failure") is not a series of flukes, it is the fingerprint
of gating effects the same size as the SE. Each incident was diagnosed locally; no required-n was
ever computed (verified: zero hits repo-wide for any power calculation).

The cruel part: the fix is nearly free. tools/parallel_gauntlet.py already has the 16-worker
sharding pattern, but every ring gate runs single-process at 1.7-1.9 games/s. A properly powered
1400-game A/B costs ~13 minutes single-threaded and ~90 seconds at 16 workers. The project
imported Kaggle's 5/day submission scarcity into an offline instrument with no budget at all
(U112 declined a rerun because "re-runs consume budget" about a gate that consumes none).

## What we are doing wrong (verified)

1. UNDERPOWERED GATES (fundamental): +5pp gates at n=100 run near 26-32% power; a +5pp true effect
   is missed ~3 times in 4, and the levers that do pass are upward-biased noise excursions
   (winner's curse). Required n at 80% power, one-sided alpha 0.05: ~710/arm for +5pp gates,
   ~195/arm for +10pp, ~640/arm to resolve the U104-style +9-vs-+15 ambiguity.
2. SEQUENTIAL RINGS ON A PARALLEL BOX (major): the 16-worker harness exists and is unused by every
   gate runner. Parallelized, a fully powered A/B is ~90s, enabling 50-100 powered experiments per
   day instead of a handful of underpowered ones.
3. NO MULTIPLICITY DISCIPLINE (major): many levers screened, passing ones shipped at their screen
   estimates, several later reversed. No FDR control, no shrinkage, and screening and confirmation
   have used the same instrument.
4. SINGLE-DECK SINGLE-RING GENERALIZATION (major): lever effects are deck- and ring-conditional
   (ability helped trolley, hurt yushin; threat passed the 9-clone ring, failed the elite ring)
   but were measured on one deck against one ring and generalized. Deck x lever factorials and a
   locked holdout ring were never standard.
5. THE "NO ML" PREMISE IS FALSE (major, systems seat): pure-Python match-time ML already ships in
   this repo (search/learned_eval.py loads a logistic model from eval_model.json, plain-Python
   sigmoid). Sizing: a 200k-param MLP costs ~25ms/decision in nested-list Python, under 1s/game
   against the 600s bank. Weight shipping is a non-issue (the 5.46MB uncompressed tarball is 99%
   four platform native libs, one of which is used; the agent code is ~13KB).

## What the closures actually closed (and what stays open)

- Agreement-objective imitation is CLOSED rigorously (4 converging attempts against the strong
  first-legal baseline, analysis/clone_quality.md).
- Search at match time is CLOSED structurally and empirically: the grader engine withholds the
  search_* forward model; force-loading our own cg scored 431.4 vs 569.6; the U109 oracle tied
  exactly. This also blocks value-net-plus-lookahead at inference (no forward model to expand).
- OPEN, the one untested deployable ML cell: an OUTCOME-LABELED per-option policy ranker shipped
  as the ladder action selector. Every prior policy model trained on is_chosen (imitation); every
  value model needs a forward model to act. P(win | take this option) over the existing per-option
  features needs neither. Training: sklearn on the 708k-row corpus plus 46k episode outcomes,
  minutes on this box; deployment: the proven eval_model.json JSON-literal template; match cost
  under 1s/game. Prior is guarded (both neighboring cells closed at baseline parity), but it is
  arithmetic-cheap and closes the ML question honestly either way.

## What we do right (keep, and feature in the writeup)

Machine-enforced pre-registration; iterated noise modeling; adversarial multi-agent audits that
killed four of eight proposed levers as already-closed and caught two real instrument bugs; honest
negatives and self-retraction; fires-vs-inert probes with positive controls; the oracle-bound
falsifier design; game-level train/test splits everywhere.

## Prescription, in order

1. Parallelize the ring runners onto the parallel_gauntlet pattern (~1 day) and adopt power-derived
   n for every gate (pure arithmetic, immediate). Re-run the live flags question at n=700/arm
   before the Aug lock.
2. Standardize: screen on the 9-clone ring, confirm at full power on the locked 35-clone elite
   holdout, deck x lever factorial arms whenever a lever ships to a different deck than it was
   validated on.
3. Batch-level FDR (Benjamini-Hochberg) across lever screens; ship confirmation-run estimates, not
   screen estimates.
4. Run the outcome-labeled option-ranker experiment (train, fires-check with positive control,
   powered elite-ring gate).
5. Writeup: present the power correction as a found-and-fixed methodology arc, and close the
   "600s of unused compute" objection with the recorded arithmetic (inert forward model, 431 vs
   570, oracle tie).

## Sources

analysis/u104_stacked_ring_pass_run.md, analysis/u112_stacked_ring_confirmation.md,
analysis/ability_ab.md (n=200), analysis/ability_isolated_confound_check.md,
analysis/u105b_threat_retreat_ring_ab.md (+6.0pp observed vs the +5.0 gate margin),
analysis/candidate_decks_ring_gate.md (+0.100 at n=20, replicated twice at n=40),
tools/parallel_gauntlet.py, search/learned_eval.py, tools/train_eval.py, analysis/clone_quality.md,
analysis/u109_oracle_bound_test.md, analysis/ladder_search_inert.md, findings.md 4B/4C/4D,
the panel workflow record (session, 2026-07-12).
