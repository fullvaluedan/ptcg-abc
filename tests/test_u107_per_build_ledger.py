"""Tests for U107 per-build loss ledger infrastructure."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.loop_state import (
    classify_dirs_per_build,
    loss_distribution_from_dirs,
    read_current,
)


class TestPerBuildLossLedger:
    """U107: segregate losses by submission ref."""

    def test_loss_distribution_from_dirs_with_ref_filter(self):
        """loss_distribution_from_dirs accepts ref_filter parameter."""
        # Call with ref_filter should use classify_dirs_per_build path
        result = loss_distribution_from_dirs(
            ["data/replays"], ref_filter=["54315802"]
        )
        assert "ref_filter" in result
        assert result["ref_filter"] == ["54315802"]
        assert isinstance(result["games"], int)
        assert isinstance(result["sample_size"], int)

    def test_loss_distribution_from_dirs_without_ref_filter(self):
        """loss_distribution_from_dirs works without ref_filter (backward compat)."""
        result = loss_distribution_from_dirs(["data/replays"])
        assert "ref_filter" in result
        assert result["ref_filter"] == []
        assert isinstance(result["games"], int)

    def test_loss_distribution_from_dirs_multiple_refs(self):
        """loss_distribution_from_dirs supports multiple refs in filter."""
        result = loss_distribution_from_dirs(
            ["data/replays"], ref_filter=["54315802", "54315565"]
        )
        assert set(result["ref_filter"]) == {"54315802", "54315565"}
        assert result["games"] >= 65  # At least the shadow-king episodes

    def test_classify_dirs_per_build_returns_correct_structure(self):
        """classify_dirs_per_build returns proper report structure."""
        result = classify_dirs_per_build(["data/replays"], ref_filter=["54315802"])
        assert "games" in result
        assert "wins" in result
        assert "losses" in result
        assert "buckets" in result
        assert "top_bucket" in result

    def test_classify_dirs_per_build_filters_episodes(self):
        """classify_dirs_per_build correctly filters episodes by ref."""
        # Get total for one ref
        one_ref = classify_dirs_per_build(["data/replays"], ref_filter=["54315802"])
        # Get total for another ref
        other_ref = classify_dirs_per_build(["data/replays"], ref_filter=["54315565"])
        # Get total for both
        both_refs = classify_dirs_per_build(
            ["data/replays"], ref_filter=["54315802", "54315565"]
        )

        # Both should be less than or equal to the sum
        total_one_plus_other = one_ref["games"] + other_ref["games"]
        assert both_refs["games"] >= total_one_plus_other

    def test_manifest_persists_episode_to_ref_mapping(self):
        """Episode-to-ref manifest exists and is populated."""
        manifest_path = Path("data/episode_to_ref.json")
        assert manifest_path.exists(), "data/episode_to_ref.json should exist"

        with open(manifest_path) as f:
            manifest = json.load(f)

        assert isinstance(manifest, dict), "manifest should be a dict"
        assert len(manifest) > 0, "manifest should have entries"
        # Check that values are refs (strings or ints)
        for ep_id, ref in list(manifest.items())[:5]:
            assert isinstance(ep_id, str), f"episode_id {ep_id} should be string"
            assert isinstance(ref, (str, int)), f"ref for {ep_id} should be str/int"
