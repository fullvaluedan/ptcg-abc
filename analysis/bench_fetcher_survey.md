# Bench-fetcher survey: the early_collapse lever must be direct-to-bench

## Why this survey

The #1 real ladder loss is empty-bench early_collapse: our lone basic active is
knocked out turn 3 to 5 with the bench at 0, deck still 44 to 46 unplayed, six
prizes ours. The queued fix is decks/trolley.csv, which spends the ACE SPEC slot
on Precious Trolley (1126). A prior survey note claimed "Ultra Ball is the only
non-ACE-SPEC any-Pokemon fetch", which, if true, would mean the only way to add
basic search without giving up the Maximum Belt ACE SPEC is Ultra Ball. That
claim was worth re-checking against the full offline card database, because a
non-ACE-SPEC fetcher that benches a basic would dominate Precious Trolley (it
would keep Maximum Belt's +50 damage AND cut collapse).

## Full survey (offline card DB, all 28 non-Pokemon deck-search-for-Pokemon cards)

The prior claim is FALSE. Several non-ACE-SPEC cards fetch a Basic Pokemon. They
split cleanly by WHERE the fetched basic lands:

Direct-to-bench (puts the basic straight onto our bench):
- Precious Trolley (1126), ACE SPEC. Any number of basics, free, no turn end.
- Buddy-Buddy Poffin (1086), non-ACE. Basics with 70 HP or less only. Both our
  basics exceed it (Snover 90, Kyogre 150), so it fetches nothing here. Dead.
- Lumiose City (1267), non-ACE Stadium. Any basic, no HP cap, recurring every
  turn, BUT "if a player searches their deck in this way, their turn ends", and
  it is symmetric (the opponent gets the same search). The heuristic deliberately
  avoids turn-ending repeatable abilities, so it would not fire it; even if forced
  it costs the whole turn to bench one basic. Dead.
- Hop's Bag (1115): only "Basic Hop's Pokemon" (a named subtype). Dead.
- Accompanying Flute (1091): benches the OPPONENT's basics. Anti-synergy.
- Risky Ruins (1260): a stadium that damages benched basics. Anti-synergy.

To-hand (fetches the basic into hand; benching is a separate later step):
- Poke Pad (1152), non-ACE Item. Any non-Rule-Box Pokemon (Snover, Kyogre
  qualify), free, no discard. Cheaper than Ultra Ball.
- Brock's Scouting (1210), non-ACE Supporter. Up to 2 basics to hand, free.
- Ultra Ball (1121), non-ACE Item. Any Pokemon to hand, costs 2 discards.
- plus Dawn, Master Ball (ACE), and others.

So among non-ACE-SPEC cards, the only ones that put OUR basics directly on the
bench are HP-capped out (Poffin) or turn-ending and heuristic-avoided (Lumiose).
Precious Trolley remains the only clean direct-to-bench basic fetcher, and it is
ACE SPEC.

## The to-hand approach does not cut collapse (measured)

Built decks/pokepad.csv = baseline with Mega Signal 4 to 2 and +2 Poke Pad,
KEEPING the Maximum Belt ACE SPEC (the build trolley cannot use). Legal by the
rule layer and engine battle_start. Measured the empty-bench collapse rate with
tools/collapse_rate.py (heuristic mirror, n=80/deck):

    trolley   40/80  50.0%  (direct-to-bench, ACE SPEC Precious Trolley)
    pokepad   60/80  75.0%  (to-hand, non-ACE Poke Pad, keeps Maximum Belt)
    baseline  62/80  77.5%

Poke Pad is statistically tied with baseline (CIs overlap heavily) and nowhere
near trolley. This matches the earlier to-hand Ultra Ball result (pooled
63.8%, also well above trolley). The mechanism is the same one the staged plan
already flagged: the collapse fires turn 3 to 5, and a to-hand fetch arrives a
turn late because benching is a separate step after the fetch, whereas Precious
Trolley benches the basic the same turn for free. Keeping Maximum Belt buys
nothing if the deck still collapses at the baseline rate.

## Conclusion

The operative selection criterion for the early_collapse lever is DIRECT-TO-BENCH
placement, not merely "fetches a basic". Under that criterion every non-ACE-SPEC
option is ruled out (HP cap, turn-end, or wrong target), leaving Precious Trolley
(ACE SPEC) as the unique viable lever for this deck. decks/trolley.csv stays the
queued next-slot submission. pokepad.csv was deleted; the negative result is the
artifact (mirroring the deleted morebasics.csv and baseline_v2.csv). This closes
the "is there a missed non-ACE-SPEC bench fetcher" lever so future iterations do
not re-walk it.
