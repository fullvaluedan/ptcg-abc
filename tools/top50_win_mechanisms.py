"""Top-50 win mechanisms (plan: top50_win_mechanisms).

analysis/top50_win_mechanisms.md described its own pipeline in prose (turn
numbering, phase buckets, prize-take curve, separator cards) but had no
committed generator -- independent verification flagged this. This tool
reconstructs it: walks analysis.replay_trace.iter_resolved_decisions over
data/derived/top50_harvest.json's harvested games (the top-50 leaderboard
teams' own decks and games only, same population the original doc used, NOT
the wider cross-episode opponent pool tools/top50_loss_modes.py also reads),
per-team-turn numbered, to build per-archetype win mechanisms: a card-play
timeline (setup/engine/finisher, won games only), the median first-turn each
signature card appears, a prize-take curve, the attacks actually thrown, and
the cards that most separate wins from losses.

Classifier decontamination. Every archetype label here goes through
tools.top50_loss_modes.decontaminate_signatures before classify_family runs,
for the same verified reason that module documents: the three named families'
builtin signatures include generic format staples, and a deck that shares only
staples with a signature can clear the 0.35 coverage threshold with zero
archetype-defining cards in common. analysis/expert_cohort.py is not edited;
only the signatures dict handed to classify_family is pre-shrunk.

"other" clustering. A deck decontaminated classify_family still scores "other"
is folded into a same-archetype cluster with every other "other" decklist at
jaccard(analysis.archetype.signature_of) >= 0.5, union-find merged -- exactly
the methodology the original doc's own notes describe. The doc never commits
to a naming algorithm for a cluster (a human presumably eyeballed "Mega
Lucario ex / Solrock & Lunatone" once); name_cluster below is a mechanical
stand-in: the cluster's most-played non-staple Pokemon card name(s), so a
cluster gets a stable, re-derivable name instead of an opaque cluster id.
Regenerated cluster membership and names can differ from the original hand
run; per the task, the regenerated numbers win.

Reliability caveat (see the doc's own "Timeline reliability" section, added by
this same fix): iter_resolved_decisions only yields a decision with more than
one legal option (a real choice). A turn where ATTACK is the only legal action
(no other legal MAIN option) never appears in this stream at all, so every
attack-derived number here (first-attack turn, "attacks actually thrown")
undercounts true attack frequency -- confirmed on episode 85300966, where the
winning seat scored knockouts across the game but zero of its 21 captured MAIN
decisions were ever an ATTACK pick, 14 of them merely had ATTACK on offer.
Deck composition and win/loss aggregates never touch this iterator and are not
affected; every per-turn timing number in this doc should be read as a lower
bound / directional signal, not an exact play-by-play.

Dev tool only, never shipped. Reads data/episodes/*.zip (gitignored
competition data) but writes only aggregated, redistributable derived output,
the same convention tools/top50_harvest.py and tools/top50_loss_modes.py
already follow.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis import archetype as archetype_mod  # noqa: E402
from analysis.expert_cohort import classify_family  # noqa: E402
from analysis.replay_trace import iter_resolved_decisions, team_seat  # noqa: E402
from tools.expert_census import build_signatures  # noqa: E402
from tools.top50_harvest import all_dumps, canonical_deck  # noqa: E402
from tools.top50_loss_modes import (  # noqa: E402
    STAPLE_CARD_IDS,
    build_episode_index,
    decontaminate_signatures,
)
from tools.top_player_tracker import DEFAULT_EPISODES_DIR  # noqa: E402

DEFAULT_HARVEST = _ROOT / "data" / "derived" / "top50_harvest.json"
DEFAULT_OUT = _ROOT / "data" / "derived" / "top50_win_mechanisms.json"
DEFAULT_SUMMARY = _ROOT / "analysis" / "top50_win_mechanisms.md"

# Minimum harvested W/L games for an archetype to get its own section, same
# bar the original doc's own coverage prose states ("each has >= 15 harvested
# W/L games").
MIN_ARCHETYPE_GAMES = 15

# jaccard(signature_of) union-find merge threshold for the "other" bucket,
# named in the original doc's own methodology notes.
CLUSTER_JACCARD_MIN = 0.5

# MAIN decision categories that make up the "development" card-play timeline
# (setup/engine/finisher) and the "median first-turn each key card appears"
# table. ATTACK is reported separately (attacks actually thrown) because the
# card_id an ATTACK option resolves to is the attacker, not a played card, and
# because iter_resolved_decisions systematically undercounts attacks (see
# module docstring); ABILITY/RETREAT/END are not part of a "how the deck
# develops" narrative.
DEV_CATEGORIES = frozenset({"PLAY", "ATTACH", "EVOLVE"})
DEV_VERB = {"PLAY": "played", "ATTACH": "energy attached to", "EVOLVE": "evolved"}

SETUP_TURNS = (1, 2)
ENGINE_TURNS = (3, 4, 5)
FINISHER_WINDOW = 2  # the game's own last N turns

TOP_TIMELINE_CARDS = 6
TOP_KEY_CARDS = 8
TOP_ATTACKS = 5
TOP_SEPARATORS = 5


def player_turn(shared_turn: int) -> int:
    """A team's own turn number from the replay's shared half-turn counter.

    Replays store one shared counter that increments every half-turn (seat 0's
    turns are the odd numbers, seat 1's the even); this is the same formula for
    either seat, since (shared+1)//2 lands both seats' turn 1 on shared turns 1
    and 2, turn 2 on shared turns 3 and 4, and so on.
    """
    return (int(shared_turn or 0) + 1) // 2


# --- "other" bucket clustering ------------------------------------------------

class _UnionFind:
    """Minimal union-find over a fixed key set, path-compressed. Pure."""

    def __init__(self, keys):
        self.parent = {k: k for k in keys}

    def find(self, k):
        root = k
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[k] != root:
            self.parent[k], k = root, self.parent[k]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def cluster_other_decks(entries: list, threshold: float = CLUSTER_JACCARD_MIN) -> dict:
    """canonical_deck key -> cluster id, for every distinct "other" decklist.

    entries: [{"key": canonical_deck_tuple, "cards": [...]}, ...], one per
    distinct decklist (already deduplicated by the caller). Pairwise
    jaccard(analysis.archetype.signature_of) >= threshold union-find merges two
    decklists into the same cluster, matching top50_win_mechanisms.md's own
    documented clustering ("pairwise-jaccard'd across the 11 decklists,
    union-find merged at jaccard >= 0.5"). The cluster id is the
    lexicographically smallest member key, so it is deterministic and stable
    across runs regardless of dict/set ordering. Pure.
    """
    keys = [e["key"] for e in entries]
    sigs = {e["key"]: archetype_mod.signature_of(e["cards"]) for e in entries}
    uf = _UnionFind(keys)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if _jaccard(sigs[keys[i]], sigs[keys[j]]) >= threshold:
                uf.union(keys[i], keys[j])
    members: dict = defaultdict(list)
    for k in keys:
        members[uf.find(k)].append(k)
    key_to_cluster = {}
    for group in members.values():
        cid = min(group)
        for k in group:
            key_to_cluster[k] = cid
    return key_to_cluster


def _slugify(name: str) -> str:
    s = name.lower().replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def name_cluster(cards, meta_signature_ids: frozenset, card_index_map: dict) -> str:
    """A stable, mechanical display name for an "other" cluster.

    The original doc hand-names each cluster from its identity Pokemon (e.g.
    "Mega Lucario ex / Solrock & Lunatone" -> mega_lucario); it does not commit
    to an algorithm. This picks the cluster representative's most-played
    Pokemon-type card(s) (CARD_TYPE_POKEMON) that are NOT part of any of the
    three named meta families' raw signature (so the name stays distinctive
    rather than picking a Pokemon the meta families also run), breaking ties on
    higher count then name, and slugifies up to 2 of them. Falls back to
    meta-shared Pokemon, then to "other_cluster" as a last resort so this never
    raises on a degenerate all-trainer deck. Pure.
    """
    from search.determinize import CARD_TYPE_POKEMON

    def _pokemon_counts(exclude_meta: bool) -> Counter:
        counts: Counter = Counter()
        for cid in cards:
            if exclude_meta and cid in meta_signature_ids:
                continue
            card = card_index_map.get(cid)
            if card is not None and int(card.cardType) == CARD_TYPE_POKEMON:
                counts[card.name] += 1
        return counts

    pokes = _pokemon_counts(exclude_meta=True)
    if not pokes:
        pokes = _pokemon_counts(exclude_meta=False)
    if not pokes:
        return "other_cluster"
    top = [name for name, _ in sorted(pokes.items(), key=lambda kv: (-kv[1], kv[0]))[:2]]
    parts = [p for p in (_slugify(n) for n in top) if p]
    return "_".join(parts) if parts else "other_cluster"


# --- archetype grouping --------------------------------------------------------

def build_rows(harvest: dict, signatures: dict, card_index_map: dict) -> tuple:
    """Every top-50 team's own harvested W/L game, labeled with its
    decontaminated archetype.

    Returns (rows, cluster_meta): rows is a flat list of {episode_id, team,
    result, archetype, cards}; cluster_meta maps a cluster archetype name to
    its representative decklist (the member with the most total harvested
    games) for downstream separator-card analysis. A deck that classifies to a
    named family directly never enters the clustering step at all, matching
    the original doc's own "the archetype_guess == other bucket ... was
    clustered" scoping.
    """
    deck_cards: dict = {}       # canonical key -> representative cards
    deck_games: Counter = Counter()  # canonical key -> total harvested games (all teams)
    deck_label: dict = {}       # canonical key -> family name, or None (pending "other")
    other_keys: list = []

    for t in harvest["teams"]:
        for d in t.get("decks") or []:
            key = canonical_deck(d["cards"])
            deck_cards.setdefault(key, d["cards"])
            deck_games[key] += d.get("games_in_window", 0)
            if key not in deck_label:
                fam = classify_family(d["cards"], signatures)
                if fam != "other":
                    deck_label[key] = fam
                else:
                    deck_label[key] = None
                    other_keys.append(key)

    other_entries = [{"key": k, "cards": deck_cards[k]} for k in other_keys]
    cluster_map = cluster_other_decks(other_entries) if other_entries else {}

    meta_raw_ids: frozenset = frozenset().union(*signatures.values()) if signatures else frozenset()
    # Representative per cluster = the member with the most total harvested games.
    cluster_members: dict = defaultdict(list)
    for key in other_keys:
        cluster_members[cluster_map[key]].append(key)
    cluster_name: dict = {}
    cluster_meta: dict = {}
    for cid, members in cluster_members.items():
        rep_key = max(members, key=lambda k: (deck_games[k], k))
        rep_cards = deck_cards[rep_key]
        name = name_cluster(rep_cards, meta_raw_ids, card_index_map)
        cluster_name[cid] = name
        cluster_meta[name] = {"representative_cards": list(rep_cards), "members": len(members)}
    for key in other_keys:
        deck_label[key] = cluster_name[cluster_map[key]]

    rows = []
    for t in harvest["teams"]:
        team = t["team"]
        decks = t.get("decks") or []
        for g in t.get("games") or []:
            if g["result"] not in ("W", "L"):
                continue
            idx = g.get("deck_index")
            if not (isinstance(idx, int) and 0 <= idx < len(decks)):
                continue
            cards = decks[idx]["cards"]
            key = canonical_deck(cards)
            archetype = deck_label.get(key)
            if archetype is None:
                continue
            rows.append({
                "episode_id": g["episode_id"],
                "team": team,
                "result": g["result"],
                "archetype": archetype,
                "cards": cards,
            })
    return rows, cluster_meta


# --- per-game trace ------------------------------------------------------------

def trace_game(replay, seat: int) -> dict:
    """One game's development timeline, attack usage, and prize curve for `seat`.

    Pure over one replay; never raises (a malformed step is skipped by
    iter_resolved_decisions itself).
    """
    max_turn = 0
    dev_events = []          # (player_turn, category, card_id)
    first_turn_by_card = {}  # card_id -> earliest player_turn (dev categories only)
    attack_ids = set()
    first_attack_turn = None
    prize_events = []        # one player_turn per prize actually taken, in order
    prev_prize = None
    for rec in iter_resolved_decisions(replay, seat):
        obs = rec.get("obs") or {}
        current = obs.get("current") or {}
        turn = player_turn(current.get("turn", 0))
        max_turn = max(max_turn, turn)
        played = rec.get("played") or {}
        cat = played.get("category")
        cid = played.get("card_id")
        if cat in DEV_CATEGORIES and cid is not None:
            dev_events.append((turn, cat, cid))
            if cid not in first_turn_by_card:
                first_turn_by_card[cid] = turn
        elif cat == "ATTACK":
            aid = played.get("attack_id")
            if aid is not None:
                attack_ids.add(aid)
                if first_attack_turn is None:
                    first_attack_turn = turn
        players = current.get("players") or []
        if 0 <= seat < len(players) and isinstance(players[seat], dict):
            prize = players[seat].get("prize")
            if isinstance(prize, list):
                count = len(prize)
                if prev_prize is not None and count < prev_prize:
                    prize_events.extend([turn] * (prev_prize - count))
                prev_prize = count
    return {
        "max_turn": max_turn,
        "dev_events": dev_events,
        "first_turn_by_card": first_turn_by_card,
        "attack_ids": attack_ids,
        "first_attack_turn": first_attack_turn,
        "prize_events": prize_events,
    }


def build_traces(rows: list, ep_index: dict) -> tuple:
    """Read each row's episode once and attach its trace_game result.

    Returns (traced_rows, errors); a row whose episode is missing, unreadable,
    or whose team cannot be resolved to a seat is dropped into errors (never
    silently skipped), mirroring tools.top50_loss_modes.process_losses.
    """
    dump_cache: dict = {}
    traced = []
    errors = []
    try:
        for row in rows:
            eid = row["episode_id"]
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
            seat = team_seat(replay, {row["team"]})
            if seat is None:
                errors.append({"episode_id": eid, "reason": "team seat not resolved in replay"})
                continue
            trace = trace_game(replay, seat)
            traced.append({**row, **trace})
    finally:
        for zf in dump_cache.values():
            zf.close()
    return traced, errors


# --- aggregation -----------------------------------------------------------

def _median(values) -> float | None:
    vals = [v for v in values if v is not None]
    return round(statistics.median(vals), 1) if vals else None


def _fmt_num(x) -> str:
    if x is None:
        return "n/a"
    return ("%g" % x)


def _dev_timeline_bucket(traced_wins: list, turn_pred) -> list:
    """Top TOP_TIMELINE_CARDS (card_id, category) pairs by GAME presence in a
    phase window: each game contributes at most one count per (card,
    category), regardless of how many times it recurs in that game's window.

    Generic format staples (STAPLE_CARD_IDS) are excluded from candidacy here
    for the same reason the doc's original "Separator cards" methodology
    excludes them from that table: they are played in most top-50 decks
    regardless of archetype (Boss's Orders, Buddy-Buddy Poffin, Poke Pad,
    Lillie's Determination, ...), so without this a "win mechanism" timeline
    would read as a list of format staples instead of the archetype's own
    distinctive plays -- confirmed against the prior hand-run doc, whose own
    timelines never named a single staple card despite every archetype
    playing them constantly.
    """
    counts: Counter = Counter()
    for g in traced_wins:
        seen = set()
        for turn, cat, cid in g["dev_events"]:
            if cid in STAPLE_CARD_IDS:
                continue
            if turn_pred(turn, g["max_turn"]) and (cat, cid) not in seen:
                seen.add((cat, cid))
                counts[(cat, cid)] += 1
    return counts.most_common(TOP_TIMELINE_CARDS)


def build_archetype_report(name: str, rows: list, traced_by_episode: dict,
                            representative_cards, decontam_signature: frozenset,
                            card_index_map: dict, attack_index_map: dict) -> dict:
    wins = [r for r in rows if r["result"] == "W"]
    losses = [r for r in rows if r["result"] == "L"]
    teams = sorted({r["team"] for r in rows})

    traced_wins = [traced_by_episode[r["episode_id"]] for r in wins
                   if r["episode_id"] in traced_by_episode]
    traced_losses = [traced_by_episode[r["episode_id"]] for r in losses
                      if r["episode_id"] in traced_by_episode]

    median_game_length = _median([g["max_turn"] for g in traced_wins])
    median_first_attack = _median([g["first_attack_turn"] for g in traced_wins])

    setup = _dev_timeline_bucket(traced_wins, lambda t, mx: t in SETUP_TURNS)
    engine = _dev_timeline_bucket(traced_wins, lambda t, mx: t in ENGINE_TURNS)
    finisher = _dev_timeline_bucket(
        traced_wins, lambda t, mx: t > mx - FINISHER_WINDOW and t <= mx and mx > 0
    )

    def _fmt_timeline(bucket) -> list:
        out = []
        for (cat, cid), n in bucket:
            card = card_index_map.get(cid)
            nm = card.name if card is not None else f"card:{cid}"
            out.append(f"{nm} ({DEV_VERB.get(cat, cat.lower())}, {n}g)")
        return out

    attack_counts: Counter = Counter()
    for g in traced_wins:
        for aid in g["attack_ids"]:
            attack_counts[aid] += 1
    attacks_thrown = []
    for aid, n in attack_counts.most_common(TOP_ATTACKS):
        atk = attack_index_map.get(aid)
        nm = atk.name if atk is not None else f"attack:{aid}"
        attacks_thrown.append(f"{nm} ({n} wins)")

    key_cards = []
    for cid in sorted(decontam_signature):
        turns = [g["first_turn_by_card"][cid] for g in traced_wins if cid in g["first_turn_by_card"]]
        if not turns:
            continue
        pct = len(turns) / len(traced_wins) if traced_wins else 0.0
        card = card_index_map.get(cid)
        nm = card.name if card is not None else f"card:{cid}"
        key_cards.append({"card": nm, "median_turn": _median(turns), "pct_wins": pct})
    key_cards.sort(key=lambda r: (r["median_turn"], -r["pct_wins"]))
    key_cards = key_cards[:TOP_KEY_CARDS]

    prize_curve = []
    max_prizes_seen = max((len(g["prize_events"]) for g in traced_wins), default=0)
    for n in range(1, min(max_prizes_seen, 6) + 1):
        turns = [g["prize_events"][n - 1] for g in traced_wins if len(g["prize_events"]) >= n]
        if not turns:
            continue
        prize_curve.append({"prize": n, "median_turn": _median(turns), "n_wins": len(turns)})

    rep_counts = Counter(representative_cards)
    candidates = [cid for cid in decontam_signature if rep_counts.get(cid, 0) >= 2]
    separators = []
    for cid in candidates:
        win_turns = [g["first_turn_by_card"][cid] for g in traced_wins if cid in g["first_turn_by_card"]]
        loss_turns = [g["first_turn_by_card"][cid] for g in traced_losses if cid in g["first_turn_by_card"]]
        rate_win = len(win_turns) / len(traced_wins) if traced_wins else 0.0
        rate_loss = len(loss_turns) / len(traced_losses) if traced_losses else 0.0
        med_win = _median(win_turns)
        med_loss = _median(loss_turns)
        turn_term = abs(med_loss - med_win) if med_win is not None and med_loss is not None else 0.0
        score = abs(rate_win - rate_loss) + 0.05 * turn_term
        card = card_index_map.get(cid)
        nm = card.name if card is not None else f"card:{cid}"
        separators.append({
            "card": nm, "play_rate_win": rate_win, "play_rate_loss": rate_loss,
            "median_turn_win": med_win, "median_turn_loss": med_loss, "score": score,
        })
    separators.sort(key=lambda r: -r["score"])
    separators = separators[:TOP_SEPARATORS]

    return {
        "archetype": name,
        "games": len(rows),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(rows), 3) if rows else None,
        "teams": teams,
        "median_game_length_wins": median_game_length,
        "median_first_attack_turn": median_first_attack,
        "wins_traced": len(traced_wins),
        "losses_traced": len(traced_losses),
        "timeline_setup": _fmt_timeline(setup),
        "timeline_engine": _fmt_timeline(engine),
        "timeline_finisher": _fmt_timeline(finisher),
        "attacks_thrown_in_wins": attacks_thrown,
        "key_cards": key_cards,
        "prize_curve": prize_curve,
        "separators": separators,
    }


def build(harvest_path=DEFAULT_HARVEST, episodes_dir=None) -> dict:
    from agents.heuristics import attack_index, card_index

    harvest = json.loads(Path(harvest_path).read_text(encoding="utf-8"))
    signatures = decontaminate_signatures(build_signatures())
    card_index_map = card_index()
    attack_index_map = attack_index()

    rows, cluster_meta = build_rows(harvest, signatures, card_index_map)

    dumps = all_dumps(episodes_dir or DEFAULT_EPISODES_DIR)
    ep_index = build_episode_index(dumps)
    traced_rows, errors = build_traces(rows, ep_index)
    traced_by_episode = {r["episode_id"]: r for r in traced_rows}

    by_archetype: dict = defaultdict(list)
    for r in rows:
        by_archetype[r["archetype"]].append(r)

    # Representative decklist + decontaminated signature per archetype, for
    # the separator-card candidate pool (count-in-representative >= 2).
    builtin_by_name = {a.name: a for a in archetype_mod._builtin_archetypes()}

    reports = []
    uncovered_games = 0
    for name, arch_rows in by_archetype.items():
        if len(arch_rows) < MIN_ARCHETYPE_GAMES:
            uncovered_games += len(arch_rows)
            continue
        if name in builtin_by_name:
            rep_cards = list(builtin_by_name[name].decklist)
        else:
            rep_cards = cluster_meta.get(name, {}).get("representative_cards") or arch_rows[0]["cards"]
        decontam_sig = signatures.get(name)
        if decontam_sig is None:
            decontam_sig = archetype_mod.signature_of(rep_cards) - STAPLE_CARD_IDS
        report = build_archetype_report(
            name, arch_rows, traced_by_episode, rep_cards, decontam_sig,
            card_index_map, attack_index_map,
        )
        reports.append(report)
    reports.sort(key=lambda r: -r["games"])

    total_games = sum(len(v) for v in by_archetype.values())
    meta = {
        "harvest_path": str(harvest_path),
        "harvest_generated_at": harvest.get("meta", {}).get("generated_at"),
        "total_wl_games": total_games,
        "archetypes_covered": len(reports),
        "games_covered": sum(r["games"] for r in reports),
        "games_uncovered": uncovered_games,
        "episodes_unresolved": len(errors),
        "min_archetype_games": MIN_ARCHETYPE_GAMES,
    }
    return {"meta": meta, "archetypes": reports, "errors": errors}


def format_summary(result: dict) -> str:
    meta = result["meta"]
    lines = [
        "# Top-50 win mechanisms",
        "",
        f"Source: `data/derived/top50_harvest.json` (the top-50 leaderboard harvest, "
        f"{meta['total_wl_games']} W/L games across the 50 harvested teams' own decks; "
        "see `analysis/top50_harvest.md`). Generated by `tools/top50_win_mechanisms.py`.",
        "",
        f"Of {meta['total_wl_games']} harvested W/L games, {meta['games_covered']} "
        f"({meta['games_covered'] / meta['total_wl_games']:.1%}) fall into one of the "
        f"{meta['archetypes_covered']} archetypes below (each has >= "
        f"{meta['min_archetype_games']} harvested W/L games); the remaining "
        f"{meta['games_uncovered']} games are smaller decklists too small to characterize "
        "and left uncovered. Archetype labels are decontaminated (see Methodology notes); "
        f"{meta['episodes_unresolved']} games could not be traced against their episode "
        "JSON and are excluded from the per-turn tables below (still counted in coverage).",
        "",
        "Every card name below is read directly from `agents.heuristics.card_index()` "
        "(id -> `CardData.name`); every attack name from `agents.heuristics.attack_index()` "
        "(id -> `Attack.name`). No card id in this document was hand-typed without that "
        "lookup.",
        "",
        "## Methodology notes (read before the numbers)",
        "",
        "- **Turn numbering.** Replays store one shared turn counter that increments "
        "every half-turn (seat 0's turns are the odd numbers, seat 1's the even). This "
        "doc reports each team's own turn number, `player_turn = (shared_turn + 1) // 2` "
        "(`tools/top50_win_mechanisms.py:player_turn`), so \"turn 3\" always means that "
        "team's own 3rd turn, not the 5th half-turn of the game.",
        "- **Timeline extraction.** Walks `analysis.replay_trace.iter_resolved_decisions` "
        "for the harvested team's own seat (seat resolved per-episode via "
        "`analysis.replay_trace.team_seat`, matching `info.TeamNames`), which yields every "
        "scorable MAIN decision (a real choice among 2+ legal options) resolved to a card "
        "id. The development timeline and \"median first-turn\" table use only PLAY / "
        "ATTACH / EVOLVE decisions; ATTACK is reported separately (attacks actually "
        "thrown) since its card_id names the attacker, not a played card. For an ATTACH "
        "decision the card id is the Pokemon that *received* the energy (the spine's own "
        "convention), not the energy card itself.",
        "- **Classifier decontamination.** Every archetype label here is computed via "
        "`analysis.expert_cohort.classify_family` against signatures with generic format "
        "staples stripped from both the coverage numerator and denominator "
        "(`tools.top50_loss_modes.decontaminate_signatures` / `STAPLE_CARD_IDS`: "
        "Buddy-Buddy Poffin, Ultra Ball, Pokegear 3.0, Poke Pad, Lillie's Determination, "
        "Boss's Orders, Judge, Night Stretcher, Wally's Compassion, Dawn, Rare Candy, "
        "Carmine, Dusk Ball, Bug Catching Set, Canari, Team Rocket's Factory), so a deck "
        "sharing only staples with a family can no longer clear the 0.35 coverage "
        "threshold on staple overlap alone. `analysis/expert_cohort.py` itself is not "
        "modified.",
        "- **\"other\" clustering.** A deck that still classifies \"other\" after "
        "decontamination is merged with every other \"other\" decklist at "
        "jaccard(`analysis.archetype.signature_of`) >= 0.5 (union-find), the same "
        "clustering this doc's methodology has always described. Each cluster is named "
        "mechanically from its representative decklist's most-played non-staple, "
        "non-meta-shared Pokemon card(s) (`tools/top50_win_mechanisms.py:name_cluster`); "
        "this is a re-derivable stand-in for a hand-picked name and can differ from a "
        "prior hand-run's naming.",
        "- **Phase buckets** (won games only): setup = turns 1-2, engine = turns 3-5, "
        "finisher = the game's own last 2 turns (for a short game the engine and finisher "
        "windows overlap; that overlap is real, not a bug: it means the deck's mid-game "
        "and kill turn are the same turn). Generic format staples (same STAPLE_CARD_IDS "
        "list) are excluded from candidacy here too, not just from the separator table "
        "below, so the timeline reads as the archetype's own distinctive plays rather than "
        "a list of cards every top-50 deck runs. Each (card, category) pair counts at most "
        "once per game within a bucket, so a repeated action in one game cannot inflate the "
        "count; the top 6 by game-count are shown per bucket.",
        "- **Prize-take curve.** A team's own `players[seat].prize` list length is their "
        "remaining prize count (starts at 6). Each observed decrease between two "
        "consecutive traced decisions is logged as one \"prize taken\" event at that "
        "snapshot's turn (a multi-prize swing logs multiple events at the same turn); "
        "turn attribution is therefore accurate to within one of that team's own turns.",
        "- **Separator cards.** For every archetype-signature card (decontaminated, "
        "non-staple) played at least twice in the representative decklist, compares play "
        "rate (fraction of TRACED games in which it is first-played at all) and median "
        "first-play turn between the archetype's own wins and its own losses. Ranked by "
        "`|win_rate - loss_rate| + 0.05 * |median_turn_loss - median_turn_win|`; a card "
        "never seen in losses shows `n/a` for that median and only the rate term scores "
        "it.",
        "- **Timeline reliability (verified independently; also see "
        "`tools/top50_loss_modes.py`'s own module docstring for the same finding).** "
        "`iter_resolved_decisions` only yields a decision with more than one legal option. "
        "A turn where ATTACK is the ONLY legal action never appears in this stream at all, "
        "so every attack-derived number here (median first-attack turn, \"attacks actually "
        "thrown\") undercounts true attack frequency -- confirmed on episode 85300966, "
        "where the winning seat scored multiple knockouts across the game but zero of its "
        "21 captured MAIN decisions were an ATTACK pick (14 had ATTACK on offer as one "
        "option among others). This does NOT undermine deck composition or the W/L "
        "aggregates above (coverage, win rate), which are read straight from the harvest's "
        "own decklists and results, never from this decision stream. It DOES mean every "
        "per-turn timing number below (first-attack turn, attacks-thrown counts, and by "
        "extension the finisher-window attack presence) should be read as a directional "
        "lower bound, not an exact play-by-play.",
        "",
    ]

    for r in result["archetypes"]:
        lines.append(f"## {r['archetype']}")
        lines.append("")
        lines.append(
            f"- Coverage: {r['games']} harvested games ({r['wins']}W-{r['losses']}L, "
            f"win rate {r['win_rate']:.1%}) across {len(r['teams'])} team(s): "
            + ", ".join(r["teams"]) + "."
        )
        lines.append(
            f"- Median game length in wins: {_fmt_num(r['median_game_length_wins'])} turns. "
            f"Median first-attack turn: {_fmt_num(r['median_first_attack_turn'])} "
            f"({r['wins_traced']} of {r['wins']} wins traced against their episode JSON)."
        )
        lines.append("")
        lines.append("### Win mechanism: card-play timeline (won games only)")
        lines.append("")
        lines.append(f"**Setup (turns 1-2):** {'; '.join(r['timeline_setup']) or '(none captured)'}")
        lines.append("")
        lines.append(f"**Engine (turns 3-5):** {'; '.join(r['timeline_engine']) or '(none captured)'}")
        lines.append("")
        lines.append(
            f"**Finisher (closing 2 turns of the game):** "
            f"{'; '.join(r['timeline_finisher']) or '(none captured)'}"
        )
        lines.append("")
        lines.append(
            "Attacks actually thrown in wins: "
            + (", ".join(r["attacks_thrown_in_wins"]) or "(none captured, see Timeline reliability note)")
            + "."
        )
        lines.append("")

        if r["key_cards"]:
            lines.append("### Median first-turn each key card appears (wins)")
            lines.append("")
            lines.append("| card | median first turn | % of wins that play it |")
            lines.append("|---|---|---|")
            for kc in r["key_cards"]:
                lines.append(f"| {kc['card']} | {_fmt_num(kc['median_turn'])} | {kc['pct_wins']:.0%} |")
            lines.append("")

        if r["prize_curve"]:
            lines.append("### Prize-take curve (median turn per Nth prize, wins)")
            lines.append("")
            lines.append("| prize # | median turn taken | n wins observed |")
            lines.append("|---|---|---|")
            for pc in r["prize_curve"]:
                lines.append(f"| {pc['prize']} | {_fmt_num(pc['median_turn'])} | {pc['n_wins']} |")
            lines.append("")

        if r["separators"]:
            lines.append("### Cards that most separate wins from losses")
            lines.append("")
            lines.append("| card | play rate in wins | play rate in losses | median turn (win) | median turn (loss) |")
            lines.append("|---|---|---|---|---|")
            for s in r["separators"]:
                lines.append(
                    f"| {s['card']} | {s['play_rate_win']:.0%} | {s['play_rate_loss']:.0%} | "
                    f"{_fmt_num(s['median_turn_win'])} | {_fmt_num(s['median_turn_loss'])} |"
                )
            lines.append("")
        lines.append("")

    if result["errors"]:
        lines += ["## Unresolved games", "",
                   f"{len(result['errors'])} harvested games could not be traced against "
                   "their episode JSON (excluded from the per-turn tables, still counted in "
                   "coverage):", ""]
        reason_counts = Counter(e["reason"].split(":")[0] for e in result["errors"])
        for reason, count in reason_counts.most_common():
            lines.append(f"- {reason}: {count}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--harvest", default=str(DEFAULT_HARVEST))
    ap.add_argument("--episodes-dir", default=str(DEFAULT_EPISODES_DIR))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    args = ap.parse_args(argv)

    result = build(harvest_path=args.harvest, episodes_dir=args.episodes_dir)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(format_summary(result), encoding="utf-8")

    print(
        f"{result['meta']['archetypes_covered']} archetypes covering "
        f"{result['meta']['games_covered']} of {result['meta']['total_wl_games']} games "
        f"({result['meta']['episodes_unresolved']} episodes unresolved)"
    )
    print(f"wrote {out_path}")
    print(f"wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
