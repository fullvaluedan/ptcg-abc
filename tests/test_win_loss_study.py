"""U63 win/loss study tests.

Fixtures are hand-built row lists / CSVs in the same shape
tools/top_player_tracker.py writes, never real competition data.
"""
import json

from ptcg_agent.features import FEATURE_NAMES
from tools import top_player_tracker as tpt
from tools import win_loss_study as wls


def _feat_row(overrides=None):
    vals = {f: 0.0 for f in FEATURE_NAMES}
    vals.update(overrides or {})
    return [vals[f] for f in FEATURE_NAMES]


def _win_row(game_id, turn, team, overrides=None):
    return [game_id, 0, turn, *_feat_row(overrides), 1, "top_player", team]


def _loss_row(game_id, turn, team, bucket, opponent, overrides=None):
    return [game_id, 0, turn, *_feat_row(overrides), 0, "top_player_loss", team, bucket, opponent]


def _write_win_csv(path, rows):
    return tpt.write_csv(rows, path)


def _write_loss_csv(path, rows):
    return tpt.write_csv(rows, path, extra_columns=["loss_bucket", "opponent"])


# --- load_rows -------------------------------------------------------------

def test_load_rows_round_trips_win_corpus(tmp_path):
    path = _write_win_csv(tmp_path / "win.csv", [_win_row("1", 2, "Alpha", {"our_bench_size": 3.0})])
    rows = wls.load_rows(path)
    assert len(rows) == 1
    row = rows[0]
    assert row["game_id"] == "1"
    assert row["team"] == "Alpha"
    assert row["turn"] == 2.0
    assert row["our_bench_size"] == 3.0
    assert row["label"] == 1.0


def test_load_rows_round_trips_loss_corpus_extra_columns(tmp_path):
    path = _write_loss_csv(tmp_path / "loss.csv", [_loss_row("2", 5, "Alpha", "early_collapse", "Beta")])
    rows = wls.load_rows(path)
    assert rows[0]["loss_bucket"] == "early_collapse"
    assert rows[0]["opponent"] == "Beta"


def test_load_rows_missing_file_returns_empty_list(tmp_path):
    assert wls.load_rows(tmp_path / "nope.csv") == []


# --- distinct_games / bucket_distribution / opponent_distribution ----------

def test_distinct_games_dedupes_by_game_and_team():
    rows = [{"game_id": "1", "team": "Alpha"}, {"game_id": "1", "team": "Alpha"}, {"game_id": "2", "team": "Alpha"}]
    assert wls.distinct_games(rows) == {("1", "Alpha"), ("2", "Alpha")}


def test_bucket_distribution_counts_once_per_game_not_per_row():
    rows = [
        {"game_id": "1", "team": "Alpha", "loss_bucket": "early_collapse"},
        {"game_id": "1", "team": "Alpha", "loss_bucket": "early_collapse"},  # same game, 2nd decision row
        {"game_id": "2", "team": "Alpha", "loss_bucket": "deckout"},
    ]
    counts = wls.bucket_distribution(rows)
    assert counts == {"early_collapse": 1, "deckout": 1}


def test_opponent_distribution_dedupes_and_ranks():
    rows = [
        {"game_id": "1", "team": "Alpha", "opponent": "Beta"},
        {"game_id": "1", "team": "Alpha", "opponent": "Beta"},
        {"game_id": "2", "team": "Alpha", "opponent": "Beta"},
        {"game_id": "3", "team": "Alpha", "opponent": "Gamma"},
    ]
    ranked = wls.opponent_distribution(rows).most_common()
    assert ranked[0] == ("Beta", 2)
    assert ("Gamma", 1) in ranked


# --- load_ours_buckets -------------------------------------------------------

def test_load_ours_buckets_missing_file_returns_none(tmp_path):
    assert wls.load_ours_buckets(tmp_path / "nope.json") is None


def test_load_ours_buckets_valid_json(tmp_path):
    path = tmp_path / "ours.json"
    path.write_text(json.dumps({"buckets": {"early_collapse": 12, "deckout": 1}, "losses": 13}))
    ours = wls.load_ours_buckets(path)
    assert ours == {"buckets": {"early_collapse": 12, "deckout": 1}, "losses": 13}


def test_load_ours_buckets_malformed_json_returns_none(tmp_path):
    path = tmp_path / "ours.json"
    path.write_text("not json")
    assert wls.load_ours_buckets(path) is None


def test_load_ours_buckets_wrong_shape_returns_none(tmp_path):
    path = tmp_path / "ours.json"
    path.write_text(json.dumps({"buckets": "nope", "losses": 5}))
    assert wls.load_ours_buckets(path) is None


# --- compare_bucket_distributions -------------------------------------------

def test_compare_bucket_distributions_with_ours_computes_rates_and_delta():
    top = wls.bucket_distribution([
        {"game_id": "1", "team": "A", "loss_bucket": "early_collapse"},
        {"game_id": "2", "team": "A", "loss_bucket": "deckout"},
    ])
    ours = {"buckets": {"early_collapse": 3, "deckout": 1}, "losses": 4}
    result = wls.compare_bucket_distributions(top, ours)
    assert result["note"] is None
    by_bucket = {r["bucket"]: r for r in result["rows"]}
    assert by_bucket["early_collapse"]["top_rate"] == 0.5
    assert by_bucket["early_collapse"]["our_rate"] == 0.75
    assert by_bucket["early_collapse"]["delta"] == -0.25
    # ranked by top-team rate descending; early_collapse and deckout tie at 0.5
    assert result["rows"][0]["top_rate"] == 0.5


def test_compare_bucket_distributions_empty_top_losses_is_insufficient_data():
    result = wls.compare_bucket_distributions(wls.bucket_distribution([]), {"buckets": {"deckout": 1}, "losses": 1})
    assert result["top_total"] == 0
    assert "insufficient data" in result["note"]
    for r in result["rows"]:
        assert r["top_rate"] is None
        assert r["delta"] is None


def test_compare_bucket_distributions_missing_ours_is_insufficient_data():
    top = wls.bucket_distribution([{"game_id": "1", "team": "A", "loss_bucket": "deckout"}])
    result = wls.compare_bucket_distributions(top, None)
    assert result["note"] is not None
    assert result["rows"][0]["our_rate"] is None


# --- feature means / deltas ------------------------------------------------

def test_feature_means_empty_rows_returns_empty_dict():
    assert wls.feature_means([]) == {}


def test_feature_deltas_by_bin_skips_bins_missing_either_side():
    win_rows = [{"turn": 10.0, **{f: 1.0 for f in FEATURE_NAMES}}]  # "late" bin only
    loss_rows = [{"turn": 1.0, **{f: 0.0 for f in FEATURE_NAMES}}]  # "early" bin only
    deltas = wls.feature_deltas_by_bin(win_rows, loss_rows)
    assert deltas == {}  # no bin has both a win row and a loss row


def test_feature_deltas_by_bin_computes_correct_delta_for_matched_bin():
    win_rows = [{"turn": 2.0, **{f: 0.0 for f in FEATURE_NAMES}, "our_bench_size": 4.0}]
    loss_rows = [{"turn": 2.0, **{f: 0.0 for f in FEATURE_NAMES}, "our_bench_size": 1.0}]
    deltas = wls.feature_deltas_by_bin(win_rows, loss_rows)
    assert "early" in deltas
    assert deltas["early"]["our_bench_size"]["win_mean"] == 4.0
    assert deltas["early"]["our_bench_size"]["loss_mean"] == 1.0
    assert deltas["early"]["our_bench_size"]["delta"] == 3.0
    assert "mid" not in deltas
    assert "late" not in deltas


def test_top_discriminative_features_ranks_by_abs_delta_and_is_deterministic():
    win_rows = [{"turn": 2.0, **{f: 0.0 for f in FEATURE_NAMES}, "our_bench_size": 5.0, "our_energy": 1.0}]
    loss_rows = [{"turn": 2.0, **{f: 0.0 for f in FEATURE_NAMES}, "our_bench_size": 0.0, "our_energy": 0.9}]
    bin_deltas = wls.feature_deltas_by_bin(win_rows, loss_rows)
    top1 = wls.top_discriminative_features(bin_deltas, k=3)
    top2 = wls.top_discriminative_features(bin_deltas, k=3)
    assert top1 == top2  # deterministic on identical input
    assert top1[0]["feature"] == "our_bench_size"  # |5.0| delta beats |0.1|


# --- study (integration) ----------------------------------------------------

def test_study_happy_path_reports_buckets_features_and_opponents():
    win_dict_rows = [
        {"game_id": "1", "team": "Alpha", "turn": 2.0, **{f: 0.0 for f in FEATURE_NAMES}, "our_bench_size": 4.0},
        {"game_id": "2", "team": "Alpha", "turn": 2.0, **{f: 0.0 for f in FEATURE_NAMES}, "our_bench_size": 4.0},
    ]
    loss_dict_rows = [
        {
            "game_id": "3", "team": "Alpha", "turn": 2.0, **{f: 0.0 for f in FEATURE_NAMES},
            "our_bench_size": 0.0, "loss_bucket": "early_collapse", "opponent": "Beta",
        },
        {
            "game_id": "4", "team": "Alpha", "turn": 2.0, **{f: 0.0 for f in FEATURE_NAMES},
            "our_bench_size": 0.0, "loss_bucket": "early_collapse", "opponent": "Beta",
        },
    ]
    ours = {"buckets": {"early_collapse": 12, "deckout": 1}, "losses": 13}
    result = wls.study(win_dict_rows, loss_dict_rows, ours)
    assert result["win_games"] == 2
    assert result["loss_games"] == 2
    assert result["bucket_comparison"]["rows"][0]["bucket"] == "early_collapse"
    assert result["top_discriminative_features"][0]["feature"] == "our_bench_size"
    assert result["opponents"] == [("Beta", 2)]
    assert result["notes"] == []


def test_study_insufficient_data_for_thin_corpora_no_divide_by_zero():
    win_rows = [{"game_id": "1", "team": "Alpha", "turn": 2.0, **{f: 0.0 for f in FEATURE_NAMES}}]
    result = wls.study(win_rows, [], ours=None)
    assert result["loss_games"] == 0
    assert result["bucket_comparison"]["rows"] == []
    assert result["top_discriminative_features"] == []
    assert len(result["notes"]) >= 1  # degraded, did not raise


# --- format_report -----------------------------------------------------------

def test_format_report_names_buckets_features_and_opponents():
    win_dict_rows = [{"game_id": "1", "team": "Alpha", "turn": 2.0, **{f: 0.0 for f in FEATURE_NAMES}, "our_bench_size": 4.0}]
    loss_dict_rows = [
        {
            "game_id": "2", "team": "Alpha", "turn": 2.0, **{f: 0.0 for f in FEATURE_NAMES},
            "our_bench_size": 0.0, "loss_bucket": "early_collapse", "opponent": "Beta",
        },
    ]
    result = wls.study(win_dict_rows, loss_dict_rows, {"buckets": {"early_collapse": 5}, "losses": 5})
    report = wls.format_report(result, "win.csv", "loss.csv", "ours.json")
    assert "early_collapse" in report
    assert "our_bench_size" in report
    assert "Beta" in report
    assert "How the best teams win vs lose" in report
    assert chr(0x2014) not in report and chr(0x2013) not in report  # no em or en dash


def test_format_report_insufficient_data_lines_present_not_crashing():
    result = wls.study([], [], ours=None)
    report = wls.format_report(result)
    assert "insufficient data" in report


# --- main (end to end) -------------------------------------------------------

def test_main_end_to_end_writes_report_and_summary(tmp_path, monkeypatch):
    win_csv = _write_win_csv(tmp_path / "top_player_corpus_20260703.csv", [
        _win_row("1", 2, "Alpha", {"our_bench_size": 4.0}),
    ])
    loss_csv = _write_loss_csv(tmp_path / "top_player_loss_corpus_20260703.csv", [
        _loss_row("2", 2, "Alpha", "early_collapse", "Beta", {"our_bench_size": 0.0}),
    ])
    ours_json = tmp_path / "ours.json"
    ours_json.write_text(json.dumps({"buckets": {"early_collapse": 3}, "losses": 3}))
    report_path = tmp_path / "study.md"
    summary_path = tmp_path / "study.json"

    rc = wls.main([
        "--win-csv", str(win_csv),
        "--loss-csv", str(loss_csv),
        "--ours-json", str(ours_json),
        "--report", str(report_path),
        "--summary", str(summary_path),
    ])
    assert rc == 0
    assert report_path.exists()
    summary = json.loads(summary_path.read_text())
    assert summary["loss_games"] == 1
    assert "early_collapse" in report_path.read_text()


def test_main_missing_corpora_returns_nonzero(tmp_path, monkeypatch):
    monkeypatch.setattr(wls, "DEFAULT_TRAIN_DIR", tmp_path)  # empty dir, no corpus CSVs to default to
    rc = wls.main([])
    assert rc == 1
