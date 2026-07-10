"""Tests for tools/score_wave2_candidates.py (plan 2026-07-10-001, U4).

Hermetic logic tests use a fixture mining-data JSON and a tmp decks dir, so
they never depend on the real data/derived/top_rated_decks.json being
present (that file is gitignored local data). A couple of tests do check the
real materialized decks/candidate_*_w2.csv files against the real mining
data and the dedup report; those skip if the mining data is unavailable in
this environment.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools import score_wave2_candidates as swc  # noqa: E402

FIXTURE_CANDIDATES = [
    {"team": "Alpha Team", "deck_index": 0, "stem": "candidate_alpha_w2"},
    {"team": "beta", "deck_index": 1, "stem": "candidate_beta_w2"},
    {"team": "変化の書ゾロアーク", "deck_index": 0, "stem": "candidate_henka_no_sho_zoroark_w2",
     "original_name": "変化の書ゾロアーク"},
]


def _fixture_signature(seed):
    """A deterministic, sorted 60-int 'signature' distinct per seed."""
    return sorted((seed * 7 + i) % 2000 for i in range(60))


def _write_fixture_mining_data(path):
    data = {
        "team_decks": {
            "Alpha Team": [
                {"signature": _fixture_signature(1), "count": 5, "cards": 60},
            ],
            "beta": [
                {"signature": _fixture_signature(2), "count": 1, "cards": 60},
                {"signature": _fixture_signature(3), "count": 9, "cards": 60},
            ],
            "変化の書ゾロアーク": [
                {"signature": _fixture_signature(4), "count": 6, "cards": 60},
            ],
        }
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return data


def test_materialize_writes_signature_matching_mining_data_not_a_stale_file(tmp_path):
    mining_data = tmp_path / "top_rated_decks.json"
    decks_dir = tmp_path / "decks"
    data = _write_fixture_mining_data(mining_data)

    # Pre-seed a same-stem file with a DIFFERENT (wave-1-like) signature, to
    # prove materialize overwrites rather than silently skipping like
    # tools/dedupe_mined_candidates.py's --create-candidates path does.
    decks_dir.mkdir()
    stale_path = decks_dir / "candidate_alpha_w2.csv"
    stale_path.write_text("\n".join(str(c) for c in _fixture_signature(999)) + "\n", encoding="utf-8")

    written = swc.materialize_wave2_decks(
        candidates=FIXTURE_CANDIDATES, decks_dir=decks_dir, mining_data=mining_data
    )

    assert set(written) == {c["stem"] for c in FIXTURE_CANDIDATES}
    for cand in FIXTURE_CANDIDATES:
        path = written[cand["stem"]]
        on_disk = [int(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
        expected = data["team_decks"][cand["team"]][cand["deck_index"]]["signature"]
        assert on_disk == expected
        # Not the stale wave-1-like signature planted above.
        assert on_disk != _fixture_signature(999)


def test_load_mined_signature_rejects_non_60_card_deck(tmp_path):
    mining_data = tmp_path / "top_rated_decks.json"
    mining_data.write_text(
        json.dumps({"team_decks": {"short": [{"signature": [1, 2, 3], "count": 1}]}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        swc.load_mined_signature("short", 0, mining_data=mining_data)


def test_non_ascii_team_name_round_trips_to_ascii_stem_with_original_recorded():
    entry = next(c for c in swc.WAVE2_CANDIDATES if c["team"] == "変化の書ゾロアーク")
    # stem must be pure ASCII so it is a safe filename/module-friendly identifier.
    entry["stem"].encode("ascii")
    assert entry["original_name"] == "変化の書ゾロアーク"
    # And the original name is recoverable from the stem's entry, not lost.
    assert entry["team"] == entry["original_name"]


def test_wave2_candidates_are_exactly_five_with_one_non_ascii_team():
    assert len(swc.WAVE2_CANDIDATES) == 5
    non_ascii = [c for c in swc.WAVE2_CANDIDATES if "original_name" in c]
    assert len(non_ascii) == 1
    for c in swc.WAVE2_CANDIDATES:
        c["stem"].encode("ascii")  # every stem, ASCII or not, is a safe filename


def test_build_builds_dict_contains_only_baseline_plus_five_w2_stems():
    builds = swc.build_builds_dict()
    assert set(builds) == {swc.BASELINE_BUILD} | set(swc.wave2_stems())
    assert len(builds) == 6
    # Never the full candidate_* pool tools/score_candidate_decks.py would score.
    assert "candidate_third_ptcg_club" not in builds  # wave-1 stem, no _w2 suffix
    assert "trolley" not in builds


def test_build_builds_dict_factories_are_independent_per_stem():
    builds = swc.build_builds_dict(FIXTURE_CANDIDATES)
    assert set(builds) == {swc.BASELINE_BUILD, "candidate_alpha_w2", "candidate_beta_w2",
                            "candidate_henka_no_sho_zoroark_w2"}


def test_screen_then_confirm_only_confirms_candidates_that_cleared_screen(monkeypatch):
    """Plant a screen result where exactly one candidate clears +0.10; confirm
    must be invoked only for that candidate (never the baseline-only build
    dict, never the ones that stayed below margin)."""
    screen_result = {
        swc.BASELINE_BUILD: {"win_rate": 0.50, "wins": 10, "draws": 0, "losses": 10, "n": 20},
        "candidate_alpha_w2": {"win_rate": 0.65, "wins": 13, "draws": 0, "losses": 7, "n": 20},  # +0.15 clears
        "candidate_beta_w2": {"win_rate": 0.52, "wins": 10, "draws": 1, "losses": 9, "n": 20},  # +0.02 no
        "candidate_henka_no_sho_zoroark_w2": {"win_rate": 0.40, "wins": 8, "draws": 0, "losses": 12, "n": 20},  # -0.10 no
    }
    confirm_result = {
        swc.BASELINE_BUILD: {"win_rate": 0.50, "wins": 50, "draws": 0, "losses": 50, "n": 100},
        "candidate_alpha_w2": {"win_rate": 0.55, "wins": 55, "draws": 0, "losses": 45, "n": 100},  # shrinks to +0.05
    }

    calls = []

    def fake_run_ring(n_matches, builds, opponent_names):
        calls.append((n_matches, sorted(builds)))
        if n_matches == 5:
            return screen_result
        return confirm_result

    monkeypatch.setattr(swc.rc, "run_ring", fake_run_ring)
    monkeypatch.setattr(swc, "build_builds_dict", lambda candidates=None: {
        name: (lambda: None) for name in screen_result
    })

    report = swc.screen_then_confirm(screen_n=5, confirm_n=100, opponent_names=["clone:fake"],
                                      candidates=FIXTURE_CANDIDATES)

    assert report["cleared_screen"] == ["candidate_alpha_w2"]
    # The confirm run's builds dict is baseline plus only the cleared candidate.
    confirm_call = [c for c in calls if c[0] == 100]
    assert len(confirm_call) == 1
    assert confirm_call[0][1] == sorted([swc.BASELINE_BUILD, "candidate_alpha_w2"])

    # Non-cleared candidates keep their SCREEN verdict (never confirmed).
    assert report["verdicts"]["candidate_beta_w2"]["promote"] is False
    assert report["verdicts"]["candidate_henka_no_sho_zoroark_w2"]["promote"] is False
    # The cleared candidate's final verdict reflects the CONFIRM run (shrunk
    # to +0.05, below margin), not the screen run's +0.15.
    assert report["verdicts"]["candidate_alpha_w2"]["delta"] == pytest.approx(0.05)
    assert report["verdicts"]["candidate_alpha_w2"]["promote"] is False


def test_screen_then_confirm_skips_confirm_when_nothing_clears(monkeypatch):
    screen_result = {
        swc.BASELINE_BUILD: {"win_rate": 0.50, "wins": 10, "draws": 0, "losses": 10, "n": 20},
        "candidate_alpha_w2": {"win_rate": 0.55, "wins": 11, "draws": 0, "losses": 9, "n": 20},
    }
    calls = []

    def fake_run_ring(n_matches, builds, opponent_names):
        calls.append(n_matches)
        return screen_result

    monkeypatch.setattr(swc.rc, "run_ring", fake_run_ring)
    monkeypatch.setattr(swc, "build_builds_dict", lambda candidates=None: {
        name: (lambda: None) for name in screen_result
    })

    report = swc.screen_then_confirm(screen_n=5, confirm_n=100, opponent_names=["clone:fake"])

    assert report["cleared_screen"] == []
    assert report["confirm"] is None
    assert calls == [5]  # confirm never invoked


def test_promote_verdict_at_exactly_plus_point_10_is_inclusive():
    results = {
        swc.BASELINE_BUILD: {"win_rate": 0.50},
        "candidate_alpha_w2": {"win_rate": 0.60},
    }
    from tools.score_candidate_decks import promote_verdicts
    verdicts = promote_verdicts(results, baseline=swc.BASELINE_BUILD, margin=swc.MATERIAL_MARGIN)
    assert verdicts["candidate_alpha_w2"]["delta"] == pytest.approx(0.10)
    assert verdicts["candidate_alpha_w2"]["promote"] is True


# --- Tests against the real, already-materialized wave-2 CSVs and the real
# mining data, when both are present in this environment. ---

_MINING_DATA = _ROOT / "data" / "derived" / "top_rated_decks.json"
_DECKS_DIR = _ROOT / "decks"


def _load_real_mining_data():
    if not _MINING_DATA.exists():
        return None
    with open(_MINING_DATA, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("cand", swc.WAVE2_CANDIDATES, ids=lambda c: c["stem"])
def test_real_w2_csv_signature_matches_dedup_reports_mined_signature_not_wave1(cand):
    data = _load_real_mining_data()
    if data is None:
        pytest.skip("data/derived/top_rated_decks.json not available in this environment")
    csv_path = _DECKS_DIR / f"{cand['stem']}.csv"
    if not csv_path.exists():
        pytest.skip(f"{csv_path} not yet materialized")

    mined_sig = sorted(data["team_decks"][cand["team"]][cand["deck_index"]]["signature"])
    on_disk_sig = sorted(
        int(x) for x in csv_path.read_text(encoding="utf-8").splitlines() if x.strip()
    )
    assert on_disk_sig == mined_sig

    # If a same-named wave-1 deck exists on disk (strip the _w2 suffix), the
    # wave-2 signature must NOT match it: that would mean we scored the
    # already-failed wave-1 deck under a new name instead of the actual new
    # wave-2 mined candidate (the exact bug this unit exists to avoid).
    wave1_stem = cand["stem"][: -len("_w2")] if cand["stem"].endswith("_w2") else None
    if wave1_stem:
        wave1_path = _DECKS_DIR / f"{wave1_stem}.csv"
        if wave1_path.exists():
            wave1_sig = sorted(
                int(x) for x in wave1_path.read_text(encoding="utf-8").splitlines() if x.strip()
            )
            assert on_disk_sig != wave1_sig


def test_real_w2_csvs_are_all_60_cards():
    for cand in swc.WAVE2_CANDIDATES:
        csv_path = _DECKS_DIR / f"{cand['stem']}.csv"
        if not csv_path.exists():
            pytest.skip(f"{csv_path} not yet materialized")
        lines = [x for x in csv_path.read_text(encoding="utf-8").splitlines() if x.strip()]
        assert len(lines) == 60


def test_real_build_builds_dict_matches_materialized_files_on_disk():
    for stem in swc.wave2_stems():
        csv_path = _DECKS_DIR / f"{stem}.csv"
        if not csv_path.exists():
            pytest.skip(f"{csv_path} not yet materialized")
    builds = swc.build_builds_dict()
    assert set(builds) == {swc.BASELINE_BUILD} | set(swc.wave2_stems())


def test_screen_then_confirm_real_tiny_smoke_run_end_to_end():
    """Not the real n=40/n=100 run (that is real compute, launched separately);
    this proves the plumbing (materialize -> builds dict -> run_ring ->
    promote_verdicts -> screen/confirm branch) executes end to end at a tiny
    n against the real engine, without crashing.
    """
    for stem in [swc.BASELINE_BUILD] + swc.wave2_stems():
        if not (_DECKS_DIR / f"{stem}.csv").exists():
            pytest.skip(f"decks/{stem}.csv not present in this environment")
    try:
        import kaggle_environments  # noqa: F401
    except ImportError:
        pytest.skip("kaggle_environments not available in this environment")

    report = swc.screen_then_confirm(screen_n=2, confirm_n=2)

    assert set(report["screen"]) == {swc.BASELINE_BUILD} | set(swc.wave2_stems())
    for name, r in report["screen"].items():
        assert r["n"] == 2
        assert r["wins"] + r["draws"] + r["losses"] == 2
    assert isinstance(report["cleared_screen"], list)
    assert set(report["verdicts"]) == set(swc.wave2_stems())
