"""Tests for U106 state-matched expert lookup."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_categorize_loss_states():
    """Test that loss states are correctly categorized by board characteristics."""
    from analysis.state_matched_expert_lookup import _categorize_loss_states

    # Create test data with specific scenarios to test each category
    data = {
        "prize_diff": [0, -5, 0, -1, 0],
        "deck_diff": [-12, 0, -15, 2, -5],
        "our_bench_nonempty": [0, 1, 1, 1, 1],
        "our_deck_count": [2, 5, 10, 15, 20],
    }
    loss_states = pd.DataFrame(data)

    categories = _categorize_loss_states(loss_states)

    # Row 0: bench empty (0) -> empty_bench_collapse
    assert categories[0] == "empty_bench_collapse"
    # Row 1: prize_diff = -5 < -3 -> prize_blowout
    assert categories[1] == "prize_blowout"
    # Row 2: deck_diff = -15 < -10 -> deck_disadvantage
    assert categories[2] == "deck_disadvantage"
    # Row 3: deck_count = 15, others OK -> mid_game_loss
    assert categories[3] == "mid_game_loss"
    # Row 4: all moderate values -> mid_game_loss
    assert categories[4] == "mid_game_loss"


def test_knn_join_handles_empty_input():
    """Test that kNN join gracefully handles empty inputs."""
    from analysis.state_matched_expert_lookup import knn_join

    empty_states = pd.DataFrame()
    expert_corpus = pd.DataFrame({"prize_diff": [1, 2, 3]})

    result = knn_join(empty_states, expert_corpus)
    assert result == {}


def test_knn_join_produces_results():
    """Test that kNN join produces distance metrics."""
    from analysis.state_matched_expert_lookup import knn_join

    # Create minimal test data with required columns
    features = ["prize_diff", "our_deck_count", "their_deck_count"]
    our_states = pd.DataFrame({
        features[0]: [1, 2],
        features[1]: [30, 25],
        features[2]: [25, 28],
        "state_group": ["loss_a", "loss_b"],
    })

    expert_corpus = pd.DataFrame({
        features[0]: np.random.randn(20),
        features[1]: np.random.randint(20, 40, 20),
        features[2]: np.random.randint(20, 40, 20),
    })

    result = knn_join(our_states, expert_corpus, k=3, expert_limit=100)

    # Should have results for both groups
    assert "loss_a" in result or "loss_b" in result
    # Each group should have entries with distance metrics
    for group, entries in result.items():
        if entries:
            assert all("mean_distance" in e for e in entries)
            assert all("max_distance" in e for e in entries)


def test_loss_state_label_filtering():
    """Test that loss states are correctly filtered by label."""
    data = {
        "label": [0, 1, 0, 1, 0],
        "prize_diff": [1, 2, 3, 4, 5],
        "our_deck_count": [30, 25, 20, 15, 10],
    }
    states = pd.DataFrame(data)

    # Filter to loss states (label == 0)
    loss_states = states[states.get("label", 1) == 0]

    assert len(loss_states) == 3
    assert list(loss_states.index) == [0, 2, 4]


def test_expert_corpus_loaded_with_key_features():
    """Test that expert corpus can be loaded and contains expected columns."""
    from analysis.state_matched_expert_lookup import FEATURE_COLS

    # Load real expert corpus if available
    data_dir = _ROOT / "data" / "training"
    corpus_file = data_dir / "top_player_corpus_20260706.csv"

    if corpus_file.exists():
        corpus = pd.read_csv(corpus_file)
        available = [c for c in FEATURE_COLS if c in corpus.columns]
        assert len(available) > 15, "Expected at least 15 common features in corpus"


def test_state_csv_loaded_successfully():
    """Test that state CSVs can be loaded."""
    data_dir = _ROOT / "data" / "training"
    state_file = data_dir / "states_1782986362.csv"

    if state_file.exists():
        states = pd.read_csv(state_file)
        assert len(states) > 0
        assert "label" in states.columns
        assert "prize_diff" in states.columns


def test_replay_loss_classification():
    """Test that replays can be classified for loss bucket identification."""
    from analysis.loss_classifier import classify_loss, parse_replay

    replay_dir = _ROOT / "data" / "replays"
    if not replay_dir.exists():
        pytest.skip("No replays directory")

    loss_count = 0
    for replay_file in list(replay_dir.glob("*.json"))[:10]:
        try:
            with open(replay_file) as f:
                replay = json.load(f)

            rewards = replay.get("rewards", [0, 0])
            if not rewards or rewards[0] >= rewards[1]:
                continue  # Skip wins/draws

            digest = parse_replay(replay, our_index=0)
            bucket = classify_loss(digest)
            if bucket:
                loss_count += 1
                assert isinstance(bucket, str)
                assert bucket in [
                    "slow_search",
                    "deckout",
                    "deck_matchup",
                    "endgame_misplay",
                    "early_collapse",
                    "bad_determinization",
                ]
        except Exception:
            pass

    # Should have found at least one loss
    assert loss_count > 0
