# early_collapse is an empty-bench board collapse (cross-agent ladder evidence)

Phase 4 loss data. This iteration pulled fresh ladder replays for the three
heuristic-family submissions currently on the board and classified each in
isolation (one replay directory per submission, self-play validation games
excluded). The goal was to decide what the next submit slot should ship, now
that the public scores have reordered.

## Board at the time of this pull (Kaggle UTC 2026-06-30)

| ref      | agent                         | publicScore | games | W/L   | early_collapse | deckout | other            |
|----------|-------------------------------|-------------|-------|-------|----------------|---------|------------------|
| 54208986 | search (U10 COUNT veto only)  | 591.9       | 7     | 4/3   | 2              | 0       | endgame 1        |
| 54209468 | heuristic + COUNT deckout v1  | 539.4       | 32    | 13/19 | 10             | 4       | bad_det 3, end 2 |
| 54211499 | heuristic + draw-guard v2     | 534.6       | 9     | 3/6   | 5              | 1       | -                |

All three run the same baseline deck on the ladder and differ only in their
deckout handling (search is heuristic-equivalent on the ladder per
ladder_search_inert.md). The scores are TrueSkill estimates over small, unequal
opponent samples, so the ordering is not a clean A/B; what the buckets show is
robust regardless of the score noise.

## Two findings

1. early_collapse is the number one leak for every agent (2, 10, 5 losses; the
   top bucket in all three). deckout is now near zero everywhere (0, 4, 1). The
   deckout guards did their job: the dominant real loss from the earlier pulls
   (self-decking, once while ahead on prizes) is no longer the leak. The v2
   draw-trainer guard cannot cause an early_collapse, because it only acts at
   deckCount <= 8, which is deep into a game, whereas every early_collapse here
   ends at turn 3 to 5 with a near-full deck.

2. Every early_collapse loss is an empty-bench collapse. Across all three
   directories, 17 of 17 early_collapse losses end with our bench at zero. The
   shape is identical: turn 3 (sometimes 5), our deck still 44 to 46 cards
   (essentially unplayed), 6 prizes still ours, our lone active knocked out with
   nothing on the bench to promote, so we lose on the no-Pokemon rule. This is
   not a deckout (the deck is full), not a prize blowout (no race happened), and
   not a heuristic misplay (the heuristic benches every basic it draws; there
   was no second basic to bench). It is deck construction: 6 basic Pokemon in 60
   cards means a large fraction of openings are a lone attacker, and one early
   knockout ends the game.

## What changed in the tooling

parse_replay now tracks final_bench alongside final_deck and final_prize and
exposes my_bench_end / opp_bench_end on the digest (purely additive; classify
behavior is unchanged, so the bucket set is stable). This makes the empty-bench
nature of an early_collapse a first-class, reproducible field rather than an
ad-hoc replay walk, so future pulls can confirm the leak shape directly.

## Decision for the next submit slot

This confirms the staged plan rather than overturning it. The only lever that
attacks early_collapse is a consistency deck that adds basic-Pokemon presence;
the deckout guards, the search layer, and any further heuristic policy work do
not touch it (the bench is empty because the hand held no benchable basic).
On quota reset, run the submissions check first, then submit the staged Ultra
Ball deck (submission_ultraball.tar.gz): it adds the only non-ACE-SPEC any-
Pokemon fetch without giving up the Maximum Belt ACE SPEC, and measured even
(non-regressing) with baseline in self-play, where its only possible upside,
fewer empty-bench openings, cannot show. trolley (Precious Trolley, puts a
basic straight to the bench for free) is the stronger follow-up for a later
slot if ultraball's ladder replays show early_collapse persists, since the
collapse lands as early as turn 3, before a discard-cost fetch like Ultra Ball
can reliably fire.
