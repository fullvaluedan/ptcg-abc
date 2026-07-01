# Copied meta decks score BELOW our own trolley deck: the deck-copy thesis is refuted

Phase 4 ladder result. The standing top priority was to copy a proven 1300+ meta
deck and let its higher ceiling carry us past the ~570 floor our heuristic reaches
on the base decks (see `analysis/meta.md`). Two copies were built, validated,
gauntleted, and submitted:

- `decks/meta_archaludon.csv` (the #1 winning archetype, 811W/1786G in the harvest)
- `decks/meta_grimmsnarl.csv` (kazuki0123's exact leaderboard-#2 signature, the
  highest focused win rate in the harvest, the actual top-players' pick)

Both have now settled COMPLETE on the ladder, and both land WELL BELOW the trolley
floor. The thesis is refuted: our simple heuristic cannot extract a meta deck's
ceiling, and handing it a top deck makes it play WORSE than our own robust deck.

## The settled board (publicScore, all COMPLETE)

| ref      | build                       | deck         | publicScore |
|----------|-----------------------------|--------------|-------------|
| 54208986 | search (Phase 3, inert)     | baseline     | 591.9       |
| 54215558 | heuristic + deckout guard   | trolley      | 569.6       |
| 54215910 | heuristic + bench guard     | trolley      | 554.5       |
| 54218335 | recovered search            | trolley      | 514.7       |
| 54219892 | heuristic (same floor)      | **archaludon** | **451.4** |
| 54220220 | heuristic (same floor)      | **grimmsnarl** | **409.4** |

The two copied meta decks are the two LOWEST live builds on the board (excluding
the pre-fix floor 460.6 and the search-v2 450.8). Archaludon lands 118 pts under
the same heuristic on the trolley deck; Grimmsnarl lands 160 pts under it. The
deck is the only change between the trolley sub (569.6) and the two meta subs, so
the drop is entirely attributable to the deck.

## Why: the heuristic mispilots decks built for a skilled agent

Fresh per-agent replay pulls (`tools/scout.py pull`, self-play kept, loss buckets
via `analysis/loss_classifier.py`):

| deck       | record  | top loss buckets                    |
|------------|---------|-------------------------------------|
| archaludon | 2W/6L   | deckout 3, early_collapse 3         |
| grimmsnarl | 1W/3L   | deck_matchup 2, early_collapse 1    |

Neither deck's dominant leak matches the trolley deck's (early_collapse). The
Archaludon deck introduces a NEW leak our own decks never had: DECKOUT is its #1
loss (3 of 6). And this is WITH our deckout guard already in the shipped heuristic
(`DECKOUT_THRESHOLD`, `DRAW_CONSERVE_THRESHOLD`, `cap_count_for_deckout`): the
guard was tuned on the leaner baseline/trolley line, and the trainer-heavy
Archaludon engine (Ultra Ball, Pokegear, Poke Pad, Explorer's Guidance, Night
Stretcher, Lillie's Determination) mills the deck faster than those thresholds
catch. A skilled pilot sequences that engine to dig for a payoff and stop; our
heuristic plays draw cards greedily and decks itself out.

The Grimmsnarl deck fails a different way: it wins in human hands off a Rare Candy
evolution line and disruption package that our heuristic has no plan for, so it
loses on matchup and still collapses on an empty bench when the evolution never
comes together.

The common cause: a top-1300 deck is one half of a system whose other half is a
skilled agent. The deck's ceiling is only reachable by a pilot that executes its
game plan. Our floor heuristic is not that pilot, and the meta decks are LESS
forgiving of a naive pilot than the trolley deck, which was purpose-built for
robustness (high basic density, minimal fragile combos) rather than ceiling.

## Decision: trolley (569.6) stays the deployable deck; stop copying meta decks blind

The deck-copy top priority is closed as refuted by ladder data. Do NOT build and
submit tonakaiiii's Grimmsnarl variant or any further meta copy on the current
heuristic: the mechanism above predicts it scores in the same ~400-450 band, and
a submission would spend a slot to displace a stronger build from the latest-two-
scored pair. The trolley deck remains our best deployable deck, and the current
board leaders (search-on-baseline 591.9, trolley 569.6) are our real floor.

The honest read on the ~570-vs-1300 gap: it is NOT purely a deck gap as
`analysis/meta.md` assumed. It is a JOINT deck-and-pilot gap, and for our agent the
deck cannot be copied without the pilot. The only path that could unlock a meta
deck is an agent that actually executes its game plan (a search agent that reaches
the deck's real forward model, or deck-specific play logic), which is a modeling
effort, not another copy. The kept meta decks stay as harvested reference in
`analysis/meta.md` and as gauntlet foils, not as ladder submissions.

## Reproduce

```
.venv/Scripts/kaggle.exe competitions submissions -c pokemon-tcg-ai-battle
.venv/Scripts/python.exe tools/scout.py pull 54219892 -p replays/meta_archaludon
.venv/Scripts/python.exe tools/scout.py pull 54220220 -p replays/meta_grimmsnarl
```

Small live samples (4 and 8 replays), but the settled publicScores (409.4, 451.4,
both far under the 569.6 same-heuristic trolley floor) are the decisive signal and
agree with the offline loss buckets.
