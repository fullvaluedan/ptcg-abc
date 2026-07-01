"""Held-out move-ranking validator: does a candidate pilot play like the top players?

This is the anti-overfit filter the self-improvement engine needs (plan U5). The
project already lived the finding that offline metrics do not transfer to the
ladder: a candidate can win self-play and still be a self-beater that ranks the
real field's moves poorly. Optimizing against ourselves manufactures exactly that
overfit. This validator scores a candidate against the ONE distribution we cannot
fake, the top players' actual recorded decisions, so a slot is never spent on a
build that wins in the mirror but does not resemble a strong pilot on real states.

Mechanism. Each episode in the 5734-game dataset is a Kaggle replay with a
top-level `steps` list. Every step holds one record per seat; the ACTIVE seat's
record carries the `observation` it decided on and the `action` (a list of option
indices) it actually played, in exactly the shape our pilot's `choose(obs)`
consumes and returns. So for each real MAIN, single-pick, multi-option decision an
expert seat made, we run the candidate pilot on the same observation and check
whether it picks the option the expert actually played. The aggregate top-1
agreement over held-out expert decisions is the score: a pilot that plays like the
top players scores high; an overfit self-beater scores low.

Scope of the metric. `choose(obs)` returns only its single best option (an argmax),
not a full ranking, so this measures top-1 agreement (k=1), the honest metric for
an argmax pilot. A mean-rank / top-k version needs a pilot that exposes a score per
option; that arrives with the weight-parameterized pilot (plan U6) and can extend
this module without changing the top-1 path. Exact-index agreement is strict (many
options are near-equivalent), so the number matters as a RELATIVE filter comparing
candidate pilots on a fixed held-out set, not as an absolute skill measure.

Everything here is pure and defensive over the raw replay dict: a malformed step,
a missing observation, or an out-of-range action is skipped, never fatal, so a
batch over thousands of real games never aborts on one bad record. It reads the
competition dataset but never redistributes it (the replay files stay gitignored).
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# SelectType.MAIN (api.py SelectType enum): the once-per-turn top-level decision
# where the pilot chooses among ATTACH / PLAY / EVOLVE / RETREAT / ATTACK / END.
# Kept local so the validator has no import-time dependency on the pilot module and
# can score any choose-like callable.
SEL_MAIN = 0

# OptionType (api.py OptionType enum) values that can appear at a MAIN decision,
# mapped to the action category name. Kept local for the same reason SEL_MAIN is:
# the validator stays independent of the pilot module. A MAIN option's `type` field
# names the KIND of action, so labeling both the option the expert played and the
# one our pilot chose turns a raw disagreement into a map of WHERE the pilot
# diverges (e.g. the expert ATTACHes but our pilot ENDs the turn).
OPT_CATEGORY = {
    7: "PLAY",
    8: "ATTACH",
    9: "EVOLVE",
    10: "ABILITY",
    12: "RETREAT",
    13: "ATTACK",
    14: "END",
}


def team_seat(replay, expert_teams) -> int | None:
    """Seat index (0 or 1) whose team name is in `expert_teams`, or None.

    A replay records the two competitors in `info.TeamNames`, seat-ordered. We only
    want to score decisions made by a strong pilot, so this maps the caller's set of
    expert handles to the seat they played. Returns None when neither seat (or both)
    match, so an episode with no clear single expert seat is skipped rather than
    scored against an unknown pilot. Pure, never raises.
    """
    try:
        names = ((replay.get("info") or {}).get("TeamNames")) or []
    except AttributeError:
        return None
    if not isinstance(names, (list, tuple)) or len(names) < 2:
        return None
    wanted = {str(t) for t in expert_teams}
    matches = [i for i in (0, 1) if str(names[i]) in wanted]
    return matches[0] if len(matches) == 1 else None


def _played_index(action) -> int | None:
    """The single option index an expert played, or None when it is not a single pick.

    A MAIN decision records the action as a list of chosen option indices. We only
    compare single-pick decisions (the ones our argmax pilot also answers with one
    index), so anything but a one-element list of a non-negative int is skipped.
    """
    if not isinstance(action, (list, tuple)) or len(action) != 1:
        return None
    idx = action[0]
    if isinstance(idx, bool) or not isinstance(idx, int) or idx < 0:
        return None
    return idx


def iter_expert_decisions(replay, expert_index):
    """Yield (obs, played_index) for each scorable MAIN decision by `expert_index`.

    A scorable decision mirrors the search-activity definition: the expert seat is
    ACTIVE, the select is a MAIN single-pick among more than one option, and the
    recorded action is a single in-range option index. The observation is yielded
    unchanged so a candidate `choose(obs)` decides on the exact real state. Mirrors
    the ACTIVE / select / current gating in loss_classifier.parse_replay so the two
    read the same decisions. Pure and defensive: a malformed step is skipped.
    """
    steps = replay.get("steps") or []
    for step in steps:
        if not isinstance(step, (list, tuple)):
            continue
        for entry in step:
            if not isinstance(entry, dict) or entry.get("status") != "ACTIVE":
                continue
            obs = entry.get("observation") or {}
            sel = obs.get("select")
            current = obs.get("current")
            if sel is None or current is None:
                continue
            if current.get("yourIndex", None) != expert_index:
                continue
            if sel.get("type") != SEL_MAIN:
                continue
            if sel.get("minCount", 1) != 1 or sel.get("maxCount", 1) != 1:
                continue
            options = sel.get("option") or []
            if len(options) <= 1:
                continue
            idx = _played_index(entry.get("action"))
            if idx is None or idx >= len(options):
                continue
            yield obs, idx


def agreement(replay, pilot_choose, expert_index) -> dict:
    """Top-1 agreement of a candidate pilot with one expert seat on one replay.

    Runs `pilot_choose(obs)` on each scorable expert decision and counts the ones
    where the pilot's single chosen index equals the option the expert played. A
    pilot that raises or returns a non-single-index answer on a decision counts as a
    non-match rather than aborting the batch, so one flaky state never voids a game.
    Returns {"n": decisions scored, "agree": matches, "agreement": ratio or None}.
    """
    n = 0
    agree = 0
    for obs, played in iter_expert_decisions(replay, expert_index):
        n += 1
        try:
            choice = pilot_choose(obs)
        except Exception:
            continue
        if isinstance(choice, (list, tuple)) and len(choice) == 1 and choice[0] == played:
            agree += 1
    return {"n": n, "agree": agree, "agreement": (agree / n) if n else None}


def _option_category(sel, index) -> str:
    """Action category name of option `index` in a MAIN select.

    Reads the option's OptionType and maps it through OPT_CATEGORY, so a decision
    can be bucketed by what KIND of action was chosen. An out-of-range index or a
    non-dict / unknown-type option maps to "OTHER" rather than raising, so one odd
    record never aborts a batch. Pure.
    """
    options = sel.get("option") or []
    if not isinstance(index, int) or isinstance(index, bool):
        return "OTHER"
    if not (0 <= index < len(options)):
        return "OTHER"
    opt = options[index]
    if not isinstance(opt, dict):
        return "OTHER"
    return OPT_CATEGORY.get(opt.get("type"), "OTHER")


def decision_categories(replay, pilot_choose, expert_index):
    """Yield (expert_category, pilot_category, agree) per scorable MAIN decision.

    For each real expert decision, run the candidate pilot on the same observation
    and label BOTH the option the expert played and the one the pilot chose by their
    action category. A pilot that raises or returns a non-single-index answer labels
    its choice "NONE" (agree False) so the decision still contributes an
    (expert, NONE) row rather than aborting the batch. This turns the pooled top-1
    agreement number into a category-level map of WHERE the pilot diverges from the
    top players. Pure and defensive.
    """
    for obs, played in iter_expert_decisions(replay, expert_index):
        sel = obs.get("select") or {}
        expert_cat = _option_category(sel, played)
        try:
            choice = pilot_choose(obs)
        except Exception:
            choice = None
        if (
            isinstance(choice, (list, tuple))
            and len(choice) == 1
            and isinstance(choice[0], int)
            and not isinstance(choice[0], bool)
        ):
            pilot_idx = choice[0]
            yield expert_cat, _option_category(sel, pilot_idx), pilot_idx == played
        else:
            yield expert_cat, "NONE", False


def category_confusion(replays, pilot_choose, expert_teams) -> dict:
    """Confusion of expert action category vs the candidate pilot's, over replays.

    Aggregates decision_categories over an iterable of (replay, label) pairs, using
    the same expert-seat resolution as score_replays (a replay with no single expert
    seat is skipped). Returns, per expert action category, the number of decisions
    and how often the pilot agreed, plus the full (expert_cat -> {pilot_cat: count})
    substitution matrix. A caller can read both the per-category agreement rate (which
    kind of decision our pilot gets right or wrong relative to the top players) and
    the dominant substitution it makes on the ones it misses. Pure, never raises.
    """
    by_expert = {}
    matrix = {}
    episodes = 0
    skipped = 0
    for replay, _label in replays:
        seat = team_seat(replay, expert_teams)
        if seat is None:
            skipped += 1
            continue
        episodes += 1
        for expert_cat, pilot_cat, agree in decision_categories(
            replay, pilot_choose, seat
        ):
            row = by_expert.setdefault(expert_cat, {"n": 0, "agree": 0})
            row["n"] += 1
            if agree:
                row["agree"] += 1
            cell = matrix.setdefault(expert_cat, {})
            cell[pilot_cat] = cell.get(pilot_cat, 0) + 1
    total_n = sum(r["n"] for r in by_expert.values())
    total_agree = sum(r["agree"] for r in by_expert.values())
    return {
        "episodes": episodes,
        "skipped": skipped,
        "n": total_n,
        "agree": total_agree,
        "agreement": (total_agree / total_n) if total_n else None,
        "by_expert": by_expert,
        "matrix": matrix,
    }


def score_replays(replays, pilot_choose, expert_teams) -> dict:
    """Aggregate top-1 agreement over an iterable of (replay, source-label) pairs.

    For each replay the expert seat is resolved from `info.TeamNames`; a replay with
    no single expert seat is skipped (counted in `skipped`). Returns the pooled
    agreement plus per-episode rows, so a caller can see both the headline filter
    number and which games contributed. Pure over the inputs, never raises.
    """
    total_n = 0
    total_agree = 0
    skipped = 0
    rows = []
    for replay, label in replays:
        seat = team_seat(replay, expert_teams)
        if seat is None:
            skipped += 1
            continue
        res = agreement(replay, pilot_choose, seat)
        total_n += res["n"]
        total_agree += res["agree"]
        rows.append({"episode": label, "seat": seat, **res})
    return {
        "episodes": len(rows),
        "skipped": skipped,
        "n": total_n,
        "agree": total_agree,
        "agreement": (total_agree / total_n) if total_n else None,
        "rows": rows,
    }


def _load_json(text):
    """Parse a replay JSON string, or None on any failure. Never raises."""
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return None


def load_replays(source, limit=None):
    """Yield (replay_dict, label) from a zip of episode JSONs or a directory of them.

    Accepts either a `.zip` (each member an `<episode>.json`) or a directory holding
    `*.json` replay files, so the same validator runs over the shipped dataset zip
    without extracting 21 GB and over a small extracted sample in a test. A member
    that is not valid JSON is skipped. `limit` caps how many replays are yielded so a
    CLI run stays bounded. Non-replay members (a manifest.csv) are ignored.
    """
    src = Path(source)
    count = 0
    if src.is_dir():
        for path in sorted(src.glob("*.json")):
            if limit is not None and count >= limit:
                return
            rep = _load_json(path.read_text(encoding="utf-8"))
            if rep is not None:
                count += 1
                yield rep, path.name
        return
    if src.suffix == ".zip" and src.exists():
        with zipfile.ZipFile(src) as zf:
            for name in zf.namelist():
                if not name.endswith(".json"):
                    continue
                if limit is not None and count >= limit:
                    return
                rep = _load_json(zf.read(name).decode("utf-8"))
                if rep is not None:
                    count += 1
                    yield rep, name


# Top-player handles seen in the harvested dataset and named in the ladder study as
# the strong aggro pilots whose bench discipline and prize racing we are trying to
# learn from (see LOOP_BRIEF.md and analysis/meta.md). The set is a default; the CLI
# takes --teams to override, and the validator is agnostic to the exact names.
DEFAULT_EXPERT_TEAMS = (
    "kazuki0123",
    "tonakaiiii",
    "The Debauchery Tea Party",
)


def _default_pilot():
    """The current deployable pilot's choose(), imported lazily so tests stay light.

    Importing the pilot pulls in the card-data path (cg.api), which is only present
    for a real dataset run; unit tests pass their own callable and never hit this.
    """
    from agents.heuristics import choose

    return choose


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "source",
        help="a .zip of episode JSONs or a directory of *.json replays",
    )
    ap.add_argument(
        "--teams",
        nargs="+",
        default=list(DEFAULT_EXPERT_TEAMS),
        help="expert team names whose seat's decisions are scored",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=200,
        help="max replays to read (keeps a dataset run bounded)",
    )
    ap.add_argument(
        "--per-episode",
        action="store_true",
        help="print the per-episode agreement rows too",
    )
    ap.add_argument(
        "--breakdown",
        action="store_true",
        help="print the per-category agreement and the expert-vs-pilot substitution "
        "matrix (where the pilot diverges from the top players)",
    )
    args = ap.parse_args(argv)

    pilot = _default_pilot()
    if args.breakdown:
        conf = category_confusion(
            load_replays(args.source, limit=args.limit), pilot, args.teams
        )
        agr = conf["agreement"]
        print(f"expert teams: {', '.join(args.teams)}")
        print(f"episodes scored: {conf['episodes']} (skipped {conf['skipped']})")
        print(f"expert decisions: {conf['n']}")
        print(
            f"top-1 agreement: {agr:.3f}" if agr is not None else "top-1 agreement: n/a"
        )
        print("\nper expert action category (decisions, our agreement):")
        for cat in sorted(conf["by_expert"], key=lambda c: -conf["by_expert"][c]["n"]):
            row = conf["by_expert"][cat]
            rate = row["agree"] / row["n"] if row["n"] else 0.0
            print(f"  {cat:<8} n={row['n']:<5} agree={row['agree']:<5} ({rate:.3f})")
        print("\nexpert chose -> our pilot chose (on all decisions):")
        for cat in sorted(conf["matrix"], key=lambda c: -conf["by_expert"][c]["n"]):
            subs = conf["matrix"][cat]
            parts = ", ".join(
                f"{k}:{subs[k]}" for k in sorted(subs, key=lambda k: -subs[k])
            )
            print(f"  {cat:<8} -> {parts}")
        return 0

    result = score_replays(
        load_replays(args.source, limit=args.limit), pilot, args.teams
    )
    agr = result["agreement"]
    print(f"expert teams: {', '.join(args.teams)}")
    print(f"episodes scored: {result['episodes']} (skipped {result['skipped']})")
    print(f"expert decisions: {result['n']}")
    print(f"top-1 agreement: {agr:.3f}" if agr is not None else "top-1 agreement: n/a")
    if args.per_episode:
        for row in result["rows"]:
            r = row["agreement"]
            rstr = f"{r:.3f}" if r is not None else "n/a"
            print(f"  {row['episode']} seat {row['seat']}: {row['agree']}/{row['n']} ({rstr})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
