# Fresh ladder pull confirms early_collapse on the search agent too

Phase 4 scout data, pulled 2026-06-30 (UTC) directly off the scored ladder. The
prior collapse-rate work classified 17 of 17 ladder losses across the three
HEURISTIC-family submissions as empty-bench early_collapse, and the offline
collapse_rate test picked the trolley deck as the fix (see
[collapse_rate_decks.md](collapse_rate_decks.md)). The open gap was whether the
SEARCH agent, which sits at the top of our ladder cluster, fails the same way.
This pull closes that gap: it does.

## What was pulled

Two submissions, each pulled into its own replay dir with `tools/scout.py pull`
and classified offline with `analysis/loss_classifier.py`:

| ref       | submission                 | publicScore | replays | W/D/L   | top loss bucket        |
|-----------|----------------------------|-------------|---------|---------|------------------------|
| 54208986  | search agent (Phase 3)     | 591.9       | 7       | 4/0/3   | early_collapse 2 of 3  |
| 54211499  | heuristic deckout guard v2 | 471.6       | 20      | 7/0/13  | early_collapse 9 of 13 |

54208986 loss buckets: early_collapse 2, endgame_misplay 1.
54211499 loss buckets: early_collapse 9, bad_determinization 3, deckout 1.

## Reading

1. **early_collapse is the cross-agent leak.** It is the single biggest loss
   bucket for the ladder leader (search) AND for the deckout-guarded heuristic.
   The empty-bench knockout (a lone basic active KO'd turn 3 to 5 with nothing to
   promote and the deck still mostly unplayed) is a property of the BASELINE DECK,
   not of the policy on top of it. Both submissions ran the same 6-basic
   baseline.csv, so both inherit the same glass-cannon failure. This is the
   strongest evidence yet that the next lever is the deck, and specifically the
   already-staged trolley deck, not another agent-logic guard.

2. **The deckout guard worked at its own job.** On 54211499 the deckout bucket is
   down to 1 of 13 losses (it was 6 in the earlier mixed batch and was the
   motivating leak for the U10 guard). The narrowed draw-trainer guard is doing
   what it was built to do; the residual losses have simply moved to the deck-level
   early_collapse that the guard was never meant to touch.

3. **Public score is noisy, do not over-read the ordering.** 54208986 (591.9) is
   above 54211499 (471.6), but the search agent is INERT on the scored ladder (the
   forward model is unavailable in the grader, so it degrades to the heuristic plus
   safety layer, see ladder_search_inert.md), the samples are small (7 and 20
   games), and TrueSkill ratings drift heavily early. The reliable signal here is
   the LOSS-BUCKET composition, not the absolute rating gap. Both agents lose to
   the same thing.

4. **bad_determinization on a heuristic submission is a classifier artifact.** The
   3 bad_determinization tags on 54211499 are not actionable: that submission runs
   no determinized search, so the bucket is a misfire of the heuristic classifier
   on those replays, not a real determinization failure. It does not change the
   ranking (early_collapse still dominates) and is not a lever.

## Decision unchanged, now cross-validated

The queued next submission stays `submission_trolley.tar.gz` (current heuristic
with the narrowed deckout guard, plus the trolley deck that frees a basic onto the
bench to answer the empty-bench knockout). This pull adds the search agent's own
ladder losses to the evidence base behind that choice. Submit it on the next slot
once the UTC daily quota resets, after the mandatory `kaggle competitions
submissions` check confirms the trolley deck is not already on the ladder.

After trolley has its own ladder episodes, re-pull and re-classify to confirm the
live early_collapse bucket shrinks versus these two baseline-deck submissions.

## Reproduce

```
.venv/Scripts/python.exe tools/scout.py pull 54208986 -p replays/search_leader
.venv/Scripts/python.exe tools/scout.py pull 54211499 -p replays/deckout_v2
```

Replays are competition data and stay gitignored under replays/; only the
classified bucket counts are recorded here.
