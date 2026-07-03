"""Top-player decision dataset for opponent cloning (plan U70).

The clone ring (docs/plans/2026-07-03-002-feat-top-player-clone-ring-plan.md)
needs a training table of the top-20 leaderboard teams' real MAIN decisions,
one ranking group per decision: a feature row per legal option
(agents.imitation_features.decision_features) plus which option that team
actually chose. Unlike analysis/expert_cohort's winner-only census, a clone
needs BOTH a team's wins and its losses -- how a top team plays under
pressure is part of the imitation, not just how it plays when it is already
winning. Each group is tagged by team handle, the seat's deck archetype
family (analysis.expert_cohort.classify_family), whether that seat won the
episode, and a held-out split by EPISODE (analysis.replay_trace.split_of),
so a later trainer can hold out whole games, never individual decisions from
a game it partly trained on.

Output is a single ragged npz under data/training/clones/ (gitignored, same
tier as every other data/training/* artifact): one flat feature matrix `X`
plus `group_sizes` (options per group) so a consumer reconstructs group i as
X[offset:offset+group_sizes[i]] with offset = sum(group_sizes[:i]); metadata
arrays (`played`, `team`, `family`, `won`, `episode`, `split`) run parallel
to `group_sizes`, one entry per group.

Dev tool only; never shipped. Reads the competition episode dataset but
never redistributes it (data/episodes and data/training stay gitignored).
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402

from agents import imitation_features  # noqa: E402
from analysis.expert_cohort import classify_family, seat_decklists, team_names, winner_seat  # noqa: E402
from analysis.move_ranking_validator import load_replays  # noqa: E402
from analysis.replay_trace import episode_id_of, iter_expert_decisions, split_of  # noqa: E402
from tools.expert_census import build_signatures  # noqa: E402
from tools.top_player_tracker import DEFAULT_EPISODES_DIR, DEFAULT_TOP_N, fetch_leaderboard, newest_dataset  # noqa: E402

DEFAULT_OUT_DIR = _ROOT / "data" / "training" / "clones"
DEFAULT_THRESHOLD = 0.35


def replay_groups(replay, episode_id, team_set, signatures, threshold: float = DEFAULT_THRESHOLD):
    """Yield one ranking-group record per top-team MAIN decision in `replay`.

    Both seats whose team name is in `team_set` are walked (a top-vs-top game
    contributes both), over every scorable MAIN decision that seat faced, win
    or lose. A drawn or malformed-reward episode (winner_seat is None) or one
    with no readable opener decklist drops the whole replay, so a group's
    `won` tag is always a real, determined outcome. Pure and defensive: a
    malformed decision or an out-of-range played index is skipped, never
    fatal. Never touches the card engine (imitation_features degrades to
    zeroed knowledge features without it).
    """
    names = team_names(replay)
    if names is None:
        return
    matched = [seat for seat, name in enumerate(names) if name in team_set]
    if not matched:
        return
    winner = winner_seat(replay)
    if winner is None:
        return
    decks = seat_decklists(replay)
    if decks is None:
        return
    for seat in matched:
        family = classify_family(decks[seat], signatures, threshold)
        won = seat == winner
        team = names[seat]
        for obs, played in iter_expert_decisions(replay, seat):
            feat_rows = imitation_features.decision_features(obs)
            if feat_rows is None or not (0 <= played < len(feat_rows)):
                continue
            yield {
                "features": feat_rows,
                "played": played,
                "team": team,
                "family": family,
                "won": won,
                "episode": episode_id,
                "split": split_of(episode_id),
            }


def groups_from_replays(replay_label_pairs, team_set, signatures, threshold: float = DEFAULT_THRESHOLD) -> tuple:
    """All clone ranking groups over an iterable of (replay, label) pairs.

    Returns (groups, meta) where meta counts episodes that contributed at
    least one group vs episodes that matched no team_set seat or produced no
    scorable decision. Pure over the inputs, never raises: a malformed replay
    is skipped by replay_groups' own guards. No I/O: build_dataset is the
    disk-reading wrapper around this.
    """
    groups = []
    episodes_matched = 0
    episodes_skipped = 0
    for replay, label in replay_label_pairs:
        eid = episode_id_of(label)
        found = list(replay_groups(replay, eid, team_set, signatures, threshold))
        if found:
            episodes_matched += 1
            groups.extend(found)
        else:
            episodes_skipped += 1
    return groups, {"episodes_matched": episodes_matched, "episodes_skipped": episodes_skipped}


def build_dataset(source, team_set, signatures, threshold: float = DEFAULT_THRESHOLD, limit=None) -> tuple:
    """All clone ranking groups over a dataset `source` (a .zip or a directory).

    Thin disk-reading wrapper around groups_from_replays: loads `source` via
    analysis.move_ranking_validator.load_replays, same as every other census
    tool in this codebase.
    """
    return groups_from_replays(load_replays(source, limit=limit), team_set, signatures, threshold)


def summarize(groups: list) -> dict:
    """Group counts by family, team, and split. Pure, never raises."""
    by_family = Counter(g["family"] for g in groups)
    by_team = Counter(g["team"] for g in groups)
    by_split = Counter(g["split"] for g in groups)
    return {
        "groups": len(groups),
        "by_family": dict(by_family),
        "by_team": dict(by_team),
        "by_split": dict(by_split),
    }


def write_npz(groups: list, out_path) -> Path:
    """Write `groups` as a ragged npz (see module docstring for the layout)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if groups:
        X = np.asarray(
            [row for g in groups for row in g["features"]], dtype=np.float32
        )
    else:
        X = np.zeros((0, imitation_features.N_FEATURES), dtype=np.float32)
    group_sizes = np.asarray([len(g["features"]) for g in groups], dtype=np.int32)
    played = np.asarray([g["played"] for g in groups], dtype=np.int32)
    team = np.asarray([g["team"] for g in groups], dtype=object)
    family = np.asarray([g["family"] for g in groups], dtype=object)
    won = np.asarray([g["won"] for g in groups], dtype=bool)
    episode = np.asarray([g["episode"] for g in groups], dtype=object)
    split = np.asarray([g["split"] for g in groups], dtype=object)
    np.savez(
        out_path,
        X=X,
        group_sizes=group_sizes,
        played=played,
        team=team,
        family=family,
        won=won,
        episode=episode,
        split=split,
        feature_version=np.array(list(imitation_features.feature_version())),
    )
    return out_path


def load_npz(path) -> dict:
    """The raw arrays written by write_npz, as a dict (allow_pickle for the object arrays)."""
    with np.load(path, allow_pickle=True) as data:
        return {k: data[k] for k in data.files}


def iter_groups(data: dict):
    """Reconstruct each ragged group from load_npz's flat arrays, in order."""
    offset = 0
    X = data["X"]
    for i, size in enumerate(data["group_sizes"]):
        size = int(size)
        yield {
            "features": X[offset:offset + size],
            "played": int(data["played"][i]),
            "team": str(data["team"][i]),
            "family": str(data["family"][i]),
            "won": bool(data["won"][i]),
            "episode": str(data["episode"][i]),
            "split": str(data["split"][i]),
        }
        offset += size


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", nargs="?", default=None,
                     help="episode dataset .zip or a directory of *.json replays "
                          "(default: newest under --episodes-dir)")
    ap.add_argument("--episodes-dir", default=str(DEFAULT_EPISODES_DIR),
                     help="directory holding episode dataset .zip files")
    ap.add_argument("--top-n", type=int, default=DEFAULT_TOP_N,
                     help="how many live leaderboard teams to clone (default 20)")
    ap.add_argument("--teams", nargs="+", default=None,
                     help="explicit team names (skips the live leaderboard fetch)")
    ap.add_argument("--decks-dir", default=None,
                     help="optional directory of extra archetype .csv decklists to classify against")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                     help="minimum signature coverage to assign a deck to a family (else other)")
    ap.add_argument("--limit", type=int, default=None,
                     help="cap episodes read (default: the whole dataset)")
    ap.add_argument("--out", default=None,
                     help="output npz path (default data/training/clones/clone_groups_<timestamp>.npz)")
    args = ap.parse_args(argv)

    source = Path(args.source) if args.source else newest_dataset(args.episodes_dir)
    if source is None or not Path(source).exists():
        print(f"no episode dataset found under {args.episodes_dir}")
        return 1

    if args.teams:
        team_set = set(args.teams)
    else:
        lb = fetch_leaderboard(args.top_n)
        if not lb["ok"]:
            print(f"leaderboard fetch failed: {lb['error']}")
            return 1
        team_set = {t["name"] for t in lb["teams"]}

    signatures = build_signatures(args.decks_dir)
    groups, meta = build_dataset(source, team_set, signatures, args.threshold, limit=args.limit)
    summary = summarize(groups)

    out_path = Path(args.out) if args.out else DEFAULT_OUT_DIR / f"clone_groups_{int(time.time())}.npz"
    write_npz(groups, out_path)

    print(f"teams: {len(team_set)}")
    print(f"episodes matched: {meta['episodes_matched']} (skipped {meta['episodes_skipped']})")
    print(f"ranking groups: {summary['groups']}")
    print("per family:")
    for fam, n in sorted(summary["by_family"].items(), key=lambda kv: -kv[1]):
        print(f"  {fam:<28} {n}")
    print(f"split: {summary['by_split']}")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
