"""S2 (plan analysis/path_above_1000.md): endgame PLAY-category divergence at scale.

The 2026-07-11 audit's proof of concept found, ad hoc: with the SHIPPED flags live
(PTCG_ABILITY and PTCG_THREAT_RETREAT both on), PLAY-category agreement with expert
choices drops 10.9pp in near-endgame states and accounts for 41% of all close-game
disagreement (1082 games, 33,295 expert decisions, 131s, one core; no script was
committed). This module reproduces that reading at scale over the full top-50
harvest (data/derived/top50_harvest.json, tools/top50_harvest.py) and extends it
into a phase-by-category agreement table plus the top concrete near-endgame PLAY
divergence patterns a rule designer can act on.

Method. For every W/L game each top-50 team harvested, resolve the team's own seat
(analysis.replay_trace.team_seat against the replay's info.TeamNames) and walk
analysis.replay_trace.iter_resolved_decisions over that seat: the shared spine every
imitation unit in this repo reads (move_ranking_validator, gameplan_mine,
top50_win_mechanisms). For each scorable MAIN decision this yields the option the
expert actually played (resolved to its category and card/attack) and every legal
option resolved the same way. Separately, agents.heuristics.choose(obs) is run on
the SAME observation with _ABILITY and _THREAT_RETREAT patched True for exactly that
one call (module-attribute patching, restored in a finally, fresh consideration per
decision: the same monkeypatch pattern tools/threat_retreat_ring_check.py and
tools/stacked_ring_u104.py use, necessary because both flags are module constants
read once from the environment at import time, agents/heuristics.py's own flag
comment). Agreement is exact-option-index match, the same definition
analysis.move_ranking_validator.category_confusion already uses, bucketed by the
EXPERT's action category so "PLAY-category agreement" means: of the decisions where
the expert chose to PLAY a card, how often did our pilot's own top-1 choice land on
that exact option.

Game phase (early / mid / near_endgame) is read from the expert's own prize counts
at decision time (both sides' remaining prize count, from the same observation):

  near_endgame: min(prize_me, prize_opp) <= 2   (either side 2 or fewer prizes left,
                                                  the plan's own near-endgame definition)
  early:        min(prize_me, prize_opp) >= 5   (neither side has taken more than
                                                  one prize yet)
  mid:          everything else (min in {3, 4})

This is a monotonic three-way split on one integer with no gap and no overlap; the
early/mid boundary is this module's own choice (the plan specifies near_endgame
precisely but not the other two), documented here rather than left implicit.

Reliability caveat (analysis/replay_trace.py's own module docstring; also
tools/top50_win_mechanisms.py and tools/top50_loss_modes.py carry it).
iter_resolved_decisions only yields a decision with 2+ legal options; a turn where
one category is the ONLY legal action never appears in this stream at all. This
under-counts ATTACK specifically and structurally more than PLAY: an attack-only
turn (no other legal MAIN option once resources are spent) is common late in a
turn and invisible here, while a PLAY decision is very rarely the sole legal
option (END is almost always also on offer). ATTACK-category rows in the table
below should be read as a directional lower bound, not an exact count; PLAY rows
are comparatively complete. Deck-level and win/loss facts are never derived from
this stream and are unaffected.

Dev tool only, never shipped. Reads data/episodes/*.zip (gitignored competition
data) but writes only aggregated, redistributable derived output (JSON to
data/derived/, gitignored like every other derived JSON in this repo; the markdown
summary is the committed artifact), the same convention every other top50_* tool
in this repo follows.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Same import-order pin tools/threat_retreat_ring_check.py and tools/top50_ring.py
# document and rely on: our agents/ package must be cached under the bare name
# "agents" before anything below can trigger kaggle_environments' own env-local
# agents.py, or later `from agents import heuristics` calls silently resolve to
# the wrong module.
from agents import heuristics as _heuristics  # noqa: E402,F401

from analysis.replay_trace import iter_resolved_decisions, team_seat  # noqa: E402
from tools.top50_harvest import all_dumps  # noqa: E402
from tools.top50_loss_modes import build_episode_index  # noqa: E402
from tools.top_player_tracker import DEFAULT_EPISODES_DIR  # noqa: E402

DEFAULT_HARVEST = _ROOT / "data" / "derived" / "top50_harvest.json"
DEFAULT_OUT_JSON = _ROOT / "data" / "derived" / "endgame_divergence.json"
DEFAULT_OUT_MD = _ROOT / "analysis" / "endgame_divergence.md"

NEAR_ENDGAME_MAX_PRIZE = 2
EARLY_MIN_PRIZE = 5
TOP_N_PATTERNS = 10
CATEGORY_ORDER = ("PLAY", "ATTACH", "EVOLVE", "ABILITY", "RETREAT", "ATTACK", "END", "OTHER")
PHASE_ORDER = ("early", "mid", "near_endgame")


# --- pure state / phase reads (hermetically tested, no cg) ------------------

def phase_of(prize_me, prize_opp) -> str:
    """early / mid / near_endgame / unknown from both sides' remaining prizes.

    near_endgame when either side is at or below NEAR_ENDGAME_MAX_PRIZE (the
    plan's own definition); early when neither side has taken more than one
    prize (min >= EARLY_MIN_PRIZE); mid otherwise. "unknown" only when a prize
    count is missing, so a malformed record is never silently misbucketed.
    """
    if (not isinstance(prize_me, int) or isinstance(prize_me, bool)
            or not isinstance(prize_opp, int) or isinstance(prize_opp, bool)):
        return "unknown"
    lo = min(prize_me, prize_opp)
    if lo <= NEAR_ENDGAME_MAX_PRIZE:
        return "near_endgame"
    if lo >= EARLY_MIN_PRIZE:
        return "early"
    return "mid"


def state_of(obs) -> dict:
    """hand_size, bench_count, prize_me, prize_opp, deck_count for the deciding
    seat, read from obs["current"]["players"][yourIndex] (the same seat the
    observation was already generated for). Any missing piece reads as None
    rather than raising.
    """
    current = obs.get("current") if isinstance(obs, dict) else None
    current = current if isinstance(current, dict) else {}
    yi = current.get("yourIndex")
    players = current.get("players") or []
    if not isinstance(yi, int) or isinstance(yi, bool) or not (0 <= yi < len(players)):
        return {"hand_size": None, "bench_count": None, "prize_me": None,
                "prize_opp": None, "deck_count": None}
    me = players[yi] if isinstance(players[yi], dict) else {}
    opp_i = 1 - yi
    opp = players[opp_i] if 0 <= opp_i < len(players) and isinstance(players[opp_i], dict) else {}
    hand = me.get("hand")
    bench = me.get("bench")
    prize_me = me.get("prize")
    prize_opp = opp.get("prize")
    return {
        "hand_size": len(hand) if isinstance(hand, list) else None,
        "bench_count": len(bench) if isinstance(bench, list) else None,
        "prize_me": len(prize_me) if isinstance(prize_me, list) else None,
        "prize_opp": len(prize_opp) if isinstance(prize_opp, list) else None,
        "deck_count": me.get("deckCount"),
    }


def describe_choice(resolved, card_index_map, attack_index_map) -> str:
    """Human-readable "category card/attack name" for a resolve_option() result.

    ATTACK names the attack (its card_id is the attacker, not what a rule
    designer wants read out); everything else with a card_id names that card.
    A missing lookup falls back to "card:<id>" / "attack:<id>" (never raises),
    same fallback convention tools/top50_win_mechanisms.py uses. None (no legal
    pilot answer) reads as "NONE".
    """
    if not isinstance(resolved, dict):
        return "NONE"
    cat = resolved.get("category") or "OTHER"
    if cat == "ATTACK":
        aid = resolved.get("attack_id")
        if aid is None:
            return "ATTACK"
        atk = attack_index_map.get(aid)
        return f"ATTACK {atk.name}" if atk is not None else f"ATTACK attack:{aid}"
    cid = resolved.get("card_id")
    if cid is None:
        return cat
    card = card_index_map.get(cid)
    name = card.name if card is not None else f"card:{cid}"
    return f"{cat} {name}"


def median_signature(rows: list) -> str:
    """A representative "hand=.. bench=.. prizes us=../opp=.. deck=.." string:
    the median of each state field across the rows sharing one divergence
    pattern, so a repeated pattern reads as one typical state, not N raw ones.
    """
    def med(field):
        vals = [r[field] for r in rows if r.get(field) is not None]
        return round(statistics.median(vals), 1) if vals else None

    hs, bc = med("hand_size"), med("bench_count")
    pm, po = med("prize_me"), med("prize_opp")
    dc = med("deck_count")
    return (f"hand={hs}, bench={bc}, prizes us={pm}/opp={po}, deck={dc} "
            f"(median, n={len(rows)})")


# --- the live pilot call (needs cg / agents.heuristics) ----------------------

def our_choice_index(obs):
    """The option index agents.heuristics.choose(obs) picks with SHIPPED flags
    (_ABILITY, _THREAT_RETREAT) patched True for exactly this call, restored in
    a finally. Fresh consideration per decision, mirroring
    tools/threat_retreat_ring_check.py's _make_agent_factory pattern but as a
    bare function (no ring, no deck pinning: the decision's own obs already
    fixes the deck and board state). Returns None on any pilot exception or a
    non-single-index answer, never raises.
    """
    from agents import heuristics as H

    orig_ability = H._ABILITY
    orig_threat = H._THREAT_RETREAT
    H._ABILITY = True
    H._THREAT_RETREAT = True
    try:
        choice = H.choose(obs)
    except Exception:  # noqa: BLE001 - one flaky state must not abort the batch
        choice = None
    finally:
        H._ABILITY = orig_ability
        H._THREAT_RETREAT = orig_threat
    if (isinstance(choice, (list, tuple)) and len(choice) == 1
            and isinstance(choice[0], int) and not isinstance(choice[0], bool)):
        return choice[0]
    return None


def build_decision_record(rec: dict, card_index_map: dict, attack_index_map: dict) -> dict:
    """One row for the aggregator: phase, expert/our category+description,
    whether they agree (exact option index), and the observable state.
    `rec` is one analysis.replay_trace.iter_resolved_decisions record.
    """
    obs = rec["obs"]
    st = state_of(obs)
    phase = phase_of(st["prize_me"], st["prize_opp"])
    expert = rec["played"] or {}
    options = rec["options"] or []
    our_idx = our_choice_index(obs)
    our_resolved = (options[our_idx]
                     if isinstance(our_idx, int) and 0 <= our_idx < len(options) else None)
    return {
        "phase": phase,
        "expert_category": expert.get("category") or "OTHER",
        "our_category": (our_resolved or {}).get("category") or "NONE",
        "agree": our_idx is not None and our_idx == rec["played_index"],
        "expert_desc": describe_choice(expert, card_index_map, attack_index_map),
        "our_desc": describe_choice(our_resolved, card_index_map, attack_index_map),
        "hand_size": st["hand_size"],
        "bench_count": st["bench_count"],
        "prize_me": st["prize_me"],
        "prize_opp": st["prize_opp"],
        "deck_count": st["deck_count"],
    }


# --- aggregation (pure, hermetically tested) ---------------------------------

def aggregate(records: list) -> dict:
    """Phase x expert-category agreement table, PLAY-specific summary numbers,
    and the top near-endgame PLAY divergence patterns. Pure over already-built
    decision records (build_decision_record); no cg, no replay reading, no
    live pilot call, so this is the one function tested hermetically.
    """
    table = defaultdict(lambda: {"n": 0, "agree": 0})
    phase_totals = defaultdict(lambda: {"n": 0, "agree": 0})
    for r in records:
        cell = table[(r["phase"], r["expert_category"])]
        cell["n"] += 1
        cell["agree"] += int(r["agree"])
        pt = phase_totals[r["phase"]]
        pt["n"] += 1
        pt["agree"] += int(r["agree"])

    def rate(row):
        return (row["agree"] / row["n"]) if row["n"] else None

    play_by_phase = {phase: dict(table.get((phase, "PLAY"), {"n": 0, "agree": 0}))
                      for phase in PHASE_ORDER}
    overall_play = {"n": sum(v["n"] for v in play_by_phase.values()),
                     "agree": sum(v["agree"] for v in play_by_phase.values())}
    near_endgame_play = play_by_phase["near_endgame"]

    near_endgame_totals = phase_totals.get("near_endgame", {"n": 0, "agree": 0})
    near_endgame_disagreements = near_endgame_totals["n"] - near_endgame_totals["agree"]
    near_endgame_play_disagreements = near_endgame_play["n"] - near_endgame_play["agree"]
    play_share_of_near_endgame_disagreement = (
        (near_endgame_play_disagreements / near_endgame_disagreements)
        if near_endgame_disagreements else None
    )

    pattern_rows = defaultdict(list)
    for r in records:
        if r["phase"] == "near_endgame" and r["expert_category"] == "PLAY" and not r["agree"]:
            pattern_rows[(r["expert_desc"], r["our_desc"])].append(r)

    patterns = []
    for (expert_desc, our_desc), rows in pattern_rows.items():
        patterns.append({
            "expert_did": expert_desc,
            "we_would_do": our_desc,
            "count": len(rows),
            "state_signature": median_signature(rows),
        })
    patterns.sort(key=lambda p: (-p["count"], p["expert_did"], p["we_would_do"]))

    total_n = sum(v["n"] for v in phase_totals.values())
    total_agree = sum(v["agree"] for v in phase_totals.values())

    return {
        "table": {
            phase: {
                cat: {**table.get((phase, cat), {"n": 0, "agree": 0}),
                      "agreement": rate(table.get((phase, cat), {"n": 0, "agree": 0}))}
                for cat in CATEGORY_ORDER if table.get((phase, cat), {"n": 0})["n"]
            }
            for phase in PHASE_ORDER
        },
        "phase_totals": {phase: {**phase_totals.get(phase, {"n": 0, "agree": 0}),
                                  "agreement": rate(phase_totals.get(phase, {"n": 0, "agree": 0}))}
                          for phase in PHASE_ORDER},
        "overall_play": {**overall_play, "agreement": rate(overall_play)},
        "near_endgame_play": {**near_endgame_play, "agreement": rate(near_endgame_play)},
        "play_agreement_drop_pp": (
            (rate(overall_play) - rate(near_endgame_play)) * 100.0
            if rate(overall_play) is not None and rate(near_endgame_play) is not None else None
        ),
        "near_endgame_disagreements_total": near_endgame_disagreements,
        "near_endgame_play_disagreements": near_endgame_play_disagreements,
        "play_share_of_near_endgame_disagreement": play_share_of_near_endgame_disagreement,
        "total_n": total_n,
        "total_agree": total_agree,
        "overall_agreement": rate({"n": total_n, "agree": total_agree}),
        "top_patterns": patterns[:TOP_N_PATTERNS],
        "distinct_near_endgame_play_divergence_patterns": len(patterns),
    }


# --- top-50 harvest walk (needs cg / episode dumps) --------------------------

def build(harvest_path=DEFAULT_HARVEST, episodes_dir=None, limit_games=None) -> dict:
    """Walk every harvested top-50 W/L game, build one decision record per
    scorable MAIN decision, and return aggregate() plus a meta block.
    """
    from agents.heuristics import attack_index, card_index

    harvest = json.loads(Path(harvest_path).read_text(encoding="utf-8"))
    card_index_map = card_index()
    attack_index_map = attack_index()

    dumps = all_dumps(episodes_dir or DEFAULT_EPISODES_DIR)
    ep_index = build_episode_index(dumps)

    games = []
    for t in harvest.get("teams") or []:
        team = t.get("team")
        for g in t.get("games") or []:
            if g.get("result") in ("W", "L"):
                games.append((g.get("episode_id"), team))
    if limit_games is not None:
        games = games[:limit_games]

    records = []
    errors = []
    games_scored = 0
    dump_cache = {}
    try:
        for eid, team in games:
            dump = ep_index.get(eid)
            if dump is None:
                errors.append({"episode_id": eid, "reason": "episode not found in any dump"})
                continue
            zf = dump_cache.get(dump)
            if zf is None:
                zf = zipfile.ZipFile(dump)
                dump_cache[dump] = zf
            try:
                replay = json.loads(zf.read(f"{eid}.json"))
            except Exception as exc:  # noqa: BLE001 - one bad member must not abort the batch
                errors.append({"episode_id": eid, "reason": f"read/parse failed: {exc}"})
                continue
            seat = team_seat(replay, {team})
            if seat is None:
                errors.append({"episode_id": eid, "reason": "team seat not resolved in replay"})
                continue
            before = len(records)
            for rec in iter_resolved_decisions(replay, seat):
                records.append(build_decision_record(rec, card_index_map, attack_index_map))
            if len(records) > before:
                games_scored += 1
    finally:
        for zf in dump_cache.values():
            zf.close()

    result = aggregate(records)
    result["meta"] = {
        "harvest_path": str(harvest_path),
        "harvest_generated_at": harvest.get("meta", {}).get("generated_at"),
        "games_considered": len(games),
        "games_scored": games_scored,
        "episodes_unresolved": len(errors),
    }
    result["errors"] = errors
    return result


# --- markdown report -----------------------------------------------------

def _pct(x):
    return f"{x:.1%}" if x is not None else "n/a"


def format_summary(result: dict) -> str:
    meta = result["meta"]
    lines = [
        "# Endgame PLAY-category divergence at scale (plan S2)",
        "",
        f"Source: `data/derived/top50_harvest.json` "
        f"({meta['games_considered']} harvested top-50 W/L games considered, "
        f"{meta['games_scored']} scored against their episode JSON, "
        f"{meta['episodes_unresolved']} unresolved). Generated by "
        "`tools/endgame_divergence.py`. Every decision is a scorable MAIN pick "
        "from `analysis.replay_trace.iter_resolved_decisions`, and our pilot's "
        "answer on the identical observation is `agents.heuristics.choose` with "
        "`_ABILITY` and `_THREAT_RETREAT` patched True for that one call (the "
        "SHIPPED flags), fresh per decision.",
        "",
        f"**Total scorable decisions: {result['total_n']}. "
        f"Overall top-1 agreement: {_pct(result['overall_agreement'])} "
        f"({result['total_agree']}/{result['total_n']}).**",
        "",
        "## Headline: the PLAY / near-endgame gap",
        "",
        f"- Overall PLAY-category agreement (all phases pooled): "
        f"**{_pct(result['overall_play']['agreement'])}** "
        f"({result['overall_play']['agree']}/{result['overall_play']['n']}).",
        f"- Near-endgame PLAY-category agreement (either side at or below "
        f"{NEAR_ENDGAME_MAX_PRIZE} prizes): "
        f"**{_pct(result['near_endgame_play']['agreement'])}** "
        f"({result['near_endgame_play']['agree']}/{result['near_endgame_play']['n']}).",
        f"- Drop: **{result['play_agreement_drop_pp']:+.1f}pp** "
        "(overall minus near-endgame; the 2026-07-11 proof of concept read "
        "10.9pp on a smaller, non-committed run)." if result['play_agreement_drop_pp'] is not None
        else "- Drop: n/a (insufficient near-endgame PLAY decisions).",
        f"- Of {result['near_endgame_disagreements_total']} total near-endgame "
        f"disagreements (all categories), {result['near_endgame_play_disagreements']} "
        f"are PLAY-category: **{_pct(result['play_share_of_near_endgame_disagreement'])}** "
        "of all close-game disagreement (the proof of concept read 41%).",
        "",
        "## Agreement by category, split by game phase",
        "",
        "Phase is read from the expert's own prize counts at decision time: "
        f"`near_endgame` = either side at or below {NEAR_ENDGAME_MAX_PRIZE} prizes "
        f"remaining; `early` = neither side has taken more than one prize "
        f"(min prizes >= {EARLY_MIN_PRIZE}); `mid` = everything between. "
        "Agreement is exact-option-index match (the same definition "
        "`analysis.move_ranking_validator.category_confusion` uses), bucketed by "
        "the EXPERT's chosen category.",
        "",
        "| phase | category | n | agree | agreement |",
        "|---|---|---|---|---|",
    ]
    for phase in PHASE_ORDER:
        pt = result["phase_totals"][phase]
        lines.append(f"| **{phase}** | **all** | **{pt['n']}** | **{pt['agree']}** | "
                      f"**{_pct(pt['agreement'])}** |")
        for cat, row in result["table"][phase].items():
            lines.append(f"| {phase} | {cat} | {row['n']} | {row['agree']} | "
                         f"{_pct(row['agreement'])} |")
    lines.append("")

    lines += [
        "## Top near-endgame PLAY divergence patterns",
        "",
        f"Filtered to near-endgame decisions where the expert's category was PLAY "
        f"and our pilot's exact pick differed ({result['distinct_near_endgame_play_divergence_patterns']} "
        "distinct (expert card, our choice) patterns observed; top "
        f"{min(TOP_N_PATTERNS, len(result['top_patterns']))} by count shown). "
        "`state_signature` is the median hand size / bench count / both prize "
        "counts / deck count across the pattern's own occurrences, so a repeated "
        "pattern reads as one typical state rather than N raw ones.",
        "",
        "| # | expert did | we would do | count | state signature (median) |",
        "|---|---|---|---|---|",
    ]
    for i, p in enumerate(result["top_patterns"], 1):
        lines.append(f"| {i} | {p['expert_did']} | {p['we_would_do']} | {p['count']} | "
                     f"{p['state_signature']} |")
    lines.append("")

    lines += [
        "## Caveats",
        "",
        "- **ATTACK undercount.** `iter_resolved_decisions` only yields a decision "
        "with 2+ legal options; a turn where ATTACK is the only legal action never "
        "appears in this stream, so ATTACK-category rows above are a directional "
        "lower bound, not an exact count (see `analysis/replay_trace.py`'s own "
        "module docstring, confirmed independently on episode 85300966). PLAY is "
        "comparatively unaffected: END is almost always a second legal option "
        "alongside PLAY, so a PLAY decision is rarely the sole legal action.",
        "- **Agreement is exact-index, not category-loose.** Two options in the "
        "same category (e.g. two different PLAY targets) that are strategically "
        "near-equivalent still count as a disagreement if the pilot picks the "
        "other one. This is the same strictness `move_ranking_validator` uses "
        "project-wide, so the number is comparable to other agreement reads in "
        "this repo, not an absolute skill measure.",
        "- **SHIPPED flags only.** Every decision here scores the pilot with "
        "`_ABILITY` and `_THREAT_RETREAT` patched True (module attributes, "
        "restored after each call); the process's own import-time flag values "
        "never matter to this run.",
        "- **W/L games only**, both wins and losses (823 of the harvest's games "
        "carry a definite result; draws and unresolved games are excluded), since "
        "expert PLAY behavior in a loss is still real signal for a rule designer.",
        f"- **Episodes unresolved: {meta['episodes_unresolved']}** (episode not "
        "found in any dump, unparseable, or team seat not resolved against "
        "`info.TeamNames`); excluded from every number above, not silently "
        "folded in.",
        "",
    ]
    return "\n".join(lines) + "\n"


def _main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--harvest", default=str(DEFAULT_HARVEST))
    ap.add_argument("--episodes-dir", default=str(DEFAULT_EPISODES_DIR))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT_JSON))
    ap.add_argument("--summary", default=str(DEFAULT_OUT_MD))
    ap.add_argument("--limit-games", type=int, default=None,
                     help="cap the number of harvested games walked (smoke testing)")
    args = ap.parse_args(argv)

    result = build(harvest_path=args.harvest, episodes_dir=args.episodes_dir,
                    limit_games=args.limit_games)

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(format_summary(result), encoding="utf-8")

    meta = result["meta"]
    print(f"decisions: {result['total_n']} across {meta['games_scored']} games "
          f"({meta['episodes_unresolved']} episodes unresolved)")
    print(f"overall agreement: {_pct(result['overall_agreement'])}")
    print(f"overall PLAY agreement: {_pct(result['overall_play']['agreement'])}")
    print(f"near-endgame PLAY agreement: {_pct(result['near_endgame_play']['agreement'])}")
    if result["play_agreement_drop_pp"] is not None:
        print(f"PLAY agreement drop (overall minus near-endgame): "
              f"{result['play_agreement_drop_pp']:+.1f}pp")
    print(f"PLAY share of near-endgame disagreement: "
          f"{_pct(result['play_share_of_near_endgame_disagreement'])}")
    print(f"wrote {out_json}")
    print(f"wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
