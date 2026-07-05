"""Tests for tools/snapshot_leaderboard.py."""
import json
import tempfile
import zipfile
from pathlib import Path

from tools import snapshot_leaderboard as ssl


def test_compute_percentiles():
    """Percentile computation matches expected values."""
    scores = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    stats = ssl.compute_percentiles(scores)
    
    assert stats['count'] == 10
    assert stats['min'] == 1.0
    assert stats['max'] == 10.0
    assert stats['median'] == 6.0
    assert stats['p25'] == 3.0
    assert stats['p75'] == 8.0
    assert stats['p95'] == 10.0


def test_extract_leaderboard_scores():
    """Extract leaderboard scores from a test zip."""
    # Create a minimal test CSV
    csv_text = "Rank,Score,LastSubmissionDate\n1,100.0,2026-07-05 12:00:00\n2,50.0,2026-07-05 12:00:00\n"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "test.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("leaderboard.csv", csv_text)
        
        timestamp, scores = ssl.extract_leaderboard_scores(zip_path)
        assert timestamp is not None
        assert scores == [50.0, 100.0]


def test_drift_log_format():
    """Drift log entry has expected JSON structure."""
    with open('data/leaderboard_cache/drift_log.jsonl') as f:
        line = f.readline()
        entry = json.loads(line)
        
        assert 'timestamp' in entry
        assert 'utc_now' in entry
        assert 'stats' in entry
        assert 'drift' in entry
        assert entry['stats']['count'] > 0
        assert entry['stats']['median'] > 0
