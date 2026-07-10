"""U105b (plan U2): same-run ring A/B for PTCG_THREAT_RETREAT on the yushin deck.

measure_threat_retreat.py already confirmed the lever is LIVE on trolley (it
flips real pilot decisions in captured positions); that tool makes no
win-rate claim. This tool is the honest follow-up: does threat-aware retreat
actually win more games on the ring, on the deck that matters (yushin, the
current strongest ring-measured build per analysis/u104_stacked_ring_pass_run.md)?

Two arms, both heuristic+yushin+ability (the U104-passed baseline), threat-retreat
off vs on, played same-run against the identical calibrated bracket-band ring
(tau 0.857, analysis/ring_calibration.md) so no cross-run variance can confound
the delta. Mirrors tools/ability_ring_check.py's monkeypatch-wrapper pattern
(flag toggled on the imported module attribute, restored in a finally) combined
with tools/stacked_ring_u104.py's `_make_agent_factory` (deck pinning plus
multi-flag patching, here patching both _ABILITY and _THREAT_RETREAT so the
ability lever stays pinned on in both arms and only threat-retreat varies).

_THREAT_RETREAT (agents/heuristics.py) is a module-level constant read once at
import time from PTCG_THREAT_RETREAT, so toggling the environment variable
after import has no effect; the same reason ability_ring_check.py and
attack_first_ring_check.py patch their flags in-process instead.

Gate (docs/plans/2026-07-10-001-feat-improvement-push-plan.md, U2/U105b): PASS
when diff_pp (on minus off) is strictly more than +5.0pp. Below that, the
standard ring is known to saturate near 0.875-0.91 (KTD) and the off-arm has
last read 0.850-0.875, so a compressed delta at a saturated off-arm is not
honest evidence of a real FAIL: when the off-arm win rate is at or above 0.85,
the verdict routes to NEEDS_U5_HARD_RING instead of a bare FAIL. Below both
bars, FAIL is recorded as an honest negative.

Secondary metric: loss rate against the three hardest clones in this run. The
ring has no pre-registered "hardest clone" list (ring_calibrate.py ranks
BUILDS against a known ladder, not opponent families against each other), so
this tool derives it from the run's own per-opponent breakdown: the three
clone: families with the highest loss rate, pooling both arms' games against
each family for a less noisy read (both arms share the same deck and ability
setting; only threat-retreat differs, so pooling does not mix different
builds' difficulty signal). Ties break alphabetically for reproducibility.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Warm sys.modules["agents"] with our repo's agents/ package *before* anything
# below can trigger `import kaggle_environments`. kaggle_environments's
# lux_ai_s3 env loads its own env-local agents.py under the bare module name
# "agents" and leaves it cached in sys.modules; if that happens first, every
# later `from agents import heuristics` in this file (and in _make_agent_factory
# below) silently resolves to the wrong module and raises ImportError from
# lux_ai_s3/agents.py's relative import. Importing our agents.heuristics here,
# first, pins the correct package in the cache for the rest of the process.
from agents import heuristics as _heuristics  # noqa: E402,F401

from ptcg_agent.engine import run_match  # noqa: E402
from tools import opponents  # noqa: E402
from tools import ring_calibrate as rc  # noqa: E402

DEFAULT_MATCHES = 100
GATE_MARGIN_PP = 5.0
SATURATION_THRESHOLD = 0.85
N_HARDEST_CLONES = 3

YUSHIN_DECK = "candidate_yushin_ito"
ARM_OFF = "heuristic+yushin+ability-threat_retreat-off"
ARM_ON = "heuristic+yushin+ability-threat_retreat-on"


def _make_agent_factory(deck_name, ability_on, threat_retreat_on):
    """Factory returning an agent that pilots deck_name with the given lever settings.

    Mirrors tools/stacked_ring_u104.py's _make_agent_factory: the deck opponent
    is wrapped with flag patching at call time, so each arm's games see only its
    own _ABILITY and _THREAT_RETREAT settings, restored after every call.
    """
    def factory():
        from agents import heuristics as H

        base_agent = opponents.get(f"deck:{deck_name}")

        def agent(obs):
            orig_ability = H._ABILITY
            orig_threat_retreat = H._THREAT_RETREAT
            H._ABILITY = ability_on
            H._THREAT_RETREAT = threat_retreat_on
            try:
                return base_agent(obs)
            finally:
                H._ABILITY = orig_ability
                H._THREAT_RETREAT = orig_threat_retreat

        return agent

    return factory


def _ring_win_rate(agent_fn, opponent_names, n_matches):
    """(win_rate, wins, draws, losses, n, per_opponent) for agent_fn round-robin
    over opponent_names, alternating seats every game.

    per_opponent maps opponent name -> {"wins", "draws", "losses", "n"}: the same
    round-robin games broken out per clone family, so the hardest-clones
    secondary metric can be computed without a second ring run.
    """
    per_opponent = {name: {"wins": 0, "draws": 0, "losses": 0, "n": 0} for name in opponent_names}
    if not opponent_names or n_matches <= 0:
        return 0.0, 0, 0, 0, 0, per_opponent
    wins = draws = losses = 0
    for i in range(n_matches):
        opp_name = opponent_names[i % len(opponent_names)]
        opp_fn = opponents.get(opp_name)
        res = run_match(agent_fn, opp_fn, swap_first=(i % 2 == 1))
        r = res["reward_a"]
        bucket = per_opponent[opp_name]
        bucket["n"] += 1
        if r == 1:
            wins += 1
            bucket["wins"] += 1
        elif r == -1:
            losses += 1
            bucket["losses"] += 1
        else:
            draws += 1
            bucket["draws"] += 1
    n = wins + draws + losses
    return (wins / n if n else 0.0), wins, draws, losses, n, per_opponent


def _merge_per_opponent(*per_opponent_dicts):
    """Sum wins/draws/losses/n across multiple per_opponent breakdowns, keyed by name."""
    merged = {}
    for d in per_opponent_dicts:
        for name, stats in d.items():
            m = merged.setdefault(name, {"wins": 0, "draws": 0, "losses": 0, "n": 0})
            m["wins"] += stats["wins"]
            m["draws"] += stats["draws"]
            m["losses"] += stats["losses"]
            m["n"] += stats["n"]
    return merged


def hardest_clones(per_opponent, k=N_HARDEST_CLONES):
    """The k opponent names with the highest loss rate in per_opponent.

    Opponents with n=0 are excluded (no games played, nothing to rank). Ties
    break alphabetically by name so the list is reproducible from the same
    per_opponent input.
    """
    ranked = sorted(
        (name for name, stats in per_opponent.items() if stats["n"] > 0),
        key=lambda name: (-(per_opponent[name]["losses"] / per_opponent[name]["n"]), name),
    )
    return ranked[:k]


def loss_rate_vs_clones(per_opponent, clone_names):
    """(loss_rate, losses, n) aggregated over only the named clone_names.

    A clone_name absent from per_opponent is ignored rather than raising, the
    same fault-tolerant shape as this module's other lookups. This is the
    "counts only the named hardest clones" secondary metric: it never folds in
    games against clones outside the given list.
    """
    losses = sum(per_opponent[name]["losses"] for name in clone_names if name in per_opponent)
    n = sum(per_opponent[name]["n"] for name in clone_names if name in per_opponent)
    return (losses / n if n else 0.0), losses, n


def compute_verdict(off_win_rate, diff_pp):
    """PASS/FAIL/NEEDS_U5_HARD_RING per the U105b saturation-routing rule.

    PASS when diff_pp clears the gate margin outright (strictly more than
    GATE_MARGIN_PP; exactly at the margin is not a pass). Otherwise, a
    saturated off-arm (win rate at or above SATURATION_THRESHOLD) means a
    compressed delta is not honest evidence of a real FAIL, so the verdict
    routes to U5's hard-ring decision instead (KTD, docs/plans/2026-07-10-001-
    feat-improvement-push-plan.md: "the standard ring saturates near 0.875-0.91
    and the off-arm ... last read 0.850-0.875 ... routes to U5 rather than
    being declared FAIL on a compressed delta"). Below both bars, FAIL is an
    honest negative.
    """
    if diff_pp > GATE_MARGIN_PP:
        return "PASS"
    if off_win_rate >= SATURATION_THRESHOLD:
        return "NEEDS_U5_HARD_RING"
    return "FAIL"


def run_check(n_matches=DEFAULT_MATCHES, opponent_names=None) -> dict:
    """Same-run ring A/B for PTCG_THREAT_RETREAT on the yushin+ability build.

    Returns a dict with per-arm {win_rate, wins, draws, losses, n} under
    ARM_OFF/ARM_ON, plus diff_pp (on minus off, percentage points), verdict
    (PASS/FAIL/NEEDS_U5_HARD_RING), the hardest_clones list, and the secondary
    hardest-clone loss-rate metric per arm.
    """
    names = opponent_names if opponent_names is not None else rc.ring_names()
    if not names:
        raise RuntimeError(
            "no clone: opponents available; run tools/bracket_decks.py or check decks/"
        )

    factory_off = _make_agent_factory(YUSHIN_DECK, ability_on=True, threat_retreat_on=False)
    factory_on = _make_agent_factory(YUSHIN_DECK, ability_on=True, threat_retreat_on=True)

    off_wr, off_w, off_d, off_l, off_n, off_per_opp = _ring_win_rate(
        factory_off(), names, n_matches
    )
    on_wr, on_w, on_d, on_l, on_n, on_per_opp = _ring_win_rate(
        factory_on(), names, n_matches
    )

    diff_pp = (on_wr - off_wr) * 100.0
    verdict = compute_verdict(off_wr, diff_pp)

    hardest = hardest_clones(_merge_per_opponent(off_per_opp, on_per_opp), k=N_HARDEST_CLONES)
    off_hardest_rate, off_hardest_losses, off_hardest_n = loss_rate_vs_clones(off_per_opp, hardest)
    on_hardest_rate, on_hardest_losses, on_hardest_n = loss_rate_vs_clones(on_per_opp, hardest)

    return {
        ARM_OFF: {"win_rate": off_wr, "wins": off_w, "draws": off_d, "losses": off_l, "n": off_n},
        ARM_ON: {"win_rate": on_wr, "wins": on_w, "draws": on_d, "losses": on_l, "n": on_n},
        "diff_pp": diff_pp,
        "verdict": verdict,
        "hardest_clones": hardest,
        "hardest_clone_loss_rate": {ARM_OFF: off_hardest_rate, ARM_ON: on_hardest_rate},
        "hardest_clone_losses": {ARM_OFF: off_hardest_losses, ARM_ON: on_hardest_losses},
        "hardest_clone_n": {ARM_OFF: off_hardest_n, ARM_ON: on_hardest_n},
    }


def _main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", "--matches", type=int, default=DEFAULT_MATCHES,
                         help="games per arm (default %(default)s)")
    args = parser.parse_args(argv)

    results = run_check(n_matches=args.matches)
    for name in (ARM_OFF, ARM_ON):
        r = results[name]
        print(f"{name}: {r['win_rate']:.3f} ({r['wins']}-{r['draws']}-{r['losses']}, n={r['n']})")
    print(f"diff_pp (on minus off) = {results['diff_pp']:+.1f}")
    print(f"gate: diff_pp > {GATE_MARGIN_PP:+.1f} -> verdict = {results['verdict']}")
    if results["verdict"] == "NEEDS_U5_HARD_RING":
        print(f"  (off-arm win rate {results[ARM_OFF]['win_rate']:.3f} >= "
              f"{SATURATION_THRESHOLD} saturation threshold; standard ring cannot "
              "resolve this delta, routes to U5)")

    print(f"hardest clones this run: {results['hardest_clones']}")
    for name in (ARM_OFF, ARM_ON):
        rate = results["hardest_clone_loss_rate"][name]
        losses = results["hardest_clone_losses"][name]
        n = results["hardest_clone_n"][name]
        print(f"  {name} loss rate vs hardest clones: {rate:.3f} ({losses}/{n})")

    print()
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
