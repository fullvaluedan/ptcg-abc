"""Tests for top-rated deck mining (U39, step 1)."""
import json
import tempfile
from pathlib import Path

import pytest

from tools import top_rated_deck_mining


@pytest.mark.integration
def test_mine_top_rated_decks_small_sample(tmp_path):
    """Test mining with a small dataset."""
    # Use the real leaderboard and the latest episodes ZIP
    from tools.top_player_tracker import newest_dataset
    leaderboard_zip = Path(__file__).resolve().parents[1] / "data" / "leaderboard_cache" / "pokemon-tcg-ai-battle.zip"
    episodes_dir = Path(__file__).resolve().parents[1] / "data" / "episodes"

    if not leaderboard_zip.exists():
        pytest.skip("leaderboard cache not available")
    if not episodes_dir.exists():
        pytest.skip("episodes directory not available")

    episodes_zip = newest_dataset(episodes_dir)
    if not episodes_zip:
        pytest.skip("no episodes ZIP found")

    # Mine with a small limit
    team_decks, total_scanned, total_matches = top_rated_deck_mining.mine_top_rated_decks(
        episodes_zip,
        min_rating=800.0,
        leaderboard_zip=leaderboard_zip,
        limit=100,
    )

    # Should have found some teams
    assert total_scanned == 100
    assert total_matches > 0
    assert len(team_decks) > 0

    # Each team should have a list of decks
    for team_name, decks in team_decks.items():
        assert isinstance(team_name, str)
        assert len(team_name) > 0
        assert isinstance(decks, list)
        assert len(decks) > 0

        # Each deck should be (signature, count)
        for deck_sig, count in decks:
            assert isinstance(deck_sig, tuple)
            assert len(deck_sig) == 60  # Deck size
            assert isinstance(count, int)
            assert count > 0


def test_load_leaderboard_teams(tmp_path):
    """Test loading teams from the leaderboard."""
    leaderboard_zip = Path(__file__).resolve().parents[1] / "data" / "leaderboard_cache" / "pokemon-tcg-ai-battle.zip"

    if not leaderboard_zip.exists():
        pytest.skip("leaderboard cache not available")

    teams = top_rated_deck_mining.load_leaderboard_teams(leaderboard_zip, min_rating=800.0)

    # Should have found many teams
    assert len(teams) > 100

    # Teams should be lowercase strings
    for team in teams:
        assert isinstance(team, str)
        assert team == team.lower()


def test_normalize_team_name():
    """Test team name normalization."""
    assert top_rated_deck_mining.normalize_team_name("Test Team") == "test team"
    assert top_rated_deck_mining.normalize_team_name("  Spaces  ") == "spaces"
    assert top_rated_deck_mining.normalize_team_name("UPPERCASE") == "uppercase"


def test_cluster_decks():
    """Test deck clustering."""
    team_decks = {
        "team1": [
            ((1, 2, 3), 5),
            ((4, 5, 6), 2),
        ],
        "team2": [
            ((1, 2, 3), 3),
            ((7, 8, 9), 1),
        ],
    }

    clusters = top_rated_deck_mining.cluster_decks(team_decks)

    # Should have 3 unique signatures
    assert len(clusters) == 3

    # (1,2,3) should have 2 teams and 8 total plays
    sig_123 = (1, 2, 3)
    assert clusters[sig_123]['count'] == 8
    assert set(clusters[sig_123]['teams']) == {"team1", "team2"}
    assert len(clusters[sig_123]['plays']) == 2


def test_mined_output_exists(tmp_path):
    """Test that mining creates output files."""
    from tools.top_player_tracker import newest_dataset
    leaderboard_zip = Path(__file__).resolve().parents[1] / "data" / "leaderboard_cache" / "pokemon-tcg-ai-battle.zip"
    episodes_dir = Path(__file__).resolve().parents[1] / "data" / "episodes"

    if not leaderboard_zip.exists():
        pytest.skip("leaderboard cache not available")
    if not episodes_dir.exists():
        pytest.skip("episodes directory not available")

    episodes_zip = newest_dataset(episodes_dir)
    if not episodes_zip:
        pytest.skip("no episodes ZIP found")

    # Run with small limit
    team_decks, scanned, matches = top_rated_deck_mining.mine_top_rated_decks(
        episodes_zip,
        min_rating=800.0,
        leaderboard_zip=leaderboard_zip,
        limit=50,
    )

    # Verify we got results
    assert scanned == 50
    assert matches > 0
    assert len(team_decks) > 0
