# Game plan: meta_grimmsnarl

Machine seeds emitted by analysis/gameplan_seeds.py (plan U36 piece 3) from
the miner's win-vs-loss stat blocks. Aggregates only; no raw episodes.

- appearances mined: 1996 winning, 1763 losing
- emission bars: share 0.70, unanimity 0.95, timing 0.80 (miner resolution bar 0.9)
- source blocks: data/derived/gameplans/gameplan_blocks_grimmsnarl.json

| block | kind | winning value | metric | bar | losing value | status |
| --- | --- | --- | --- | --- | --- | --- |
| opening_category | categorical | PLAY | 0.482 | 0.95 | PLAY | below_bar |
| attach_target | categorical | 7 | 0.285 | 0.70 | 5 | below_bar |
| play_target | categorical | None | 0.000 | 0.70 | None | barred |
| evolve_target | categorical | 66 | 0.489 | 0.70 | 66 | below_bar |
| first_attack_ordinal | timing | 7 | 0.060 | 0.80 | 6 | barred |
| first_evolve_ordinal | timing | 3 | 0.121 | 0.80 | 3 | barred |

Seeded blocks: none.
