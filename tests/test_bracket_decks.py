"""U81 bracket-band opponent decklist harvest tests (tools/bracket_decks.py).

All fixtures are synthetic in-process replays, same style as
tests/test_clone_dataset.py; the injectable validate_fn means no test ever
touches the native card engine, and no test reads or writes real competition
data.
"""
import json

from analysis.expert_cohort import DECK_SIZE
from tools import bracket_decks as BD


def _deck(distinct_ids, filler=8):
    deck = list(distinct_ids)
    return tuple(deck + [filler] * (DECK_SIZE - len(deck)))


DECK_A = _deck([10, 11, 12])
DECK_B = _deck([20, 21, 22])
DECK_C = _deck([30, 31, 32])


def _replay(deck0, deck1, names):
    step0 = [
        {"status": "ACTIVE", "visualize": [{"action": [list(deck0), list(deck1)]}]},
        {"status": "INACTIVE"},
    ]
    return {"info": {"TeamNames": list(names)}, "steps": [step0]}


def _always_legal(_deck):
    return {"ok": True}


def _always_illegal(_deck):
    return {"ok": False, "rule_errors": ["nope"], "engine": None}


def test_decklist_counts_only_matched_team_seats():
    pairs = [(_replay(DECK_A, DECK_B, ("bracket_team", "other_team")), "ep1")]
    counts = BD.decklist_counts(pairs, {"bracket_team"})
    assert counts == {tuple(sorted(DECK_A)): {"count": 1, "teams": {"bracket_team"}}}


def test_decklist_counts_both_seats_matched():
    pairs = [(_replay(DECK_A, DECK_B, ("team_x", "team_y")), "ep1")]
    counts = BD.decklist_counts(pairs, {"team_x", "team_y"})
    assert set(counts) == {tuple(sorted(DECK_A)), tuple(sorted(DECK_B))}


def test_decklist_counts_accumulates_across_replays_and_teams():
    pairs = [
        (_replay(DECK_A, DECK_B, ("team_x", "other")), "ep1"),
        (_replay(DECK_A, DECK_C, ("team_y", "team_x")), "ep2"),
    ]
    counts = BD.decklist_counts(pairs, {"team_x", "team_y"})
    assert counts[tuple(sorted(DECK_A))]["count"] == 2
    assert counts[tuple(sorted(DECK_A))]["teams"] == {"team_x", "team_y"}
    assert counts[tuple(sorted(DECK_C))]["count"] == 1


def test_decklist_counts_skips_unmatched_and_missing_decklist():
    unmatched = [(_replay(DECK_A, DECK_B, ("other_x", "other_y")), "ep1")]
    assert BD.decklist_counts(unmatched, {"team_x"}) == {}

    malformed = [({"info": {"TeamNames": ["team_x", "other"]}, "steps": []}, "ep2")]
    assert BD.decklist_counts(malformed, {"team_x"}) == {}


def test_top_decklists_ranks_by_count_then_deck_id():
    counts = {
        tuple(sorted(DECK_B)): {"count": 3, "teams": {"y"}},
        tuple(sorted(DECK_A)): {"count": 5, "teams": {"x"}},
        tuple(sorted(DECK_C)): {"count": 3, "teams": {"z"}},
    }
    top = BD.top_decklists(counts, k=3, validate_fn=_always_legal)
    assert [e["count"] for e in top] == [5, 3, 3]
    assert top[0]["deck"] == tuple(sorted(DECK_A))
    # tie on count=3 breaks on deck id: DECK_B < DECK_C lexicographically.
    assert top[1]["deck"] == tuple(sorted(DECK_B))
    assert top[2]["deck"] == tuple(sorted(DECK_C))


def test_top_decklists_respects_k():
    counts = {
        tuple(sorted(DECK_A)): {"count": 5, "teams": {"x"}},
        tuple(sorted(DECK_B)): {"count": 3, "teams": {"y"}},
    }
    top = BD.top_decklists(counts, k=1, validate_fn=_always_legal)
    assert len(top) == 1
    assert top[0]["deck"] == tuple(sorted(DECK_A))


def test_top_decklists_skips_illegal_decks():
    counts = {tuple(sorted(DECK_A)): {"count": 5, "teams": {"x"}}}
    assert BD.top_decklists(counts, k=3, validate_fn=_always_illegal) == []


def test_write_decks_writes_ranked_csvs(tmp_path):
    selected = [
        {"deck": tuple(sorted(DECK_A)), "count": 5, "teams": ["x"]},
        {"deck": tuple(sorted(DECK_B)), "count": 3, "teams": ["y"]},
    ]
    paths = BD.write_decks(selected, tmp_path)
    assert [p.name for p in paths] == ["bracket_1.csv", "bracket_2.csv"]
    ids = [int(line) for line in paths[0].read_text().splitlines() if line.strip()]
    assert ids == sorted(DECK_A)
    assert len(ids) == DECK_SIZE


def test_load_team_set_reads_teams_list(tmp_path):
    path = tmp_path / "teams.json"
    path.write_text(json.dumps({"teams": ["a", "b", "b"]}), encoding="utf-8")
    assert BD.load_team_set(path) == {"a", "b"}


def test_load_team_set_missing_file_returns_empty(tmp_path):
    assert BD.load_team_set(tmp_path / "does_not_exist.json") == set()


def test_load_team_set_malformed_json_returns_empty(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("not json", encoding="utf-8")
    assert BD.load_team_set(path) == set()


def test_build_end_to_end(tmp_path):
    replays_dir = tmp_path / "replays"
    replays_dir.mkdir()
    (replays_dir / "ep1.json").write_text(
        json.dumps(_replay(DECK_A, DECK_B, ("team_x", "other"))), encoding="utf-8"
    )
    (replays_dir / "ep2.json").write_text(
        json.dumps(_replay(DECK_A, DECK_C, ("team_x", "other"))), encoding="utf-8"
    )
    result = BD.build(replays_dir, {"team_x"}, k=2, validate_fn=_always_legal)
    assert result["distinct_decklists"] == 1
    assert len(result["selected"]) == 1
    assert result["selected"][0]["count"] == 2


def test_main_writes_deck_csvs_and_report(tmp_path, monkeypatch):
    replays_dir = tmp_path / "replays"
    replays_dir.mkdir()
    (replays_dir / "ep1.json").write_text(
        json.dumps(_replay(DECK_A, DECK_B, ("team_x", "other"))), encoding="utf-8"
    )
    teams_path = tmp_path / "teams.json"
    teams_path.write_text(json.dumps({"teams": ["team_x"]}), encoding="utf-8")
    decks_dir = tmp_path / "decks"
    report_path = tmp_path / "report.json"

    monkeypatch.setattr(BD, "validate", _always_legal)
    rc = BD.main([
        str(replays_dir),
        "--teams-path", str(teams_path),
        "--decks-dir", str(decks_dir),
        "--top-k", "2",
        "--out", str(report_path),
    ])
    assert rc == 0
    assert (decks_dir / "bracket_1.csv").exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["selected"][0]["count"] == 1


def test_main_missing_source_returns_nonzero(tmp_path):
    rc = BD.main([str(tmp_path / "no_such_dataset.zip"), "--episodes-dir", str(tmp_path)])
    assert rc == 1


def test_main_missing_teams_returns_nonzero(tmp_path):
    replays_dir = tmp_path / "replays"
    replays_dir.mkdir()
    rc = BD.main([str(replays_dir), "--teams-path", str(tmp_path / "no_teams.json")])
    assert rc == 1


def test_console_safe_drops_unencodable_chars(monkeypatch):
    class FakeStdout:
        encoding = "cp1252"

    monkeypatch.setattr(BD.sys, "stdout", FakeStdout())
    assert BD._console_safe("Alfonso Sánchez") == "Alfonso Sánchez"
    assert BD._console_safe("山田") == "??"
