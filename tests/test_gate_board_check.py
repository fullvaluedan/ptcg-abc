"""Tests for tools/gate_board_check.py."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from tools import gate_board_check


class TestGateBoardCheck(unittest.TestCase):
    """Test board-check gating logic."""

    def test_should_gate_open_no_last_check(self):
        """Gate opens on first check (no prior baseline)."""
        with patch.object(
            gate_board_check, "max_newest_episode", return_value=1000
        ) as mock_max:
            result = gate_board_check.should_gate_open(["ref1"], last_check_episode=None)
            self.assertTrue(result)
            mock_max.assert_called_once_with(["ref1"])

    def test_should_gate_open_episode_advanced(self):
        """Gate opens when newest episode has advanced."""
        with patch.object(
            gate_board_check, "max_newest_episode", return_value=2000
        ) as mock_max:
            result = gate_board_check.should_gate_open(
                ["ref1"], last_check_episode=1000
            )
            self.assertTrue(result)
            mock_max.assert_called_once_with(["ref1"])

    def test_should_gate_closed_episode_unchanged(self):
        """Gate closes when newest episode is unchanged."""
        with patch.object(
            gate_board_check, "max_newest_episode", return_value=1000
        ) as mock_max:
            result = gate_board_check.should_gate_open(
                ["ref1"], last_check_episode=1000
            )
            self.assertFalse(result)
            mock_max.assert_called_once_with(["ref1"])

    def test_should_gate_closed_query_failed(self):
        """Gate closes when episode query returns None."""
        with patch.object(
            gate_board_check, "max_newest_episode", return_value=None
        ) as mock_max:
            result = gate_board_check.should_gate_open(
                ["ref1"], last_check_episode=1000
            )
            self.assertFalse(result)
            mock_max.assert_called_once_with(["ref1"])

    def test_max_newest_episode_single_ref(self):
        """max_newest_episode returns the episode ID for a single ref."""
        with patch.object(
            gate_board_check, "newest_episode_for_ref", return_value=5000
        ) as mock_newest:
            result = gate_board_check.max_newest_episode(["ref1"])
            self.assertEqual(result, 5000)
            mock_newest.assert_called_once_with("ref1")

    def test_max_newest_episode_multiple_refs(self):
        """max_newest_episode returns the max across multiple refs."""
        with patch.object(
            gate_board_check,
            "newest_episode_for_ref",
            side_effect=[5000, 6000, 5500],
        ) as mock_newest:
            result = gate_board_check.max_newest_episode(["ref1", "ref2", "ref3"])
            self.assertEqual(result, 6000)
            self.assertEqual(mock_newest.call_count, 3)

    def test_max_newest_episode_some_failures(self):
        """max_newest_episode skips None results and returns max of valid ones."""
        with patch.object(
            gate_board_check,
            "newest_episode_for_ref",
            side_effect=[5000, None, 5500],
        ) as mock_newest:
            result = gate_board_check.max_newest_episode(["ref1", "ref2", "ref3"])
            self.assertEqual(result, 5500)
            self.assertEqual(mock_newest.call_count, 3)

    def test_max_newest_episode_all_failures(self):
        """max_newest_episode returns None when all queries fail."""
        with patch.object(
            gate_board_check,
            "newest_episode_for_ref",
            side_effect=[None, None],
        ) as mock_newest:
            result = gate_board_check.max_newest_episode(["ref1", "ref2"])
            self.assertIsNone(result)
            self.assertEqual(mock_newest.call_count, 2)

    def test_newest_episode_for_ref_happy_path(self):
        """newest_episode_for_ref parses the last episode ID from CLI output."""
        mock_output = (
            "Episode  Seed  NumSteps  ScoringType  TeamNames\n"
            "1000     123   42        standard     TeamA v TeamB\n"
            "1001     456   50        standard     TeamA v TeamC\n"
        )
        with patch.object(
            gate_board_check,
            "run_kaggle",
            return_value={"ok": True, "output": mock_output},
        ) as mock_run:
            result = gate_board_check.newest_episode_for_ref("ref123")
            self.assertEqual(result, 1001)
            mock_run.assert_called_once()

    def test_newest_episode_for_ref_single_episode(self):
        """newest_episode_for_ref handles single episode output."""
        mock_output = "Episode  Seed  NumSteps  ScoringType  TeamNames\n" "2000     789   55        standard     TeamA v TeamD\n"
        with patch.object(
            gate_board_check,
            "run_kaggle",
            return_value={"ok": True, "output": mock_output},
        ) as mock_run:
            result = gate_board_check.newest_episode_for_ref("ref456")
            self.assertEqual(result, 2000)

    def test_newest_episode_for_ref_query_failed(self):
        """newest_episode_for_ref returns None on Kaggle API error."""
        with patch.object(
            gate_board_check,
            "run_kaggle",
            return_value={"ok": False, "error": "unauthorized"},
        ) as mock_run:
            result = gate_board_check.newest_episode_for_ref("ref789")
            self.assertIsNone(result)

    def test_newest_episode_for_ref_parse_error(self):
        """newest_episode_for_ref returns None on malformed output."""
        with patch.object(
            gate_board_check,
            "run_kaggle",
            return_value={"ok": True, "output": "Header only\n"},
        ) as mock_run:
            result = gate_board_check.newest_episode_for_ref("refbad")
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
