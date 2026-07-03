"""Tests for the teacher self-play label store (plan U83 prep step).

Pure logic only, no engine: `is_scorable_main`/`played_index` mirror
`analysis.replay_trace`'s scorable-decision definition and `agreement` mirrors
`analysis.move_ranking_validator.agreement`'s contract, so these tests pin the
same shapes and edge cases those modules already pin, on the JSONL record
source instead of a Kaggle replay.
"""
import json

from analysis import teacher_labels as tl


def test_is_scorable_main_filters_non_main_select():
    assert tl.is_scorable_main({"select": None}) is None
    sel = {"type": 1, "minCount": 1, "maxCount": 1, "option": [1, 2]}
    assert tl.is_scorable_main({"select": sel}) is None


def test_is_scorable_main_filters_multi_pick():
    sel = {"type": 0, "minCount": 1, "maxCount": 2, "option": [1, 2, 3]}
    assert tl.is_scorable_main({"select": sel}) is None


def test_is_scorable_main_filters_single_option():
    sel = {"type": 0, "minCount": 1, "maxCount": 1, "option": [1]}
    assert tl.is_scorable_main({"select": sel}) is None


def test_is_scorable_main_accepts_valid_decision():
    sel = {"type": 0, "minCount": 1, "maxCount": 1, "option": [1, 2, 3]}
    got = tl.is_scorable_main({"select": sel})
    assert got is not None
    got_sel, options = got
    assert got_sel is sel
    assert options == [1, 2, 3]


def test_played_index_accepts_single_nonnegative_int():
    assert tl.played_index([2]) == 2
    assert tl.played_index([0]) == 0


def test_played_index_rejects_multi_bool_negative_and_other():
    assert tl.played_index([1, 2]) is None
    assert tl.played_index([True]) is None
    assert tl.played_index([-1]) is None
    assert tl.played_index("nope") is None
    assert tl.played_index(list(range(60))) is None


def test_agreement_counts_matches_and_mismatches():
    records = [
        {"obs": {"i": 0}, "played": 1},
        {"obs": {"i": 1}, "played": 0},
    ]

    def pilot(obs):
        return [1]

    result = tl.agreement(records, pilot)
    assert result == {"n": 2, "agree": 1, "agreement": 0.5}


def test_agreement_pilot_exception_counts_as_nonmatch():
    records = [{"obs": {}, "played": 0}]

    def pilot(obs):
        raise ValueError("boom")

    result = tl.agreement(records, pilot)
    assert result == {"n": 1, "agree": 0, "agreement": 0.0}


def test_agreement_non_single_index_reply_counts_as_nonmatch():
    records = [{"obs": {}, "played": 0}]
    assert tl.agreement(records, lambda obs: [0, 1]) == {"n": 1, "agree": 0, "agreement": 0.0}


def test_agreement_empty_records_reports_none():
    assert tl.agreement([], lambda obs: [0]) == {"n": 0, "agree": 0, "agreement": None}


def test_logger_wrap_only_logs_scorable_decisions(tmp_path):
    path = tmp_path / "labels.jsonl"
    logger = tl.TeacherLogger(path)
    rows = []
    sel_multi = {"type": 0, "minCount": 1, "maxCount": 1, "option": [1, 2, 3]}
    sel_single = {"type": 0, "minCount": 1, "maxCount": 1, "option": [1]}

    obs_seq = [{"select": sel_multi}, {"select": sel_single}, {"select": None}]
    moves = iter([[2], [0], list(range(60))])

    def fake_agent(obs):
        return next(moves)

    wrapped = logger.wrap(fake_agent, game_id=7, seat=0, rows=rows)
    for obs in obs_seq:
        wrapped(obs)
    logger.flush_game(rows)
    logger.close()

    loaded = list(tl.load_records(path))
    assert len(loaded) == 1
    rec = loaded[0]
    assert rec["game_id"] == 7
    assert rec["seat"] == 0
    assert rec["decision_id"] == 0
    assert rec["played"] == 2
    assert rec["obs"]["select"] == sel_multi


def test_logger_append_mode_accumulates_across_calls(tmp_path):
    path = tmp_path / "labels.jsonl"
    sel = {"type": 0, "minCount": 1, "maxCount": 1, "option": [1, 2]}

    for game_id in (0, 1):
        logger = tl.TeacherLogger(path)
        rows = []
        wrapped = logger.wrap(lambda obs: [1], game_id, 0, rows)
        wrapped({"select": sel})
        logger.flush_game(rows)
        logger.close()

    loaded = list(tl.load_records(path))
    assert [rec["game_id"] for rec in loaded] == [0, 1]


def test_load_records_respects_limit(tmp_path):
    path = tmp_path / "labels.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        for i in range(5):
            fh.write(json.dumps({"game_id": i, "seat": 0, "played": 0, "obs": {}}) + "\n")
    loaded = list(tl.load_records(path, limit=3))
    assert len(loaded) == 3


def test_load_records_skips_malformed_lines(tmp_path):
    path = tmp_path / "labels.jsonl"
    path.write_text(
        json.dumps({"game_id": 0, "played": 0, "obs": {}}) + "\nnot json\n\n",
        encoding="utf-8",
    )
    loaded = list(tl.load_records(path))
    assert len(loaded) == 1


def test_load_records_reads_directory_of_jsonl(tmp_path):
    (tmp_path / "a.jsonl").write_text(
        json.dumps({"game_id": 0, "played": 0, "obs": {}}) + "\n", encoding="utf-8"
    )
    (tmp_path / "b.jsonl").write_text(
        json.dumps({"game_id": 1, "played": 0, "obs": {}}) + "\n", encoding="utf-8"
    )
    loaded = list(tl.load_records(tmp_path))
    assert len(loaded) == 2


def test_load_records_stamps_the_source_file_name(tmp_path):
    (tmp_path / "a.jsonl").write_text(
        json.dumps({"game_id": 0, "played": 0, "obs": {}}) + "\n", encoding="utf-8"
    )
    loaded = list(tl.load_records(tmp_path / "a.jsonl"))
    assert loaded[0]["_source"] == "a.jsonl"


def test_match_key_combines_source_and_game_id():
    assert tl.match_key({"_source": "a.jsonl", "game_id": 3}) == "a.jsonl:3"
    assert tl.match_key({"game_id": 3}) == ":3"


def test_match_key_distinguishes_same_game_id_across_files():
    # game_id resets to 0 in every harvest run/file, so the source name must
    # disambiguate or two unrelated games would collide onto one split bucket.
    a = tl.match_key({"_source": "a.jsonl", "game_id": 0})
    b = tl.match_key({"_source": "b.jsonl", "game_id": 0})
    assert a != b


def test_split_of_is_stable_and_covers_both_buckets():
    records = [{"_source": "a.jsonl", "game_id": i} for i in range(200)]
    splits = {tl.split_of(rec) for rec in records}
    assert splits <= {"train", "test"}
    assert "test" in splits and "train" in splits
    # Same record, same split, every time (no wall-clock or randomness involved).
    assert tl.split_of(records[0]) == tl.split_of(records[0])


def test_split_of_keeps_every_decision_of_one_game_together():
    game = [
        {"_source": "a.jsonl", "game_id": 5, "decision_id": i} for i in range(4)
    ]
    assert len({tl.split_of(rec) for rec in game}) == 1
