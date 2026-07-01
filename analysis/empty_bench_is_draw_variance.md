# Empty-bench collapse is draw variance, not play ordering

Phase 4 loss-data finding, from the first ladder replays of the two Precious
Trolley submissions (07-01 UTC). It explains why the agent-level bench-first
guard (commit a7fe629, ref 54215910) is not the improvement it was staged to be,
and it retires bench-ordering heuristics as a lever against early_collapse.

## The data

Pulled the live ladder replays for both new submissions and classified them:

- ref 54215558 (plain trolley deck, c94f927 heuristic): 8 replays, 3W/5L,
  early_collapse 4 of 5 losses, endgame_misplay 1. Live publicScore 633.3.
- ref 54215910 (trolley deck + bench-first guard a7fe629): 3 episodes so far
  (too thin to classify), early_collapse in the one loss seen. Live publicScore
  480.6.

early_collapse (our lone active knocked out with an empty bench, nothing to
promote) stays the number one leak even on the higher-search trolley deck. So
the deck-search fix lifted the score but did not close the leak.

## Why the bench-first guard cannot close it

The guard (a7fe629) benches a Basic first whenever the bench is thin, before any
other play, on the theory that we were mis-ordering and playing a draw Supporter
instead of benching an available Basic. Tested that theory directly: for every
one of the 5 early_collapse losses, walked every decision where our bench was
empty and our active was in play, and checked whether our hand held a benchable
Basic Pokemon at that moment.

Per game (empty-bench decision moments / of-those holding a benchable Basic):

- ep 82936844 (turn 3):  7 / 0
- ep 82939014 (turn 13): 3 / 1
- ep 82939795 (turn 7):  8 / 1
- ep 82940174 (turn 9):  5 / 0
- ep 82940487 (turn 11): 11 / 0

Totals: 34 empty-bench decision moments, and in only 2 of them (6 percent) did
we hold a benchable Basic. In 3 of the 5 losses we never once held a Basic while
the bench was empty.

The 2 exceptions do not rescue the guard either. Inspecting their select
options: ep 82939014 was a forced single-option decision (no bench choice), and
ep 82939795 offered only an ATTACK and two selectors (no bench-a-Basic play).
So in zero of the 34 empty-bench moments could a bench-first guard have benched a
Basic. The guard has no purchase on the actual collapse losses.

That is fully consistent with 54215910 sitting below plain trolley (480.6 vs
633.3), though that gap alone is inside the TrueSkill drift band the notes track
(130-plus points between identical agents), so the offline mechanism, not the
score, is the reason to stop pursuing bench ordering.

## What the collapse actually is

The trolley deck runs 6 benchable Basic copies of 60 (Kyogre 2, Snover 4), the
same count as baseline. Trolley never raised Basic density; its lever is Basic
search: Precious Trolley (ACE SPEC, one copy, free, direct to bench) plus Ultra
Ball (to hand). The finding above says that search has a consistency ceiling: in
roughly half our losses neither a second Basic nor a resolved fetch is online by
the turn the lone active is knocked out (as early as turn 3, and in ep 82940487
never across 11 turns). The collapse is a draw and search-consistency failure,
not a mis-ordered play.

## Consequences for the loop

- Bench-ordering heuristics are retired as an early_collapse lever. Do not
  invest further in play-order guards for the empty-bench collapse; the losing
  games have no Basic in hand to reorder.
- Do not resubmit the bench-guard family. Let 54215910 accrue episodes; if a
  larger sample confirms it below trolley, plain trolley (54215558) is already on
  the ladder as the stronger scored entry and must not be double-submitted.
- The one untried consistency lever is a different early draw or search engine
  that finds Basics without diluting the Mega Abomasnow win condition (more
  literal Basics was falsified on overall win rate: morebasics was the worst
  competitive deck, see analysis/deck_design.md). That is a prepared-slot deck
  research task, not a same-iteration submit. Until such a candidate is built and
  measured, the residual empty-bench collapse looks like an irreducible cost of
  the glass-cannon win condition, and trolley (633.3) is the standing best.

Sample caveat: 5 losses over 8 games is thin, and these are per-decision
snapshots within multi-decision turns. The signal is one-directional and the
mechanism (no Basic in hand) is unambiguous, but re-pull once trolley and the
bench-guard accrue more episodes to confirm the 6 percent hold-rate holds.
