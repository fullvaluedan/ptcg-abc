# Real game-plan mine + emit run (U36 pieces 2/3 on real data; gates U37)

The U36 miner (analysis/gameplan_mine.py) and seeds emitter
(analysis/gameplan_seeds.py) were run on the real 2026-06-30 expert dataset
(data/episodes/pokemon-tcg-ai-battle-episodes-2026-06-30.zip, 5732 scored
episodes) for the two families the U36 selector named: the quality target
meta_grimmsnarl and the mastery runner-up / opponent anchor meta_archaludon.
This produces the committed aggregates-only game-plan docs
(meta_grimmsnarl_gameplan.md, meta_archaludon_gameplan.md) and is the input the
U37 seeds CONSUMER will bake.

## Headline result: the seeds channel is nearly empty at scale

Across the two top families, six mined blocks each, exactly ONE block clears
both the miner's 0.90 resolution bar and its per-shape concentration bar.

| family | appearances (win/loss) | seeds emitted | which |
| --- | --- | --- | --- |
| meta_grimmsnarl (quality target) | 1996 / 1763 | 0 | none |
| meta_archaludon (mastery runner-up) | 2294 / 2442 | 1 | evolve_target = card 190 (share 0.875) |

The smoke run (--limit 200) looked concentrated (grimmsnarl attach share 0.470,
evolve 0.543), but at full scale the modes wash out: grimmsnarl's best
categorical concentration is evolve_target at 0.489, well under the 0.70 share
bar, and its opening is only 48% PLAY (against a 0.95 unanimity bar). Small-N
concentration was a sampling artifact.

## Per-block detail

meta_grimmsnarl (all six SKIP):
- opening_category PLAY 0.482 < 0.95 (below_bar)
- attach_target card 7 share 0.285 < 0.70 (below_bar)
- play_target barred (0.000 resolution: PLAY-category card ids never resolve
  from the observation for this family)
- evolve_target card 66 share 0.489 < 0.70 (below_bar)
- first_attack_ordinal barred (0.797 resolution < 0.90); even so consistency
  0.060 is far under 0.80
- first_evolve_ordinal barred (0.843 resolution < 0.90)

meta_archaludon (one SEED, five SKIP):
- opening_category PLAY 0.683 < 0.95 (below_bar) -- opens PLAY more often than
  grimmsnarl but still not near-unanimous
- attach_target card 8 share 0.470 < 0.70 (below_bar)
- play_target barred (0.000 resolution, same as grimmsnarl)
- evolve_target card 190 share 0.875 >= 0.70 -> SEEDED (the winning AND losing
  modal evolve are both card 190, so this is a deck-identity seed, not a
  win-vs-loss discriminator)
- first_attack_ordinal 0.918 resolution but consistency 0.123 < 0.80 (below_bar)
- first_evolve_ordinal barred (0.572 resolution < 0.90)

## What this means for U37 (the seeds consumer)

1. The mined-seeds lever is far thinner than the U36 design assumed. For the
   QUALITY target (grimmsnarl) there is nothing to bake; for archaludon there is
   exactly one evolve-target preference, and it does NOT separate wins from
   losses (both splits favor card 190), so it is a deck-identity fact the pilot
   could already read off the decklist, not a learned winning-play edge.
2. play_target is structurally barred for BOTH families (0.0 resolution): PLAY
   decisions do not expose their placed card id in the observation stream
   iter_resolved_decisions reads. If PLAY targeting is wanted as a seed, the
   resolver, not the emission bar, is the thing to fix -- record as the
   play_target re-test condition.
3. The two timing blocks never clear on either family: first-attack / first-evolve
   ordinals are too spread (top players vary their tempo), so baking a fixed
   "attack by move N" is unsupported by the data.

Recommendation for U37: build the consumer as designed (default-off lever,
byte-identical unset) but expect its baked dict to be EMPTY for grimmsnarl and a
single evolve-target entry for archaludon. Do not spend a ladder slot on a seeds
build until a block emits a seed that is BOTH concentrated and win-vs-loss
discriminating (the archaludon evolve seed is neither novel nor discriminating).
The honest Strategy-writeup story is that the mined-game-plan channel was
measured on real data and found nearly empty; the deck-aware edge, if any, has to
come from the guard stack / card_effects / ranker, not from baked opening or
timing constants.

## Re-test conditions (stateful)

- gameplan_seeds_diffuse (this result): re-mine if a NARROWER cohort is adopted
  (e.g. a single top handle rather than all winning seats), or if the miner adds
  a block shape that concentrates (e.g. attach-target conditioned on turn, or a
  bench-count opening rather than raw category).
- play_target_unresolved: re-test only after the PLAY resolver in
  analysis/replay_trace exposes the placed card id (a resolver fix, not a bar
  change).
