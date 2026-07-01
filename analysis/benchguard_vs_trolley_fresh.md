# Bench guard vs plain trolley: fresh ladder pull corrects the "drift" call

Date: 2026-07-01 (UTC ~00:59, after the 00:00 reset).

## What was pulled

Both submissions run the SAME Precious Trolley deck. The only difference is the
heuristic: 54215910 carries the bench-development guard (bench a Basic first when the
bench is thin, before any other play), 54215558 runs the plain fail-open-fixed
heuristic.

Per-agent pull into isolated dirs, self-play skipped, seat detected per replay:

| sub | agent | W/D/L | early_collapse | endgame | board score |
| --- | --- | --- | --- | --- | --- |
| 54215910 | trolley + bench guard | 5/0/1 | 1 | 0 | 767.6 (BEST) |
| 54215558 | trolley, plain | 6/0/6 | 5 | 1 | 630.4 |

The prior pull had bench guard at n=4 (3W/1L), called too thin. It is still thin at
n=6, but it is now the board leader and its fresh record and early_collapse rate are
both better than the plain deck's.

## Every loss is still the same empty-bench signature

Per-loss digest (deck_end / bench_end):

- bench guard, 1 loss: deck 40, bench 0.
- plain trolley, 6 losses: deck 32/40/45/34/40 bench 0 (early_collapse), deck 32 bench 0
  (endgame_misplay).

Every loss ends with our bench at 0 and the deck still 32 to 45 cards deep: the lone
active knocked out with nothing to promote, deck barely played. Consistent with every
prior cross-agent pull. The guard's single loss is the same shape (bench 0, deck 40
full), so in that game the hand simply held no Basic to bench and no ordering rule could
have saved it.

## The correction

The standing NEXT guidance called the bench guard "drift, not signal," resting on the
prior iter's walk of every empty-bench LOSS: in 32 of 34 collapse moments the hand held
no benchable Basic, so no ordering rule could fire. That walk is sound but it can only
prove the guard cannot rescue an already-lost game.

It is blind to the guard's actual upside. When a Basic IS in hand, benching it first
(before a draw Supporter) can keep the bench non-empty through the turn-3 to turn-5
knockout window, turning a would-be collapse into a win. Those games never appear as
losses to walk, so a loss-only analysis structurally cannot see the benefit. The board
lead (767.6 over 630.4) and the cleaner fresh record (5W/1L, early_collapse 1/6 = 17%
vs 6W/6L, 5/12 = 42%) are weak positive evidence that the guard genuinely helps.

n is still small (6 vs 12) and the two scores sit inside the 130-plus point TrueSkill
drift band the notes track, so this is not conclusive. But it is enough to retire the
"drift, not signal" dismissal: the honest read is that the bench guard is the current
standing best and the preferred artifact for any future slot, not an inert re-hash.

## Decision

No submission this iter. The bench guard (54215910) is already on the ladder and
leading; the plain trolley (54215558) is already up; there is nothing validated-better
to ship, so all 3 remaining slots are held. Keep accruing episodes on both and re-pull
to see whether the guard's edge survives a larger sample.
