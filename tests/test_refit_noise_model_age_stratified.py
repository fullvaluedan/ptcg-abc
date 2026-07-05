"""Tests for age-stratified noise model refitting."""
import pytest
from datetime import datetime
from tools.refit_noise_model_age_stratified import (
    extract_date_from_note,
    compute_age_hours,
    stratify_reads_by_age,
    compute_stratified_stats,
    family_key,
)


def test_extract_date_from_note():
    """Test date extraction from note field."""
    assert extract_date_from_note("Board check 2026-07-04: 540.9") == datetime(2026, 7, 4)
    assert extract_date_from_note("No date here") is None
    assert extract_date_from_note("") is None
    assert extract_date_from_note("SETTLED WIN 2026-07-04: 561.1") == datetime(2026, 7, 4)


def test_compute_age_hours():
    """Test age computation in hours."""
    ref = datetime(2026, 7, 5, 0, 0, 0)
    read = datetime(2026, 7, 4, 12, 0, 0)  # 12 hours ago
    assert compute_age_hours(read, ref) == 12.0

    read = datetime(2026, 7, 3, 0, 0, 0)  # 2 days ago = 48 hours
    assert compute_age_hours(read, ref) == 48.0

    read = datetime(2026, 7, 2, 0, 0, 0)  # 3 days ago = 72 hours
    assert compute_age_hours(read, ref) == 72.0

    assert compute_age_hours(None, ref) is None


def test_family_key():
    """Test family key extraction."""
    assert family_key("heuristic+trolley (king-copy revert, 2026-07-04)") == "heuristic+trolley"
    assert family_key("heuristic+trolley-ability (floor restoration)") == "heuristic+trolley-ability"
    assert family_key("heuristic+trolley") == "heuristic+trolley"


def test_stratify_reads_by_age():
    """Test stratification by age."""
    reference_date = datetime(2026, 7, 5)

    ledger = [
        # Fresh (<48h old, from 2026-07-05)
        {"build": "heuristic+trolley", "ladder": "500", "note": "Board check 2026-07-05: 500"},
        # Fresh (<48h old, from 2026-07-04 is 24h old)
        {"build": "heuristic+trolley-ability", "ladder": "570", "note": "Board check 2026-07-04: 570"},
        # Aged (>72h old, from 2026-07-02)
        {"build": "heuristic+trolley", "ladder": "550", "note": "Board check 2026-07-02: 550"},
        # Undated
        {"build": "heuristic+trolley", "ladder": "510", "note": "No date here"},
        # Invalid ladder score
        {"build": "heuristic+trolley", "ladder": "invalid", "note": "Board check 2026-07-05: X"},
    ]

    strata = stratify_reads_by_age(ledger, reference_date)

    assert len(strata["<48h"]) == 2
    assert strata["<48h"][0][0] == "heuristic+trolley"
    assert strata["<48h"][0][1] == 500.0
    assert strata["<48h"][1][0] == "heuristic+trolley-ability"
    assert strata["<48h"][1][1] == 570.0

    assert len(strata[">72h"]) == 1
    assert strata[">72h"][0][0] == "heuristic+trolley"
    assert strata[">72h"][0][1] == 550.0

    assert len(strata["48-72h"]) == 0

    assert len(strata["undated"]) == 1
    assert strata["undated"][0] == ("heuristic+trolley", 510.0)


def test_compute_stratified_stats():
    """Test per-stratum statistics computation."""
    strata = {
        "<48h": [("heuristic+trolley", 500.0), ("heuristic+trolley", 510.0)],
        "48-72h": [],
        ">72h": [("heuristic+trolley", 600.0)],
        "undated": []
    }

    stats = compute_stratified_stats(strata)

    # Fresh reads
    assert stats["<48h"]["per_family"]["heuristic+trolley"]["n"] == 2
    assert stats["<48h"]["per_family"]["heuristic+trolley"]["mean"] == 505.0
    assert stats["<48h"]["per_family"]["heuristic+trolley"]["stdev"] == pytest.approx(7.07, abs=0.01)
    assert stats["<48h"]["per_family"]["heuristic+trolley"]["min"] == 500.0
    assert stats["<48h"]["per_family"]["heuristic+trolley"]["max"] == 510.0

    # Aged reads (only 1, so stdev=0)
    assert stats[">72h"]["per_family"]["heuristic+trolley"]["n"] == 1
    assert stats[">72h"]["per_family"]["heuristic+trolley"]["mean"] == 600.0
    assert stats[">72h"]["per_family"]["heuristic+trolley"]["stdev"] == 0.0


def test_stratify_and_compute_empty_strata():
    """Test handling of empty strata."""
    strata = {
        "<48h": [],
        "48-72h": [],
        ">72h": [],
        "undated": []
    }

    stats = compute_stratified_stats(strata)

    for stratum_name in ["<48h", "48-72h", ">72h"]:
        assert stats[stratum_name]["per_family"] == {}
        assert stats[stratum_name]["pooled_n"] == 0
