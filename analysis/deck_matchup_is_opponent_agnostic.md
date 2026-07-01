# The empty-bench collapse is opponent agnostic: no deck_matchup lever exists

## Why this analysis

For twenty-odd Phase 4 iterations the loss classifier has named `deck_matchup`
as one of the four candidate loss buckets that could drive the next improvement,
yet it was never grounded in real data. The classifier only reads OUR end state
(empty bench, self-deckout, prize blowout); it has never looked across the table
at WHICH opponents beat us. So the question "do we lose to a specific archetype a
tech card could answer?" had never actually been asked of the replays.

`analysis/opponent_archetype.py` asks it: for every ladder replay it reads the
opponent's revealed Pokemon, labels the deck by its headline attacker (the Mega
or ex line that wins the game), and tallies our win/loss record per archetype.

## The data

Fresh pull of both standing leaders on 2026-07-01 (benchguard 54215910 and
trolley 54215558, self-play validation games excluded): 28 ladder games,
16W/12L (57%), across 15 distinct opponent archetypes.

| archetype          |  W |  L | note                         |
|--------------------|----|----|------------------------------|
| Mega Starmie ex    |  6 |  1 | most common opponent; we win it 86% |
| Mega Lucario ex    |  2 |  2 |                              |
| Fezandipiti ex/-   |  1 |  3 | a shared draw-engine support, not a deck (see below) |
| Dragapult ex       |  1 |  1 |                              |
| Mega Lopunny ex    |  0 |  1 |                              |
| Mega Abomasnow ex  |  0 |  1 | a mirror of our own deck on the ladder |
| Crustle / Dwebble  |  0 |  2 |                              |
| Alakazam (Abra)    |  0 |  1 |                              |
| Dunsparce / Duosion / Riolu / Sinistcha ex / Palafin | 5 | 0 | |

## The finding: the losses do not cluster

The 12 losses spread across 10 distinct archetypes. The most we lose to any
single line is 2. We BEAT the single most common opponent, Mega Starmie ex, 6-1.
There is no archetype that beats us often enough to justify a sideboard or tech
card, and there is no archetype we are structurally helpless against.

Two of the "Fezandipiti" losses illustrate the mechanism rather than a matchup:
Fezandipiti (and Fezandipiti ex) is a support Pokemon whose ability draws cards;
it appears on the bench of many different decks. In those games we collapsed so
early that the opponent's actual headline attacker never came down to be
revealed, so the game is labeled by the only ex on their board. That is the
opposite of a bad matchup: it is us bricking on an empty bench before the
opponent had to commit anything.

Every one of the 12 losses is also classified `early_collapse` by the loss
classifier (empty bench, lone active knocked out, prizes untouched). Combining
the two views: we lose the same way (our own empty-bench brick) regardless of
who is across the table. The collapse is opponent agnostic.

## Consequence: close the deck_matchup lever

A tech or sideboard card only helps when losses concentrate on a matchup it
answers. They do not. The leak is our opening-hand consistency (no Basic to
bench), which is deck-composition bound and already at the falsified frontier:
the Precious Trolley fetcher deck (the standing artifact) is the best collapse
rate the card pool offers, more literal basics was falsified competitively
(analysis/deck_design.md), the direct-to-bench fetcher survey found Precious
Trolley is the unique viable one (analysis/bench_fetcher_survey.md), and the
agent already benches and fetches a Basic first when the bench is thin
(agents/heuristics.py choose_play / _choose_card_select).

So `deck_matchup` is retired as a lever with data, the same way bench-ordering,
the draw-engine survey, and portfolio decks were retired. Future iterations
should not chase a matchup tech card. `scan_dir` in the new module lets any
later pull re-check this cheaply as more episodes accrue: if a single archetype
ever climbs to a real share of our losses, that would reopen the question, but
nothing in the current 28 games does.
