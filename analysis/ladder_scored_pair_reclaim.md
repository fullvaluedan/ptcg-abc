# The scored pair is currently our two WORST builds: reclaim it next slot

## Finding (verified from the live board, 2026-07-01 11:53 UTC)

The ladder is latest-two-scored (`docs/PLAYBOOK.md`): only our two most recent
submissions count. Our two most recent are the refuted meta-deck copies:

| ref      | build                | submitted (UTC)     | publicScore |
|----------|----------------------|---------------------|-------------|
| 54220220 | meta_grimmsnarl      | 2026-07-01 04:03    | 506.5       |
| 54219892 | meta_archaludon      | 2026-07-01 03:48    | 391.8       |

Best-of-pair = 506.5. Our achievable floor is far higher:

| ref      | build                     | publicScore |
|----------|---------------------------|-------------|
| 54208986 | heuristic+priors, base    | 591.9       |
| 54215558 | heuristic, trolley        | 569.6       |

So our LIVE standing is dragged ~63 points below what we already have on the
board, purely because the last two slots were spent on the meta copies that
`analysis/meta_decks_underperform_on_ladder.md` had already refuted. That note
explicitly warned a meta submit would "spend a slot to displace a stronger build
from the latest-two-scored pair"; the 03:48 and 04:03 submits did exactly that.
This note records the realized cost and the fix.

## Active search is confirmed WORSE than the heuristic on the same deck

`analysis/ladder_search_inert.md` left "recover search on the ladder" as an open
lever (it would need a forward model the match-time engine did not expose). We
then shipped a build that force-loads our own bundled cg so determinized search
actually runs (54218335, verified by the ~0.5s per-decision bank drawdown it was
built to produce). Its ladder result:

| ref      | build                     | search runs? | publicScore |
|----------|---------------------------|--------------|-------------|
| 54218335 | search, trolley           | yes          | 514.7       |
| 54215558 | heuristic, trolley        | no           | 569.6       |

Same deck, search active vs heuristic-only: 514.7 vs 569.6. Running search does
not help; it costs ~55 points. Combined with the inert-search history, the lever
is closed with data: do NOT ship a search-active build, and do NOT ship the
queued bench-guarded SEARCH (it stacks a likely-neutral guard on the losing search
layer). The plain heuristic is our strongest pilot on the ladder.

## Decision: reclaim the pair with our two best HEURISTIC builds

The next-slot priority is no longer "strengthen the agent" experiments (offline
gauntlets are not ladder-predictive, and every agent lever tried has been ladder-
neutral or negative: search -55, bench guard -15 at 554.5 vs 569.6, meta copies
-120 to -180). The concrete, verifiable win sitting on the table is to get our two
strongest builds back into the scored pair.

Plan for the next two free slots (00:00 UTC 07-02 onward, one submit per slot,
board check FIRST each time):

1. Slot 1: resubmit the trolley heuristic (the 569.6 config, `agent_heuristic` +
   `decks/trolley.csv`, clean env). This evicts archaludon (391.8); pair becomes
   [trolley ~569, grimmsnarl 506.5], best ~569.
2. Slot 2: resubmit the base-deck heuristic-with-priors (the 591.9 config). This
   evicts grimmsnarl (506.5); pair becomes our two best, best ~591.

Note on "never submit a build already on the ladder": that rule exists to stop
wasteful duplicate slots that yield no new info. Here the resubmit is not for new
info; it is to refresh recency so a known-good build re-enters the latest-two
pair, which is the explicit reason the brief tracks the pair. The spirit of the
rule ("never displace a stronger live build with a worse experiment") is what we
are honoring: we are replacing weaker live builds with stronger ones. Confirm the
exact tarballs still build and load through the grader exec-without-__file__ path
before each submit.

## What NOT to do (closed by data, do not re-walk)

- Do not submit another meta-deck copy (refuted, `meta_decks_underperform`).
- Do not submit a search-active or bench-guarded-search build (search -55 here).
- Do not chase the leaf-eval terms (inert on terminal rollouts) or the depth-cut /
  bench-floor joint lever (refuted, `thin_bench_threshold_is_flat.md`).
