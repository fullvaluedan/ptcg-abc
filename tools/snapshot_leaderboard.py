"""Snapshot the current leaderboard and track median/percentile drift."""
import argparse
import csv
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

CACHE_DIR = _ROOT / "data" / "leaderboard_cache"
DRIFT_LOG = CACHE_DIR / "drift_log.jsonl"


def extract_leaderboard_scores(zip_path):
    """Extract scores from a leaderboard zip, returning (timestamp, scores list)."""
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.endswith('.csv'):
                text = zf.read(name).decode('utf-8-sig')
                rows = list(csv.DictReader(text.splitlines()))
                scores = []
                timestamp = None
                for row in rows:
                    try:
                        score = float(row['Score'])
                        scores.append(score)
                        if not timestamp and row.get('LastSubmissionDate'):
                            timestamp = row['LastSubmissionDate']
                    except ValueError:
                        pass
                scores.sort()
                return timestamp, sorted(scores)
    return None, []


def compute_percentiles(scores):
    """Compute percentile statistics."""
    n = len(scores)
    if n == 0:
        return {}
    
    def percentile(p):
        idx = int(n * p / 100.0)
        return scores[min(idx, n-1)]
    
    return {
        'count': n,
        'min': float(scores[0]),
        'p25': float(percentile(25)),
        'median': float(percentile(50)),
        'p75': float(percentile(75)),
        'p95': float(percentile(95)),
        'max': float(scores[-1]),
    }


def snapshot(leaderboard_zip_path, write=False):
    """Snapshot a leaderboard zip, optionally appending drift to the log."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    leaderboard_zip = Path(leaderboard_zip_path)
    
    timestamp, scores = extract_leaderboard_scores(leaderboard_zip)
    if not scores:
        print(f"ERROR: could not extract scores from {leaderboard_zip}", file=sys.stderr)
        return False
    
    stats = compute_percentiles(scores)
    
    # Read prior snapshot from the zip in cache (if it exists)
    prior_stats = None
    prior_timestamp = None
    cache_zip = CACHE_DIR / "pokemon-tcg-ai-battle.zip"
    if cache_zip.exists():
        try:
            prior_timestamp, prior_scores = extract_leaderboard_scores(cache_zip)
            prior_stats = compute_percentiles(prior_scores)
        except Exception as e:
            print(f"WARNING: could not read prior cache: {e}", file=sys.stderr)
    
    # Compute drift
    drift = {}
    if prior_stats:
        for key in ['count', 'median', 'p25', 'p75', 'p95']:
            if key in prior_stats and key in stats:
                if key == 'count':
                    drift[key] = stats[key] - prior_stats[key]
                else:
                    drift[key] = round(stats[key] - prior_stats[key], 1)
    
    result = {
        'timestamp': timestamp,
        'utc_now': datetime.now(timezone.utc).isoformat(),
        'stats': stats,
        'drift': drift,
    }
    
    if write:
        # Move the new leaderboard to cache
        import shutil
        shutil.move(str(leaderboard_zip), str(cache_zip))
        
        # Append to drift log
        with open(DRIFT_LOG, 'a') as f:
            f.write(json.dumps(result) + '\n')
        
        print(f"Cached leaderboard and logged drift")
        print(f"Timestamp: {timestamp}")
        print(f"Teams: {stats['count']} (drift {drift.get('count', 0):+d})")
        print(f"Median: {stats['median']:.1f} (drift {drift.get('median', 0):+.1f})")
        print(f"p95: {stats['p95']:.1f} (drift {drift.get('p95', 0):+.1f})")
    else:
        print(json.dumps(result, indent=2))
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--leaderboard", default="pokemon-tcg-ai-battle.zip",
                        help="path to leaderboard zip")
    parser.add_argument("--write", action="store_true",
                        help="write snapshot to cache and log")
    args = parser.parse_args()
    
    if not snapshot(args.leaderboard, write=args.write):
        sys.exit(1)
