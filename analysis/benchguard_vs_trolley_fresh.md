# Bench guard vs plain trolley: a 35-game pull settles the call

Date: 2026-07-01 (UTC ~01:30). Supersedes the ~00:59 thin-sample read on this page.
See the "Update (UTC ~01:50)" section at the foot: a second, larger pull plus a board
flip now push the call past "tied" to "the plain deck leads."

## What was pulled

Both submissions run the SAME Precious Trolley deck. The only difference is the
heuristic: 54215910 carries the bench-development guard (bench a Basic first when the
bench is thin, before any other play), 54215558 runs the plain fail-open-fixed
heuristic. Per-agent pull into isolated dirs (replays_bg910_full, replays_tr558_full),
self-play skipped, seat detected per replay.

| sub | agent | public W/L | winrate | early_collapse | board score |
| --- | --- | --- | --- | --- | --- |
| 54215910 | trolley + bench guard | 8/6 | 57.1% | 6 of 6 (100%) | 680.2 |
| 54215558 | trolley, plain | 12/9 | 57.1% | 9 of 9 (100%) | 672.1 |

The prior read on this page used n=6 (guard 5W/1L, early_collapse 1/6 = 17%) against
n=12 (plain 6W/6L, 5/12 = 42%) and called the guard the standing best. That gap was
small-sample noise. At n=14 vs n=21 the two agents post the identical 57.1% winrate,
every loss is early_collapse, and the 8-point score gap sits deep inside the 130-plus
TrueSkill drift band. The guard's edge did not survive the larger sample.

## Every loss is the same empty-bench, full-deck signature

Per-loss digest (turn / my_prize_remaining / deck_end / bench_end), all early_collapse:

- guard, 6 losses: turns 5 to 13, deck still 17 to 40, bench 0. One is a developed-board
  collapse (turn 13, we had taken 4 prizes, deck 17, bench 0).
- plain, 9 losses: turns 3 to 13, deck still 32 to 45, bench 0. Three are pure turn-3
  openings (6-6 prizes, deck 44-45, bench 0): our lone active fell with nothing benched.

Every loss ends with our bench at 0 and 17 to 45 cards still in the deck. We do not deck
ourselves out here; the lone active is knocked out with nothing to promote, deck barely
played. Consistent with every prior cross-agent pull.

## The guard fires correctly; the residual is a draw-access brick

The earlier "drift, not signal" dismissal rested on a loss-only walk finding no benchable
Basic to reorder; the ~00:59 correction argued that walk is blind to the guard's upside
(benching before a would-be collapse becomes a win, which never shows as a loss). The
larger sample lets us test the guard directly instead of arguing from absence.

For each of our decisions in the 15 losses, we mirrored the live `choose` path: is this a
main select, is the bench thin (< THIN_BENCH), and does the menu actually offer a Pokemon
PLAY option? That last check is the real "we could have benched a Basic this turn."

The count of such bench-offered-while-thin decisions tracks the max bench we ever reached,
game for game. Where a Pokemon play was offered while thin, the bench grew; where the max
bench stayed 0, no such option was ever offered. The five plain-deck losses with max bench
0 (episodes 82936844, 82939817, 82941133, 82945486, 82949165) had zero bench opportunities
the entire game. In short: the guard benches every Basic it is ever handed. It is firing
correctly and it is not the flaw.

The flaw is upstream. Across the 15 losses, 6 (40%) never put a Basic on the play menu
while thin; in 5 of those the bench stayed empty the whole game and the lone active fell
alone. The rest benched the one or two Basics they drew and traded them off faster than
the deck replaced them. Raising basic density at the deck level (the trolley deck) and benching Basics first
at the agent level (the guard) are BOTH downstream of the same binding constraint: drawing
into a Basic in the first place.

## Decision and next lever

No submission this iter. Both agents are already on the ladder, statistically tied at
57.1%, and there is nothing validated-better to ship, so the remaining slots are held.

The bench-ordering lever is now settled: correct, firing, and not the leak. Two
independent bench levers (deck density, agent ordering) have each failed to move the
early_collapse rate off 100% of losses. The next genuine lever is not a third bench rule;
it is draw access, digging into a Basic when the bench is thin and the hand holds none
(search Items or draw Supporters played earlier), a deck-consistency change measured
against the offline collapse-rate mirror before any slot is spent.

## Update (UTC ~01:50): a larger sample and a board flip retire "benchguard is best"

Both leaders accrued another ~7 public episodes each and the board reordered. Re-pulled
both into fresh isolated dirs (replays/trolley_fresh, replays/benchguard_fresh),
self-play skipped, seat per replay.

| sub | agent | public W/L | winrate | early_collapse | board score |
| --- | --- | --- | --- | --- | --- |
| 54215558 | trolley, plain | 13/11 | 54.2% (n=24) | 11 of 11 (100%) | 668.8 |
| 54215910 | trolley + bench guard | 9/10 | 47.4% (n=19) | 10 of 10 (100%) | 639.7 |

Two things moved together since the ~01:30 read above. On the board the pair CROSSED:
last iter the guard led (701.4 > 686.0) and the standing NEXT called it "the preferred
future artifact"; now the plain deck leads (668.8 > 639.7). Independently, on the larger
head-to-head sample the plain deck also pulls ahead (54.2% vs 47.4%, where at n=14/21 they
were dead even at 57.1%). Two separate signals, board and record, now point the same way.

This does not prove the plain deck is durably better; the 29-point gap still sits inside
the 130-plus TrueSkill drift band and the winrate gap is a handful of games. What it does
retire is the opposite claim: five iters ago (044ff0b) the guard was reinstated as "the
standing best" off an n=6 pull, and the standing NEXT has carried "benchguard is the
preferred artifact" since. On the larger sample neither metric supports that. The honest
resting state is the writeup's own coda: the two are a wash within noise, the guard fires
correctly and is not the leak, and the binding constraint is draw access, not play order.

## Update (UTC ~01:50): the matchup lever stays closed on the larger sample

Re-ran analysis.opponent_archetype.scan_dir on both fresh pulls (the stated reopening gate
was a single opponent archetype climbing to a real share of our losses). It has not:

- trolley: 11 losses spread across 8 distinct archetypes, max 2 to any one line (Mega
  Starmie ex, Mega Lucario ex, Crustle), and we go 3W/2L and 2W/2L into the first two.
- benchguard: 10 losses across 7 archetypes, max 3 (Mega Lucario ex). That 30% share is
  the one borderline case, but it is n=19 small-sample and the plain deck is 2W/2L into
  Lucario, so it is not a durable matchup hole.

Every loss on both agents is still early_collapse (empty bench, deck 17 to 45). The
collapse is opponent-agnostic on the larger sample too, so no tech or sideboard card
reopens deck_matchup. The lever stays closed alongside bench-ordering, draw-engine, and
portfolio.
