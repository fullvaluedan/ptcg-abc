"""U101: engine invariant fuzzer, calibrate then enforce.

Thesis under test: engine bookkeeping mistakes are exploit opportunities,
possibly by design. This tool hunts for them by playing N games through the
local cabt engine, intercepting EVERY observation on both seats (the same
agent-wrapping interception pattern tools/gauntlet.py uses), and evaluating a
fixed set of state invariants at each observed state.

Zone accounting in this engine is subtle (attached energyCards, tools, and
preEvolution lists on each in-play Pokemon, facedown prizes as None entries,
the opponent hand exposed only as handCount, a state-level stadium and looking
zone), so hardcoding a card-conservation constant risks flagging our own
misunderstanding of the accounting model instead of a real engine bug. A run
therefore has two phases:

  Phase 1 CALIBRATE: over the first K clean games (completed without a crash)
  compute each calibrated quantity at every observed state and learn the
  stable value set per seat (I1 own-side total card count, expected 60, and
  the I7 duplicate-serial baseline). I1 is calibrated per (seat, context)
  where context is "effect" when the select carries an effect or contextCard
  (a card mid-resolution legally sits in no zone, so totals dip to 59 there)
  and "plain" otherwise; keying on context keeps the plain-state invariant
  sharp at exactly the calibrated constant.
  Phase 2 ENFORCE: in the remaining games, any deviation from the calibrated
  relation is logged as a VIOLATION.

The unambiguous invariants are hardcoded and enforced from game zero:
  I2 HP bounds (0 <= hp <= maxHp for every Pokemon on board)
  I3 own prizes-remaining never increases mid-game (turn >= 1)
  I4 bench size <= benchMax
  I5 deckCount never negative (monotone decrease is NOT asserted: recovery
     effects legally shuffle cards back into the deck)
  I6 turn number non-decreasing; result stays -1 until terminal, then never
     reverts or flips

Only live observations are scanned: the final recorded env step carries
STALE per-seat observation copies (each seat's last decision view; result
never leaves -1 in any recorded observation), so scanning it would fabricate
turn regressions. I6's result check still guards against the engine ever
exposing or flipping a result mid-game.

Dev tool only, never ships in a submission. Never raises out of the fuzz
loop: a checker error or a crashed game is counted and the run continues.
Each violation goes as one compact JSON line (no raw state dumps) to
analysis/engine_quirks_fuzz.jsonl and a human summary is appended to
analysis/engine_quirks.md. Zero violations is also a reportable result: the
summary always records games and states scanned.

Usage:
  .venv/Scripts/python.exe tools/fuzz_invariants.py --games 30 --agents mixed --seed 0
  Parallel hunt: one process per shard, e.g. for S in 0..7 run
  tools/fuzz_invariants.py --games 500 --agents mixed --seed 0 --shard $S
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DEFAULT_JSONL = _ROOT / "analysis" / "engine_quirks_fuzz.jsonl"
DEFAULT_MD = _ROOT / "analysis" / "engine_quirks.md"
DEFAULT_CALIBRATION_GAMES = 5

INVARIANT_NAMES = {
    "I1": "own-side card conservation (calibrated)",
    "I2": "HP within [0, maxHp]",
    "I3": "own prizes-remaining never increases mid-game",
    "I4": "bench size <= benchMax",
    "I5": "deckCount never negative",
    "I6": "turn non-decreasing; result terminal-stable",
    "I7": "no duplicate card serial across own visible zones (calibrated)",
}

MD_HEADER = """# Engine Quirks: invariant fuzz findings (U101)

Method: tools/fuzz_invariants.py plays games through the local cabt engine,
intercepting every observation on both seats via the gauntlet wrapper pattern,
and evaluates state invariants at each observed state. Because zone accounting
is subtle (attached energyCards/tools/preEvolution, facedown prizes as None,
opponent hand as handCount only), each run first CALIBRATES the subtle
quantities over its first K clean games (I1 own-side card conservation, keyed
per seat and per plain-vs-effect-resolution context, and the I7
duplicate-serial baseline), then ENFORCES the calibrated relations plus the
hardcoded invariants (I2 HP bounds, I3 prize monotonicity, I4 bench size,
I5 non-negative deck count, I6 turn/result monotonicity) over the rest.

Standing observations from building the tool (verified against raw env steps):
- A card mid-resolution legally sits in no zone: own-side totals read 59
  instead of 60 exactly when the select carries an effect/contextCard. The
  context-keyed calibration turns that from noise into a sharp invariant.
- The final recorded env step holds stale per-seat observation copies and no
  recorded observation ever exposes result != -1, so only live observations
  are scanned.

Violations stream one compact JSON line each (no raw state dumps) to
analysis/engine_quirks_fuzz.jsonl. A clean run is also a result: every run
appends its games and states scanned below.
"""


# ---------------------------------------------------------------------------
# Pure state helpers and invariant checkers (engine-free, unit-testable).
# Every function is defensive: malformed input is skipped, never raised.
# ---------------------------------------------------------------------------


def _player_list(state):
    """The two-seat players list, or None when the state is malformed."""
    players = state.get("players") if isinstance(state, dict) else None
    if not isinstance(players, list) or len(players) < 2:
        return None
    return players


def _board_slots(player):
    """Yield (zone_name, slot) for every entry in active and bench."""
    if not isinstance(player, dict):
        return
    active = player.get("active")
    if isinstance(active, list):
        for i, slot in enumerate(active):
            yield f"active[{i}]", slot
    bench = player.get("bench")
    if isinstance(bench, list):
        for i, slot in enumerate(bench):
            yield f"bench[{i}]", slot


def check_hp_bounds(state):
    """I2: every visible Pokemon on board has 0 <= hp <= maxHp."""
    violations = []
    players = _player_list(state)
    if players is None:
        return violations
    for pi, player in enumerate(players):
        for zone, slot in _board_slots(player):
            if not isinstance(slot, dict):
                continue  # facedown (None) or malformed slot: nothing to check
            hp, mx = slot.get("hp"), slot.get("maxHp")
            if not isinstance(hp, int) or not isinstance(mx, int):
                continue
            if hp < 0 or hp > mx:
                violations.append({
                    "seat": pi,
                    "zone": zone,
                    "cardId": slot.get("id"),
                    "hp": hp,
                    "maxHp": mx,
                })
    return violations


def check_bench_size(state):
    """I4: occupied bench slots never exceed benchMax."""
    violations = []
    players = _player_list(state)
    if players is None:
        return violations
    for pi, player in enumerate(players):
        if not isinstance(player, dict):
            continue
        bench, bench_max = player.get("bench"), player.get("benchMax")
        if not isinstance(bench, list) or not isinstance(bench_max, int):
            continue
        if len(bench) > bench_max:
            violations.append({"seat": pi, "bench": len(bench), "benchMax": bench_max})
    return violations


def check_deck_counts(state):
    """I5: deckCount is never negative (decrease is NOT asserted monotone)."""
    violations = []
    players = _player_list(state)
    if players is None:
        return violations
    for pi, player in enumerate(players):
        if not isinstance(player, dict):
            continue
        dc = player.get("deckCount")
        if isinstance(dc, int) and dc < 0:
            violations.append({"seat": pi, "deckCount": dc})
    return violations


def check_prizes_monotone(state, tracker):
    """I3: the acting seat's prize slots remaining never increase mid-game.

    Gated on turn >= 1 so the setup deal (prizes appearing at game start) is
    never mistaken for an increase.
    """
    violations = []
    players = _player_list(state)
    if players is None:
        return violations
    turn = state.get("turn")
    if not isinstance(turn, int) or turn < 1:
        return violations
    seat = state.get("yourIndex")
    if not isinstance(seat, int) or not (0 <= seat < len(players)):
        return violations
    me = players[seat]
    prize = me.get("prize") if isinstance(me, dict) else None
    if not isinstance(prize, list):
        return violations
    now = len(prize)
    prev = tracker.prev_prizes.get(seat)
    if prev is not None and now > prev:
        violations.append({"seat": seat, "prev": prev, "now": now})
    tracker.prev_prizes[seat] = now
    return violations


def check_turn_result(state, tracker):
    """I6: turn never decreases; result stays -1 until terminal, then is stable."""
    violations = []
    if not isinstance(state, dict):
        return violations
    turn = state.get("turn")
    if isinstance(turn, int):
        if tracker.max_turn is not None and turn < tracker.max_turn:
            violations.append({"kind": "turn_decreased", "turn": turn, "maxSeen": tracker.max_turn})
        else:
            tracker.max_turn = turn
    result = state.get("result")
    if isinstance(result, int):
        if tracker.final_result is None:
            if result != -1:
                tracker.final_result = result
        elif result != tracker.final_result:
            violations.append({
                "kind": "result_changed",
                "result": result,
                "terminal": tracker.final_result,
            })
    return violations


def compute_own_total(state, seat):
    """(total own-side card count, components) or (None, skip_reason).

    Counts everything the acting seat can fully see on its own side:
    deckCount + hand + discard + prize slots (facedown None entries are still
    cards) + every in-play Pokemon with its attached energyCards, tools, and
    preEvolution cards + own stadium card. A facedown in-play slot (None)
    counts as one card. States with a non-empty looking zone are skipped as
    ambiguous (those cards may or may not still be counted in deckCount), and
    any malformed field skips the state rather than raising.
    """
    players = _player_list(state)
    if players is None or not isinstance(seat, int) or not (0 <= seat < len(players)):
        return None, "malformed_players"
    me = players[seat]
    if not isinstance(me, dict):
        return None, "malformed_player"
    deck = me.get("deckCount")
    if not isinstance(deck, int):
        return None, "malformed_deckCount"
    hand = me.get("hand")
    if isinstance(hand, list):
        hand_n = len(hand)
    elif isinstance(me.get("handCount"), int):
        hand_n = me["handCount"]
    else:
        return None, "malformed_hand"
    discard, prize = me.get("discard"), me.get("prize")
    if not isinstance(discard, list) or not isinstance(prize, list):
        return None, "malformed_zones"
    looking = state.get("looking")
    if isinstance(looking, list) and looking:
        return None, "looking_active"
    in_play = 0
    for _zone, slot in _board_slots(me):
        if slot is None:
            in_play += 1  # facedown card occupies the slot, attachments hidden
        elif isinstance(slot, dict):
            in_play += 1
            for key in ("energyCards", "tools", "preEvolution"):
                extra = slot.get(key)
                if isinstance(extra, list):
                    in_play += len(extra)
    stadium_n = 0
    stadium = state.get("stadium")
    if isinstance(stadium, list):
        for card in stadium:
            if isinstance(card, dict) and card.get("playerIndex") == seat:
                stadium_n += 1
    components = {
        "deckCount": deck,
        "hand": hand_n,
        "discard": len(discard),
        "prizeSlots": len(prize),
        "inPlay": in_play,
        "stadium": stadium_n,
    }
    return deck + hand_n + len(discard) + len(prize) + in_play + stadium_n, components


def _own_zone_serials(state, seat):
    """Yield (zone_name, serial, cardId) for the acting seat's visible cards."""
    players = _player_list(state)
    if players is None or not isinstance(seat, int) or not (0 <= seat < len(players)):
        return
    me = players[seat]
    if not isinstance(me, dict):
        return

    def cards(zone, seq):
        if not isinstance(seq, list):
            return
        for i, card in enumerate(seq):
            if isinstance(card, dict) and isinstance(card.get("serial"), int):
                yield f"{zone}[{i}]", card["serial"], card.get("id")

    yield from cards("hand", me.get("hand"))
    yield from cards("discard", me.get("discard"))
    yield from cards("prize", me.get("prize"))  # facedown None entries skipped
    for zone, slot in _board_slots(me):
        if not isinstance(slot, dict):
            continue
        if isinstance(slot.get("serial"), int):
            yield zone, slot["serial"], slot.get("id")
        for key in ("energyCards", "tools", "preEvolution"):
            yield from cards(f"{zone}.{key}", slot.get(key))
    stadium = state.get("stadium")
    if isinstance(stadium, list):
        for i, card in enumerate(stadium):
            if (isinstance(card, dict) and card.get("playerIndex") == seat
                    and isinstance(card.get("serial"), int)):
                yield f"stadium[{i}]", card["serial"], card.get("id")


def duplicate_serials(state, seat, benign=frozenset()):
    """I7: serials appearing in two or more of the seat's visible zones.

    A serial is unique per physical card for the whole match, so the same
    serial in two zones at once means the engine double-books a card. Serial
    values in `benign` (learned during calibration, e.g. a placeholder 0) are
    ignored, keeping this best-effort rather than assumption-driven.
    """
    seen = {}
    for zone, serial, card_id in _own_zone_serials(state, seat):
        seen.setdefault(serial, []).append((zone, card_id))
    violations = []
    for serial, places in seen.items():
        if len(places) > 1 and serial not in benign:
            violations.append({
                "seat": seat,
                "serial": serial,
                "zones": [z for z, _ in places],
                "cardIds": [c for _, c in places],
            })
    return violations


# ---------------------------------------------------------------------------
# Per-game tracking, calibration store, and the fuzz checker.
# ---------------------------------------------------------------------------


class GameTracker:
    """Mutable per-game bookkeeping the monotonic invariants need."""

    def __init__(self, game_id="0:0", seed=0, agents="random/random"):
        self.game_id = game_id
        self.seed = seed
        self.agents = agents
        self.step = 0
        self.prev_prizes = {}
        self.max_turn = None
        self.final_result = None


def select_context(obs):
    """"effect" when the select carries an effect or contextCard, else "plain".

    A card whose effect is resolving legally sits in no zone (played from hand
    but not yet in discard), so own-side totals differ between the two
    contexts. Calibrating I1 per context keeps the plain-state constant sharp.
    """
    sel = obs.get("select") if isinstance(obs, dict) else None
    if isinstance(sel, dict) and (sel.get("effect") or sel.get("contextCard")):
        return "effect"
    return "plain"


class Calibration:
    """Learns the stable values of the subtle invariants over clean games."""

    def __init__(self):
        self.own_totals = {}  # (seat, context) -> Counter of observed totals
        self.i1_skips = Counter()
        self.dup_serials = Counter()  # serial value -> times seen duplicated
        self.states = 0
        self.finalized = False
        self.allowed_totals = {}
        self.benign_serials = frozenset()
        self.i1_enabled = False

    def observe(self, state, seat, context="plain"):
        self.states += 1
        turn = state.get("turn") if isinstance(state, dict) else None
        if isinstance(turn, int) and turn >= 1:
            total, comp = compute_own_total(state, seat)
            if total is None:
                self.i1_skips[comp] += 1
            else:
                self.own_totals.setdefault((seat, context), Counter())[total] += 1
        for v in duplicate_serials(state, seat):
            self.dup_serials[v["serial"]] += 1

    def finalize(self):
        self.allowed_totals = {k: set(c) for k, c in self.own_totals.items() if c}
        self.i1_enabled = bool(self.allowed_totals)
        self.benign_serials = frozenset(self.dup_serials)
        self.finalized = True

    def allowed_for(self, seat, context="plain"):
        """Allowed I1 totals for (seat, context).

        Falls back to the other seat's totals for the SAME context (both decks
        are 60 cards), never across contexts. Returns None when the context was
        never calibrated at all, so enforcement skips rather than guesses.
        """
        key = (seat, context)
        base = None
        if key in self.allowed_totals:
            base = set(self.allowed_totals[key])
        else:
            union = set()
            for (s, c), vals in self.allowed_totals.items():
                if c == context:
                    union |= vals
            base = union or None
        # Effect-resolution states are STRUCTURALLY bimodal: the context card
        # sits in no zone while an effect resolves (total 59) or the effect
        # holds no card out of zone (total 60). Verified during bring-up
        # (analysis/engine_quirks.md). Per-shard calibration samples are too
        # small (4-8 effect states) to always observe both modes, which
        # produced 850 false I1 violations in the first 4000-game hunt. Encode
        # the proven mechanism instead of trusting an undersampled calibration.
        if context == "effect":
            return (base or set()) | {59, 60}
        return base


class FuzzChecker:
    """Evaluates all invariants on each observation and logs violations.

    observe() NEVER raises: every checker call is individually guarded, and
    any internal failure only increments internal_errors.
    """

    def __init__(self, calibration=None, jsonl_path=None):
        self.calibration = calibration if calibration is not None else Calibration()
        self.mode = "calibrate"
        self.jsonl_path = Path(jsonl_path) if jsonl_path else None
        self._fh = None
        self.violations = []
        self.by_invariant = Counter()
        self.states_scanned = 0
        self.enforce_skips = Counter()
        self.internal_errors = 0

    def enforce(self):
        if not self.calibration.finalized:
            self.calibration.finalize()
        self.mode = "enforce"

    def observe(self, obs, tracker):
        try:
            self._observe(obs, tracker)
        except Exception:
            self.internal_errors += 1

    def _observe(self, obs, tracker):
        current = obs.get("current") if isinstance(obs, dict) else None
        if not isinstance(current, dict):
            return
        tracker.step += 1
        self.states_scanned += 1
        seat = current.get("yourIndex")
        turn = current.get("turn") if isinstance(current.get("turn"), int) else None

        # Hardcoded invariants, active in both phases.
        for invariant, call in (
            ("I2", lambda: check_hp_bounds(current)),
            ("I3", lambda: check_prizes_monotone(current, tracker)),
            ("I4", lambda: check_bench_size(current)),
            ("I5", lambda: check_deck_counts(current)),
            ("I6", lambda: check_turn_result(current, tracker)),
        ):
            try:
                for v in call():
                    self._emit(invariant, tracker, turn, v.pop("seat", seat), v)
            except Exception:
                self.internal_errors += 1

        # Calibrated invariants: learn in phase 1, enforce in phase 2.
        if not isinstance(seat, int):
            return
        context = select_context(obs)
        if self.mode == "calibrate":
            try:
                self.calibration.observe(current, seat, context)
            except Exception:
                self.internal_errors += 1
            return
        try:
            if self.calibration.i1_enabled and turn is not None and turn >= 1:
                total, comp = compute_own_total(current, seat)
                if total is None:
                    self.enforce_skips[comp] += 1
                else:
                    allowed = self.calibration.allowed_for(seat, context)
                    if allowed is None:
                        self.enforce_skips[f"uncalibrated_context_{context}"] += 1
                    elif total not in allowed:
                        self._emit("I1", tracker, turn, seat, {
                            "total": total,
                            "context": context,
                            "expected": sorted(allowed),
                            "components": comp,
                        })
        except Exception:
            self.internal_errors += 1
        try:
            for v in duplicate_serials(current, seat, self.calibration.benign_serials):
                self._emit("I7", tracker, turn, v.pop("seat", seat), v)
        except Exception:
            self.internal_errors += 1

    def _emit(self, invariant, tracker, turn, seat, detail):
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "invariant": invariant,
            "name": INVARIANT_NAMES.get(invariant, invariant),
            "game": tracker.game_id,
            "step": tracker.step,
            "turn": turn,
            "seat": seat,
            "detail": detail,
            "seed": tracker.seed,
            "agents": tracker.agents,
        }
        self.violations.append(record)
        self.by_invariant[invariant] += 1
        if self.jsonl_path is not None:
            try:
                if self._fh is None:
                    self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
                    self._fh = open(self.jsonl_path, "a", encoding="utf-8")
                self._fh.write(json.dumps(record, default=str) + "\n")
                self._fh.flush()
            except Exception:
                self.internal_errors += 1

    def close(self):
        if self._fh is not None:
            try:
                self._fh.close()
            except Exception:
                pass
            self._fh = None


def _observing(agent_fn, checker, tracker):
    """Gauntlet-style wrapper: check invariants on every observation, then act."""

    def wrapped(obs):
        checker.observe(obs, tracker)  # never raises
        return agent_fn(obs)

    return wrapped


# ---------------------------------------------------------------------------
# The fuzz loop (engine imports stay inside so unit tests never need it).
# ---------------------------------------------------------------------------


def run_fuzz(games, seed=0, shard=0, agents="random",
             calibration_games=DEFAULT_CALIBRATION_GAMES,
             jsonl_path=DEFAULT_JSONL, md_path=DEFAULT_MD):
    """Play `games` matches, calibrate over the first clean ones, then enforce."""
    from ptcg_agent.engine import make_env
    from tools import opponents

    checker = FuzzChecker(jsonl_path=jsonl_path)
    game_errors = []
    games_completed = 0
    calibration_done = 0
    enforced_games = 0
    t0 = time.time()
    try:
        for i in range(games):
            if checker.mode == "calibrate" and calibration_done >= calibration_games:
                checker.enforce()
            game_id = f"{shard}:{i}"
            game_seed = seed * 1_000_003 + shard * 8_191 + i
            random.seed(game_seed)
            try:
                if agents == "mixed":
                    heur, rand = opponents.get("heuristic"), opponents.get("random")
                    if i % 2 == 0:
                        order, names = [heur, rand], "seat0=heuristic,seat1=random"
                    else:
                        order, names = [rand, heur], "seat0=random,seat1=heuristic"
                else:
                    order, names = [opponents.get("random"), opponents.get("random")], \
                        "seat0=random,seat1=random"
                tracker = GameTracker(game_id, game_seed, names)
                env = make_env()
                env.run([_observing(fn, checker, tracker) for fn in order])
                # No terminal post-scan: the final recorded step holds STALE
                # per-seat observation copies (verified: turn lags by one for
                # the non-acting seat, result never leaves -1), so scanning it
                # would fabricate turn regressions. Live observations only.
                games_completed += 1
                if checker.mode == "calibrate":
                    calibration_done += 1
                else:
                    enforced_games += 1
            except Exception as exc:
                game_errors.append({"game": game_id, "error": repr(exc)[:300]})
        if checker.mode == "calibrate":
            checker.enforce()  # finalize even if the run never left phase 1
    finally:
        checker.close()

    calib = checker.calibration
    summary = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": (f"--games {games} --agents {agents} --seed {seed} "
                    f"--shard {shard} --calibrate {calibration_games}"),
        "games_requested": games,
        "games_completed": games_completed,
        "calibration_games": calibration_done,
        "enforced_games": enforced_games,
        "game_errors": len(game_errors),
        "game_error_samples": game_errors[:5],
        "states_scanned": checker.states_scanned,
        "internal_errors": checker.internal_errors,
        "violations": len(checker.violations),
        "by_invariant": {k: checker.by_invariant[k] for k in sorted(checker.by_invariant)},
        "i1_allowed_totals": {f"seat{s}/{c}": sorted(v)
                              for (s, c), v in sorted(calib.allowed_totals.items())},
        "i1_calibration_counts": {f"seat{s}/{c}": dict(cnt)
                                  for (s, c), cnt in sorted(calib.own_totals.items())},
        "i1_calibration_skips": dict(calib.i1_skips),
        "i1_enforce_skips": dict(checker.enforce_skips),
        "benign_serials": sorted(calib.benign_serials),
        "seed": seed,
        "shard": shard,
        "agents": agents,
        "duration_s": round(time.time() - t0, 1),
        "jsonl": str(jsonl_path),
    }
    if md_path:
        try:
            append_md_summary(Path(md_path), summary)
        except Exception as exc:
            summary["md_error"] = repr(exc)[:200]
    return summary


def append_md_summary(md_path, summary):
    """Append a human-readable run summary, creating the file with its header."""
    md_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if not md_path.exists():
        lines.append(MD_HEADER)
    lines.append(f"\n## Run {summary['ts']} (shard {summary['shard']})\n")
    lines.append(f"- command: `tools/fuzz_invariants.py {summary['command']}`")
    lines.append(
        f"- games: {summary['games_requested']} requested, "
        f"{summary['games_completed']} completed "
        f"({summary['calibration_games']} calibration, "
        f"{summary['enforced_games']} enforced), "
        f"{summary['game_errors']} crashed"
    )
    lines.append(
        f"- states scanned: {summary['states_scanned']}, "
        f"checker internal errors: {summary['internal_errors']}, "
        f"duration: {summary['duration_s']}s"
    )
    lines.append(
        f"- calibration: I1 own-side totals per seat "
        f"{summary['i1_calibration_counts'] or 'none observed'}; "
        f"I1 skips {summary['i1_calibration_skips'] or '{}'}; "
        f"I7 benign duplicate serials "
        f"{summary['benign_serials'] or 'none'}"
    )
    if summary["violations"]:
        lines.append(
            f"- verdict: {summary['violations']} VIOLATION(S) "
            f"{summary['by_invariant']}, details in {summary['jsonl']}"
        )
    else:
        lines.append(
            f"- verdict: CLEAN, 0 violations over "
            f"{summary['enforced_games']} enforced games "
            f"({summary['states_scanned']} states scanned)"
        )
    if summary.get("game_error_samples"):
        lines.append(f"- crash samples: {summary['game_error_samples']}")
    with open(md_path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="U101 engine invariant fuzzer: calibrate then enforce."
    )
    ap.add_argument("--games", type=int, default=30, help="total games to play")
    ap.add_argument("--seed", type=int, default=0, help="base RNG seed")
    ap.add_argument("--shard", type=int, default=0,
                    help="shard id, namespaces game ids for parallel hunts")
    ap.add_argument("--agents", choices=("random", "mixed"), default="random",
                    help="random = random vs random; mixed = heuristic vs random "
                         "(deeper game states)")
    ap.add_argument("--calibrate", type=int, default=DEFAULT_CALIBRATION_GAMES,
                    help="clean games used to calibrate I1/I7 before enforcing")
    ap.add_argument("--jsonl", default=str(DEFAULT_JSONL),
                    help="violation log path (one JSON line per violation)")
    ap.add_argument("--md", default=str(DEFAULT_MD),
                    help="human summary markdown path")
    args = ap.parse_args(argv)

    summary = run_fuzz(
        args.games, seed=args.seed, shard=args.shard, agents=args.agents,
        calibration_games=args.calibrate, jsonl_path=args.jsonl, md_path=args.md,
    )
    print(f"fuzz_invariants shard {summary['shard']}: "
          f"{summary['games_completed']}/{summary['games_requested']} games "
          f"({summary['calibration_games']} calibration, "
          f"{summary['enforced_games']} enforced), "
          f"{summary['states_scanned']} states scanned, "
          f"{summary['game_errors']} crashed, "
          f"{summary['internal_errors']} checker errors")
    print(f"  calibration I1 totals: {summary['i1_calibration_counts']}")
    if summary["benign_serials"]:
        print(f"  calibration I7 benign serials: {summary['benign_serials']}")
    if summary["violations"]:
        print(f"  VIOLATIONS: {summary['violations']} {summary['by_invariant']}")
        print(f"  details: {summary['jsonl']}")
    else:
        print("  VERDICT: CLEAN, 0 violations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
