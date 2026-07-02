# Learned eval A/B: PTCG_LEARNED_EVAL off vs on in the search agent

Plan U5. Same agent (search), same opponent pool, learned eval flag off vs
on, 400 games per arm via tools/run_ab.py's resumable checkpointed batches
(checkpoint: data/training/ab_progress.json, batch size 20).

## Setup

- Agent under test: search (agent_search, not the shipped ladder agent).
- Opponents: deck:meta_archaludon, deck:meta_grimmsnarl,
  deck:meta_grimmsnarl_tonakaiiii, deck:aggro, deck:control, deck:ultraball,
  deck:trolley, deck:trolley_thick.
- Matches per arm: 400.

## Results

| arm | wins | losses | matches | win rate |
|---|---|---|---|---|
| off (PTCG_LEARNED_EVAL=0) | 272 | 128 | 400 | 68.00% |
| on (PTCG_LEARNED_EVAL=1) | 275 | 125 | 400 | 68.75% |

diff_pp (on minus off): +0.75 percentage points.

## Gate

Keep PTCG_LEARNED_EVAL default on only if on beats off by more than 4
percentage points at N=400/arm. Otherwise keep the flag default off,
document why, and continue.

Verdict: **keep default off**. on beat off (+0.75pp), so the learned eval is
not worse than the hand-tuned eval, but the margin falls well short of the
4pp bar required to flip the shipped default. search/eval.py's
PTCG_LEARNED_EVAL default (`os.environ.get("PTCG_LEARNED_EVAL", "0") != "0"`)
is unchanged; no code change was needed since off was already the default.

## Phase A gate (whole-plan check)

The Phase A gate asks for the learned eval to at least match the hand-tuned
eval (win or documented tie) before Phase B starts. on's 68.75% vs off's
68.00% is a small win for the learned eval, so this condition is satisfied
even though the flag stays off by default. Nothing here changes the shipped
agent: agent_search is not the ladder agent (agent_heuristic ships), so this
A/B affects only the offline search evaluation and the Strategy writeup, not
the submission.

## Next

U6: one retrain generation, folding the weighted top_player corpus (U3c,
--source-weights) into the combined training set, then re-run this A/B.
