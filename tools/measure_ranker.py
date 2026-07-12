"""Measure whether PTCG_RANKER actually FLIPS a real pilot decision on yushin.

The outcome-labeled per-option policy ranker (PTCG_RANKER, staged off behind
the flag; design and training in analysis/ranker_outcome_model.md) ranks every
L2/L3-safe legal MAIN option by predicted P(win | option taken)
(search/learned_ranker.py, the model tools/train_ranker.py exported) and takes
the argmax in place of the category ladder. Same discipline as
measure_threat_retreat.py / measure_endgame_play.py: CAN-fire is not the same
as MATTERS, so before any ring compute is spent this captures real mid-game
MAIN observations from yushin self-play where the ranker's structural
precondition holds (at least two L2/L3-safe candidate options -- the minimum
for an argmax to matter at all), toggles heuristics._RANKER off and on with
the REAL committed search/ranker_model.json (never mocked for these rows),
and checks whether choose() actually picks a different option index on the
identical obs.

It ALSO evaluates one hand-built positive-control observation whose scorer IS
mocked (to strongly prefer RETREAT, an option the historical ladder never
picks first here) -- this is a check on the PTCG_RANKER wiring itself (the
flag -> _ranker_safe_indices -> decision_features -> score_option -> argmax
chain), not on the trained model's judgment, so it is expected to flip
regardless of what the real model thinks about real yushin positions. If the
control does not flip, the probe is broken and any yushin zero below is
uninterpretable. If the rule is inert on real yushin positions (control
flips, captured positions do not), do NOT spend ring compute; record the
honest inert result and stop, per the U105 lesson.

Dev/measurement tool only; never shipped, touches no shipped code path (the
_RANKER flag and, for the control row only, learned_ranker.score_option are
toggled on the imported module attributes and restored in a finally), so the
frozen batch stays byte-identical. The native engine is a per-process
singleton, so it runs one match in process.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agents import heuristics as h  # noqa: E402
from agents import imitation_features as IF  # noqa: E402
from ptcg_agent.engine import ensure_official_cg, make_env  # noqa: E402
from search import learned_ranker  # noqa: E402
from tools import opponents  # noqa: E402
from tools.deck_match import deck_bound  # noqa: E402
from tools.deck_validate import read_deck  # noqa: E402

YUSHIN_DECK = str(_ROOT / "decks" / "candidate_yushin_ito.csv")


def _safe_count(obs) -> int:
    sel = obs.get("select") or {}
    options = sel.get("option", [])
    state = obs.get("current") or {}
    yi = state.get("yourIndex", 0)
    players = state.get("players") or []
    me = players[yi] if len(players) > yi else {}
    return len(h._ranker_safe_indices(options, obs, me))


def capture_ranker_obs(deck_ids, limit=25, min_turn=1, max_matches=60):
    """Play heuristic-vs-random matches piloting deck_ids and collect MAIN
    observations where the ranker's structural precondition holds: at least
    two L2/L3-safe candidate options. A single match rarely offers this
    overlap more than a few times, so this plays up to max_matches matches,
    stopping early once limit positions are captured.
    """
    piloted = deck_bound(opponents.get("heuristic"), deck_ids)
    captured: list = []

    def capturing(obs):
        sel = obs.get("select")
        if (
            len(captured) < limit
            and sel is not None
            and sel.get("type") == h.SEL_MAIN
            and sel.get("maxCount", 1) == 1
            and (obs.get("current") or {}).get("turn", 0) >= min_turn
        ):
            if _safe_count(obs) >= 2:
                captured.append(obs)
        return piloted(obs)

    for _ in range(max_matches):
        if len(captured) >= limit:
            break
        make_env().run([capturing, "random"])
    return captured


def _decide(obs, ranker_on):
    """Return the chosen option index under a _RANKER setting.

    The flag is toggled on the imported module attribute and restored in a
    finally, so no shipped code path is mutated.
    """
    saved = h._RANKER
    h._RANKER = ranker_on
    try:
        chosen = h.choose(obs)
    finally:
        h._RANKER = saved
    return chosen[0] if isinstance(chosen, list) and chosen else None


def _option_type(obs, idx):
    if idx is None:
        return None
    opts = (obs.get("select") or {}).get("option", [])
    if 0 <= idx < len(opts):
        return opts[idx].get("type")
    return None


def _row_for(obs, source):
    n_safe = _safe_count(obs)
    off_idx = _decide(obs, False)
    on_idx = _decide(obs, True)
    return {
        "turn": (obs.get("current") or {}).get("turn"),
        "n_options": len((obs.get("select") or {}).get("option", [])),
        "n_safe": n_safe,
        "off_idx": off_idx,
        "on_idx": on_idx,
        "off_type": _option_type(obs, off_idx),
        "on_type": _option_type(obs, on_idx),
        "flip": off_idx != on_idx,
        "source": source,
    }


def _positive_control_obs():
    """A hand-built MAIN decision with three legal options (RETREAT, ATTACH,
    END), all L2/L3-safe (RETREAT/ATTACH/END are never excluded by
    _ranker_safe_indices, which only ever filters ABILITY/PLAY), so the
    ranker's structural precondition holds. The historical ladder (flag off)
    picks ATTACH here (attach outranks retreat/end at shipped priorities).
    """
    me = {
        "active": [{"id": 722, "hp": 90, "maxHp": 90}],
        "bench": [{"id": 722, "hp": 90, "maxHp": 90}],
        "hand": [], "deckCount": 30, "prize": [None] * 6,
    }
    opp = {"active": [{"id": 722, "hp": 60, "maxHp": 90}], "bench": [], "prize": [None] * 6}
    return {
        "select": {
            "type": h.SEL_MAIN, "context": 0, "minCount": 1, "maxCount": 1,
            "option": [
                {"type": h.OPT_RETREAT},
                {"type": h.OPT_ATTACH, "inPlayArea": h.AREA_ACTIVE},
                {"type": h.OPT_END},
            ],
        },
        "current": {"yourIndex": 0, "energyAttached": True, "players": [me, opp]},
    }


def _positive_control_row():
    """The design's pre-registered positive control: the same obs and off/on
    toggle as every other row, but with search.learned_ranker.score_option
    itself mocked (strongly preferring RETREAT, saved and restored around the
    "on" decision only) so a working _resolve_ranker chain is REQUIRED to
    flip choose() to RETREAT regardless of what the real trained model
    thinks. Proves the wiring, not the model.
    """
    obs = _positive_control_obs()
    off_idx = _decide(obs, False)
    is_retreat_idx = IF._INDEX["is_retreat"]
    saved_score = learned_ranker.score_option
    try:
        learned_ranker.score_option = lambda features: (0.9 if features[is_retreat_idx] else 0.1)
        on_idx = _decide(obs, True)
    finally:
        learned_ranker.score_option = saved_score
    return {
        "turn": None,
        "n_options": 3,
        "n_safe": _safe_count(obs),
        "off_idx": off_idx,
        "on_idx": on_idx,
        "off_type": _option_type(obs, off_idx),
        "on_type": _option_type(obs, on_idx),
        "flip": off_idx != on_idx,
        "source": "synthetic_control",
    }


def measure(deck_path=YUSHIN_DECK, limit=25):
    deck_ids = read_deck(deck_path)
    ensure_official_cg()
    positions = capture_ranker_obs(deck_ids, limit=limit)
    rows = [_row_for(obs, "captured") for obs in positions]
    control = _positive_control_row()
    return {"deck": Path(deck_path).stem, "rows": rows, "control": control}


def _format(result):
    lines = [
        f"PTCG_RANKER decision effect on {result['deck']} "
        f"(heuristic pilot, real captured >=2-safe-candidate positions, "
        f"REAL committed search/ranker_model.json, never mocked for these rows):",
        "  turn  n_options  n_safe  off_type  on_type  flip",
    ]
    for r in result["rows"]:
        lines.append(
            f"  {str(r['turn']):>4s}  {str(r['n_options']):>9s}  {str(r['n_safe']):>6s}  "
            f"{str(r['off_type']):>8s}  {str(r['on_type']):>7s}  {str(r['flip']):>5s}"
        )
    n = len(result["rows"])
    flips = sum(1 for r in result["rows"] if r["flip"])
    lines.append(f"  positions captured (>=2 L2/L3-safe candidates): {n}")
    lines.append(f"  PTCG_RANKER flipped the pilot decision on {flips}/{n} real yushin positions")

    control = result["control"]
    lines.append("")
    lines.append(
        f"  positive control (synthetic, scorer mocked to prefer RETREAT): "
        f"off_type={control['off_type']} on_type={control['on_type']} flip={control['flip']}"
    )
    if not control["flip"]:
        lines.append(
            "  => POSITIVE CONTROL DID NOT FLIP: the PTCG_RANKER wiring itself is broken "
            "(a mocked scorer with a forced preference still failed to change choose()'s "
            "pick); fix the probe/wiring before trusting any yushin result above. Do NOT "
            "spend ring compute."
        )
    elif flips == 0:
        lines.append(
            "  => PTCG_RANKER flips no decision on these real yushin positions (the "
            "positive control DID flip, so the wiring works): the trained model is INERT "
            "on the ring deck. Do NOT spend a hard-ring slot on it; record the honest "
            "inert result and stop (per the U105 lesson)."
        )
    else:
        lines.append(
            f"  => PTCG_RANKER is LIVE on yushin ({flips}/{n} real positions flip); "
            "proceed to the pre-registered powered gate run before any ladder slot."
        )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck", nargs="?", default=YUSHIN_DECK,
                    help="deck csv path (default: decks/candidate_yushin_ito.csv, the ring deck)")
    ap.add_argument("-n", "--positions", type=int, default=25,
                    help="max mid-game MAIN >=2-safe-candidate positions to capture and measure")
    args = ap.parse_args()
    print(_format(measure(args.deck, limit=args.positions)))


if __name__ == "__main__":
    main()
