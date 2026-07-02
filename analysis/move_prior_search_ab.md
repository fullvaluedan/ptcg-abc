# Move-prior search A/B: PTCG_MOVE_PRIOR off vs on in the search agent

Plan U8c. Same agent (search), same opponent pool, move-prior candidate
ordering flag off vs on, 400 games per arm via tools/run_ab.py's resumable
checkpointed batches (checkpoint: data/training/ab_progress_u8c.json, batch
size 20).

## Setup

- Agent under test: search (agent_search, not the shipped ladder agent).
- Opponents: deck:meta_archaludon, deck:meta_grimmsnarl,
  deck:meta_grimmsnarl_tonakaiiii, deck:aggro, deck:control, deck:ultraball,
  deck:trolley, deck:trolley_thick.
- Matches per arm: 400.

## Results

| arm | wins | losses | matches | win rate |
|---|---|---|---|---|
| off (PTCG_MOVE_PRIOR=0) | 254 | 146 | 400 | 63.50% |
| on (PTCG_MOVE_PRIOR=1) | 274 | 126 | 400 | 68.50% |

diff_pp (on minus off): +5.00 percentage points.

## Gate

Per the addendum plan: keep only if win rate does not drop and speed
improves, or win rate improves outright. run_ab.py's own numeric gate
(matching the U5/U6 posture) additionally asks for the margin to clear 4
percentage points before flipping a shipped default.

Verdict: **flip default on**. on beat off outright by +5.00pp, clearing the
4pp margin, so search/rollout.py's `_MOVE_PRIOR` default is flipped from off
to on (`os.environ.get("PTCG_MOVE_PRIOR", "1") != "0"`).

## Speed criterion (documented gap, per U8c's own prior note)

This repo has no existing nodes/decisions-per-second instrumentation
(tools/run_ab.py, tools/parallel_gauntlet.py, tools/gauntlet.py do not
capture it), and `search_decision`'s per-move work is bounded by a fixed
time budget and a fixed max_determinizations count regardless of candidate
order, so PTCG_MOVE_PRIOR is not expected to change wall-clock speed except
in the rare abandoned-determinization edge case. The resumable/checkpointed
run for this gate does not produce a clean per-arm elapsed figure either
(each arm ran across two separate background invocations split by a
time-budget cutoff, so wall time reflects process-restart overhead as much
as search work). Speed is therefore not blocking here: the win-rate result
alone clears the gate with room to spare (+5.00pp vs the +4.0pp bar), so no
new profiling infrastructure was built to chase the secondary criterion.

## Scope note

This wires into agent_search, NOT agent_heuristic (the shipped ladder
agent). Per LOOP_BRIEF.md this stays TRACK S regardless of gate outcome:
agent_search has been ladder-negative (514.7 vs the 569.6 king), so this
result improves the offline search and the Strategy writeup only. It never
touches agents/heuristics.py or the deck csv and never spends a ladder slot.

## Next

U9, U11, U12 per the combined plan; U10 is already superseded by U62/U63.
