"""Decide the search-revival branch (Phase 3) from data, offline (plan U27).

Perfect-Information Monte Carlo (PIMC) is exactly what our determinized search
does: sample hidden worlds, evaluate each candidate move per world, average, pick
the argmax. Long et al. (2010), "Understanding the Success of Perfect Information
Monte Carlo Sampling in Game Tree Search," show that PIMC approximates the true
game well only when three structural properties hold, and fails (strategy fusion,
non-locality) otherwise. We already know the ladder fact: active search scored
514.7 vs the heuristic's 569.6 on the same deck (search costs points). This unit
explains WHY from the game's structure and issues the one-time favorable /
unfavorable verdict that fixes the Phase 3 branch (U45 belief-weighted search if
favorable, else U46 doubled deck-aware breadth). The branch is never revisited.

The three Long et al. properties, operationalized on OUR real states:

1. Leaf correlation. Whether sibling leaves tend to share a value, i.e. whether
   the best move is stable across the hidden worlds. We sample K determinized
   worlds of a real mid-game MAIN state, roll each candidate move to a terminal
   result per world (the shipped forward model and rollout policy), and measure
   how often the worlds agree on the best move (the modal-argmax share) plus the
   mean pairwise correlation of the per-world value vectors. HIGH leaf correlation
   means plain PIMC averaging is sound; LOW means strategy fusion dominates and no
   amount of belief-weighting rescues the average.

2. Bias. How strongly the game favors one player regardless of the move. Measured
   as the mean magnitude of the terminal rollout values. Near 1.0 means the
   position is already decided and search cannot matter; moderate is healthy.

3. Disambiguation. How fast hidden information resolves. Measured as the slope of
   the revealed-opponent-card fraction against the turn number over full matches.
   HIGH disambiguation means worlds collapse quickly (PIMC's determinizations
   become accurate late); LOW means the fog never lifts.

Verdict thresholds are pre-registered below (set before the run, honesty gate):
FAVORABLE requires leaf correlation >= LEAF_CORR_MIN AND disambiguation slope >=
DISAMBIG_SLOPE_MIN AND bias magnitude <= BIAS_ABS_MAX. Otherwise UNFAVORABLE.

Dev/measurement tool only; never shipped. The native engine is a per-process
singleton, so matches run one at a time in process. The pure metric functions
(leaf_correlation, bias, disambiguation_slope, verdict) take plain matrices and
are unit-tested cg-free; only capture/rollout touch the native model.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis import archetype  # noqa: E402
from ptcg_agent.engine import ensure_official_cg, make_env  # noqa: E402
from search import rollout  # noqa: E402
from search.determinize import (  # noqa: E402
    _opponent_visible_ids,
    determinize,
)
from tools import opponents  # noqa: E402
from tools.deck_match import deck_bound  # noqa: E402
from tools.deck_validate import read_deck  # noqa: E402

_SEED = 20260702

# Pre-registered verdict thresholds (set before the run; do not tune to the data).
LEAF_CORR_MIN = 0.55       # worlds must mostly agree on the best move
DISAMBIG_SLOPE_MIN = 0.02  # revealed fraction must climb with the turn count
BIAS_ABS_MAX = 0.9         # position must not be already decided regardless of move

# Total opponent decklist size; the denominator for the revealed fraction.
_DECK_SIZE = 60

# A state whose every rollout is a win (or loss) is already decided: its
# modal-argmax share is a degenerate 1.0 (all values tie, argmax falls to index
# 0), which would inflate leaf correlation for a reason unrelated to the move. We
# report leaf correlation over the DISCRIMINATING states (|bias| below this) as
# the robustness check, so a favorable verdict cannot rest on saturation alone.
_SATURATED_ABS = 0.98


# --------------------------------------------------------------------------
# Pure metric functions (cg-free, unit-tested on synthetic matrices).
# --------------------------------------------------------------------------

def _modal_share(argmaxes) -> float:
    """Fraction of worlds that pick the single most-popular best move.

    1.0 when every world agrees; 1/n_distinct when they split evenly. This is the
    leaf-correlation proxy: high share means a move good in one world is good in
    the others, which is exactly the condition PIMC averaging needs.
    """
    if not argmaxes:
        return 0.0
    counts: dict = {}
    for a in argmaxes:
        counts[a] = counts.get(a, 0) + 1
    return max(counts.values()) / len(argmaxes)


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _pearson(xs, ys) -> float | None:
    """Pearson correlation, or None when either vector is constant."""
    n = len(xs)
    if n < 2:
        return None
    mx, my = _mean(xs), _mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / (sxx ** 0.5 * syy ** 0.5)


def _argmax(row) -> int:
    """Index of the max value; ties break to the lower index (PIMC convention)."""
    best_i, best_v = 0, row[0]
    for i, v in enumerate(row):
        if v > best_v:
            best_i, best_v = i, v
    return best_i


def leaf_correlation(value_matrix) -> dict:
    """Leaf correlation of one state's [world][candidate] value matrix.

    Returns the modal-argmax share (primary proxy) and the mean pairwise Pearson
    correlation of the per-world value vectors (secondary, continuous). A matrix
    with fewer than two worlds or candidates yields a share of 1.0 (a single
    option cannot suffer strategy fusion) and no pairwise correlation.
    """
    worlds = [row for row in value_matrix if row]
    if len(worlds) < 2 or len(worlds[0]) < 2:
        return {"modal_share": 1.0, "pairwise_corr": None, "n_worlds": len(worlds)}
    argmaxes = [_argmax(row) for row in worlds]
    corrs = []
    for i in range(len(worlds)):
        for j in range(i + 1, len(worlds)):
            c = _pearson(worlds[i], worlds[j])
            if c is not None:
                corrs.append(c)
    return {
        "modal_share": _modal_share(argmaxes),
        "pairwise_corr": _mean(corrs) if corrs else None,
        "n_worlds": len(worlds),
    }


def bias(value_matrix) -> float:
    """Mean signed terminal value across all worlds and candidates of a state.

    Magnitude near 1.0 means the position is already won or lost regardless of the
    move; magnitude near 0 means the move genuinely matters.
    """
    flat = [v for row in value_matrix for v in row]
    return _mean(flat)


def disambiguation_slope(points) -> float:
    """Least-squares slope of revealed_fraction vs turn over MAIN decisions.

    points is a list of (turn, revealed_fraction). Returns 0.0 when there are
    fewer than two distinct turns (no divide-by-zero on a flat or single-point
    sample, which is the fully-observed / degenerate case).
    """
    xs = [float(t) for t, _ in points]
    ys = [float(f) for _, f in points]
    n = len(xs)
    if n < 2:
        return 0.0
    mx = _mean(xs)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        return 0.0
    my = _mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / sxx


def verdict(leaf_corr, disambig_slope, bias_abs) -> dict:
    """Apply the pre-registered thresholds; return the branch decision."""
    ok_leaf = leaf_corr >= LEAF_CORR_MIN
    ok_disambig = disambig_slope >= DISAMBIG_SLOPE_MIN
    ok_bias = bias_abs <= BIAS_ABS_MAX
    favorable = ok_leaf and ok_disambig and ok_bias
    return {
        "favorable": favorable,
        "branch": "U45 belief-weighted search" if favorable else "U46 doubled deck-aware breadth",
        "leaf_ok": ok_leaf,
        "disambig_ok": ok_disambig,
        "bias_ok": ok_bias,
    }


# --------------------------------------------------------------------------
# Native capture + rollout (touches the singleton forward model).
# --------------------------------------------------------------------------

def _revealed_fraction(obs) -> float:
    """Fraction of the opponent's 60 cards whose identity we have observed."""
    state = obs["current"]
    yi = state["yourIndex"]
    opp = state["players"][1 - yi]
    return len(_opponent_visible_ids(opp)) / _DECK_SIZE


def capture(deck_ids, n_states, max_matches, policy="heuristic", opponent="random",
            min_turn=3):
    """Play matches; collect searchable mid-game states and disambiguation points.

    Returns (states, points): states is a list of up to n_states raw MAIN obs
    dicts that pass the shipped searchable gate (MAIN, >1 option, search input,
    past the opening); points is every MAIN decision's (turn, revealed_fraction)
    across all matches played, the disambiguation curve. The opponent is a
    registered agent name; a competitive foil (heuristic) de-saturates the leaf
    values a weak foil (random) would push toward a near-certain win.
    """
    policy_fn = opponents.get(policy)
    piloted = deck_bound(policy_fn, deck_ids)
    foil = opponents.get(opponent)
    states: list = []
    points: list = []

    def capturing(obs):
        sel = obs.get("select")
        cur = obs.get("current") or {}
        if sel is not None and sel.get("type") == 0:
            points.append((cur.get("turn", 0), _revealed_fraction(obs)))
            searchable = (
                len(states) < n_states
                and sel.get("maxCount", 1) == 1
                and len(sel.get("option", [])) > 1
                and obs.get("search_begin_input")
                and cur.get("turn", 0) >= min_turn
            )
            if searchable:
                states.append(obs)
        return piloted(obs)

    matches = 0
    while len(states) < n_states and matches < max_matches:
        make_env().run([capturing, foil])
        matches += 1
    return states, points, matches


def disambiguation_curve(deck_ids, opponent, n_matches, policy="heuristic"):
    """Cheap pass: play n_matches full games, collect every MAIN (turn, revealed).

    No rollouts, so this scales to many matches for a stable slope. The revealed
    fraction is opponent-driven, so it needs a faithful foil (a competitive
    opponent develops and thus reveals its board, a random one barely does), and a
    single game's trajectory is far too noisy to anchor a permanent branch call.
    """
    policy_fn = opponents.get(policy)
    piloted = deck_bound(policy_fn, deck_ids)
    foil = opponents.get(opponent)
    points: list = []

    def watcher(obs):
        sel = obs.get("select")
        if sel is not None and sel.get("type") == 0:
            cur = obs.get("current") or {}
            points.append((cur.get("turn", 0), _revealed_fraction(obs)))
        return piloted(obs)

    for _ in range(n_matches):
        make_env().run([watcher, foil])
    return points


def world_values(obs, deck_ids, worlds, rng):
    """Value matrix [world][candidate] of terminal rollouts for one state.

    For each of `worlds` determinizations, open a fresh search state per candidate
    first move, roll to a terminal result with the shipped heuristic policy, and
    read our value. Mirrors search_decision's begin/release/end discipline exactly
    (the native core is a fork-less singleton), so the values are the shipped
    forward model's, not a reimplementation.
    """
    search_begin, search_step, search_end, search_release, to_obs = rollout._cg()
    sel = obs["select"]
    n = len(sel["option"])
    your_index = obs["current"]["yourIndex"]
    obs_class = to_obs(obs)
    try:
        prior = archetype.opponent_prior(obs, deck_ids)
    except Exception:
        prior = None
    matrix = []
    try:
        for _ in range(worlds):
            det = determinize(obs, deck_ids, rng, prior)
            kwargs = det.as_search_begin_kwargs()
            row = []
            for ci in range(n):
                try:
                    root = search_begin(obs_class, **kwargs)
                except Exception:
                    row = []
                    break
                try:
                    value = rollout.rollout(root.searchId, [ci], your_index, search_step)
                except Exception:
                    value = 0.0
                finally:
                    try:
                        search_release(root.searchId)
                    except Exception:
                        pass
                row.append(value)
            if row:
                matrix.append(row)
    finally:
        try:
            search_end()
        except Exception:
            pass
    return matrix


def measure(deck_path, n_states=10, worlds=6, max_matches=6, opponent="random",
            disambig_matches=8):
    deck_ids = read_deck(deck_path)
    ensure_official_cg()
    if not rollout.search_api_available():
        raise SystemExit("no cg.api forward model reachable; cannot run the diagnostic")
    # Leaf/bias states come from a few matches (each is expensive to roll out); the
    # disambiguation slope gets its own many-match cheap pass so it is not read off
    # a single noisy game trajectory.
    states, _, matches = capture(deck_ids, n_states, max_matches, opponent=opponent)
    points = disambiguation_curve(deck_ids, opponent, disambig_matches)
    rng = random.Random(_SEED)
    per_state = []
    for obs in states:
        matrix = world_values(obs, deck_ids, worlds, rng)
        if not matrix:
            continue
        lc = leaf_correlation(matrix)
        per_state.append({
            "turn": (obs.get("current") or {}).get("turn"),
            "options": len(obs["select"].get("option", [])),
            "modal_share": lc["modal_share"],
            "pairwise_corr": lc["pairwise_corr"],
            "bias": bias(matrix),
        })

    leaf_corr = _mean([s["modal_share"] for s in per_state])
    corrs = [s["pairwise_corr"] for s in per_state if s["pairwise_corr"] is not None]
    pairwise = _mean(corrs) if corrs else None
    bias_signed = _mean([s["bias"] for s in per_state])
    bias_abs = _mean([abs(s["bias"]) for s in per_state])
    slope = disambiguation_slope(points)

    # Robustness: leaf correlation restricted to states the move can still swing.
    discriminating = [s for s in per_state if abs(s["bias"]) < _SATURATED_ABS]
    leaf_corr_disc = _mean([s["modal_share"] for s in discriminating]) if discriminating else None

    # The verdict uses the discriminating leaf correlation when enough such states
    # exist, so a win-saturated foil cannot manufacture a favorable read.
    leaf_for_verdict = leaf_corr_disc if len(discriminating) >= 3 else leaf_corr
    v = verdict(leaf_for_verdict, slope, bias_abs)

    return {
        "deck": Path(deck_path).stem,
        "opponent": opponent,
        "matches_played": matches,
        "disambig_matches": disambig_matches,
        "states_measured": len(per_state),
        "worlds_per_state": worlds,
        "disambig_points": len(points),
        "leaf_correlation": leaf_corr,
        "leaf_correlation_discriminating": leaf_corr_disc,
        "discriminating_states": len(discriminating),
        "leaf_used_for_verdict": leaf_for_verdict,
        "pairwise_corr": pairwise,
        "bias_signed": bias_signed,
        "bias_abs": bias_abs,
        "disambig_slope": slope,
        "thresholds": {
            "leaf_corr_min": LEAF_CORR_MIN,
            "disambig_slope_min": DISAMBIG_SLOPE_MIN,
            "bias_abs_max": BIAS_ABS_MAX,
        },
        "verdict": v,
        "per_state": per_state,
    }


def _format(result) -> str:
    v = result["verdict"]
    lines = [
        f"PIMC diagnostic (Long et al.) on {result['deck']} "
        f"[{result['states_measured']} states x {result['worlds_per_state']} worlds, "
        f"{result['matches_played']} matches, {result['disambig_points']} disambig points]:",
        f"  leaf correlation (modal-argmax share): {result['leaf_correlation']:.3f} all, "
        + ("n/a" if result["leaf_correlation_discriminating"] is None
           else f"{result['leaf_correlation_discriminating']:.3f}")
        + f" on {result['discriminating_states']} discriminating "
        f"(min {LEAF_CORR_MIN}) -> {'ok' if v['leaf_ok'] else 'FAIL'}",
        f"    pairwise value correlation: "
        + ("n/a" if result["pairwise_corr"] is None else f"{result['pairwise_corr']:.3f}"),
        f"  disambiguation slope (revealed/turn): {result['disambig_slope']:.4f} "
        f"(min {DISAMBIG_SLOPE_MIN}) -> {'ok' if v['disambig_ok'] else 'FAIL'}",
        f"  bias |mean terminal value|: {result['bias_abs']:.3f} "
        f"(max {BIAS_ABS_MAX}) -> {'ok' if v['bias_ok'] else 'FAIL'}"
        f"  (signed {result['bias_signed']:+.3f})",
        f"  VERDICT: {'FAVORABLE' if v['favorable'] else 'UNFAVORABLE'} -> {v['branch']}",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck", nargs="?", default=str(_ROOT / "decks" / "trolley.csv"),
                    help="deck csv path (default: decks/trolley.csv, the shipped deck)")
    ap.add_argument("-n", "--states", type=int, default=10,
                    help="searchable mid-game states to measure")
    ap.add_argument("-w", "--worlds", type=int, default=6,
                    help="determinized worlds sampled per state")
    ap.add_argument("-m", "--max-matches", type=int, default=6,
                    help="cap on matches played to gather states")
    ap.add_argument("-o", "--opponent", default="random",
                    help="registered foil name (random weak; heuristic competitive)")
    ap.add_argument("-d", "--disambig-matches", type=int, default=8,
                    help="full matches for the cheap disambiguation-slope pass")
    ap.add_argument("--json", action="store_true", help="also write the result JSON")
    args = ap.parse_args()
    result = measure(args.deck, n_states=args.states, worlds=args.worlds,
                     max_matches=args.max_matches, opponent=args.opponent,
                     disambig_matches=args.disambig_matches)
    print(_format(result))
    if args.json:
        from tools.isolation import derived_path

        out = derived_path("pimc", "pimc_diagnostic_result.json")
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"  wrote {out}")


if __name__ == "__main__":
    main()
