"""Measure whether PTCG_ENDGAME_PLAY actually FLIPS a real pilot decision on yushin.

The endgame PLAY-priority correction (PTCG_ENDGAME_PLAY, staged off behind the
flag, design in analysis/endgame_play_rule_design.md) demotes the discretionary
EVOLVE below PLAY when we are near-endgame (either side at or below 2 prizes)
with a bloated hand (>= ENDGAME_HAND, default 10) and both OPT_PLAY and
OPT_EVOLVE are legal. The lever is motivated by expert Dudunsparce decks; the
ring pilots candidate_yushin_ito, whose evolution line (Staryu -> Mega Starmie
ex) IS the win condition, so this is the mandatory Step 0 precheck (the U105
lesson) before any ring compute is spent: CAN-fire is not the same as MATTERS,
and a zero from a subsumed/broken probe is indistinguishable from a zero from a
lever that is genuinely inert on this deck.

Same discipline as measure_threat_retreat.py: this tool captures real mid-game
MAIN observations from yushin self-play where the rule's two-category structural
precondition holds (both OPT_PLAY and OPT_EVOLVE legal), toggles
heuristics._ENDGAME_PLAY off and on, and checks whether choose() actually flips
from an EVOLVE pick to a PLAY pick on the identical obs. It ALSO evaluates one
hand-built positive-control observation (our prizes = 2, hand = 12, both
categories legal) that the design pre-registers as required to flip -- if the
control does not flip, the probe itself is broken and any yushin zero is
uninterpretable. If the rule is inert on real yushin positions (control flips,
captured positions do not), do NOT spend ring compute; record the honest inert
result and stop.

Dev/measurement tool only; never shipped, touches no shipped code path (the
_ENDGAME_PLAY flag is toggled on the imported module attribute, read once at
import in heuristics.py, and restored in a finally), so the frozen batch stays
byte-identical. The native engine is a per-process singleton, so it runs one
match in process.
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
from ptcg_agent.engine import ensure_official_cg, make_env  # noqa: E402
from tools import opponents  # noqa: E402
from tools.deck_match import deck_bound  # noqa: E402
from tools.deck_validate import read_deck  # noqa: E402

YUSHIN_DECK = str(_ROOT / "decks" / "candidate_yushin_ito.csv")


def capture_endgame_play_obs(deck_ids, limit=25, min_turn=1, max_matches=60):
    """Play heuristic-vs-random matches piloting deck_ids and collect MAIN
    observations where both OPT_PLAY and OPT_EVOLVE are legal (the rule's
    structural precondition, section 3 condition 4 of the design). A single
    match rarely offers this overlap more than a few times, so this plays up to
    max_matches matches, stopping early once limit positions are captured.
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
            groups = h.options_by_type(sel.get("option", []))
            if h.OPT_PLAY in groups and h.OPT_EVOLVE in groups:
                captured.append(obs)
        return piloted(obs)

    for _ in range(max_matches):
        if len(captured) >= limit:
            break
        make_env().run([capturing, "random"])
    return captured


def _decide(obs, endgame_play):
    """Return the chosen option index under an _ENDGAME_PLAY setting.

    The flag is toggled on the imported module attribute and restored in a
    finally, so no shipped code path is mutated.
    """
    saved = h._ENDGAME_PLAY
    h._ENDGAME_PLAY = endgame_play
    try:
        chosen = h.choose(obs)
    finally:
        h._ENDGAME_PLAY = saved
    return chosen[0] if isinstance(chosen, list) and chosen else None


def _option_type(obs, idx):
    """The OptionType of the option choose() picked, or None if idx is unresolved."""
    if idx is None:
        return None
    opts = (obs.get("select") or {}).get("option", [])
    if 0 <= idx < len(opts):
        return opts[idx].get("type")
    return None


def _fires(obs):
    """(fires, hand_n, near_endgame) for the full trigger, assuming the flag is on.

    fires mirrors the design's exact condition 2-4 (condition 1, the flag, is
    varied separately by _decide): near-endgame, a bloated hand, and both
    categories legal.
    """
    sel = obs.get("select") or {}
    groups = h.options_by_type(sel.get("option", []))
    state = obs.get("current") or {}
    yi = state.get("yourIndex", 0)
    players = state.get("players") or []
    me = players[yi] if len(players) > yi else {}
    hand_n = len(me.get("hand") or [])
    near_endgame = min(h._our_prize_count(obs), h._opp_prize_count(obs)) <= 2
    both_legal = h.OPT_PLAY in groups and h.OPT_EVOLVE in groups
    fires = both_legal and hand_n >= h.ENDGAME_HAND and near_endgame
    return fires, hand_n, near_endgame


def _row_for(obs, source):
    fires, hand_n, near_endgame = _fires(obs)
    off_idx = _decide(obs, False)
    on_idx = _decide(obs, True)
    off_type = _option_type(obs, off_idx)
    on_type = _option_type(obs, on_idx)
    # Flips per the design's exact definition: off resolves EVOLVE, on resolves
    # PLAY, on the identical obs.
    flip = off_type == h.OPT_EVOLVE and on_type == h.OPT_PLAY
    return {
        "turn": (obs.get("current") or {}).get("turn"),
        "hand_n": hand_n,
        "near_endgame": near_endgame,
        "fires": fires,
        "off_type": off_type,
        "on_type": on_type,
        "flip": flip,
        "source": source,
    }


def _positive_control_obs():
    """The design's pre-registered positive control: our prizes = 2, a legal
    OPT_EVOLVE option, a legal OPT_PLAY option, hand of 12 cards.

    Hand-built exactly like the design specifies (section 6, Step 0), so a
    broken probe (one that cannot flip even the textbook trigger state) is
    caught before any yushin zero is trusted.
    """
    hand = [{"id": 1205} for _ in range(12)]  # Cyrano, a real Supporter card id
    bench = [{"id": 722, "hp": 90, "maxHp": 90} for _ in range(2)]  # Snover, real Basic
    me = {
        "active": [{"id": 722, "hp": 90, "maxHp": 90}],
        "bench": bench,
        "hand": hand,
        "prize": [None, None],
    }
    opp = {
        "active": [{"id": 722, "hp": 90, "maxHp": 90}],
        "bench": [],
        "prize": [None, None],
    }
    return {
        "select": {
            "type": h.SEL_MAIN, "context": 0, "minCount": 1, "maxCount": 1,
            "option": [
                {"type": h.OPT_EVOLVE, "index": 0},
                {"type": h.OPT_PLAY, "index": 0},
                {"type": h.OPT_END},
            ],
        },
        "current": {"yourIndex": 0, "energyAttached": True, "players": [me, opp]},
    }


def measure(deck_path=YUSHIN_DECK, limit=25):
    deck_ids = read_deck(deck_path)
    ensure_official_cg()
    positions = capture_endgame_play_obs(deck_ids, limit=limit)
    rows = [_row_for(obs, "captured") for obs in positions]
    control = _row_for(_positive_control_obs(), "synthetic_control")
    return {"deck": Path(deck_path).stem, "rows": rows, "control": control}


def _format(result):
    lines = [
        f"endgame-play decision effect on {result['deck']} "
        f"(heuristic pilot, real captured PLAY+EVOLVE-legal positions):",
        "  turn  hand_n  near_endgame  fires  off_type  on_type  flip",
    ]
    for r in result["rows"]:
        lines.append(
            f"  {str(r['turn']):>4s}  {str(r['hand_n']):>6s}  "
            f"{str(r['near_endgame']):>12s}  {str(r['fires']):>5s}  "
            f"{str(r['off_type']):>8s}  {str(r['on_type']):>7s}  {str(r['flip']):>5s}"
        )
    n = len(result["rows"])
    flips = sum(1 for r in result["rows"] if r["flip"])
    fires_n = sum(1 for r in result["rows"] if r["fires"])
    lines.append(f"  positions captured (PLAY+EVOLVE legal): {n}")
    lines.append(
        f"  positions where the full trigger fires (near-endgame, hand>={h.ENDGAME_HAND}): "
        f"{fires_n}/{n}"
    )
    lines.append(f"  endgame-play flipped EVOLVE->PLAY on {flips}/{n} captured yushin positions")

    control = result["control"]
    lines.append("")
    lines.append(
        f"  positive control (synthetic, our_prizes=2, hand=12, both categories legal): "
        f"fires={control['fires']} off_type={control['off_type']} on_type={control['on_type']} "
        f"flip={control['flip']}"
    )
    if not control["flip"]:
        lines.append(
            "  => POSITIVE CONTROL DID NOT FLIP: the probe itself is broken (a genuine "
            "trigger state does not flip choose()); fix the probe before trusting any "
            "yushin result above. Do NOT spend ring compute."
        )
    elif flips == 0:
        lines.append(
            "  => PTCG_ENDGAME_PLAY flips no decision on these real yushin positions "
            "(the positive control DID flip, so the probe works): the lever is INERT "
            "on the ring deck. Do NOT spend a hard-ring slot on it; record the honest "
            "inert result and stop (per the U105 lesson / analysis/endgame_play_rule_design.md)."
        )
    else:
        lines.append(
            f"  => PTCG_ENDGAME_PLAY is LIVE on yushin ({flips}/{n} real positions flip); "
            "proceed to the pre-registered gate run (Step 1/Step 2) before any ladder slot."
        )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck", nargs="?", default=YUSHIN_DECK,
                    help="deck csv path (default: decks/candidate_yushin_ito.csv, the ring deck)")
    ap.add_argument("-n", "--positions", type=int, default=25,
                    help="max mid-game MAIN PLAY+EVOLVE-legal positions to capture and measure")
    args = ap.parse_args()
    print(_format(measure(args.deck, limit=args.positions)))


if __name__ == "__main__":
    main()
