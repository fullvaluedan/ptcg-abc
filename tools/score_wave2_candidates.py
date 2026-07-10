"""Score the five wave-2 mined deck candidates against the yushin baseline
(plan 2026-07-10-001, U4 / U39 wave 2).

The on-disk decks/candidate_third_ptcg_club.csv, candidate_kashiwashira.csv,
candidate_zoroark190.csv and candidate_bluezlee.csv are NOT the wave-2
decks: analysis/mined_candidates_dedup_report.md classifies all five wave-2
signatures as new precisely because they match no on-disk CSV, and those
four same-named on-disk stems were already ring-scored and FAILED on
2026-07-06 (analysis/new_candidates_phase2_verdict.md). Mining windows drift:
the same team can top-rate a different 60-card list in a later scrape.

This tool materializes the five wave-2 signatures directly from
data/derived/top_rated_decks.json (the dedup report's "New Candidates" rows)
into fresh, collision-free decks/candidate_<team>_w2.csv files, then scores
ONLY {candidate_yushin_ito baseline, five _w2 stems} through the calibrated
ring -- never tools/score_candidate_decks.py's full candidate_* pool (it
hardcodes a different, trolley, baseline and would score all ~40 candidate
CSVs on disk, which is the wrong comparison for this unit).

Does not route through tools/dedupe_mined_candidates.py: that module's
--create-candidates write path silently *skips* a candidate whose target
filename already exists on disk (exactly the wave-1/wave-2 collision this
tool exists to avoid) and silently skips any non-ASCII team name outright.
Both silent-skip behaviors would corrupt this exact five-candidate set, so
the mined signatures are read and written directly here instead.

Dev tool only; never ships. Screen at n=40 first; only a candidate that
clears +0.10 win rate over yushin re-runs at n=100 before any promote
verdict is recorded (screen-then-confirm, mirrors the plan's n=100-settles
rule from the U104 shrink-on-confirm precedent).
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
from tools import ring_calibrate as rc  # noqa: E402
from tools.score_candidate_decks import promote_verdicts  # noqa: E402

MINING_DATA = _ROOT / "data" / "derived" / "top_rated_decks.json"
DECKS_DIR = _ROOT / "decks"

BASELINE_BUILD = "candidate_yushin_ito"
SCREEN_MATCHES = 40
CONFIRM_MATCHES = 100
MATERIAL_MARGIN = 0.10

# The five "New Candidates" rows from analysis/mined_candidates_dedup_report.md,
# identified by (team, deck_index) into data/derived/top_rated_decks.json's
# team_decks map. "team" is the exact team_decks key (source-language name,
# used only to look up the signature); "stem" is the ASCII filename stem this
# tool writes to decks/. One team name is non-ASCII (Japanese); its original
# name is recorded here and again in analysis/wave2_ring_scores.md per the
# plan's transliteration requirement.
WAVE2_CANDIDATES = [
    {"team": "THIRD PTCG Club", "deck_index": 0, "stem": "candidate_third_ptcg_club_w2"},
    {"team": "kashiwashira", "deck_index": 0, "stem": "candidate_kashiwashira_w2"},
    {"team": "zoroark190", "deck_index": 0, "stem": "candidate_zoroark190_w2"},
    {
        "team": "変化の書ゾロアーク",
        "deck_index": 0,
        "stem": "candidate_henka_no_sho_zoroark_w2",
        "original_name": "変化の書ゾロアーク",
    },
    {"team": "BluezLee", "deck_index": 1, "stem": "candidate_bluezlee_w2"},
]


def load_mined_signature(team, deck_index, mining_data=None):
    """The 60-card signature (list of card ids, as mined) for one team_decks entry.

    Raises KeyError/IndexError if the team or index is not present (loudly,
    rather than silently materializing an empty or short deck), and
    ValueError if the signature is not a full 60-card deck.
    """
    path = Path(mining_data) if mining_data else MINING_DATA
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    decks_list = data["team_decks"][team]
    sig = decks_list[deck_index]["signature"]
    if len(sig) != 60:
        raise ValueError(
            f"{team!r} deck_index {deck_index} signature has {len(sig)} cards, expected 60"
        )
    return list(sig)


def materialize_wave2_decks(candidates=None, decks_dir=None, mining_data=None) -> dict:
    """Write decks/candidate_<team>_w2.csv for each wave-2 candidate.

    Always (re)writes: these files are owned by this unit, and re-running the
    materialization must reproduce the same bytes from the same mining data
    rather than silently no-op on a stale prior write. Returns {stem: Path}.
    """
    candidates = candidates if candidates is not None else WAVE2_CANDIDATES
    decks_dir = Path(decks_dir) if decks_dir else DECKS_DIR
    decks_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for cand in candidates:
        sig = load_mined_signature(cand["team"], cand["deck_index"], mining_data=mining_data)
        path = decks_dir / f"{cand['stem']}.csv"
        with open(path, "w", encoding="utf-8") as f:
            for card_id in sig:
                f.write(f"{card_id}\n")
        written[cand["stem"]] = path
    return written


def wave2_stems(candidates=None) -> list:
    candidates = candidates if candidates is not None else WAVE2_CANDIDATES
    return [c["stem"] for c in candidates]


def build_builds_dict(candidates=None) -> dict:
    """{candidate_yushin_ito, five _w2 stems} -> deck: opponent factory.

    Deliberately never the full decks/candidate_*.csv pool that
    tools/score_candidate_decks.py's candidate_deck_names() would return.
    """
    stems = [BASELINE_BUILD] + wave2_stems(candidates)
    builds = {}
    for stem in stems:
        builds[stem] = lambda stem=stem: opponents.get(f"deck:{stem}")
    return builds


def screen_then_confirm(screen_n=SCREEN_MATCHES, confirm_n=CONFIRM_MATCHES,
                         opponent_names=None, candidates=None,
                         margin=MATERIAL_MARGIN) -> dict:
    """Screen all six builds at screen_n; only a candidate clearing +margin
    re-runs at confirm_n before its verdict is finalized.

    Returns {"screen": results, "confirm": results_or_None,
    "cleared_screen": [names], "verdicts": {name: {"delta", "promote"}}}.
    verdicts holds the confirm-run verdict for any candidate that cleared the
    screen, and the screen-run verdict (always a no-promote, by construction)
    for every candidate that did not -- so screen-then-confirm only ever
    *confirms* a candidate that cleared the screen; it never promotes off a
    screen-only reading.
    """
    names = opponent_names if opponent_names is not None else rc.ring_names()
    builds = build_builds_dict(candidates)

    screen_results = rc.run_ring(n_matches=screen_n, builds=builds, opponent_names=names)
    screen_verdicts = promote_verdicts(screen_results, baseline=BASELINE_BUILD, margin=margin)

    cleared = sorted(name for name, v in screen_verdicts.items() if v["promote"])

    confirm_results = None
    verdicts = dict(screen_verdicts)
    if cleared:
        confirm_builds = {BASELINE_BUILD: builds[BASELINE_BUILD]}
        for name in cleared:
            confirm_builds[name] = builds[name]
        confirm_results = rc.run_ring(n_matches=confirm_n, builds=confirm_builds, opponent_names=names)
        confirm_verdicts = promote_verdicts(confirm_results, baseline=BASELINE_BUILD, margin=margin)
        for name, v in confirm_verdicts.items():
            verdicts[name] = v

    return {
        "screen": screen_results,
        "confirm": confirm_results,
        "cleared_screen": cleared,
        "verdicts": verdicts,
    }


def _main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--screen-n", type=int, default=SCREEN_MATCHES,
                     help="games per build for the screen pass (default %(default)s)")
    ap.add_argument("--confirm-n", type=int, default=CONFIRM_MATCHES,
                     help="games per build for the confirm pass (default %(default)s)")
    ap.add_argument("--margin", type=float, default=MATERIAL_MARGIN,
                     help="minimum win-rate delta over yushin to promote (default %(default)s)")
    ap.add_argument("--skip-materialize", action="store_true",
                     help="skip (re)writing the wave-2 CSVs; assumes they already exist")
    ap.add_argument("--out", default=None, help="optional JSON report path")
    args = ap.parse_args(argv)

    if not args.skip_materialize:
        written = materialize_wave2_decks()
        for stem, path in written.items():
            print(f"materialized {stem} -> {path}")

    report = screen_then_confirm(screen_n=args.screen_n, confirm_n=args.confirm_n, margin=args.margin)

    screen = report["screen"]
    base = screen[BASELINE_BUILD]
    print(f"screen (n={args.screen_n}): {BASELINE_BUILD} (baseline) "
          f"{base['win_rate']:.3f} ({base['wins']}/{base['n']})")
    for name in wave2_stems():
        r = screen[name]
        v = report["verdicts"][name]
        tag = f"CLEARED SCREEN (+{v['delta']:.3f})" if name in report["cleared_screen"] else f"no clear ({v['delta']:+.3f})"
        print(f"  {name}: {r['win_rate']:.3f} ({r['wins']}/{r['n']}) -> {tag}")

    if report["confirm"] is not None:
        confirm = report["confirm"]
        cbase = confirm[BASELINE_BUILD]
        print(f"confirm (n={args.confirm_n}): {BASELINE_BUILD} (baseline) "
              f"{cbase['win_rate']:.3f} ({cbase['wins']}/{cbase['n']})")
        for name in report["cleared_screen"]:
            r = confirm[name]
            v = report["verdicts"][name]
            tag = f"PROMOTE (+{v['delta']:.3f})" if v["promote"] else f"no promote ({v['delta']:+.3f})"
            print(f"  {name}: {r['win_rate']:.3f} ({r['wins']}/{r['n']}) -> {tag}")
    else:
        print("confirm: skipped, no candidate cleared the screen")

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"wrote report {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
