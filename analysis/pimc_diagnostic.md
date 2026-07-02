# PIMC diagnostic: the Phase 3 search-branch decision (plan U27)

**Verdict: FAVORABLE.** On our real states the game has the structure Long et al.
(2010) identify as making Perfect-Information Monte Carlo sound: **high leaf
correlation** (worlds agree on the best move, 0.80-0.91 on discriminating states,
threshold 0.55), **moderate bias** (|mean terminal value| 0.46-0.68, threshold
0.9), and **positive-but-marginal disambiguation** (revealed-fraction slope
0.023-0.037 per turn, threshold 0.02). Five robust readings (four competitive-foil
runs plus one weak-foil run at a large disambiguation sample) all clear all three
thresholds. So the Phase 3 branch is fixed to **U45 belief-weighted search**
(latest start Jul 27); the U46 doubled-deck-aware-breadth branch is not taken.
This decision is not revisited (plan KD7).

This DIFFERS from the plan's stated expected base case (unfavorable). The
diagnostic is the arbiter, and it says search is structurally viable here; the
observed ladder underperformance (below) is an implementation gap, not a
structural PIMC failure. That is exactly the gap U45 is specced to close.

Reproduce (native forward model required; writes gitignored
`data/derived/pimc/`):
`python -m analysis.pimc_diagnostic decks/trolley.csv -n 12 -w 6 -m 8 -o heuristic -d 12 --json`

## What was tested

Our determinized search IS PIMC: sample hidden worlds, roll each candidate first
move to a terminal result per world with the shipped heuristic policy, average,
argmax. Long et al. prove PIMC approximates the true game well only when three
game properties hold, and suffers strategy fusion / non-locality otherwise. This
unit measures those three properties on OUR real mid-game states, using the
shipped forward model and rollout, so the leaf values ARE the values search sees.

- **Leaf correlation** (`_modal_share`, `_pearson`): per state, sample K
  determinized worlds, build the [world][candidate] terminal-value matrix, and
  measure the fraction of worlds that agree on the single best move (the
  modal-argmax share) plus the mean pairwise correlation of the per-world value
  vectors. High share means a move good in one hidden world is good in the others,
  which is the precondition for PIMC averaging.
- **Bias** (`bias`): mean signed terminal value across worlds and candidates.
  Magnitude near 1.0 means the position is already decided regardless of the move
  (search cannot matter); moderate is healthy.
- **Disambiguation** (`disambiguation_slope`): the least-squares slope of the
  revealed-opponent-card fraction against the turn number, over a dedicated cheap
  many-match pass (no rollouts). High slope means hidden worlds collapse quickly,
  so late-game determinizations become accurate.

Pre-registered thresholds (set before the run, in the module): leaf >= 0.55,
disambiguation slope >= 0.02, bias magnitude <= 0.9. Favorable requires all three.

## Results (trolley deck, 6 worlds/state, 12 states/run)

| run | foil | leaf (disc / all) | pairwise corr | disambig slope | bias abs (signed) | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| A | heuristic | - / 0.944 | +0.467 | 0.0374 | 0.621 (+0.394) | FAVORABLE |
| B | heuristic | 0.796 / 0.847 | -0.123 | 0.0228 | 0.627 (+0.007) | FAVORABLE |
| C | heuristic | 0.909 / 0.917 | n/a | 0.0324 | 0.460 (+0.031) | FAVORABLE |
| D | heuristic | 0.850 / 0.875 | n/a | 0.0248 | 0.678 (+0.449) | FAVORABLE |
| E | random | - / 0.903 | +0.208 | 0.0262 | 0.717 (+0.717) | FAVORABLE |

(Matches are unseeded, so each run samples fresh games; the table bounds the
run-to-run variance rather than reporting one point. Run A predates the
discriminating-only leaf metric.)

## Honesty caveats (each shaped the method)

- **Foil sensitivity was real and is resolved.** A first random-foil run read
  disambiguation 0.008 (UNFAVORABLE) purely because the 2-match sample was tiny
  and a random opponent barely develops its board. Decoupling disambiguation into
  its own many-match pass (114-131 points) lifted the same weak foil to 0.026
  (favorable) and stabilized the competitive foil at 0.023-0.037. The slope is a
  property of the opponent's board development, so it needs both a faithful foil
  (competitive) and a many-game sample; a single trajectory is not trustworthy.
- **Win-saturation cannot manufacture the verdict.** The pilot beats both foils,
  so 3-4 of 12 states per run are already decided (|bias| = 1.0); their
  modal-argmax share is a degenerate 1.0 and their value vectors are constant (so
  their pairwise correlation is correctly skipped). The verdict uses leaf
  correlation over the DISCRIMINATING states only (|bias| < 0.98), which stays
  0.80-0.91: worlds agree on the best move even where the move genuinely swings the
  game.
- **Pairwise value correlation is weak and unstable** (-0.12 to +0.47). The
  ranking is stable across worlds (high modal share) but the value MAGNITUDES are
  noisy world to world. This is the fingerprint of a noisy determinization prior
  (the mirror assumption), and it is precisely why U45's archetype-biased,
  reach-weighted worlds are the lever, not deeper search on a bad prior.
- **Disambiguation is marginal, not comfortable** (min 0.0228 vs 0.02). TCG hidden
  information resolves slowly. The favorable read leans on high leaf correlation,
  the strongest of Long's three signals; disambiguation only just clears.
- **The foils are weaker than ladder opponents (~1300).** A behavior-cloned
  top-player foil (plan U43, a U45 dependency anyway) would be the gold-standard
  measurement. That is a confirmation opportunity when U43 lands, not a re-opening
  of the branch (KD7: the decision is not revisited).

## Reconciliation with the ladder fact (514.7 < 569.6)

Active search scored 514.7 vs the heuristic's 569.6 on the same deck: search cost
~55 points. A favorable structural verdict is consistent with that, not
contradicted by it. Long's properties say PIMC APPROXIMATES the true game well
here (no strategy-fusion catastrophe); they do NOT say a first, naive PIMC
implementation beats a tuned heuristic. The measured weaknesses point straight at
the implementation: a noisy mirror-prior (weak, sign-unstable pairwise value
correlation), too few worlds per decision (`tools/measure_worlds.py` showed the
world-count keystone barely fires), and search overhead. U45 attacks exactly
these: reach-weighted worlds via the U43 policy, archetype-biased deal priors,
and more-worlds-shallower. The high leaf correlation is the headroom that makes
that worth attempting; the ladder protocol (M=60, in-band-by-Aug-3,
beat-king-by-Aug-8) still gates every actual slot, and the tuned heuristic king
stays live throughout.

## Consequences

- Phase 3 branch = U45 belief-weighted search revival (deps: U27 favorable [met],
  U43 seat-identity contract). Latest start Jul 27; search-active must read
  in-band-or-better by Aug 3 and beat the king at M by Aug 8, else the branch
  closes forever.
- U46 (doubled deck-aware breadth) is NOT taken; it remains the documented
  fallback only if U45's own kill dates fire.
- The `search_active_beats_heuristic` refutation in `state/hypotheses.md` stands;
  its recorded re-test condition ("P3 only, and only if the U27 determinization
  diagnostic is favorable") is now MET, so U45 may re-confirm 514.7 vs 569.6 under
  the protocol as part of that lane, never before.
