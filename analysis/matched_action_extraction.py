#!/usr/bin/env python3
"""Matched-action extraction (plan U3 / U106b): replaces U106's unsound verdicts.

LOOP_BRIEF.md P9 rule 4 retired analysis/state_matched_expert_lookup.py's (U106)
"experts also lose here" verdicts as unsound: a win-only expert corpus made that
question unanswerable, its loss "buckets" were invented per-state categories
rather than the real loss_classifier buckets, its distance bands were
uncalibrated, and it silently capped the expert corpus at 10k rows while
reporting "1.3M". The corrected follow-up this module implements is narrower
and honest about what it can and cannot say: for each of our real loss states,
find the nearest expert neighbor STATE and report what that expert actually
DID there (their recorded entry["action"], resolved from the raw episode JSON),
aggregated per real loss bucket. It does not attempt an "experts also lose
here" verdict at all -- the win-only corpus still cannot answer that -- so this
module reports only expert action distributions, never a win/lose verdict.

Pipeline:
  1. build_our_loss_states  -- one row per decision state from OUR real ladder
     loss games (data/replays), labeled with the REAL loss_classifier bucket
     for that game (not an invented per-state category).
  2. load_expert_corpus     -- every top_player_corpus_*.csv row, full corpus,
     no subsampling (the corrected pass P9 rule 4 asked for).
  3. knn_join               -- for each of our loss states, the SINGLE nearest
     expert neighbor's IDENTITY (game_id, seat, turn), not just its distance,
     on the full 24-feature layout (ptcg_agent.features.FEATURE_NAMES; the
     predecessor script only used 21 of the 24 shared features). Also records
     the mean/max distance across k neighbors as a support signal.
  4. build_zip_index / load_episode_from_zip -- resolve a neighbor's game_id to
     its real episode JSON by searching every data/episodes zip's member index
     (never assume same-day: corpus game_ids lag the zip's dataset date by
     about a day, so a same-day-only lookup silently misses real episodes).
  5. extract_expert_action  -- the expert's chosen MAIN action category at the
     matched (seat, turn), via tools.replays_to_rows.move_rows_from_replay
     (unmodified) behind the zip-reader adapter above.
  6. aggregate_by_cluster   -- per real loss bucket: support, mean distance,
     and an expert action distribution weighted PER OUR GAME (not per raw
     state), so one chatty loss game logging 50 states in a bucket cannot
     outvote four games that log one state each 50:1.

Scope note (stated here and in the output doc): this first pass reports expert
action distributions only. Our OWN actions at these matched states are not
extracted or compared -- they are unlogged for this pass, a recorded scope
limit, not a silent gap. Interpret every distribution under the deck-blind
feature caveat carried from the U65 audit (analysis/state_matched_expert_lookup.py
caveats section): these 24 features do not encode deck identity, so two states
that look identical in feature space can call for different correct plays
depending on the actual matchup.
"""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agents import heuristics as H  # noqa: E402
from agents import imitation_features  # noqa: E402
from analysis.loss_classifier import classify_loss, parse_replay  # noqa: E402
from ptcg_agent.features import FEATURE_NAMES as STATE_FEATURE_NAMES  # noqa: E402
from tools.replays_to_rows import move_rows_from_replay, rows_from_replay  # noqa: E402
from tools.scout import OUR_TEAM, is_self_play, load_replay, our_index_from_replay  # noqa: E402

# Full 24-feature layout shared by our state rows and the expert corpus (LOOP_
# BRIEF P8: "24 shared features"). The superseded U106 script's FEATURE_COLS
# only listed 21 of these (missing the U64 append: our_bench_cliff,
# our_deckout_risk, our_prize_tempo); this pass uses the complete layout.
FEATURE_COLS = list(STATE_FEATURE_NAMES)

K_NEIGHBORS = 5  # neighbors used for the mean/max distance support signal
DEFAULT_EXPERT_LIMIT = None  # None = no subsampling (the corrected behavior)

# Action-category order, matches agents.imitation_features.FEATURE_NAMES[0:7].
ACTION_CATEGORY_FEATURES = (
    ("PLAY", "is_play"),
    ("ATTACH", "is_attach"),
    ("EVOLVE", "is_evolve"),
    ("ABILITY", "is_ability"),
    ("RETREAT", "is_retreat"),
    ("ATTACK", "is_attack"),
    ("END", "is_end"),
)
_MOVE_FEATURE_INDEX = {name: i for i, name in enumerate(imitation_features.FEATURE_NAMES)}


def _find_data_root() -> Path | None:
    """Locate a real data/ directory, never raises.

    Tries this checkout's own data/ first. An isolated agent worktree (created
    fresh per unit, per README-isolation.txt) has no data/ checked out -- it is
    gitignored competition data that only exists in the main working copy --
    so this also tries the main repo, located via git's shared common-dir
    (never a hardcoded relative path, which would break if the worktree layout
    changes). Returns None, and only None, when neither exists: callers must
    treat that as "real corpus not reachable" and say so, not fabricate output.
    """
    candidates = [_ROOT / "data"]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=_ROOT, capture_output=True, text=True, timeout=10, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            main_root = Path(result.stdout.strip()).resolve().parent
            candidates.append(main_root / "data")
    except (OSError, subprocess.SubprocessError):
        pass
    for c in candidates:
        if c.is_dir():
            return c
    return None


# ---------------------------------------------------------------------------
# 1. Our loss states, labeled with the REAL loss_classifier bucket.
# ---------------------------------------------------------------------------

def build_our_loss_states(replay_dir: Path) -> pd.DataFrame:
    """One row per decision state from our own real ladder loss games.

    Walks every replay JSON in replay_dir, skips self-play validation
    episodes, classifies each loss with analysis.loss_classifier's REAL
    buckets (slow_search / deckout / deck_matchup / endgame_misplay /
    early_collapse / bad_determinization -- not an invented per-state
    category), and keeps only the rows belonging to OUR seat with label == 0
    (rows_from_replay emits rows for both seats; the opponent's rows, and any
    of our rows from a game we won, are dropped here).
    """
    records = []
    for path in sorted(Path(replay_dir).glob("*.json")):
        try:
            replay = load_replay(path)
        except (OSError, json.JSONDecodeError):
            continue
        try:
            if is_self_play(replay):
                continue
            seat = our_index_from_replay(replay, OUR_TEAM)
            if seat is None:
                seat = 0
            digest = parse_replay(replay, our_index=seat)
            if digest.get("outcome") != "loss":
                continue
            bucket = classify_loss(digest)
            if not bucket:
                continue
            game_id = path.stem
            for row in rows_from_replay(replay, game_id):
                if row[1] != seat or row[-1] != 0:
                    continue
                feats = row[3:3 + len(FEATURE_COLS)]
                records.append(
                    {
                        "our_game_id": game_id,
                        "seat": row[1],
                        "turn": row[2],
                        **dict(zip(FEATURE_COLS, feats)),
                        "bucket": bucket,
                    }
                )
        except (AttributeError, TypeError, KeyError):
            continue
    return pd.DataFrame.from_records(records)


# ---------------------------------------------------------------------------
# 2. Expert corpus.
# ---------------------------------------------------------------------------

def load_expert_corpus(data_dir: Path) -> pd.DataFrame:
    """Every top_player_corpus_*.csv row, concatenated, no subsampling.

    The predecessor script silently sampled the corpus down to 10k rows while
    its report claimed the full "1.3M" (P9 rule 4). This loads every row; the
    kNN join below uses a tree/ball-query index rather than brute pairwise
    distance specifically so the full corpus stays usable at real scale.
    """
    files = sorted(Path(data_dir).glob("top_player_corpus_*.csv"))
    if not files:
        raise FileNotFoundError(f"No top_player_corpus_*.csv under {data_dir}")
    frames = [pd.read_csv(f) for f in files]
    return pd.concat(frames, ignore_index=True).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 3. kNN join that keeps neighbor IDENTITY, not just distance.
# ---------------------------------------------------------------------------

DEFAULT_QUERY_CHUNK = 500  # bounds knn_join's peak query memory, see docstring


def knn_join(loss_states: pd.DataFrame, expert_corpus: pd.DataFrame,
             feature_cols=None, k: int = K_NEIGHBORS,
             query_chunk_size: int = DEFAULT_QUERY_CHUNK) -> pd.DataFrame:
    """Attach the nearest expert neighbor's (game_id, seat, turn) to every row.

    Z-scores both sides on the expert corpus's own mean/std, fits a
    NearestNeighbors index on the expert side, and for each loss state records
    the SINGLE nearest neighbor's identity (the one whose episode gets
    resolved for action extraction) plus the mean/max distance across the k
    nearest as a support signal -- distance support is reported ALONGSIDE the
    action distribution, never used to fabricate a verdict on its own (that
    was U106's mistake).

    Memory: `algorithm="auto"` was measured against the real ~2.5M-row corpus
    at this module's 24-feature dimensionality and confirmed (empirically,
    `nn._fit_method` after fit) to resolve to "brute" -- sklearn's dimension
    heuristic falls back to brute force well before 24 features. A real run
    with "auto" ballooned to 48GB resident and had to be killed. Two
    independent bounds fix it: an explicit ball_tree index (near-linear memory
    in n_samples * n_features regardless of corpus size, and degrades more
    gracefully than kd_tree at this dimensionality), plus querying the loss
    states in bounded chunks so peak query memory never scales with the full
    loss-state count even if a future change shifts sklearn's internal
    chunking behavior again. float32 (half the footprint of float64, ample
    precision for a z-scored feature space) is used throughout.
    """
    feature_cols = list(feature_cols or FEATURE_COLS)
    out = loss_states.reset_index(drop=True).copy()
    for col in ("nn_game_id", "nn_seat", "nn_turn", "nn_distance", "mean_distance", "max_distance"):
        out[col] = pd.Series([None] * len(out), dtype=object)

    if loss_states.empty or expert_corpus.empty:
        return out

    from sklearn.neighbors import NearestNeighbors

    expert_feats = expert_corpus[feature_cols].fillna(0).to_numpy(dtype=np.float32)
    mean = expert_feats.mean(axis=0)
    std = expert_feats.std(axis=0) + 1e-6
    expert_norm = ((expert_feats - mean) / std).astype(np.float32)

    loss_feats = out[feature_cols].fillna(0).to_numpy(dtype=np.float32)
    loss_norm = ((loss_feats - mean) / std).astype(np.float32)

    k_eff = max(1, min(k, len(expert_corpus)))
    nn = NearestNeighbors(n_neighbors=k_eff, algorithm="ball_tree")
    nn.fit(expert_norm)

    distances_parts, indices_parts = [], []
    chunk = max(1, query_chunk_size)
    for start in range(0, len(loss_norm), chunk):
        d, idx = nn.kneighbors(loss_norm[start:start + chunk])
        distances_parts.append(d)
        indices_parts.append(idx)
    distances = np.concatenate(distances_parts, axis=0) if distances_parts else np.empty((0, k_eff))
    indices = np.concatenate(indices_parts, axis=0) if indices_parts else np.empty((0, k_eff), dtype=int)

    nn_idx = indices[:, 0]
    expert_game_ids = expert_corpus["game_id"].to_numpy()
    expert_seats = expert_corpus["seat"].to_numpy()
    expert_turns = expert_corpus["turn"].to_numpy()

    out["nn_game_id"] = expert_game_ids[nn_idx]
    out["nn_seat"] = expert_seats[nn_idx]
    out["nn_turn"] = expert_turns[nn_idx]
    out["nn_distance"] = distances[:, 0]
    out["mean_distance"] = distances.mean(axis=1)
    out["max_distance"] = distances.max(axis=1)
    return out


# ---------------------------------------------------------------------------
# 4. Zip index and reader adapter.
# ---------------------------------------------------------------------------

def build_zip_index(episodes_dir: Path) -> dict:
    """stem (bare episode id) -> the zip Path that contains it.

    Scans EVERY zip's member index, never just a same-day guess: corpus
    game_ids lag the zip dataset's date by about a day (a game finishing near
    a day boundary lands in the NEXT day's daily dump), so a lookup scoped to
    one day's zip silently misses real episodes. The small manifest-only
    "-index.zip" is skipped (it carries no per-episode JSON members).
    """
    index: dict = {}
    for zpath in sorted(Path(episodes_dir).glob("*.zip")):
        if zpath.stem.endswith("-index"):
            continue
        try:
            with zipfile.ZipFile(zpath) as zf:
                for name in zf.namelist():
                    if not name.endswith(".json"):
                        continue
                    stem = Path(name).stem
                    index.setdefault(stem, zpath)
        except (zipfile.BadZipFile, OSError):
            continue
    return index


def load_episode_from_zip(zip_index: dict, game_id) -> dict | None:
    """Thin zip-reader adapter: read one episode JSON from its indexed zip.

    Mirrors tools.scout.load_replay's contract (returns the parsed replay
    dict, or None on any failure) but reads a zip member instead of a loose
    file. Downstream parsing (move_rows_from_replay, _main_decision_turns) is
    completely unmodified -- this function's only job is producing the same
    dict shape load_replay would from a loose file.
    """
    stem = str(game_id)
    zpath = zip_index.get(stem)
    if zpath is None:
        return None
    try:
        with zipfile.ZipFile(zpath) as zf:
            with zf.open(f"{stem}.json") as fh:
                return json.load(fh)
    except (zipfile.BadZipFile, KeyError, OSError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# 5. Expert action extraction at the matched (seat, turn).
# ---------------------------------------------------------------------------

def _main_decision_turns(replay: dict) -> dict:
    """decision_id -> (seat, turn) for every MAIN decision in `replay`.

    move_rows_from_replay's row schema (game_id, seat, decision_id, n_options,
    option_index, is_chosen, *features) does not carry turn, so this is the
    thin bookkeeping companion needed to align a (seat, turn) query to a
    decision_id -- it mirrors move_rows_from_replay's exact walk and
    decision_id counter (status ACTIVE, a real select/current pair, seat in
    (0, 1), a MAIN select with more than one option) so a decision_id
    produced here always names the SAME decision there. It does not
    reimplement move_rows_from_replay's feature extraction or chosen-option
    logic; those are called unmodified in extract_expert_action below.
    """
    index: dict = {}
    decision_id = 0
    for step in replay.get("steps") or []:
        if not isinstance(step, (list, tuple)):
            continue
        for p, entry in enumerate(step):
            if not isinstance(entry, dict) or entry.get("status") != "ACTIVE":
                continue
            obs = entry.get("observation") or {}
            sel = obs.get("select")
            current = obs.get("current")
            if sel is None or current is None:
                continue
            seat = current.get("yourIndex", p)
            if seat not in (0, 1):
                continue
            if sel.get("type") != H.SEL_MAIN:
                continue
            options = sel.get("option") or []
            if len(options) <= 1:
                continue
            index[decision_id] = (seat, current.get("turn", 0))
            decision_id += 1
    return index


def _action_category(feature_row) -> str | None:
    """The chosen option's action category, read off its imitation-feature row.

    ACTION_CATEGORY_FEATURES mirrors imitation_features.FEATURE_NAMES[0:7]
    (is_play .. is_end), which are mutually exclusive by construction
    (agents.imitation_features.option_features sets exactly one from the
    option's own `type` field).
    """
    for label, feat_name in ACTION_CATEGORY_FEATURES:
        if feature_row[_MOVE_FEATURE_INDEX[feat_name]]:
            return label
    return None


def extract_expert_action(replay: dict, game_id, seat: int, turn: int) -> str | None:
    """The expert's chosen MAIN action category at (seat, turn), or None.

    Calls tools.replays_to_rows.move_rows_from_replay UNMODIFIED for the
    actual chosen-option extraction (the recorded entry["action"] index); the
    only local logic is resolving which decision_id corresponds to the
    requested turn, via _main_decision_turns. A turn can carry more than one
    MAIN decision for the same seat (e.g. play a card, then attack, then end);
    the first (lowest decision_id) is reported, since it best matches the
    board position the neighbor state was drawn from. Returns None when the
    seat had no MAIN decision at that turn, or the recorded action could not
    be resolved to a legal option (both are recorded as unresolved support,
    never fabricated).
    """
    turns = _main_decision_turns(replay)
    matches = sorted(did for did, (s, t) in turns.items() if s == seat and t == turn)
    if not matches:
        return None
    target_id = matches[0]
    rows = move_rows_from_replay(replay, game_id)
    for row in rows:
        if row[2] == target_id and row[5] == 1:
            return _action_category(row[6:])
    return None


def resolve_actions(matched: pd.DataFrame, zip_index: dict) -> pd.DataFrame:
    """Adds an `action` column: the resolved expert MAIN action, or None.

    Resolves each UNIQUE nearest-neighbor episode from its zip exactly ONCE
    (many loss states can share the same nearest neighbor game) by grouping
    on nn_game_id and holding only ONE parsed replay in memory at a time.

    A real episode JSON runs several MB raw and parses into several times
    that many bytes of Python dict/list objects (measured: ~3.9MB raw ->
    ~14.7MB parsed on a real episode). An earlier version of this function
    cached every parsed replay for the life of the whole run; with a real
    loss-state batch touching thousands of distinct neighbor episodes, that
    cache alone is what actually drove a real run's memory into the tens of
    GB (more than the kNN query itself, which sklearn/knn_join already bound).
    Grouping and discarding each replay after its group is processed removes
    the unbounded-cache growth entirely rather than just capping it.
    """
    out = matched.copy()
    if out.empty:
        out["action"] = pd.Series(dtype=object)
        return out

    actions = pd.Series([None] * len(out), index=out.index, dtype=object)
    valid = out[out["nn_game_id"].notna()]
    if not valid.empty:
        keys = valid["nn_game_id"].astype(str)
        for game_id, idxs in valid.index.groupby(keys).items():
            replay = load_episode_from_zip(zip_index, game_id)
            if replay is None:
                continue
            for idx in idxs:
                row = out.loc[idx]
                if row["nn_seat"] is None or row["nn_turn"] is None:
                    continue
                try:
                    actions.at[idx] = extract_expert_action(
                        replay, game_id, int(row["nn_seat"]), int(row["nn_turn"])
                    )
                except (AttributeError, TypeError, KeyError, IndexError):
                    actions.at[idx] = None
            del replay  # one episode alive at a time; next group's replay
            # is only parsed after this one is eligible for collection.
    out["action"] = actions
    return out


# ---------------------------------------------------------------------------
# 6. Per-cluster aggregation, weighted per OUR game.
# ---------------------------------------------------------------------------

def aggregate_by_cluster(resolved: pd.DataFrame) -> dict:
    """Per real loss bucket: support, mean distance, and a per-game-weighted
    expert action distribution.

    Weighting is by OUR game (our_game_id), not raw state count: within a
    bucket, each of our games that contributed at least one resolved neighbor
    action gets its OWN normalized action distribution, and the cluster
    aggregate is the unweighted MEAN of those per-game distributions. A game
    that logged 50 states in the bucket therefore contributes exactly one vote
    (its own distribution), the same as a game that logged one -- it cannot
    dominate the aggregate 50:1 the way summing raw state counts would let it.

    An empty-support cluster (no neighbor action could be resolved for any of
    its states) reports support=0 and an empty action_distribution, rather
    than fabricating a verdict from partial or absent data.
    """
    result = {}
    if resolved.empty:
        return result
    for bucket in sorted(resolved["bucket"].dropna().unique()):
        bdf = resolved[resolved["bucket"] == bucket]
        n_states = len(bdf)
        distances = pd.to_numeric(bdf["nn_distance"], errors="coerce").dropna()
        mean_distance = float(distances.mean()) if len(distances) else None
        resolved_rows = bdf[bdf["action"].notna()]
        support = len(resolved_rows)
        if support == 0:
            result[bucket] = {
                "n_states": n_states,
                "mean_distance": mean_distance,
                "support": 0,
                "n_games": 0,
                "action_distribution": {},
            }
            continue
        per_game_dists = [
            gdf["action"].value_counts(normalize=True)
            for _, gdf in resolved_rows.groupby("our_game_id")
        ]
        agg = pd.concat(per_game_dists, axis=1).fillna(0.0).mean(axis=1)
        result[bucket] = {
            "n_states": n_states,
            "mean_distance": mean_distance,
            "support": support,
            "n_games": len(per_game_dists),
            "action_distribution": agg.sort_values(ascending=False).round(4).to_dict(),
        }
    return result


# ---------------------------------------------------------------------------
# Report writer.
# ---------------------------------------------------------------------------

def _write_report(path: Path, cluster_results: dict, n_loss_states: int,
                   n_loss_games: int, n_expert_rows: int, data_reachable: bool,
                   note: str = "") -> None:
    lines = []
    lines.append("# Matched-Action Extraction (plan U3 / U106b)\n")
    lines.append(
        "Supersedes analysis/state_matched_expert_lookup.py (U106), retired as "
        "unsound by LOOP_BRIEF.md P9 rule 4. That script's \"experts also lose "
        "here\" verdicts, invented per-state categories, and uncalibrated "
        "distance bands are not reused; this pass reports something narrower "
        "and checkable instead: what the nearest expert neighbor actually "
        "DID at each of our matched loss states.\n"
    )
    lines.append("## Scope note\n")
    lines.append(
        "This first pass reports expert action distributions only. Our OWN "
        "actions at these matched states are not extracted or compared here "
        "-- that is a recorded scope limit for this pass, not a silent gap. "
        "The win-only expert corpus also means this pass makes no claim about "
        "whether experts also lose from these states; it only reports what "
        "they did at the single nearest matched state.\n"
    )
    if not data_reachable:
        lines.append("## Data reachability\n")
        lines.append(
            "**Real corpus NOT reachable in this run.** " + (note or "") + "\n"
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return

    lines.append("## Method\n")
    lines.append(f"- Our loss states: {n_loss_states} decision rows from {n_loss_games} real ladder loss games "
                  "(data/replays), labeled with the REAL analysis.loss_classifier bucket for that game.\n")
    lines.append(f"- Expert corpus: {n_expert_rows} rows across every top_player_corpus_*.csv, no subsampling.\n")
    lines.append(f"- Features: all {len(FEATURE_COLS)} shared state features (ptcg_agent.features.FEATURE_NAMES).\n")
    lines.append(f"- kNN: k={K_NEIGHBORS}, z-scored on the expert corpus's own mean/std; the SINGLE nearest "
                  "neighbor's identity (game_id, seat, turn) is resolved to its real episode JSON and its "
                  "chosen MAIN action extracted; mean/max distance across the k nearest is reported as a "
                  "support signal alongside the action distribution.\n")
    lines.append("- Action distribution weighting: per OUR game, not per raw state (see aggregate_by_cluster "
                  "docstring) -- a chatty loss game cannot dominate a cluster's reported distribution.\n")
    lines.append(
        "- Deck-blind feature caveat (from the U65 audit, carried forward): these state features do not "
        "encode deck identity, so two states that look identical in feature space may call for different "
        "correct plays depending on the actual matchup. Every distribution below should be read as \"what "
        "experts did near this board shape,\" not as a deck-aware recommendation.\n"
    )

    lines.append("\n## Findings by loss bucket\n")
    if not cluster_results:
        lines.append("No loss states were available to bucket (empty join input).\n")
    for bucket, r in cluster_results.items():
        lines.append(f"### {bucket}\n")
        lines.append(f"- States analyzed: {r['n_states']}\n")
        lines.append(f"- Mean nearest-neighbor distance: "
                      f"{r['mean_distance']:.4f}\n" if r["mean_distance"] is not None else "- Mean nearest-neighbor distance: n/a\n")
        lines.append(f"- Resolved-action support: {r['support']} states across {r['n_games']} of our games\n")
        if r["support"] == 0:
            lines.append("- **support=0: no verdict.** No neighbor action could be resolved for this bucket "
                          "(episode not found in any indexed zip, or no matching MAIN decision at that turn). "
                          "Reporting support=0 rather than fabricating a distribution from partial data.\n\n")
            continue
        lines.append("- Expert action distribution (per-game weighted):\n")
        for action, frac in r["action_distribution"].items():
            lines.append(f"  - {action}: {frac:.1%}\n")
        lines.append("\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    data_root = _find_data_root()
    if data_root is None:
        print("Real data/ not reachable (checked this checkout and the main repo via git common-dir). "
              "Writing a report that states this explicitly rather than fabricating numbers.")
        _write_report(
            _ROOT / "analysis" / "matched_expert_actions.md", {}, 0, 0, 0,
            data_reachable=False,
            note="Neither this worktree's data/ nor the main repo's data/ (located via "
                 "`git rev-parse --git-common-dir`) exists. Re-run from an environment with the "
                 "competition data checked out.",
        )
        return

    replay_dir = data_root / "replays"
    training_dir = data_root / "training"
    episodes_dir = data_root / "episodes"

    print(f"Using data root: {data_root}")
    print("1. Building our loss states from real ladder loss games...")
    loss_states = build_our_loss_states(replay_dir)
    print(f"   {len(loss_states)} loss-state rows from "
          f"{loss_states['our_game_id'].nunique() if not loss_states.empty else 0} loss games")

    print("2. Loading expert corpus...")
    expert_corpus = load_expert_corpus(training_dir)
    print(f"   {len(expert_corpus)} expert rows")

    print("3. Building zip index over data/episodes...")
    zip_index = build_zip_index(episodes_dir)
    print(f"   {len(zip_index)} episode ids indexed across every zip")

    print("4. kNN join (neighbor identity retained)...")
    matched = knn_join(loss_states, expert_corpus)

    print("5. Resolving expert actions from episode zips...")
    resolved = resolve_actions(matched, zip_index)

    print("6. Aggregating per loss bucket (per-game weighted)...")
    cluster_results = aggregate_by_cluster(resolved)

    report_path = _ROOT / "analysis" / "matched_expert_actions.md"
    _write_report(
        report_path, cluster_results, len(loss_states),
        loss_states["our_game_id"].nunique() if not loss_states.empty else 0,
        len(expert_corpus), data_reachable=True,
    )
    print(f"Done. Report: {report_path}")


if __name__ == "__main__":
    main()
