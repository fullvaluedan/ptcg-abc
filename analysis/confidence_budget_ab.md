# U12: confidence-based search time allocation, gauntlet A/B

Plan: docs/plans/2026-07-02-combined-learned-eval-plan-v2.md, U12. Scale the per-decision
soft time cap by how uncertain the learned evaluator (search/learned_eval.py) is about the
root position: an undecided position (win probability near 0.5) gets more of the thinking
bank, an already-decided one (near 0 or 1) gets less. Implemented in search/timebudget.py's
`confidence_multiplier` and `TimeBudget.allot`, wired into agents/agent_search.py behind
`PTCG_CONFIDENCE_BUDGET` via a new `_root_confidence(obs)` helper that scores the root state
with `learned_eval.predict_win_probability` and never raises (returns `None`, no scaling, on
any missing field or scoring failure).

Track: search/agent_search.py is not the shipped ladder agent (agents/agent_heuristic.py
ships). This unit is TRACK S (Strategy-prize offline work); it cannot move the ladder and
spends no submission slot regardless of its gate result.

## Gauntlet

`tools/confidence_budget_ab.py --agent search -n 200`, the standard 8-deck opponent pool
(`deck:meta_archaludon deck:meta_grimmsnarl deck:meta_grimmsnarl_tonakaiiii deck:aggro
deck:control deck:ultraball deck:trolley deck:trolley_thick`), 200 games/arm via
`tools.parallel_gauntlet.run_parallel_gauntlet` with `PTCG_CONFIDENCE_BUDGET` baked into each
shard's env (raw result in data/training/confidence_budget_ab_result.json, gitignored):

| arm | wins | losses | win rate | avg bank spend |
| --- | --- | --- | --- | --- |
| off (PTCG_CONFIDENCE_BUDGET=0) | 144 | 56 | 72.0% | 12.69s |
| on (PTCG_CONFIDENCE_BUDGET=1) | 146 | 54 | 73.0% | 11.01s |

0 invalid moves in either arm.

## Gate

Plan U12 gate: keep only if win rate does not drop AND average bank spend does not increase,
at least 400 games total (400 here: 200/arm).

- win_rate_kept: True (73.0% >= 72.0%)
- bank_spend_kept: True (11.01s <= 12.69s)
- gate_passed: True

Both conditions clear, with the on arm directionally better on both axes at once: it wins
slightly more often while spending noticeably less of the thinking bank per match. That is
the intended effect, not a coincidence: scaling the cap down on already-decided positions frees
bank that the reserve-fraction guard would otherwise have left partly idle, while the boost on
genuinely uncertain positions buys the extra determinizations that matter most.

## Applied

`PTCG_CONFIDENCE_BUDGET` default flipped on in agents/agent_search.py (`os.environ.get(...,
"1") != "0"`; the env override still works either direction). agent_search.py is not on a
shipped path, so this flip earns zero ladder rank points on its own, same posture as U8c's
move-prior flip and every other search-side lever.
