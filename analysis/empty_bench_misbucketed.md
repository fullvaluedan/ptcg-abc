# Empty-bench collapses were hiding inside bad_determinization

## Finding

The `bad_determinization` bucket was over-counting on the real ladder. Inspecting
every `bad_determinization` loss across the three heuristic-family replay pulls
(54208986 search, 54209468 deckout v1, 54211499 deckout v2) showed that most of
them ended with **our bench at zero** while our deck was still full and the
opponent had not taken all six prizes. That is the empty-bench collapse signature
(lone active knocked out, nothing to promote), the same deck-thinness failure that
`early_collapse` already names. They missed that bucket only because of two gates:

- `early_collapse` required the game to end by turn 8 (`EARLY_TURN_LIMIT`), but
  these collapses landed at turn 9 to 12.
- `early_collapse` required `took_at_most_one` (five or more prizes still ours),
  but in several games we had already traded two or three prizes before the lone
  active fell.

So a collapse that happened a turn or two late, or after a couple of early
trades, fell through to `bad_determinization`. The name is doubly misleading on
the ladder: determinized search is inert there (see ladder_search_inert.md), and
the bucket was not even capturing search-shaped losses, it was capturing the
empty-bench collapse the deck-thinness fix targets.

## Fix

`classify_loss` now buckets a loss as `early_collapse` whenever the final bench is
empty (`my_bench_end == 0`), placed after `deckout` and `endgame_misplay` and
after the `deck_matchup` blowout check, so:

- a deckout (deck hit zero) stays `deckout`,
- a near win we needed one or two prizes to close stays `endgame_misplay`,
- a clean prize blowout stays `deck_matchup`,
- a developed-board midgame race loss (bench not empty) stays
  `bad_determinization`, the genuine residual lever,
- an empty bench with cards still in deck and the opponent not steamrolling is
  `early_collapse`, regardless of turn or prizes already traded.

`my_bench_end` is `None` when the field was never observed, so the rule never
fires on a guess (it only reclassifies losses where an empty bench was actually
recorded).

## Reclassification on the real pulls

| agent | before | after |
| --- | --- | --- |
| 54209468 v1 (19 losses) | early_collapse 10, deckout 4, bad_det 3, endgame 2 | early_collapse 12, deckout 4, endgame 2, bad_det 1 |
| 54211499 v2 (13 losses) | early_collapse 9, bad_det 3, deckout 1 | early_collapse 12, deckout 1 |
| 54208986 search (3 losses) | early_collapse 2, endgame 1 | unchanged (its losses were not empty-bench) |

Five losses moved from `bad_determinization` to `early_collapse`;
`bad_determinization` across the three agents dropped from 6 to 1. The honest
report now shows empty-bench deck-thinness as the overwhelming ladder leak, with a
single genuine developed-board race loss left in `bad_determinization`.

## Why this matters

It does not change the next submission, it strengthens it. The queued
`submission_trolley.tar.gz` (Precious Trolley, a free basic straight to the bench)
targets exactly this empty-bench collapse, and this reclassification shows the
collapse owns an even larger share of real losses than the prior report credited.
The lone residual `bad_determinization` is the developed-board midgame race, the
honest **second** lever to characterize only after trolley has reduced the
collapse on the ladder. Do not read the old `bad_determinization` count as a
search or determinization problem.
