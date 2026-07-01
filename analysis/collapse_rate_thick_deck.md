# More basics cut empty-bench collapse: the trolley_thick deck lever

## Why this lever, and why now

Two of our own refutations closed the pilot-side bench knobs and pointed here. The
THIN_BENCH sweep (thin_bench_threshold_is_flat.md) showed no develop-first threshold in
0..4 beats the shipped 2: the ~40% our-seat board-out floor "is set by the deck's basic
density and the opponent's pressure, NOT by how wide we insist the bench gets." Its own
conclusion named the open levers: "the DECK (basic density / bench-fetch card count)" or a
stronger pilot that does not trade into the knockout. The pilot-side and search-side levers
are ladder-gated and the ladder is rationed; the DECK lever is measurable offline TODAY via
the trusted mechanism (collapse rate), not a noisy win rate. So this iteration tests it.

## What was tried first and rejected

A free bench-fetch item (Buddy-Buddy Poffin, 1086: "Search your deck for up to 2 Basic
Pokemon with 70 HP or less and put them onto your Bench") would have been the ideal add:
no discard cost, runnable at 4 copies, and its text already matches the pilot's
_benches_basic_from_deck develop-first priority. It is dead in this deck: both our basics
exceed the 70 HP cap (Snover 90, Kyogre 150), so Poffin could never fetch either. The only
any-basic fetch in the pool (Precious Trolley) is an ACE SPEC, capped at one and already in.
That leaves adding basics directly.

## The change

`decks/trolley_thick.csv`: Kyogre 2 -> 4 (+2 Basics, 6 -> 8) and Basic {W} Energy 35 -> 33
(-2), everything else identical to trolley.csv, still 60 cards. Kyogre is already the deck's
secondary Basic attacker (150 HP, Swirling Waves 130 for 3 {W}), so the two extra copies are
in-theme board presence, not filler, and 33 {W} in 60 is still a heavy water base that easily
powers Mega Abomasnow ex (3 {W} for 200) and Kyogre.

## Result: empty-bench early_collapse rate, heuristic mirror self-play

Same tool and reading as collapse_rate_decks.md: `tools/collapse_rate.py`, N mirror games
per deck, loser classified by loss_classifier. The mirror OVER-states the absolute rate (both
seats pilot the same glass cannon); the signal is the RELATIVE reduction, since on the ladder
only our deck carries the fix.

| deck          | run 1 (n=120) | run 2 (n=120) | pooled (n=240) |
|---------------|---------------|---------------|----------------|
| trolley       | 92/120 76.7%  | 102/120 85.0% | 194/240 80.8%  |
| trolley_thick | 74/120 61.7%  | 83/120 69.2%  | 157/240 65.4%  |

Pooled reduction -15.4pp, two-proportion z ~ 3.8 (p < 0.001), same direction and magnitude in
both independent runs. This is comparable to the original baseline -> trolley lever
(-19.4pp, z ~ 3.7, collapse_rate_decks.md): adding two basics buys most of what the
Ultra-Ball + Trolley consistency package bought.

## Win-rate non-regression

Cutting two energy for two Kyogre does not cost win rate. Head-to-head (heuristic on each
deck, seats alternated, n=120): trolley_thick beats trolley 66-54 (55.0%, z ~ 1.1 vs 50%,
inside noise). Not a regression, a slight edge, exactly as the collapse metric would predict
from denser board presence. Note the meta.md caveat: this in-house head-to-head is not
ladder-predictive for win rate; it is only a gross non-regression check, not an upside claim.

## Decision: stage it, do NOT deploy it now

trolley_thick is the next DECK candidate to ladder-test, not a deploy this iteration. Two
reasons. First, the pending high-value action is the scored-pair reclaim (restore the verified
569.6 trolley floor after the meta-copy experiments pushed it out), and the deployable stays
trolley until a candidate is ladder-validated. Second, per the measurement discipline the
collapse-rate reduction is a real mechanism fact but offline win rate is not ladder-predictive,
so trolley_thick earns a scored slot only AFTER the floor is reclaimed and a slot is free to
A/B it as a clean single-deck change. Sequence: reclaim the trolley floor first; then, on a
later slot, submit trolley_thick (heuristic pilot) and read the ladder, keeping trolley as the
paired floor so the standing never drops below the known-good build.

This does not touch the shipped pilot and is consistent with "keep the robust trolley deck as
the deployable deck until a stronger agent proves it can pilot a better one": trolley_thick is
the same pilot on a denser-basic version of the same deck, staged behind the reclaim.
