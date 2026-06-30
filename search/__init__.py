"""Determinized lookahead search over the engine's native forward model.

The search agent samples plausible hidden opponent state (determinize), drives
the official cg.api search_* forward model through rollouts (rollout), and scores
candidate options by expected value within the time bank (timebudget). This
package is bundled next to main.py in a submission, so its modules avoid the
ptcg_agent package import and locate the official cg/ lazily, the same way the
heuristic does.
"""
