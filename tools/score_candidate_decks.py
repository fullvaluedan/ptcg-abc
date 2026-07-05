"""Score new deck candidates through the calibrated bracket ring (plan U39
step 2 correction, 2026-07-05).

The existing ring (tools/ring_calibrate.py, tau 0.857) already has
deck-judging gate authority: its calibration set includes two deck-changed
builds (meta_archaludon, meta_grimmsnarl) alongside four trolley variants.
This tool reuses run_ring's exact mechanics, unchanged, to score every
decks/candidate_*.csv (tools/select_new_deck_candidates.py) against the SAME
ring, in the SAME run as a fresh trolley reading, so the comparison is not
contaminated by ring-composition drift or match-count noise between two
separate runs.

Dev tool only; never ships. A candidate only earns a TRACK L pre-registration
if its ring win rate clears trolley's FRESH reading (this run's, not the
historical 0.85) by a material margin (default +0.10, half the discordant
gap that already existed in the passing calibration run).
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

from tools import opponents  # noqa: E402
from tools.ring_calibrate import DEFAULT_MATCHES, _ring_win_rate, ring_names  # noqa: E402

CANDIDATE_PREFIX = "candidate_"
BASELINE_BUILD = "trolley"
MATERIAL_MARGIN = 0.10


def candidate_deck_names(decks_dir=None) -> list:
    """Sorted deck: stems for every decks/candidate_*.csv on disk."""
    decks_dir = Path(decks_dir) if decks_dir else _ROOT / "decks"
    if not decks_dir.is_dir():
        return []
    return sorted(p.stem for p in decks_dir.glob(f"{CANDIDATE_PREFIX}*.csv"))


def score_candidates(n_matches=DEFAULT_MATCHES, decks_dir=None, opponent_names=None) -> dict:
    """Fresh ring win rate for trolley (baseline) and every candidate_* deck.

    Uses the SAME opponent_names list (defaults to ring_names()) for every
    build in one call, so all readings share the same ring composition.
    Returns {build_name: {"win_rate", "wins", "draws", "losses", "n"}},
    always including BASELINE_BUILD first.
    """
    names = opponent_names if opponent_names is not None else ring_names()
    if not names:
        raise RuntimeError("no clone: opponents available; cannot score candidates against an empty ring")
    stems = candidate_deck_names(decks_dir)
    builds = {BASELINE_BUILD: opponents.get(f"deck:{BASELINE_BUILD}")}
    for stem in stems:
        builds[stem] = opponents.get(f"deck:{stem}")
    results = {}
    for name, agent_fn in builds.items():
        win_rate, wins, draws, losses, n = _ring_win_rate(agent_fn, names, n_matches)
        results[name] = {"win_rate": win_rate, "wins": wins, "draws": draws, "losses": losses, "n": n}
    return results


def promote_verdicts(results: dict, baseline: str = BASELINE_BUILD, margin: float = MATERIAL_MARGIN) -> dict:
    """{candidate_name: {"delta", "promote"}} for every non-baseline build in results.

    promote is True only when delta >= margin (a candidate merely tying or
    slightly beating the baseline is not material; the ring itself carries
    match-count noise). Pure over its input so it is unit-testable on planted
    win-rate dicts without playing real games.
    """
    if baseline not in results:
        return {}
    base_rate = results[baseline]["win_rate"]
    out = {}
    for name, r in results.items():
        if name == baseline:
            continue
        delta = r["win_rate"] - base_rate
        # win_rate is wins/n, so delta rarely lands exactly on margin in float;
        # a 1e-9 tolerance treats the intended boundary as inclusive without
        # opening the gate to a materially smaller delta.
        out[name] = {"delta": delta, "promote": delta >= margin - 1e-9}
    return out


def _main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-n", "--matches", type=int, default=DEFAULT_MATCHES,
                     help="games per build against the ring (default %(default)s)")
    ap.add_argument("--margin", type=float, default=MATERIAL_MARGIN,
                     help="minimum win-rate delta over trolley to promote (default %(default)s)")
    ap.add_argument("--out", default=None, help="optional JSON report path")
    args = ap.parse_args(argv)

    results = score_candidates(n_matches=args.matches)
    verdicts = promote_verdicts(results, margin=args.margin)

    print(f"ring: {len(ring_names())} opponents, {args.matches} games/build")
    base = results[BASELINE_BUILD]
    print(f"{BASELINE_BUILD} (baseline): {base['win_rate']:.3f} ({base['wins']}/{base['n']})")
    for name, r in results.items():
        if name == BASELINE_BUILD:
            continue
        v = verdicts[name]
        tag = f"PROMOTE (+{v['delta']:.3f})" if v["promote"] else f"no promote ({v['delta']:+.3f})"
        print(f"{name}: {r['win_rate']:.3f} ({r['wins']}/{r['n']}) vs baseline -> {tag}")

    if args.out:
        Path(args.out).write_text(
            json.dumps({"results": results, "verdicts": verdicts}, indent=2), encoding="utf-8"
        )
        print(f"wrote report {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
