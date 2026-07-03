"""U3c top-player leaderboard tracker tests.

Fixtures are hand-built replay dicts (matching the env.toJSON shape the rest of
the replay tooling reads) plus a small synthetic dataset .zip, never real
competition data.
"""
import csv
import json
import zipfile
from datetime import datetime, timedelta

from analysis import loss_classifier
from tools import top_player_tracker as tpt

RECENT = datetime(2026, 7, 1)
OLD = RECENT - timedelta(days=20)


def _player(prizes=6, deck_count=50, hand_count=5, bench=None):
    return {
        "prize": [None] * prizes,
        "deckCount": deck_count,
        "handCount": hand_count,
        "active": [],
        "bench": bench or [],
    }


def _current(seat, turn=3, prizes=(6, 6)):
    return {
        "yourIndex": seat,
        "turn": turn,
        "firstPlayer": 0,
        "players": [_player(prizes=prizes[0]), _player(prizes=prizes[1])],
    }


def _active_entry(seat, turn=3, prizes=(6, 6)):
    return {
        "action": [0],
        "status": "ACTIVE",
        "reward": 0,
        "observation": {
            "select": {"option": [0, 1, 2], "minCount": 1, "maxCount": 1},
            "current": _current(seat, turn=turn, prizes=prizes),
        },
    }


def _inactive():
    return {"action": [], "status": "INACTIVE", "reward": 0, "observation": {"select": None, "current": None}}


def _handshake():
    return [_inactive(), _inactive()]


def _step(seat_deciding, turn=3):
    entry = _active_entry(seat_deciding, turn=turn)
    return [entry, _inactive()] if seat_deciding == 0 else [_inactive(), entry]


def _replay(team0, team1, rewards=(1, -1)):
    return {
        "info": {"TeamNames": [team0, team1]},
        "rewards": list(rewards),
        "steps": [_handshake(), _step(0, turn=1), _step(1, turn=2)],
    }


def _build_dataset_zip(tmp_path, episodes, manifest_rows, name="dataset.zip"):
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as zf:
        lines = ["episode_id,create_time,avg_score,min_score,sum_score,agent_count,size_bytes"]
        for eid, ct in manifest_rows:
            lines.append(f"{eid},{ct.isoformat()},0,0,0,2,0")
        zf.writestr("manifest.csv", "\n".join(lines) + "\n")
        for eid, replay in episodes.items():
            zf.writestr(f"{eid}.json", json.dumps(replay))
    return path


def _six_game_dataset(tmp_path):
    """2 matching+recent, 1 matching+old, 3 non-matching. Top set: Alpha, Beta, Gamma."""
    episodes = {
        "1": _replay("Alpha", "Opp1", rewards=(1, -1)),   # Alpha wins, recent, matching
        "2": _replay("Opp2", "Beta", rewards=(-1, 1)),    # Beta wins, recent, matching
        "3": _replay("Alpha", "Opp3", rewards=(1, -1)),   # matching but OLD
        "4": _replay("Foo", "Bar", rewards=(1, -1)),      # non-matching
        "5": _replay("Baz", "Qux", rewards=(1, -1)),      # non-matching
        "6": _replay("Zed", "Yak", rewards=(1, -1)),      # non-matching
    }
    manifest_rows = [
        ("1", RECENT), ("2", RECENT), ("3", OLD), ("4", RECENT), ("5", RECENT), ("6", RECENT),
    ]
    return _build_dataset_zip(tmp_path, episodes, manifest_rows)


def _dataset_with_losses(tmp_path):
    """Alpha wins once, loses twice (once to a non-top opponent, once to Beta).

    Top set: Alpha, Beta, Gamma (Gamma never appears, stays unmapped). Game 3
    has BOTH seats top-N (Alpha loses, Beta wins), so it exercises the win
    corpus and loss corpus drawing from the same game_id for different teams.
    """
    episodes = {
        "1": _replay("Alpha", "Opp1", rewards=(1, -1)),   # Alpha wins
        "2": _replay("Opp2", "Alpha", rewards=(1, -1)),   # Alpha loses to Opp2 (seat 1)
        "3": _replay("Alpha", "Beta", rewards=(-1, 1)),   # Alpha loses to Beta; Beta wins
        "4": _replay("Alpha", "Opp3", rewards=(0, 0)),    # draw, contributes nothing
    }
    manifest_rows = [("1", RECENT), ("2", RECENT), ("3", RECENT), ("4", RECENT)]
    return _build_dataset_zip(tmp_path, episodes, manifest_rows)


def test_collect_top_player_rows_matches_recent_games_only(tmp_path):
    zip_path = _six_game_dataset(tmp_path)
    team_set = {"Alpha", "Beta", "Gamma"}

    result = tpt.collect_top_player_rows(zip_path, team_set, days=14, signatures=None)

    assert result["games_matched"] == 2
    assert {r[0] for r in result["rows"]} == {"1", "2"}
    assert result["unmapped"] == ["Gamma"]
    assert result["per_team_games"]["Alpha"] == 1
    assert result["per_team_wins"]["Alpha"] == 1
    assert result["per_team_games"]["Beta"] == 1
    assert result["per_team_wins"]["Beta"] == 1


def test_collect_top_player_rows_tags_source_and_team(tmp_path):
    zip_path = _six_game_dataset(tmp_path)
    result = tpt.collect_top_player_rows(zip_path, {"Alpha"}, days=14, signatures=None)

    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row[-2] == "top_player"
    assert row[-1] == "Alpha"


def test_collect_top_player_rows_excludes_losses(tmp_path):
    zip_path = _dataset_with_losses(tmp_path)
    team_set = {"Alpha", "Beta", "Gamma"}

    result = tpt.collect_top_player_rows(zip_path, team_set, days=14, signatures=None)

    # Only the win (game 1) contributes rows for Alpha; the loss games (2, 3)
    # do not, even though Alpha is a matched seat in all three.
    assert {r[0] for r in result["rows"] if r[-1] == "Alpha"} == {"1"}
    # Beta's win in game 3 still lands in the win corpus.
    assert {r[0] for r in result["rows"] if r[-1] == "Beta"} == {"3"}
    # Stats still count every matched game (win or loss), so win rate stays meaningful.
    assert result["per_team_games"]["Alpha"] == 3
    assert result["per_team_wins"]["Alpha"] == 1
    assert result["unmapped"] == ["Gamma"]


def test_collect_top_player_loss_rows_tags_bucket_and_opponent(tmp_path):
    zip_path = _dataset_with_losses(tmp_path)
    team_set = {"Alpha", "Beta", "Gamma"}

    loss_result = tpt.collect_top_player_loss_rows(zip_path, team_set, days=14)

    alpha_game_ids = {r[0] for r in loss_result["rows"] if r[-3] == "Alpha"}
    assert alpha_game_ids == {"2", "3"}
    for row in loss_result["rows"]:
        assert row[-4] == tpt.SOURCE_LOSS
        assert row[-3] in ("Alpha",)  # only Alpha lost in this fixture
        assert row[-2] in loss_classifier.BUCKETS or row[-2] == "unclassified"
    opponents = {r[0]: r[-1] for r in loss_result["rows"]}
    assert opponents["2"] == "Opp2"
    assert opponents["3"] == "Beta"
    assert loss_result["per_team_losses"]["Alpha"] == 2
    assert loss_result["per_team_beaten_by"]["Alpha"]["Opp2"] == 1
    assert loss_result["per_team_beaten_by"]["Alpha"]["Beta"] == 1
    assert loss_result["unmapped"] == ["Gamma"]


def test_collect_top_player_loss_rows_excludes_wins_and_draws(tmp_path):
    zip_path = _dataset_with_losses(tmp_path)
    loss_result = tpt.collect_top_player_loss_rows(zip_path, {"Alpha", "Beta"}, days=14)

    # Alpha's win (game 1) and the draw (game 4) contribute no loss rows.
    game_ids = {r[0] for r in loss_result["rows"]}
    assert "1" not in game_ids
    assert "4" not in game_ids
    # Beta only won in this fixture, so it never appears in the loss corpus.
    assert "Beta" not in loss_result["per_team_losses"]


def test_win_and_loss_corpora_never_share_a_teams_rows_for_one_game(tmp_path):
    zip_path = _dataset_with_losses(tmp_path)
    team_set = {"Alpha", "Beta"}

    win_result = tpt.collect_top_player_rows(zip_path, team_set, days=14, signatures=None)
    loss_result = tpt.collect_top_player_loss_rows(zip_path, team_set, days=14)

    win_pairs = {(r[0], r[-1]) for r in win_result["rows"]}
    loss_pairs = {(r[0], r[-3]) for r in loss_result["rows"]}
    assert win_pairs.isdisjoint(loss_pairs)
    # Game 3 legitimately appears in both corpora, but for different teams.
    assert ("3", "Beta") in win_pairs
    assert ("3", "Alpha") in loss_pairs


def test_recency_cutoff_anchors_to_dataset_newest_not_wall_clock():
    manifest = {"a": RECENT, "b": OLD}
    cutoff = tpt.recency_cutoff(manifest, days=14)
    assert cutoff == RECENT - timedelta(days=14)
    assert tpt.recency_cutoff({}, days=14) is None


def test_newest_dataset_picks_lexicographically_last_zip(tmp_path):
    (tmp_path / "pokemon-tcg-ai-battle-episodes-2026-06-20.zip").write_bytes(b"")
    newest = tmp_path / "pokemon-tcg-ai-battle-episodes-2026-06-30.zip"
    newest.write_bytes(b"")
    assert tpt.newest_dataset(tmp_path) == newest


def test_newest_dataset_none_when_empty(tmp_path):
    assert tpt.newest_dataset(tmp_path) is None


def test_newest_dataset_ignores_index_and_leaderboard_zips(tmp_path):
    """A leaderboard -d download (tools/bracket_select.py, named
    "<slug>.zip") or the -index dataset (tools/daily_refresh.py, named
    "<slug>-episodes-index.zip") can legitimately land next to the dated
    dumps in data/episodes/. Both sort lexicographically AFTER every dated
    dump ("pokemon-tcg-ai-battle-episodes-2026-07-02.zip" < either name), so
    a naive "*.zip" sort would pick one of them instead of the real newest
    dump -- this must not happen."""
    real_newest = tmp_path / "pokemon-tcg-ai-battle-episodes-2026-07-02.zip"
    real_newest.write_bytes(b"")
    (tmp_path / "pokemon-tcg-ai-battle-episodes-index.zip").write_bytes(b"")
    (tmp_path / "pokemon-tcg-ai-battle.zip").write_bytes(b"")
    assert tpt.newest_dataset(tmp_path) == real_newest


def test_dedupe_new_games_drops_already_seen_game_ids():
    rows = [["1", 0, 3, 1, "top_player", "Alpha"], ["2", 1, 4, 1, "top_player", "Beta"]]
    out = tpt.dedupe_new_games(rows, existing_game_ids={"1"})
    assert [r[0] for r in out] == ["2"]


def test_read_existing_game_ids_round_trips_with_write_csv(tmp_path):
    from ptcg_agent.features import FEATURE_NAMES

    rows = [["1", 0, 3, *[0.0] * len(FEATURE_NAMES), 1, "top_player", "Alpha"]]
    out = tpt.write_csv(rows, tmp_path / "corpus.csv")
    assert tpt.read_existing_game_ids(out) == {"1"}

    tpt.write_csv([["2", 1, 4, *[0.0] * len(FEATURE_NAMES), 0, "top_player", "Beta"]], out, append=True)
    assert tpt.read_existing_game_ids(out) == {"1", "2"}
    with open(out, newline="") as fh:
        assert sum(1 for _ in csv.reader(fh)) == 3  # header + 2 rows


def test_write_csv_round_trips_non_ascii_team_names(tmp_path):
    """Team/opponent handles carry CJK characters and accents; write_csv and
    read_existing_game_ids must round-trip them as utf-8 rather than falling
    back to a locale codec (cp1252 on Windows) that cannot encode them."""
    from ptcg_agent.features import FEATURE_NAMES

    rows = [
        ["1", 0, 3, *[0.0] * len(FEATURE_NAMES), 1, "top_player", "élite チーム"],
        ["2", 1, 4, *[0.0] * len(FEATURE_NAMES), 0, "top_player_loss", "Alpha",
         "early_collapse", "élite チーム"],
    ]
    out = tpt.write_csv(rows[:1], tmp_path / "corpus.csv")
    assert tpt.read_existing_game_ids(out) == {"1"}
    loss_out = tpt.write_csv(rows[1:], tmp_path / "loss_corpus.csv", extra_columns=["loss_bucket", "opponent"])
    with open(loss_out, newline="", encoding="utf-8") as fh:
        loss_reader = csv.reader(fh)
        next(loss_reader)
        row = next(loss_reader)
    assert row[-1] == "élite チーム"


def test_write_csv_extra_columns_extend_header(tmp_path):
    from ptcg_agent.features import FEATURE_NAMES

    rows = [["2", 1, 4, *[0.0] * len(FEATURE_NAMES), 0, "top_player_loss", "Alpha", "early_collapse", "Beta"]]
    out = tpt.write_csv(rows, tmp_path / "loss_corpus.csv", extra_columns=["loss_bucket", "opponent"])
    with open(out, newline="") as fh:
        header = next(csv.reader(fh))
    assert header[-4:] == ["source", "team", "loss_bucket", "opponent"]
    assert tpt.read_existing_game_ids(out) == {"2"}


def test_strip_overlap_from_ladder_removes_planted_duplicate_game_id(tmp_path):
    from ptcg_agent.features import FEATURE_NAMES

    ladder_csv = tmp_path / "ladder_rows.csv"
    with open(ladder_csv, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["game_id", "seat", "turn", *FEATURE_NAMES, "label", "source"])
        writer.writerow(["1", 0, 3, *[0.0] * len(FEATURE_NAMES), 1, "ladder"])  # planted duplicate
        writer.writerow(["99", 0, 1, *[0.0] * len(FEATURE_NAMES), 0, "ladder"])

    removed = tpt.strip_overlap_from_ladder(ladder_csv, {"1", "2"})
    assert removed == 1

    with open(ladder_csv, newline="") as fh:
        reader = csv.reader(fh)
        next(reader)
        remaining_ids = {row[0] for row in reader}
    assert remaining_ids == {"99"}


def test_strip_overlap_from_ladder_noop_when_no_overlap(tmp_path):
    from ptcg_agent.features import FEATURE_NAMES

    ladder_csv = tmp_path / "ladder_rows.csv"
    with open(ladder_csv, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["game_id", "seat", "turn", *FEATURE_NAMES, "label", "source"])
        writer.writerow(["99", 0, 1, *[0.0] * len(FEATURE_NAMES), 0, "ladder"])
    assert tpt.strip_overlap_from_ladder(ladder_csv, {"1"}) == 0


def test_fetch_leaderboard_parses_leading_page_token(monkeypatch):
    stdout = (
        "Next Page Token = CfDJ8EgiEKLz2SFKpKvT-xxAYKIpp7\n"
        "[\n"
        '  {"teamId": 1, "teamName": "Alpha", "score": "1243.3"},\n'
        '  {"teamId": 2, "teamName": "Beta", "score": "1230.4"}\n'
        "]\n"
    )
    monkeypatch.setattr(tpt, "run_kaggle", lambda args: {"ok": True, "stdout": stdout, "error": None})

    res = tpt.fetch_leaderboard(top_n=2)
    assert res["ok"] is True
    assert res["teams"] == [
        {"rank": 1, "team_id": 1, "name": "Alpha", "rating": 1243.3},
        {"rank": 2, "team_id": 2, "name": "Beta", "rating": 1230.4},
    ]


def test_fetch_leaderboard_propagates_cli_failure(monkeypatch):
    monkeypatch.setattr(tpt, "run_kaggle", lambda args: {"ok": False, "error": "401 unauthorized"})
    res = tpt.fetch_leaderboard(top_n=5)
    assert res == {"ok": False, "error": "401 unauthorized", "teams": []}


def test_format_report_contains_ratings_and_win_rates(tmp_path):
    zip_path = _six_game_dataset(tmp_path)
    team_set = {"Alpha", "Beta", "Gamma"}
    result = tpt.collect_top_player_rows(zip_path, team_set, days=14, signatures=None)
    teams = [
        {"rank": 1, "team_id": 111, "name": "Alpha", "rating": 1243.3},
        {"rank": 2, "team_id": 222, "name": "Beta", "rating": 1230.4},
        {"rank": 3, "team_id": 333, "name": "Gamma", "rating": 1200.0},
    ]

    report = tpt.format_report(teams, result, ladder_rows_removed=0, days=14,
                                now=RECENT + timedelta(days=1))

    assert "1243.3" in report
    assert "100%" in report  # both Alpha and Beta went 1-0 in the corpus
    assert "Gamma" in report
    assert "no game in the scanned dataset names this team" in report
    assert "not collected this run" in report  # no loss_result passed


def test_format_report_losses_section_lists_bucket_and_opponent(tmp_path):
    zip_path = _dataset_with_losses(tmp_path)
    team_set = {"Alpha", "Beta"}
    result = tpt.collect_top_player_rows(zip_path, team_set, days=14, signatures=None)
    loss_result = tpt.collect_top_player_loss_rows(zip_path, team_set, days=14)
    teams = [
        {"rank": 1, "team_id": 111, "name": "Alpha", "rating": 1243.3},
        {"rank": 2, "team_id": 222, "name": "Beta", "rating": 1230.4},
    ]

    report = tpt.format_report(teams, result, ladder_rows_removed=0, days=14,
                                now=RECENT + timedelta(days=1), loss_result=loss_result)

    assert "## Losses" in report
    assert "| Alpha | 2 |" in report
    assert "Opp2" in report or "Beta" in report  # one of the two opponents named


def test_safe_downconverts_unencodable_characters(monkeypatch):
    class _Cp1252Stdout:
        encoding = "cp1252"

    monkeypatch.setattr(tpt.sys, "stdout", _Cp1252Stdout())
    # a CJK team handle would raise UnicodeEncodeError on a raw cp1252 print;
    # _safe must down-convert it instead of raising.
    assert tpt._safe("team やる気元") == "team ????"


def test_main_end_to_end_writes_corpus_and_report(tmp_path, monkeypatch):
    zip_path = _six_game_dataset(tmp_path)
    stdout = json.dumps([
        {"teamId": 1, "teamName": "Alpha", "score": "1243.3"},
        {"teamId": 2, "teamName": "Beta", "score": "1230.4"},
        {"teamId": 3, "teamName": "Gamma", "score": "1200.0"},
    ])
    monkeypatch.setattr(tpt, "run_kaggle", lambda args: {"ok": True, "stdout": stdout, "error": None})
    monkeypatch.setattr(tpt, "build_signatures", lambda: None)

    out_csv = tmp_path / "corpus.csv"
    loss_csv = tmp_path / "loss_corpus.csv"
    report_path = tmp_path / "report.md"
    rc = tpt.main([
        "--top-n", "3", "--days", "14",
        "--dataset", str(zip_path),
        "--out", str(out_csv),
        "--loss-out", str(loss_csv),
        "--report", str(report_path),
    ])

    assert rc == 0
    assert out_csv.exists()
    assert loss_csv.exists()
    assert report_path.exists()
    with open(out_csv, newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = list(reader)
    assert header[-2:] == ["source", "team"]
    assert {r[-1] for r in rows} == {"Alpha", "Beta"}
    with open(loss_csv, newline="") as fh:
        loss_header = next(csv.reader(fh))
    assert loss_header[-4:] == ["source", "team", "loss_bucket", "opponent"]
    report_text = report_path.read_text(encoding="utf-8")
    assert "Gamma" in report_text
    assert "## Losses" in report_text
    assert "no losses captured this run" in report_text  # this fixture's top teams never lose


def test_main_end_to_end_writes_loss_corpus_rows(tmp_path, monkeypatch):
    zip_path = _dataset_with_losses(tmp_path)
    stdout = json.dumps([
        {"teamId": 1, "teamName": "Alpha", "score": "1243.3"},
        {"teamId": 2, "teamName": "Beta", "score": "1230.4"},
    ])
    monkeypatch.setattr(tpt, "run_kaggle", lambda args: {"ok": True, "stdout": stdout, "error": None})
    monkeypatch.setattr(tpt, "build_signatures", lambda: None)

    out_csv = tmp_path / "corpus.csv"
    loss_csv = tmp_path / "loss_corpus.csv"
    report_path = tmp_path / "report.md"
    rc = tpt.main([
        "--top-n", "2", "--days", "14",
        "--dataset", str(zip_path),
        "--out", str(out_csv),
        "--loss-out", str(loss_csv),
        "--report", str(report_path),
    ])

    assert rc == 0
    with open(loss_csv, newline="") as fh:
        reader = csv.reader(fh)
        next(reader)  # header
        rows = list(reader)
    assert {r[0] for r in rows} == {"2", "3"}  # Alpha's two losses
    report_text = report_path.read_text(encoding="utf-8")
    assert "| Alpha | 2 |" in report_text
