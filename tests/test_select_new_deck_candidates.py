"""Tests for tools/select_new_deck_candidates.py."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.select_new_deck_candidates import (
    load_existing_signatures,
    rank_new_candidates,
    slug_for,
    write_candidate_decks,
)


class TestLoadExistingSignatures:
    """load_existing_signatures reads all decks/*.csv and builds a signature index."""

    def test_empty_dir(self):
        """Returns {} if no csv files exist."""
        with tempfile.TemporaryDirectory() as td:
            result = load_existing_signatures(td)
            assert result == {}

    def test_single_valid_deck(self):
        """Reads a single 60-card deck and indexes it by sorted tuple."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "test.csv"
            ids = list(range(1, 61))
            path.write_text("\n".join(str(i) for i in ids) + "\n", encoding="utf-8")
            result = load_existing_signatures(td)
            key = tuple(sorted(ids))
            assert key in result
            assert result[key] == str(path)

    def test_skips_malformed_file(self):
        """Skips files that can't be parsed as integers."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.csv"
            path.write_text("not a number\n", encoding="utf-8")
            result = load_existing_signatures(td)
            assert result == {}

    def test_skips_wrong_card_count(self):
        """Skips files with != 60 cards."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "short.csv"
            ids = list(range(1, 50))  # 49 cards
            path.write_text("\n".join(str(i) for i in ids) + "\n", encoding="utf-8")
            result = load_existing_signatures(td)
            assert result == {}

    def test_multiple_decks(self):
        """Handles multiple valid decks and one invalid."""
        with tempfile.TemporaryDirectory() as td:
            valid1 = Path(td) / "a.csv"
            valid1.write_text("\n".join(str(i) for i in range(1, 61)) + "\n", encoding="utf-8")
            valid2 = Path(td) / "b.csv"
            valid2.write_text("\n".join(str(i) for i in range(1000, 1060)) + "\n", encoding="utf-8")
            invalid = Path(td) / "c.csv"
            invalid.write_text("x\n", encoding="utf-8")
            result = load_existing_signatures(td)
            assert len(result) == 2
            assert all(len(sig) == 60 for sig in result.keys())

    def test_handles_missing_dir(self):
        """Returns {} if directory doesn't exist."""
        result = load_existing_signatures("/nonexistent/path")
        assert result == {}


class TestSlugFor:
    """slug_for generates filesystem-safe names from team names."""

    def test_empty_team_list(self):
        """Returns 'unknown' if teams is empty."""
        assert slug_for([]) == "unknown"
        assert slug_for(None) == "unknown"

    def test_simple_name(self):
        """Lowercases and keeps alphanumeric."""
        assert slug_for(["SimpleTeam"]) == "simpleteam"

    def test_special_chars_converted_to_underscore(self):
        """Replaces non-alphanumeric with underscore."""
        assert slug_for(["Team-Name!"]) == "team_name"
        assert slug_for(["A B  C"]) == "a_b_c"

    def test_strips_leading_trailing_underscores(self):
        """Removes leading/trailing underscores."""
        assert slug_for(["_team_"]) == "team"
        assert slug_for(["!!!team!!!"]) == "team"

    def test_uses_first_team_only(self):
        """Takes name from first team in list."""
        assert slug_for(["First", "Second"]) == "first"

    def test_returns_unknown_for_empty_result(self):
        """Returns 'unknown' if slug reduces to empty string."""
        assert slug_for(["___"]) == "unknown"
        assert slug_for(["!!!"]) == "unknown"


class TestRankNewCandidates:
    """rank_new_candidates dedupes clusters against existing decks."""

    def test_empty_clusters(self):
        """Returns empty new/duplicate lists if no clusters."""
        result = rank_new_candidates({}, {})
        assert result == {"new": [], "duplicates": []}

    def test_all_new_candidates(self):
        """All clusters are new if no existing sigs."""
        clusters = {
            (1, 2, 3): {"count": 10, "teams": ["A"]},
            (4, 5, 6): {"count": 5, "teams": ["B"]},
        }
        result = rank_new_candidates(clusters, {})
        assert len(result["new"]) == 2
        assert len(result["duplicates"]) == 0
        # Should be ranked by count descending
        assert result["new"][0]["count"] == 10
        assert result["new"][1]["count"] == 5

    def test_detects_duplicates(self):
        """Identifies duplicates of existing decks."""
        sig1 = (1, 2, 3)
        clusters = {sig1: {"count": 10, "teams": ["A"]}}
        existing = {tuple(sorted(sig1)): "/path/to/existing.csv"}
        result = rank_new_candidates(clusters, existing)
        assert len(result["new"]) == 0
        assert len(result["duplicates"]) == 1
        assert result["duplicates"][0]["duplicate_of"] == "/path/to/existing.csv"

    def test_top_k_limits_new(self):
        """Respects top_k limit for new candidates."""
        clusters = {
            (1, 2, 3): {"count": 30, "teams": ["A"]},
            (4, 5, 6): {"count": 20, "teams": ["B"]},
            (7, 8, 9): {"count": 10, "teams": ["C"]},
        }
        result = rank_new_candidates(clusters, {}, top_k=2)
        assert len(result["new"]) == 2
        assert result["new"][0]["count"] == 30
        assert result["new"][1]["count"] == 20

    def test_mixed_new_and_duplicates(self):
        """Handles mix of new and duplicate clusters."""
        sig_new = (1, 2, 3)
        sig_dup = (4, 5, 6)
        clusters = {
            sig_new: {"count": 20, "teams": ["A"]},
            sig_dup: {"count": 10, "teams": ["B"]},
        }
        existing = {tuple(sorted(sig_dup)): "/path/dup.csv"}
        result = rank_new_candidates(clusters, existing, top_k=10)
        assert len(result["new"]) == 1
        assert result["new"][0]["deck"] == list(sig_new)
        assert len(result["duplicates"]) == 1
        assert result["duplicates"][0]["deck"] == list(sig_dup)

    def test_entry_structure(self):
        """Returned entries have expected keys."""
        sig = (1, 2, 3)
        clusters = {sig: {"count": 5, "teams": ["TeamA", "TeamB"]}}
        result = rank_new_candidates(clusters, {})
        entry = result["new"][0]
        assert "deck" in entry
        assert "count" in entry
        assert "teams" in entry
        assert entry["deck"] == list(sig)
        assert entry["count"] == 5
        assert sorted(entry["teams"]) == ["TeamA", "TeamB"]


class TestWriteCandidateDecks:
    """write_candidate_decks writes valid candidates to files."""

    def test_write_valid_candidate(self):
        """Writes a legal deck to decks/candidate_<slug>.csv."""
        with tempfile.TemporaryDirectory() as td:
            entries = [
                {
                    "deck": list(range(1, 61)),
                    "count": 10,
                    "teams": ["TestTeam"],
                }
            ]
            mock_validate = MagicMock(return_value={"ok": True})
            result = write_candidate_decks(entries, td, mock_validate)
            assert len(result) == 1
            assert result[0]["ok"]
            assert result[0]["slug"] == "testteam"
            assert Path(td, "candidate_testteam.csv").exists()

    def test_skips_invalid_candidate(self):
        """Rejects illegal decks and records the error."""
        with tempfile.TemporaryDirectory() as td:
            entries = [
                {"deck": list(range(1, 61)), "count": 10, "teams": ["BadTeam"]}
            ]
            mock_validate = MagicMock(
                return_value={"ok": False, "rule_errors": ["too many water"]}
            )
            result = write_candidate_decks(entries, td, mock_validate)
            assert len(result) == 1
            assert not result[0]["ok"]
            assert "rule_errors" in result[0]
            assert not Path(td, "candidate_badteam.csv").exists()

    def test_slug_deduplication(self):
        """Handles multiple teams with same slug by adding suffix."""
        with tempfile.TemporaryDirectory() as td:
            entries = [
                {"deck": list(range(1, 61)), "count": 10, "teams": ["TeamA"]},
                {"deck": list(range(100, 160)), "count": 5, "teams": ["TeamA"]},
            ]
            mock_validate = MagicMock(return_value={"ok": True})
            result = write_candidate_decks(entries, td, mock_validate)
            assert len(result) == 2
            assert result[0]["slug"] == "teama"
            assert result[1]["slug"] == "teama_2"
            assert Path(td, "candidate_teama.csv").exists()
            assert Path(td, "candidate_teama_2.csv").exists()

    def test_creates_decks_dir_if_missing(self):
        """Creates the directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as td:
            decks_dir = Path(td) / "subdir" / "decks"
            entries = [
                {"deck": list(range(1, 61)), "count": 10, "teams": ["Test"]}
            ]
            mock_validate = MagicMock(return_value={"ok": True})
            result = write_candidate_decks(entries, str(decks_dir), mock_validate)
            assert len(result) == 1
            assert result[0]["ok"]
            assert decks_dir.exists()

    def test_file_format(self):
        """Writes deck as newline-separated card IDs."""
        with tempfile.TemporaryDirectory() as td:
            cards = list(range(1, 61))
            entries = [
                {"deck": cards, "count": 10, "teams": ["Test"]}
            ]
            mock_validate = MagicMock(return_value={"ok": True})
            result = write_candidate_decks(entries, td, mock_validate)
            written_path = Path(td) / "candidate_test.csv"
            content = written_path.read_text(encoding="utf-8").strip()
            written_cards = [int(line) for line in content.split("\n")]
            assert written_cards == cards
