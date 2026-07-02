# Game plan: meta_archaludon

Machine seeds emitted by analysis/gameplan_seeds.py (plan U36 piece 3) from
the miner's win-vs-loss stat blocks. Aggregates only; no raw episodes.

- appearances mined: 2294 winning, 2442 losing
- emission bars: share 0.70, unanimity 0.95, timing 0.80 (miner resolution bar 0.9)
- source blocks: data/derived/gameplans/gameplan_blocks_archaludon.json

| block | kind | winning value | metric | bar | losing value | status |
| --- | --- | --- | --- | --- | --- | --- |
| opening_category | categorical | PLAY | 0.683 | 0.95 | PLAY | below_bar |
| attach_target | categorical | 8 | 0.470 | 0.70 | 8 | below_bar |
| play_target | categorical | None | 0.000 | 0.70 | None | barred |
| evolve_target | categorical | 190 | 0.875 | 0.70 | 190 | SEEDED |
| first_attack_ordinal | timing | 3 | 0.123 | 0.80 | 4 | below_bar |
| first_evolve_ordinal | timing | 7 | 0.091 | 0.80 | 5 | barred |

Seeded blocks: evolve_target.
