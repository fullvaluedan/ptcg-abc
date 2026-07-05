"""Mine 800+ rated decks from episode dumps (plan U39, step 1).

Identifies top-rated teams from the current leaderboard, mines their winning
decklists from the full episode dataset, and clusters them by signature.

The goal: understand what decks the top 800+ rated players actually play, so
we can rebuild the practice ring with stronger opponents for the convergence
phase (Aug 17+). This is distinct from the bracket ring (450-750 band we
actually face); this is the TRUE STRENGTH study (P2).

Outputs:
- data/derived/top_rated_decks.json: team -> list of winning decklists
- analysis/top_rated_mining.md: human-readable report with clustering
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.expert_cohort import seat_decklists, team_names  # noqa: E402
from analysis.move_ranking_validator import load_replays  # noqa: E402
from tools.isolation import derived_path  # noqa: E402
from tools.top_player_tracker import newest_dataset  # noqa: E402


LEADERBOARD_PATH = _ROOT / "data" / "leaderboard_cache" / "pokemon-tcg-ai-battle.zip"
EPISODES_DIR = _ROOT / "data" / "episodes"
MIN_RATING = 800.0
DEFAULT_DECKS_DIR = _ROOT / "decks"


def load_leaderboard_teams(zip_path: Path, min_rating: float) -> set:
    """Load team names with rating >= min_rating from the leaderboard zip.

    Returns a set of normalized team names (lowercase for case-insensitive match).
    """
    teams = set()
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.namelist():
                if member.endswith('.csv'):
                    text = zf.read(member).decode('utf-8-sig')
                    reader = csv.DictReader(text.splitlines())
                    for row in reader:
                        try:
                            score = float(row.get('Score', 0))
                            if score >= min_rating:
                                team_name = (row.get('TeamName') or '').strip()
                                if team_name:
                                    # Normalize for matching: lowercase
                                    teams.add(team_name.lower())
                        except (ValueError, AttributeError):
                            pass
    except Exception as e:
        print(f"ERROR reading leaderboard: {e}", file=sys.stderr)
    return teams


def normalize_team_name(name: str) -> str:
    """Normalize a team name for matching against leaderboard."""
    return (name or '').lower().strip()


def mine_top_rated_decks(
    episodes_source: Path | str,
    min_rating: float,
    leaderboard_zip: Path = LEADERBOARD_PATH,
    limit: int | None = None,
) -> tuple:
    """Mine decklists from episodes where the winning team has rating >= min_rating.

    Returns (team_decks dict, total_episodes_scanned, matches_found).
    team_decks: {team_name -> list of (deck_sig, count) tuples, sorted by count desc}
    """
    # Load the target teams from leaderboard
    target_teams = load_leaderboard_teams(leaderboard_zip, min_rating)
    if not target_teams:
        print(f"WARNING: no teams found with rating >= {min_rating}", file=sys.stderr)

    print(f"Loaded {len(target_teams)} teams with rating >= {min_rating}")

    # Mine decklists: scan episodes for winning decks by target teams
    team_decks = defaultdict(Counter)  # team_name -> Counter of deck signatures
    total_scanned = 0

    for replay, label in load_replays(episodes_source, limit=limit):
        total_scanned += 1

        # Get the winning seat
        try:
            rewards = replay.get("rewards") or []
            if not isinstance(rewards, (list, tuple)) or len(rewards) != 2:
                continue
            winner_seat = 0 if rewards[0] > rewards[1] else 1
        except Exception:
            continue

        # Get team names
        try:
            names = team_names(replay)
            if not names:
                continue
        except Exception:
            continue

        winner_name = names[winner_seat]
        winner_norm = normalize_team_name(winner_name)

        # Check if winner is in target set
        if winner_norm not in target_teams:
            continue

        # Extract decklists
        try:
            decks = seat_decklists(replay)
            if not decks:
                continue
        except Exception:
            continue

        winner_deck = decks[winner_seat]
        if not winner_deck or len(winner_deck) != 60:
            continue

        # Canonicalize deck signature
        deck_sig = tuple(sorted(int(c) for c in winner_deck))
        team_decks[winner_name][deck_sig] += 1

    # Convert Counters to sorted lists
    result = {}
    total_matches = 0
    for team, counter in team_decks.items():
        # Sort by count descending, then by signature for determinism
        result[team] = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
        total_matches += sum(count for _, count in result[team])

    return result, total_scanned, total_matches


def cluster_decks(team_decks: dict) -> dict:
    """Cluster decklists by signature across all teams.

    Returns {deck_sig -> {'count': n, 'teams': [team1, ...], 'plays': [(team, count), ...]}}
    """
    clusters = defaultdict(lambda: {'count': 0, 'teams': set(), 'plays': []})

    for team, decks in team_decks.items():
        for deck_sig, count in decks:
            clusters[deck_sig]['count'] += count
            clusters[deck_sig]['teams'].add(team)
            clusters[deck_sig]['plays'].append((team, count))

    # Sort teams sets to lists for JSON serialization
    for sig in clusters:
        clusters[sig]['teams'] = sorted(clusters[sig]['teams'])

    return clusters


def run(
    episodes_source: Path | str = None,
    min_rating: float = MIN_RATING,
    leaderboard_zip: Path = LEADERBOARD_PATH,
    limit: int | None = None,
) -> bool:
    """Mine top-rated decks and write outputs."""
    if episodes_source is None:
        # Use the newest episode dataset ZIP
        episodes_source = newest_dataset(EPISODES_DIR)
        if not episodes_source:
            print(f"ERROR: no episode dataset found in {EPISODES_DIR}", file=sys.stderr)
            return False
    else:
        episodes_source = Path(episodes_source)

    if not episodes_source.exists():
        print(f"ERROR: episodes source not found: {episodes_source}", file=sys.stderr)
        return False

    if not leaderboard_zip.exists():
        print(f"ERROR: leaderboard not found: {leaderboard_zip}", file=sys.stderr)
        return False

    print(f"Mining top-rated ({min_rating}+) decklists...")
    team_decks, total_scanned, total_matches = mine_top_rated_decks(
        episodes_source, min_rating, leaderboard_zip, limit=limit
    )

    print(f"Scanned {total_scanned} episodes, found {total_matches} wins by {len(team_decks)} teams")

    # Cluster by deck signature
    clusters = cluster_decks(team_decks)
    print(f"Clustered into {len(clusters)} unique deck signatures")

    # Write machine-readable output
    output = {
        'min_rating': min_rating,
        'total_episodes_scanned': total_scanned,
        'total_matches': total_matches,
        'teams_count': len(team_decks),
        'unique_signatures': len(clusters),
        'team_decks': {
            team: [
                {
                    'signature': list(sig),
                    'count': count,
                    'cards': len(sig) if isinstance(sig, (list, tuple)) else 60,
                }
                for sig, count in decks
            ]
            for team, decks in team_decks.items()
        },
        'clusters': {
            str(list(sig)): {
                'count': cluster['count'],
                'team_count': len(cluster['teams']),
                'teams': cluster['teams'],
                'plays': [
                    {'team': team, 'count': count}
                    for team, count in sorted(cluster['plays'], key=lambda kv: (-kv[1], kv[0]))
                ],
            }
            for sig, cluster in clusters.items()
        },
    }

    # Output path
    output_path = derived_path('top_rated_decks.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Wrote {output_path}")

    # Write analysis report
    report_path = _ROOT / "analysis" / "top_rated_mining.md"
    report_lines = [
        "# U39 Top-Rated Deck Mining (Step 1)",
        "",
        "## Summary",
        f"- Minimum rating: {min_rating}",
        f"- Episodes scanned: {total_scanned}",
        f"- Winning plays by 800+ teams: {total_matches}",
        f"- Unique teams: {len(team_decks)}",
        f"- Unique deck signatures: {len(clusters)}",
        "",
        "## Top 20 Deck Clusters",
        "",
    ]

    # Sort clusters by frequency
    top_clusters = sorted(
        clusters.items(),
        key=lambda kv: (-kv[1]['count'], kv[0]),
    )[:20]

    for rank, (sig, cluster) in enumerate(top_clusters, 1):
        team_list = ', '.join(cluster['teams'][:5])
        if len(cluster['teams']) > 5:
            team_list += f", ... ({len(cluster['teams'])} teams total)"
        report_lines.extend([
            f"### Cluster {rank}: {cluster['count']} plays by {len(cluster['teams'])} teams",
            f"- Teams: {team_list}",
            f"- Signature: {list(sig[:10])}... (60 cards)",
            "",
        ])

    report_path.write_text('\n'.join(report_lines), encoding='utf-8')
    print(f"Wrote {report_path}")

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Mine 800+ rated decks from episode dumps"
    )
    parser.add_argument(
        "--episodes",
        type=Path,
        default=None,
        help=f"Episode dataset ZIP or directory (default: newest in {EPISODES_DIR})",
    )
    parser.add_argument(
        "--min-rating",
        type=float,
        default=MIN_RATING,
        help=f"Minimum team rating (default: {MIN_RATING})",
    )
    parser.add_argument(
        "--leaderboard",
        type=Path,
        default=LEADERBOARD_PATH,
        help=f"Leaderboard ZIP (default: {LEADERBOARD_PATH})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of episodes to scan (for testing)",
    )
    args = parser.parse_args()

    if not run(args.episodes, args.min_rating, args.leaderboard, args.limit):
        sys.exit(1)
