"""Game-plan miner (plan U36, piece 2 of 3).

The target selector (piece 1, tools/archetype_select) names the family the
deck-aware pilot should master. This miner reads that family's real expert
episodes and distills HOW the top players pilot it into a fixed set of stat
blocks, each contrasting the family's WINNING appearances with its LOSING ones,
so the seeds emitter (piece 3) can turn the winning-play signal into baked
constants for the U37 consumer (attach targeting, bench / play targets, evolve
priorities, the deckout floor).

Six blocks, in the two shapes the emitter thresholds:

  categorical (a "what" distribution over resolved decisions):
    opening_category  the action category of the seat's FIRST MAIN decision
    attach_target     the card an ATTACH decision put energy on
    play_target       the card a PLAY decision put down
    evolve_target     the card an EVOLVE decision evolved into
  timing (a "when" ordinal, the 1-based index among the seat's MAIN decisions):
    first_attack_ordinal  when the seat took its first ATTACK
    first_evolve_ordinal  when the seat made its first EVOLVE

Three more blocks (plan U91, comprehension track) read WITHIN a turn rather than
across the whole game, so they need turn boundaries: a seat can make several MAIN
decisions in one turn (PLAY, ATTACH, EVOLVE, ATTACK) before ending it, and END is
always the last decision of a turn (_turns splits on it):

  categorical (a per-turn True/False, not per-decision):
    attach_before_attack  on turns with BOTH an ATTACH and an ATTACK, did the
                          ATTACH come first (within-turn sequencing)
    energy_banking        on turns with an ATTACH, was there NO attack that same
                          turn (energy attached ahead rather than spent at once)
  timing (a per-episode count, not an ordinal into one game):
    game_length_turns     how many turns the seat took this episode (a family's
                          win-condition timing: how long a winning game runs)

Every block carries a resolution_rate: for a categorical block the fraction of
its relevant decisions whose card / category actually resolved from the
observation (an unresolved option is card_id None), for a timing block the
fraction of episodes in which the event occurred at all. A block whose winning
split resolves under BAR_RESOLUTION (0.90) is marked barred: the emitter must
not read a seed off a stat that is mostly unobservable. This is the miner's half
of the 0.90 resolution gate; the 0.70 share / 0.80 timing / 0.95 unanimity
emission thresholds live with piece 3.

Pure and cg-free at import, exactly like the selector and the census: the block
extractors take an already-resolved decision stream (from
analysis.replay_trace.iter_resolved_decisions, which resolves options from the
observation alone), and family classification takes injected archetype
signatures. Output is competition-derived, so the machine-readable blocks JSON is
written THROUGH tools.isolation into data/derived/gameplans/ (gitignored); the
committed artifact is the human game-plan doc under analysis/gameplans/, authored
from this tool's summary and carrying only per-family aggregates, never raw
episodes.

Dev tool only; never shipped.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis import expert_cohort as ec  # noqa: E402
from analysis.move_ranking_validator import load_replays  # noqa: E402
from analysis.replay_trace import iter_resolved_decisions  # noqa: E402
from tools.expert_census import build_signatures  # noqa: E402
from tools.isolation import derived_path  # noqa: E402

# A block whose WINNING split resolves below this fraction is barred: the stat is
# mostly unobservable from the replay, so the emitter must not read a seed off it.
BAR_RESOLUTION = 0.90


# --- block extractors -------------------------------------------------------
#
# Each takes one seat's ordered resolved-decision stream (the list
# iter_resolved_decisions yields for that seat in one episode) and returns the
# block's contribution for that episode. Categorical extractors return a LIST of
# values (one per relevant decision; None marks an unresolved card / category).
# Timing extractors return a SINGLE value (the ordinal the event first occurred,
# or None when it never did that episode). All pure, never raise.

def _played_of_category(decisions, category):
    """The played options in `decisions` whose chosen category is `category`."""
    return [d["played"] for d in decisions if d["played"]["category"] == category]


def _opening_category(decisions):
    """The category of the seat's first MAIN decision (None if it made none / OTHER)."""
    if not decisions:
        return []
    cat = decisions[0]["played"]["category"]
    return [cat if cat != "OTHER" else None]


def _attach_targets(decisions):
    """The Pokemon card each ATTACH decision put energy on (None where unresolved).

    resolve_option's card_id for ATTACH is the RECEIVING Pokemon
    (replay_trace.attach_receiver_id), not the energy spent, so this reads as
    "which attacker did the expert power up," the game-plan question.
    """
    return [p["card_id"] for p in _played_of_category(decisions, "ATTACH")]


def _play_targets(decisions):
    """The card each PLAY decision put down (None where unresolved)."""
    return [p["card_id"] for p in _played_of_category(decisions, "PLAY")]


def _evolve_targets(decisions):
    """The card each EVOLVE decision evolved into (None where unresolved)."""
    return [p["card_id"] for p in _played_of_category(decisions, "EVOLVE")]


def _first_ordinal(decisions, category):
    """1-based index of the first `category` decision among `decisions`, or None."""
    for i, d in enumerate(decisions):
        if d["played"]["category"] == category:
            return i + 1
    return None


def _first_attack_ordinal(decisions):
    return _first_ordinal(decisions, "ATTACK")


def _first_evolve_ordinal(decisions):
    return _first_ordinal(decisions, "EVOLVE")


def _turns(decisions):
    """Split one seat's ordered decisions into per-turn sublists.

    A turn ends at its END decision (inclusive); a trailing partial turn (the
    seat's decisions after its last END, e.g. the game ended before it chose to
    end again) is kept as its own turn so no decision is dropped. Pure.
    """
    turns = []
    current = []
    for d in decisions:
        current.append(d)
        if d["played"]["category"] == "END":
            turns.append(current)
            current = []
    if current:
        turns.append(current)
    return turns


def _attach_before_attack(decisions):
    """Per turn with BOTH an ATTACH and an ATTACK, True when ATTACH came first.

    A turn with only one of the two (or neither) contributes nothing: the
    sequencing question only exists when both happened that turn.
    """
    out = []
    for turn in _turns(decisions):
        attach_i = next(
            (i for i, d in enumerate(turn) if d["played"]["category"] == "ATTACH"), None
        )
        attack_i = next(
            (i for i, d in enumerate(turn) if d["played"]["category"] == "ATTACK"), None
        )
        if attach_i is not None and attack_i is not None:
            out.append(attach_i < attack_i)
    return out


def _energy_banking(decisions):
    """Per turn with an ATTACH, True when the seat did NOT also attack that turn.

    "Banking" energy: attaching ahead of an attack instead of only attaching just
    enough to swing immediately. A turn with no ATTACH contributes nothing.
    """
    out = []
    for turn in _turns(decisions):
        has_attach = any(d["played"]["category"] == "ATTACH" for d in turn)
        if not has_attach:
            continue
        has_attack = any(d["played"]["category"] == "ATTACK" for d in turn)
        out.append(not has_attack)
    return out


def _game_length_turns(decisions):
    """Number of turns the seat took this episode, or None with no decisions."""
    if not decisions:
        return None
    return len(_turns(decisions))


CATEGORICAL_BLOCKS = (
    ("opening_category", _opening_category),
    ("attach_target", _attach_targets),
    ("play_target", _play_targets),
    ("evolve_target", _evolve_targets),
    ("attach_before_attack", _attach_before_attack),
    ("energy_banking", _energy_banking),
)

TIMING_BLOCKS = (
    ("first_attack_ordinal", _first_attack_ordinal),
    ("first_evolve_ordinal", _first_evolve_ordinal),
    ("game_length_turns", _game_length_turns),
)


# --- stat folds -------------------------------------------------------------

def categorical_stats(values) -> dict:
    """Fold a list of categorical values (None = unresolved) into a block stat.

    Reports the total count, how many resolved, the resolution_rate, the
    distribution over resolved values, and the modal value with its share OF THE
    RESOLVED decisions. mode_share is the number the emitter tests against its
    0.70 share (or 0.95 unanimity) threshold. Pure, never raises.
    """
    total = len(values)
    resolved = [v for v in values if v is not None]
    dist = Counter(resolved)
    mode, mode_count = dist.most_common(1)[0] if dist else (None, 0)
    n_res = len(resolved)
    return {
        "total": total,
        "resolved": n_res,
        "resolution_rate": (n_res / total) if total else 0.0,
        "distribution": dict(dist),
        "mode": mode,
        "mode_share": (mode_count / n_res) if n_res else 0.0,
    }


def timing_stats(values) -> dict:
    """Fold per-episode ordinals (None = event absent that episode) into a stat.

    Reports episodes considered, how many saw the event (present), the
    resolution_rate (present / episodes), the distribution over the observed
    ordinals, the modal ordinal, and consistency (the modal ordinal's share of
    the episodes that saw the event) -- the number the emitter tests against its
    0.80 timing threshold. Pure, never raises.
    """
    total = len(values)
    present = [v for v in values if v is not None]
    dist = Counter(present)
    mode, mode_count = dist.most_common(1)[0] if dist else (None, 0)
    n = len(present)
    return {
        "episodes": total,
        "present": n,
        "resolution_rate": (n / total) if total else 0.0,
        "distribution": {str(k): v for k, v in dist.items()},
        "mode_ordinal": mode,
        "consistency": (mode_count / n) if n else 0.0,
    }


def mine(episode_streams, keep_raw: bool = False) -> dict:
    """Mine the nine stat blocks over the target family's (won, decisions) streams.

    `episode_streams` is an iterable of (won, decisions) pairs -- one per seat
    appearance of the target family, `won` True when that seat won the episode and
    `decisions` its ordered resolved MAIN decisions. Each block is computed twice,
    over the winning appearances and over the losing ones, so the emitter reads the
    winning-play signal and can contrast it with losses. A block is barred when its
    WINNING split resolves below BAR_RESOLUTION. `keep_raw` additionally stashes each
    block's pre-fold value lists under block["raw"] = {"win": [...], "loss": [...]}
    (default off, so the ordinary seeds pipeline's block shape is unchanged); the
    U91 claim/prediction gates (analysis/gameplan_claim_gate) need those raw values
    to bootstrap a CI, but the committed aggregate docs never read this key. Pure,
    never raises.
    """
    win_cat = {name: [] for name, _ in CATEGORICAL_BLOCKS}
    loss_cat = {name: [] for name, _ in CATEGORICAL_BLOCKS}
    win_tim = {name: [] for name, _ in TIMING_BLOCKS}
    loss_tim = {name: [] for name, _ in TIMING_BLOCKS}
    n_win = 0
    n_loss = 0
    for won, decisions in episode_streams:
        cat_side, tim_side = (win_cat, win_tim) if won else (loss_cat, loss_tim)
        if won:
            n_win += 1
        else:
            n_loss += 1
        for name, fn in CATEGORICAL_BLOCKS:
            cat_side[name].extend(fn(decisions))
        for name, fn in TIMING_BLOCKS:
            tim_side[name].append(fn(decisions))

    blocks = {}
    for name, _ in CATEGORICAL_BLOCKS:
        win = categorical_stats(win_cat[name])
        loss = categorical_stats(loss_cat[name])
        block = {
            "kind": "categorical",
            "win": win,
            "loss": loss,
            "barred": win["resolution_rate"] < BAR_RESOLUTION,
        }
        if keep_raw:
            block["raw"] = {"win": win_cat[name], "loss": loss_cat[name]}
        blocks[name] = block
    for name, _ in TIMING_BLOCKS:
        win = timing_stats(win_tim[name])
        loss = timing_stats(loss_tim[name])
        block = {
            "kind": "timing",
            "win": win,
            "loss": loss,
            "barred": win["resolution_rate"] < BAR_RESOLUTION,
        }
        if keep_raw:
            block["raw"] = {"win": win_tim[name], "loss": loss_tim[name]}
        blocks[name] = block
    return {"episodes_win": n_win, "episodes_loss": n_loss, "blocks": blocks}


# --- live wrappers ----------------------------------------------------------

def episode_family_streams(replay, signatures, target, threshold: float = 0.35):
    """Yield (won, decisions) for each seat in `replay` that played `target`.

    Resolves the winner (expert_cohort.winner_seat) and both openers, classifies
    each seat's family, and for every seat whose family is `target` yields whether
    it won and its ordered resolved MAIN decisions. Losing appearances are included
    (unlike the census, which credits only the winner) so a block can contrast
    winning and losing play of the same deck. A draw or an unreadable opener yields
    nothing. Pure, never raises.
    """
    seat = ec.winner_seat(replay)
    if seat is None:
        return
    decks = ec.seat_decklists(replay)
    if decks is None:
        return
    for s in (0, 1):
        if ec.classify_family(decks[s], signatures, threshold) != target:
            continue
        yield (s == seat, list(iter_resolved_decisions(replay, s)))


def run_mine(
    source, signatures, target, threshold: float = 0.35, limit=None, keep_raw: bool = False
) -> dict:
    """Mine the target family's game plan over every episode in `source`."""
    def streams():
        for replay, _label in load_replays(source, limit=limit):
            yield from episode_family_streams(replay, signatures, target, threshold)

    return mine(streams(), keep_raw=keep_raw)


def _print_summary(target, result) -> None:
    print(f"target family: {target}")
    print(
        f"appearances: {result['episodes_win']} winning, "
        f"{result['episodes_loss']} losing"
    )
    print(f"\nblocks (bar resolution {BAR_RESOLUTION:.2f}):")
    for name, block in result["blocks"].items():
        win = block["win"]
        bar = " BARRED" if block["barred"] else ""
        if block["kind"] == "categorical":
            print(
                f"  {name:<20} res={win['resolution_rate']:.3f} "
                f"mode={win['mode']} share={win['mode_share']:.3f}{bar}"
            )
        else:
            print(
                f"  {name:<20} res={win['resolution_rate']:.3f} "
                f"ord={win['mode_ordinal']} consistency={win['consistency']:.3f}{bar}"
            )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "source",
        help="a .zip of episode JSONs or a directory of *.json replays",
    )
    ap.add_argument(
        "target",
        help="the archetype family to mine (e.g. meta_grimmsnarl)",
    )
    ap.add_argument(
        "--decks-dir",
        default=None,
        help="optional directory of extra archetype .csv decklists to classify against",
    )
    ap.add_argument(
        "--threshold",
        type=float,
        default=0.35,
        help="minimum signature coverage to assign a deck to a family",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        help="cap episodes read (default: the whole dataset)",
    )
    ap.add_argument(
        "--out",
        default="gameplan_blocks.json",
        help="blocks JSON filename under data/derived/gameplans/ (isolated)",
    )
    args = ap.parse_args(argv)

    signatures = build_signatures(args.decks_dir)
    result = run_mine(
        args.source, signatures, args.target, args.threshold, limit=args.limit
    )
    _print_summary(args.target, result)

    payload = {
        "target_family": args.target,
        "threshold": args.threshold,
        "bar_resolution": BAR_RESOLUTION,
        **result,
    }
    out = derived_path("gameplans", args.out)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nblocks written (isolated): {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
