"""How top-50 leaderboard teams LOSE (plan: top50_loss_modes).

Input: data/derived/top50_harvest.json (tools/top50_harvest.py's per-team last-N
games + decklists). This tool walks every game in that harvest with result "L"
for the top-50 team, re-opens the exact episode JSON from data/episodes/*.zip
(the harvest only kept the LOSER's own decklist, not the winner's -- the winner's
deck has to be re-read from the same episode), and extracts:

  - the winner's decklist and archetype (analysis.expert_cohort.seat_decklists +
    classify_family, the same signatures top50_harvest.py already used, so labels
    match the harvest's own archetype_guess column)
  - the winner's rank/rating when the winner is ALSO a top-50 team (looked up in
    the harvest's own team list; no live leaderboard fetch, and the repo has no
    working broader leaderboard snapshot -- see analysis/top50_loss_modes.md notes)
  - a compact "loss shape" for the top-50 loser: deckout / setup_denied (empty
    bench, early) / late_collapse (empty bench, later) / close_loss (lost within
    2 prizes) / outraced (opponent finished clean, loser barely scored) /
    grind_loss (everything else -- an extended, traded game the loser still lost)

Loss shape reuses the SIGNAL FIELDS analysis.loss_classifier.parse_replay already
computes and battle-tests (deck/bench/prize end-state) but not its BUCKET TAXONOMY
or thresholds tuned for our own search agent's losses -- classify_loss_shape below
is a separate, purpose-built decision tree for a top-50 human/bot ladder loss.

Scope note on "winning line": this tool does NOT attempt to reconstruct a
per-turn card-play timeline. A spot check of the replay format found that
correlating a decision's chosen action index back to that decision's own option
list (or a naive one-step-shifted pairing) produces implausible results on real
games (a 21-turn game the winner clearly won showed zero attack-type options
ever chosen by the winning seat) -- the actual action/option pairing convention
in this competition's replay JSON is not resolved from the fields inspected here.
Rather than fabricate a first-attack-turn or per-card timeline on an unverified
pairing, "winning line" is reported using only fields already proven in this
codebase: game length (n_turns) as the kill-turn / pacing signal, and both
seats' final remaining-prize counts as the prize-curve endpoint (0 remaining =
a clean prize sweep; >0 = the game ended some other way, e.g. the loser
deckout or bench collapse before prizes ran out).

Dev tool only, never shipped. Reads data/episodes/*.zip (gitignored competition
data) but writes only aggregated, redistributable derived output, the same
convention tools/top50_harvest.py already follows.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.expert_cohort import classify_family, seat_decklists, team_names  # noqa: E402
from analysis.expert_cohort import winner_seat as replay_winner_seat  # noqa: E402
from analysis.loss_classifier import parse_replay  # noqa: E402
from tools.expert_census import build_signatures  # noqa: E402
from tools.top50_harvest import all_dumps, canonical_deck  # noqa: E402
from tools.top_player_tracker import DEFAULT_EPISODES_DIR  # noqa: E402

DEFAULT_HARVEST = _ROOT / "data" / "derived" / "top50_harvest.json"
DEFAULT_OUT = _ROOT / "data" / "derived" / "top50_loss_modes.json"
DEFAULT_SUMMARY = _ROOT / "analysis" / "top50_loss_modes.md"

# -- classifier decontamination (verified defect, fixed without touching
# analysis/expert_cohort.py) --
#
# analysis.expert_cohort.classify_family scores a decklist against a family by
# COVERAGE: len(deck_ids & signature) / len(signature). The three builtin
# family signatures (analysis.archetype._BUILTIN_DECKLISTS, via
# tools.expert_census.build_signatures) are the full non-basic-energy card set
# of one representative decklist, which includes generic format staples that
# appear in most top-50 decks regardless of archetype (the same list
# analysis/top50_win_mechanisms.md's own "Separator cards" methodology note
# already excludes from candidacy, for the same reason: they never separate
# one archetype from another). At the default 0.35 threshold, a deck that
# plays several of these staples plus a couple of incidental overlaps can
# clear the coverage bar on staple overlap alone, with zero archetype-defining
# cards in common. Verified real examples: nasuo445's Cynthia's Garchomp ex
# toolbox (episode 85300993, staple overlap only: Buddy-Buddy Poffin, Poke
# Pad, Lillie's Determination, Night Stretcher, Boss's Orders, raw coverage
# 6/17 = 0.353) and ZETADIVISION's Dragapult ex toolbox (episode 85299931,
# same five staples plus Munkidori and Unfair Stamp, raw coverage 8/17 = 0.47)
# both cleared meta_grimmsnarl_tonakaiiii's threshold with no Grimmsnarl-line
# card in the deck at all.
#
# Fix: strip the staple ids from every family signature before scoring, so a
# staple can never contribute to either the numerator (deck & signature) or
# the denominator (signature size) of the coverage fraction. classify_family
# itself is untouched; this only pre-shrinks the `signatures` dict passed into
# it, which is exactly the caller-supplied extension point that function
# already exposes. Re-scored under the decontaminated signatures, both
# verified examples above drop to 1/10 and 2/10 coverage respectively, well
# under 0.35, and correctly fall through to "other".
STAPLE_CARD_IDS = frozenset({
    1086,  # Buddy-Buddy Poffin
    1121,  # Ultra Ball
    1122,  # Pokegear 3.0
    1152,  # Poke Pad
    1227,  # Lillie's Determination
    1182,  # Boss's Orders
    1213,  # Judge
    1097,  # Night Stretcher
    1229,  # Wally's Compassion
    1231,  # Dawn
    1079,  # Rare Candy
    1192,  # Carmine
    1102,  # Dusk Ball
    1094,  # Bug Catching Set
    1233,  # Canari
    1257,  # Team Rocket's Factory
})


def decontaminate_signatures(signatures: dict) -> dict:
    """Family-name -> signature, with STAPLE_CARD_IDS stripped from every set.

    Pass the result to classify_family (or label_archetype below) in place of
    the raw tools.expert_census.build_signatures() output. Never mutates the
    input; a family whose entire signature is staples (none in this dataset)
    is left with an empty frozenset, which classify_family already skips (`if
    not sig: continue`), never dividing by zero. Pure.
    """
    return {name: frozenset(sig) - STAPLE_CARD_IDS for name, sig in signatures.items()}

# -- loss-shape thresholds (purpose-built for this report; see module docstring) --
CLOSE_REMAINING = 2      # loser needed at most this many more prizes: a near win that slipped
STEAMROLL_REMAINING = 4  # loser had taken at most (6 - this) = 2 prizes: barely scored
NEAR_DECKOUT_DECK = 1    # a forced-draw deckout is caught one observation early, same as loss_classifier
EARLY_TURN_LIMIT = 8     # a bench collapse this early reads as a setup failure, not a late grind
ANECDOTE_MIN = 5         # fewer than this many games backing a claim: flag as anecdote


def build_episode_index(dumps: list) -> dict:
    """episode_id -> dump Path, from a cheap namelist() scan (no decompression).

    Mirrors tools.top50_harvest.scan_all_dumps's cheap-first-pass philosophy: a
    zip namelist() read is metadata-only and does not decompress any member.
    First dump wins on a duplicate id (should not happen across daily dumps, but
    defensive rather than silently picking the last).
    """
    index: dict = {}
    for dump in dumps:
        with zipfile.ZipFile(dump) as zf:
            for name in zf.namelist():
                if not name.endswith(".json") or name == "manifest.csv":
                    continue
                index.setdefault(name[:-5], dump)
    return index


def collect_losses(harvest: dict) -> list:
    """Every game across all top-50 teams with result "L", one dict per loss.

    Carries the loser's OWN decklist (already in the harvest) and archetype
    label straight through; only the winner's side needs a fresh episode read.
    """
    losses = []
    for t in harvest["teams"]:
        decks = t.get("decks") or []
        for g in t["games"]:
            if g["result"] != "L":
                continue
            idx = g.get("deck_index")
            deck = decks[idx] if isinstance(idx, int) and 0 <= idx < len(decks) else None
            losses.append({
                "episode_id": g["episode_id"],
                "date": g["date"],
                "loser_rank": t["rank"],
                "loser_team": t["team"],
                "loser_rating": t["rating"],
                "opponent": g["opponent"],
                "loser_deck_cards": list(deck["cards"]) if deck else None,
            })
    return losses


def build_slug_map(harvest: dict, decks_dir=None) -> dict:
    """canonical_deck(cards) -> the top50_harvest.py slug for that exact decklist.

    Reads the CSVs tools/top50_harvest.py already wrote under decks/top50/ (one
    60-card-id-per-line file per globally-eligible decklist) rather than
    re-deriving anything, so an "other"-family loser or winner deck that matches
    one of those CSVs gets the SAME readable slug the harvest report already uses
    instead of a bare, uninformative "other".
    """
    decks_dir = Path(decks_dir) if decks_dir else _ROOT / "decks" / "top50"
    out = {}
    for entry in harvest.get("decks_written", []):
        path = entry.get("path")
        if not path or not Path(path).exists():
            continue
        cards = [int(line) for line in Path(path).read_text(encoding="utf-8").split() if line.strip()]
        out[canonical_deck(cards)] = entry["slug"]
    return out


def label_archetype(cards, signatures, slug_map: dict, fallback_name: str) -> str:
    """Archetype label for a decklist: a named meta family, a known "other" slug,
    or "other:<team>" as a last resort so distinct unnamed decks never collapse
    into one uninformative "other" bucket. None cards (decklist unavailable in
    this episode) label as "unknown"."""
    if cards is None:
        return "unknown"
    fam = classify_family(cards, signatures)
    if fam != "other":
        return fam
    slug = slug_map.get(canonical_deck(cards))
    return slug if slug else f"other:{fallback_name}"


def classify_loss_shape(digest: dict) -> str:
    """Descriptive loss-shape bucket for one top-50 team's loss.

    Order matters, most decisive signal first:
      1. deckout        the loser's deck hit zero, or one card left with a
                         non-empty bench and an opponent who has not closed the
                         prize race (the forced-draw deckout caught one
                         observation early, same reasoning as
                         analysis.loss_classifier.classify_loss).
      2. setup_denied    the loser's bench was empty (lone active knocked out,
                         nothing to promote) within the first EARLY_TURN_LIMIT
                         turns: the loser never got a board established.
      3. late_collapse   same empty-bench structural failure, but later: a board
                         existed and then thinned out.
      4. close_loss      the loser needed at most CLOSE_REMAINING more prizes: a
                         near win that slipped, not a blowout.
      5. outraced        the loser had taken at most (6 - STEAMROLL_REMAINING)
                         prizes while the winner finished with 0 remaining: a
                         clean, fast prize sweep the loser never contested.
      6. grind_loss      everything else: an extended, traded game the loser
                         still lost without any of the sharper signals above.
    """
    my_deck_end = digest.get("my_deck_end")
    my_bench_end = digest.get("my_bench_end")
    my_prize_end = digest.get("my_prize_end")
    opp_prize_end = digest.get("opp_prize_end")
    n_turns = digest.get("n_turns") or 0

    if my_deck_end == 0:
        return "deckout"
    if (
        my_deck_end is not None
        and my_deck_end <= NEAR_DECKOUT_DECK
        and my_bench_end not in (0, None)
        and opp_prize_end is not None
        and opp_prize_end > CLOSE_REMAINING
    ):
        return "deckout"
    if my_bench_end == 0:
        return "setup_denied" if n_turns <= EARLY_TURN_LIMIT else "late_collapse"
    if my_prize_end is not None and my_prize_end <= CLOSE_REMAINING:
        return "close_loss"
    if my_prize_end is not None and my_prize_end >= STEAMROLL_REMAINING and opp_prize_end == 0:
        return "outraced"
    return "grind_loss"


def process_losses(losses: list, ep_index: dict, signatures: dict, slug_map: dict,
                    top50_by_name: dict) -> tuple:
    """Resolve every collected loss against its episode JSON.

    Returns (results, errors). A loss is dropped into errors (never silently
    skipped) when its episode is missing from every dump, unreadable, carries no
    TeamNames/decklist match, or its recorded reward disagrees with the harvest's
    own W/L label (a data-integrity guard, not expected to fire in practice).
    """
    dump_cache: dict = {}
    results = []
    errors = []
    try:
        for loss in losses:
            eid = loss["episode_id"]
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
            except Exception as exc:  # noqa: BLE001 - a single bad member must not abort the batch
                errors.append({"episode_id": eid, "reason": f"read/parse failed: {exc}"})
                continue

            names = team_names(replay)
            if names is None or loss["loser_team"] not in names:
                errors.append({"episode_id": eid, "reason": "loser team not found in replay TeamNames"})
                continue
            loser_seat = names.index(loss["loser_team"])
            winner_seat_idx = 1 - loser_seat
            check = replay_winner_seat(replay)
            if check is not None and check != winner_seat_idx:
                errors.append({"episode_id": eid, "reason": "replay reward disagrees with harvest W/L label"})
                continue

            decks = seat_decklists(replay)
            winner_cards = decks[winner_seat_idx] if decks is not None else None
            winner_team = names[winner_seat_idx]
            winner_archetype = label_archetype(winner_cards, signatures, slug_map, winner_team)
            loser_archetype = label_archetype(loss["loser_deck_cards"], signatures, slug_map, loss["loser_team"])

            digest = parse_replay(replay, our_index=loser_seat)
            if digest.get("outcome") != "loss":
                errors.append({
                    "episode_id": eid,
                    "reason": f"replay outcome '{digest.get('outcome')}' disagrees with harvest 'L' label",
                })
                continue

            winner_info = top50_by_name.get(winner_team)
            results.append({
                "episode_id": eid,
                "date": loss["date"],
                "loser_team": loss["loser_team"],
                "loser_rank": loss["loser_rank"],
                "loser_rating": loss["loser_rating"],
                "loser_archetype": loser_archetype,
                "winner_team": winner_team,
                "winner_rank": winner_info["rank"] if winner_info else None,
                "winner_rating": winner_info["rating"] if winner_info else None,
                "winner_archetype": winner_archetype,
                "n_turns": digest.get("n_turns"),
                "loser_prize_remaining": digest.get("my_prize_end"),
                "winner_prize_remaining": digest.get("opp_prize_end"),
                "loser_deck_remaining": digest.get("my_deck_end"),
                "loser_bench_remaining": digest.get("my_bench_end"),
                "loss_shape": classify_loss_shape(digest),
            })
    finally:
        for zf in dump_cache.values():
            zf.close()
    return results, errors


def _median(values: list):
    vals = [v for v in values if v is not None]
    return round(statistics.median(vals), 1) if vals else None


def aggregate_by_loser(results: list) -> list:
    """Per losing archetype: what beats it, how, and how often."""
    by_loser: dict = defaultdict(list)
    for r in results:
        by_loser[r["loser_archetype"]].append(r)
    out = []
    for archetype, rows in by_loser.items():
        winner_counts = Counter(r["winner_archetype"] for r in rows)
        shape_counts = Counter(r["loss_shape"] for r in rows)
        out.append({
            "archetype": archetype,
            "losses": len(rows),
            "anecdote": len(rows) < ANECDOTE_MIN,
            "beaten_by": winner_counts.most_common(),
            "loss_shapes": shape_counts.most_common(),
            "median_kill_turn": _median([r["n_turns"] for r in rows]),
            "median_loser_prize_remaining": _median([r["loser_prize_remaining"] for r in rows]),
            "median_winner_prize_remaining": _median([r["winner_prize_remaining"] for r in rows]),
        })
    out.sort(key=lambda e: -e["losses"])
    return out


def aggregate_predators(results: list) -> list:
    """Per WINNING archetype across all top-50 losses: the natural predators of the meta."""
    by_winner: dict = defaultdict(list)
    for r in results:
        by_winner[r["winner_archetype"]].append(r)
    out = []
    for archetype, rows in by_winner.items():
        victim_counts = Counter(r["loser_archetype"] for r in rows)
        shape_counts = Counter(r["loss_shape"] for r in rows)
        kill_turns = [r["n_turns"] for r in rows if r["n_turns"] is not None]
        # winner_prize_remaining never reaches 0 in this replay format (see
        # module docstring / build(): the last captured decision precedes the
        # game-ending move, so 1 is the observed floor for a genuine finished
        # prize race, not a real "one prize short"). <=1 is therefore the
        # "prize race basically completed normally" signal, as opposed to a
        # loss shape (deckout / bench collapse) that ends the game while the
        # winner still visibly had several prizes left to take.
        prize_race_done = sum(1 for r in rows if r["winner_prize_remaining"] <= 1)
        prize_race_rate = round(prize_race_done / len(rows), 2) if rows else None
        dominant_shape = shape_counts.most_common(1)[0][0] if shape_counts else None
        median_turn = _median(kill_turns)
        recurring_line = (
            f"median kill turn {median_turn}" if median_turn is not None else "kill turn unknown"
        )
        recurring_line += (
            f"; prize race essentially complete (winner <=1 from a sweep) in {prize_race_rate:.0%} of kills"
            if prize_race_rate is not None else ""
        )
        recurring_line += f"; dominant loss shape inflicted: {dominant_shape}" if dominant_shape else ""
        out.append({
            "archetype": archetype,
            "kills": len(rows),
            "anecdote": len(rows) < ANECDOTE_MIN,
            "victim_archetypes": victim_counts.most_common(),
            "loss_shapes_inflicted": shape_counts.most_common(),
            "median_kill_turn": median_turn,
            "prize_race_completed_rate": prize_race_rate,
            "recurring_line": recurring_line,
        })
    out.sort(key=lambda e: -e["kills"])
    return out


def format_summary(results: list, errors: list, losers: list, predators: list, meta: dict) -> str:
    lines = [
        "# Top-50 loss modes: how they lose",
        "",
        f"Generated from {meta['harvest_path']} (harvest generated "
        f"{meta['harvest_generated_at']}). {meta['total_losses_found']} losses found across "
        f"the top-50 teams' harvested windows; {len(results)} resolved against their episode "
        f"JSON and analyzed below, {len(errors)} could not be resolved (see Unresolved below).",
        "",
        "Every claim below carries its game count (n). Any bucket with n < "
        f"{ANECDOTE_MIN} is flagged **anecdote** and should not be read as a trend.",
        "",
        "## Predator table: who beats the top-50 field, and how",
        "",
        "Every winning archetype across ALL top-50 losses, ranked by kills. \"Prize race "
        "complete\" = the winner's own remaining-prize count was <=1 at the last captured "
        "decision (this replay format's observed floor is 1, never 0 -- the last decision "
        "logged always precedes the actual game-ending move, so <=1 is the closest signal to "
        "\"the winner finished a normal KO-based prize race\" this data supports; see Method "
        "notes). A LOW rate means that archetype's kills mostly end the game some other way "
        "(the loser deckout-ing or collapsing) while the winner still had several prizes left.",
        "",
        "| winner archetype | kills | top victims | median kill turn | prize race complete rate | dominant loss shape inflicted |",
        "|---|---|---|---|---|---|",
    ]
    for p in predators:
        victims = ", ".join(f"{a} ({c})" for a, c in p["victim_archetypes"][:4])
        anec = " (anecdote)" if p["anecdote"] else ""
        rate = f"{p['prize_race_completed_rate']:.0%}" if p["prize_race_completed_rate"] is not None else "n/a"
        lines.append(
            f"| {p['archetype']}{anec} | {p['kills']} | {victims} | {p['median_kill_turn']} | "
            f"{rate} | {p['loss_shapes_inflicted'][0][0] if p['loss_shapes_inflicted'] else 'n/a'} |"
        )

    lines += ["", "## How each losing archetype loses", ""]
    for l in losers:
        anec = " (ANECDOTE, n < 5)" if l["anecdote"] else ""
        lines.append(f"### {l['archetype']} -- {l['losses']} losses{anec}")
        lines.append("")
        beaten_by = ", ".join(f"{a} ({c})" for a, c in l["beaten_by"][:6])
        lines.append(f"- Beaten by: {beaten_by}")
        shapes = ", ".join(f"{s} ({c})" for s, c in l["loss_shapes"])
        lines.append(f"- Loss shapes: {shapes}")
        lines.append(
            f"- Median kill turn {l['median_kill_turn']}; at loss, this archetype had "
            f"{l['median_loser_prize_remaining']} prizes left to take (median) while the "
            f"winner had {l['median_winner_prize_remaining']} left (median; 1 is this format's "
            "observed floor for a finished prize race, see Method notes -- higher means the "
            "game ended some other way while the winner still had prizes to go)."
        )
        lines.append("")

    if errors:
        lines += ["## Unresolved losses", "", f"{len(errors)} losses could not be resolved against "
                  "their episode JSON and are excluded from the tables above:", ""]
        reason_counts = Counter(e["reason"].split(":")[0] for e in errors)
        for reason, count in reason_counts.most_common():
            lines.append(f"- {reason}: {count}")
        lines.append("")

    lines += [
        "## Method notes",
        "",
        "- Losing archetype: the top-50 team's OWN decklist for that game, taken straight from "
        "data/derived/top50_harvest.json (already computed by tools/top50_harvest.py).",
        "- Winning archetype: re-derived from the SAME episode JSON's opening decklist "
        "(analysis.expert_cohort.seat_decklists) via the same 3-family signature set "
        "(meta_archaludon / meta_grimmsnarl / meta_grimmsnarl_tonakaiiii); anything else "
        "resolves to a top50_harvest.py deck slug when the exact 60-card list matches one, "
        "otherwise \"other:<team name>\".",
        "- Classifier decontamination: family signatures have generic format staples "
        "(Buddy-Buddy Poffin, Ultra Ball, Pokegear 3.0, Poke Pad, Lillie's Determination, "
        "Boss's Orders, Judge, Night Stretcher, Wally's Compassion, Dawn, Rare Candy, "
        "Carmine, Dusk Ball, Bug Catching Set, Canari, Team Rocket's Factory -- the same "
        "list top50_win_mechanisms.md's own methodology excludes from separator-card "
        "candidacy) stripped from BOTH the coverage numerator and denominator before "
        "classify_family scores a deck (tools/top50_loss_modes.py:STAPLE_CARD_IDS / "
        "decontaminate_signatures), so a deck that shares only staples with a family "
        "signature can no longer clear the 0.35 coverage threshold on staple overlap "
        "alone. Without this, a deck with zero archetype-defining cards in common with a "
        "family (verified real cases: nasuo445's Cynthia's Garchomp ex toolbox, "
        "ZETADIVISION's Dragapult ex toolbox) cleared threshold and polluted that "
        "family's win/loss and predator counts; analysis.expert_cohort.py itself is "
        "unmodified, only the signatures dict passed into it is pre-shrunk. The effect is "
        "large, not anecdotal: several teams previously pooled under meta_grimmsnarl (e.g. "
        "bono's exact decklist, shared with wkonishi/soyukke/Majkel1337) carry none of "
        "Marnie's Impidimp / Morgrem / Grimmsnarl ex / Morpeko at all (only the generic "
        "Dunsparce/Dudunsparce draw engine and Xerosic's Machinations, both shared with "
        "other archetypes), so meta_grimmsnarl's kill count drops from 183 to 29 below; the "
        "magnitude matches the independently measured 94-of-98 (95.9%) contamination rate "
        "on meta_archaludon-labeled winners, which drops from 98 to 4 kills here.",
        "- Legacy slug-name residue: a top50_NN_<team>_meta_<family> \"other\" fallback slug "
        "was minted by tools/top50_harvest.py, which still runs the UNDECONTAMINATED "
        "classifier for its own CSV filenames (regenerating top50_harvest.md itself is out "
        "of scope here; this tool only reads that file, never writes it). A deck that no "
        "longer clears a named family's decontaminated threshold correctly falls out of "
        "that family's counts, but the slug text it falls back to can still carry a stale "
        "\"_meta_grimmsnarl\" / \"_meta_archaludon\" / \"_meta_grimmsnarl_tonakaiiii\" suffix "
        "from that old classification (e.g. top50_02_bono_meta_grimmsnarl, see above). Read "
        "every top50_NN_* row below as an opaque per-deck identifier, not an archetype "
        "claim.",
        "- Winner rank/rating is reported only when the winner is ALSO one of the harvested "
        "top-50 teams (looked up in the same harvest snapshot); this repo has no working "
        "broader leaderboard snapshot to resolve a rating for a winner outside the top 50 "
        "(data/leaderboard_cache/leaderboard_2026_07_05.csv is a stale kaggle-CLI error dump, "
        "not real leaderboard data).",
        "- Loss shape buckets (deckout / setup_denied / late_collapse / close_loss / outraced / "
        "grind_loss) are a purpose-built decision tree over the same board-state fields "
        "analysis.loss_classifier.parse_replay already extracts (deck/bench/prize end-state); "
        "they reuse those SIGNALS, not our own agent's classify_loss BUCKETS or thresholds "
        "tuned for search-agent losses. See tools/top50_loss_modes.py:classify_loss_shape.",
        "- \"Winning line\" is reported as game length (n_turns, the kill-turn signal the task "
        "asked for) and both seats' final remaining-prize counts, not a per-turn card-play "
        "timeline: a spot check of the replay JSON found the decision-to-chosen-option "
        "correlation is not reliably resolvable from the fields inspected (see module "
        "docstring), so no first-attack-turn or per-card timeline is claimed here.",
        "- winner_prize_remaining is 1 at minimum across all 460 resolved losses, never 0: this "
        "replay format's last captured decision always precedes the actual game-ending move, "
        "so a genuine finished prize race shows up as \"1 left\", not \"0 left\". "
        "\"prize race complete rate\" therefore uses <=1, not ==0, as the winner-finished-a-real-"
        "prize-race signal.",
        "",
    ]
    return "\n".join(lines) + "\n"


def build(harvest_path=DEFAULT_HARVEST, episodes_dir=None) -> dict:
    harvest = json.loads(Path(harvest_path).read_text(encoding="utf-8"))
    top50_by_name = {t["team"]: t for t in harvest["teams"]}

    dumps = all_dumps(episodes_dir or DEFAULT_EPISODES_DIR)
    ep_index = build_episode_index(dumps)

    signatures = decontaminate_signatures(build_signatures())
    slug_map = build_slug_map(harvest)

    losses = collect_losses(harvest)
    results, errors = process_losses(losses, ep_index, signatures, slug_map, top50_by_name)

    losers = aggregate_by_loser(results)
    predators = aggregate_predators(results)

    meta = {
        "harvest_path": str(harvest_path),
        "harvest_generated_at": harvest.get("meta", {}).get("generated_at"),
        "total_losses_found": len(losses),
        "losses_resolved": len(results),
        "losses_unresolved": len(errors),
    }
    return {
        "meta": meta,
        "results": results,
        "errors": errors,
        "by_losing_archetype": losers,
        "predator_archetypes": predators,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--harvest", default=str(DEFAULT_HARVEST))
    ap.add_argument("--episodes-dir", default=str(DEFAULT_EPISODES_DIR))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    args = ap.parse_args(argv)

    out = build(harvest_path=args.harvest, episodes_dir=args.episodes_dir)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        format_summary(out["results"], out["errors"], out["by_losing_archetype"],
                        out["predator_archetypes"], out["meta"]),
        encoding="utf-8",
    )

    print(
        f"{out['meta']['total_losses_found']} losses found, "
        f"{out['meta']['losses_resolved']} resolved, "
        f"{out['meta']['losses_unresolved']} unresolved"
    )
    print(f"wrote {out_path}")
    print(f"wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
