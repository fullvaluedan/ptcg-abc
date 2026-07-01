# Determinized search is inert on the Kaggle ladder

## Finding

The submitted search agent (ref 54208986, publicScore ~592) does NOT actually run
its determinized lookahead on the ladder. Every searchable decision falls back to
the heuristic. The search agent is therefore heuristic-equivalent on the ladder,
statistically tied with the deckout-guarded heuristic (ref 54209468, ~586) since
both run the same heuristic over the same baseline deck.

## Evidence

1. The competition sets `actTimeout: 0` and gives each player a single ~600s
   overage bank (`remainingOverageTime`). With no per-step base allowance, the
   drop in that bank per decision IS the real wall-clock thinking time.

2. In every search-agent replay, our MAIN (searchable) decisions draw only
   0.02 to 0.05s from the bank:

   ```
   episode 82872130: 23 searchable MAIN decisions, max bank draw 0.029s
   episode 82873746: 12 searchable MAIN decisions, max bank draw 0.046s
   episode 82874740: 24 searchable MAIN decisions, max bank draw 0.035s
   ```

   The per-move search soft cap is 0.5s and the endgame solver raises it to 4.0s.
   If search ran, even one decision would draw hundreds of ms. None do.

3. Locally, the exact same replayed observations take 500 to 830ms through
   `agent()` (search runs to its budget). So the observation shape is fine; the
   difference is the match-time engine, not the data.

## Root cause

The agent's fallback chain swallows the failure silently. The decisive detail is
the 0.02s cost: a `search_begin` that merely raised at CALL time would still burn
the full 0.5s budget loop (the loop retries fresh determinizations until the
clock expires). A 0.02s cost means `search_decision` raises BEFORE the loop, in
`rollout._cg()`, at:

```python
from cg.api import search_begin, search_step, search_end, search_release, to_observation_class
```

The heuristic imports `all_card_data` and `all_attack` from the same `cg.api` and
plays card-aware moves on the ladder, so `cg.api` imports fine and carries card
data. It just does NOT expose the `search_*` forward model at match time. The
match-time engine (already in `sys.modules` as `cg.api`) provides the data API
the agent needs to act, but not the SDK search functions used for lookahead.

Reproduced exactly: with a `cg.api` that has `all_card_data`/`all_attack` but no
`search_*`, `agent()` on a real searchable observation falls back in 0.1ms (the
heuristic cost); with the full SDK `cg.api`, the same call takes 833ms (search
runs). See `tests/test_search_agent.py::test_search_api_available_*`.

## What changed

`rollout.search_api_available()` probes whether the resolved `cg.api` exposes the
forward model, and `agent_search.agent()` gates search on it. Behavior on the
ladder is unchanged (still the heuristic), but the inert-search condition is now
a first-class, tested fact instead of a per-decision swallowed `ImportError`.

## Implication for the climb (read this before optimizing search)

Do NOT treat the search agent as "our best" or invest more in search quality for
the ladder: U5 to U10 (determinization, archetype priors, endgame solver,
low-variance safety) are all inert on the ladder by this engine constraint. They
remain valid for self-play measurement and the writeup, but they do not move the
public score.

The levers that DO execute on the ladder are the heuristic policy and the deck.
The genuine climb is therefore:

- the heuristic improvements (self-deckout guard, basic-fetch / discard
  sub-select support), which run every match, and
- the deck (the Ultra Ball consistency build attacks early_collapse, the largest
  real loss bucket: a lone basic active knocked out with an empty bench).

Recovering search on the ladder would require a forward model the match-time
engine does not expose, so it is not a near-term lever. Verification channel for
any future attempt: the overage-bank drawdown in the next replay (a working
search shows ~0.5s draws instead of ~0.02s).

## Update (2026-07-01): search recovered but scores BELOW the heuristic

The recovery was later built (54218335 force-loads our own bundled cg so search
actually runs, verified by the ~0.5s bank draws it was designed to produce). Its
ladder result closes the lever with data rather than the forward-model caveat:
on the SAME trolley deck, search-active 514.7 vs heuristic-only 569.6 (54215558).
Running the determinized search costs ~55 public-score points versus just playing
the heuristic. So the lever is not merely "hard to reach"; when reached it is
negative. Do not ship a search-active build; the plain heuristic is the stronger
ladder pilot. See `analysis/ladder_scored_pair_reclaim.md`.
