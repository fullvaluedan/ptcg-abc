# Unit-zero linear-ranker spike (plan U26)

**Verdict: PASS.** A linear pairwise ranker over ~20 hand-decoded features beats
the deployed heuristic pilot by **+0.087 top-1** on held-out top-player decisions
(0.343 vs 0.256) and fills the specced known gap: it top-1s **191 of 649**
ability decisions the heuristic never gets right (0 of 649). Both PASS conditions
are met, so the U40/U41 learned-pilot pipeline is unblocked on the ranker bet.

Reproduce: `python -m analysis.unit_zero_spike data/episodes/pokemon-tcg-ai-battle-episodes-2026-06-30.zip --limit 1500`
(writes the full result JSON to the gitignored `data/derived/spike/`).

## What was tested

The central bet under ~26 specced units is that a LINEAR ranker over a small
feature set can play the top players' MAIN decisions better than the hand-coded
heuristic. This spike tests that bet before those units exist.

- **Cohort:** the winning seat of every episode (plan U25), the exact imitation
  target. Scorable decisions are the validator's MAIN single-pick multi-option
  moments, so the spike learns from and is scored on the same decisions the census
  counted.
- **Features (`analysis/unit_zero_spike.py`, 20):** seven option-category
  indicators, seven option-content signals (play card type, attack damage / lethal,
  attach-to-active), and six state crosses (attack x turn, develop-basic x thin
  bench, end x action-count, attach x energy-not-yet-attached, attach-active
  underpowered). Every card-data lookup reuses the pilot's own decoders
  (`agents.heuristics`) so the spike reads options exactly as the pilot does, and
  each lookup is wrapped so the module imports and unit-tests without the engine.
- **Ranker:** numpy pairwise-logistic (RankNet with a linear score), gradient
  descent on within-decision difference vectors, L2 = 1e-3, deterministic (no RNG).
  Substituted for the plan's sklearn ranker because sklearn is not in the venv and
  the shipped agent must stay dependency-light; this IS the linear ranking pilot
  U40/U41 would build, so the bet is proven with the production math and no new dep.
- **Split:** 1500 episodes -> 42,849 scorable winner-seat decisions, first ~75%
  train (32,145) / last ~25% held out (10,704). The cut is snapped to an episode
  boundary so no game straddles train and test.
- **Baseline:** the DEPLOYED heuristic `choose()` top-1 on the identical held-out
  decisions (the "recomputed baseline" the plan means). A fixed-weight unlearned
  proxy (0.194) is also reported so a cg-free run still has a reference.

## Result (held-out, 10,713 decisions)

| pilot | top-1 agreement |
| --- | --- |
| unlearned proxy weight | 0.194 |
| deployed heuristic `choose()` | 0.256 |
| **learned linear ranker** | **0.343** |

(held-out: 10,704 decisions)

Delta vs the deployed heuristic: **+0.087** (PASS threshold +0.03).

### Per expert action category (held-out; baseline = heuristic)

| category | n | heuristic agree | ranker agree |
| --- | --- | --- | --- |
| ABILITY | 649 | 0 | **191** |
| ATTACH | 2291 | 180 | 316 |
| ATTACK | 1120 | 501 | 255 |
| END | 419 | 12 | 1 |
| EVOLVE | 743 | 455 | 83 |
| PLAY | 5132 | 1587 | 2791 |
| RETREAT | 350 | 3 | 35 |

The ranker rescues the two categories the heuristic ignores (ABILITY 0 -> 191,
RETREAT 3 -> 35), improves ATTACH and the majority PLAY class, and loses ground on
ATTACK (501 -> 255) and EVOLVE (455 -> 83), which the heuristic's explicit
lethal/evolve rules nail. Top learned weights: attach-to-active +0.41, is_end
-0.27, is_retreat -0.25, is_play +0.24, play_trainer +0.23, is_evolve +0.15,
is_ability +0.14.

## PASS conditions (both met)

1. **>= +0.03 top-1 over the baseline:** +0.087 vs the deployed heuristic. PASS.
2. **Reorders a known-gap category (ABILITY, heuristic 0 of 554):** ranker top-1s
   191 of 649 ability decisions the heuristic scores 0 on. PASS.

## Caveats the U40/U41 build must carry (not blockers)

- **The ranker regresses on ATTACK and EVOLVE**, the categories the heuristic's
  explicit lethal / evolve rules already win. A pure linear-score override would
  DROP those decisions. So the learned pilot must sit BEHIND the heuristic's safety
  layer (take-the-lethal, forced-evolve), not replace it. This matches the plan's
  four-layer guard-stack spec; the spike is evidence the guard stack is load-bearing,
  not optional.
- **Class imbalance:** PLAY is 48% of decisions. Part of the ranker's gain is
  learning the majority-category preference the proxy lacked. The net is still
  positive against the heuristic (which already knows the class mix), and the
  ABILITY / RETREAT rescues are genuine within-category reorders, not base-rate
  effects.
- **Exact-index agreement is strict** (many options are near-equivalent), so 0.34
  is a RELATIVE filter number for comparing pilots on a fixed held-out set, not an
  absolute skill measure. It transfers to the ladder only through the pre-registered
  A/B protocol, never on its own.

## Consequence for the roadmap

U40/U41 (unified featurizer + imitation dataset + trainer) is UNBLOCKED on the
ranker bet: the linear-ranker head is worth building. The census already cleared
the volume tier (FULL, plan U25), so the remaining U40 gates are the contract
reconciliation (U28) and ship-safety (U30), not the bet itself. The learned pilot
ships behind the guard stack; the heuristic king stays the floor throughout.
