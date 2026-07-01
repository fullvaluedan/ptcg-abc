"""U6 scout and loss classifier tests.

Replay parsing and bucketing are exercised on synthetic replays shaped exactly
like env.toJSON output, plus one real local match. The Kaggle CLI wrapper is
exercised only on its graceful failure paths so the suite stays fully offline.
"""
import json

from analysis.loss_classifier import (
    BUCKETS,
    classify_batch,
    classify_loss,
    parse_replay,
)
from tools import scout


def _decision(player, turn, n_options, my_prize, opp_prize, overage):
    """One per player record as it appears inside a replay step."""
    return {
        "action": [0],
        "status": "ACTIVE",
        "reward": 0,
        "observation": {
            "remainingOverageTime": overage,
            "select": {"option": list(range(n_options)), "minCount": 1, "maxCount": 1},
            "current": {
                "yourIndex": player,
                "turn": turn,
                "players": [
                    {"prize": [None] * (my_prize if player == 0 else opp_prize)},
                    {"prize": [None] * (opp_prize if player == 0 else my_prize)},
                ],
            },
        },
    }


def _inactive():
    return {"action": [], "status": "INACTIVE", "reward": 0, "observation": {"select": None, "current": None}}


def _replay(rows, rewards):
    """Build a replay from rows of (player, turn, n_options, my_prize, opp_prize, overage).

    Each row becomes a step with the acting player's record in their seat and an
    inactive placeholder in the other, matching env.toJSON's two entry steps.
    """
    steps = [[_inactive(), _inactive()]]  # deck handshake, both select None
    for player, turn, n_opt, myp, oppp, ov in rows:
        step = [None, None]
        step[player] = _decision(player, turn, n_opt, myp, oppp, ov)
        step[1 - player] = _inactive()
        steps.append(step)
    return {"steps": steps, "rewards": rewards}


def test_parse_outcome_and_records():
    rep = _replay(
        [(0, 1, 3, 6, 6, 600.0), (0, 3, 5, 5, 4, 599.0)],
        rewards=[1, -1],
    )
    dg = parse_replay(rep, our_index=0)
    assert dg["outcome"] == "win"
    assert dg["n_decisions"] == 2
    assert len(dg["our_decisions"]) == 2
    last = dg["our_decisions"][-1]
    assert last["my_prize"] == 5 and last["opp_prize"] == 4
    assert last["n_options"] == 5 and last["turn"] == 3
    # decision_time is the drop in our own overage bank since the prior decision.
    assert abs(last["decision_time"] - 1.0) < 1e-9


def test_inactive_stale_select_not_counted():
    # The engine leaves an inactive seat a stale non null select. Only the seat
    # marked ACTIVE is a real decision, so the stale one must not be recorded.
    active = _decision(1, 2, 3, 6, 6, 600.0)
    stale = _decision(0, 1, 2, 6, 6, 600.0)
    stale["status"] = "INACTIVE"  # stale select, not acting
    rep = {"steps": [[_inactive(), _inactive()], [stale, active]], "rewards": [-1, 1]}
    dg = parse_replay(rep, our_index=1)
    assert dg["n_decisions"] == 1
    assert dg["our_decisions"][0]["player"] == 1


def test_outcome_from_our_index():
    rep = _replay([(1, 2, 2, 5, 6, 600.0)], rewards=[1, -1])
    assert parse_replay(rep, our_index=1)["outcome"] == "loss"
    assert parse_replay(rep, our_index=0)["outcome"] == "win"


def test_classify_steamroll_is_deck_matchup():
    # We lost having taken only one prize (five still remaining): a blowout.
    rep = _replay(
        [(0, 1, 3, 6, 6, 600.0), (0, 5, 4, 5, 1, 599.5)],
        rewards=[-1, 1],
    )
    assert classify_loss(parse_replay(rep)) == "deck_matchup"


def test_classify_close_is_endgame_misplay():
    # We needed one more prize and lost: a near win that slipped.
    rep = _replay(
        [(0, 4, 3, 3, 2, 600.0), (0, 8, 4, 1, 1, 599.0)],
        rewards=[-1, 1],
    )
    assert classify_loss(parse_replay(rep)) == "endgame_misplay"


def test_classify_slow_search_wins_over_board():
    # A single slow move flags timing even though the board looks like a misplay.
    rep = _replay(
        [(0, 4, 3, 2, 2, 600.0), (0, 8, 4, 1, 1, 585.0)],  # 15s on one move
        rewards=[-1, 1],
    )
    assert classify_loss(parse_replay(rep)) == "slow_search"


def test_classify_low_bank_is_slow_search():
    rep = _replay(
        [(0, 4, 3, 3, 3, 200.0), (0, 8, 4, 3, 1, 40.0)],  # ended under the 60s bank floor
        rewards=[-1, 1],
    )
    assert classify_loss(parse_replay(rep)) == "slow_search"


def test_classify_middling_is_bad_determinization():
    rep = _replay(
        [(0, 3, 3, 4, 3, 600.0), (0, 7, 4, 3, 1, 599.0)],
        rewards=[-1, 1],
    )
    assert classify_loss(parse_replay(rep)) == "bad_determinization"


def test_classify_returns_none_for_non_loss():
    rep = _replay([(0, 1, 3, 5, 6, 600.0)], rewards=[1, -1])
    assert classify_loss(parse_replay(rep)) is None


def test_classify_batch_ranks_buckets():
    steamroll = parse_replay(_replay([(0, 5, 3, 5, 1, 600.0)], rewards=[-1, 1]))
    close = parse_replay(_replay([(0, 8, 3, 1, 1, 599.0)], rewards=[-1, 1]))
    another_steamroll = parse_replay(_replay([(0, 5, 3, 6, 0, 600.0)], rewards=[-1, 1]))
    win = parse_replay(_replay([(0, 3, 3, 4, 6, 600.0)], rewards=[1, -1]))
    rep = classify_batch([steamroll, close, another_steamroll, win])
    assert rep["games"] == 4
    assert rep["wins"] == 1 and rep["losses"] == 3
    assert rep["buckets"]["deck_matchup"] == 2
    assert rep["buckets"]["endgame_misplay"] == 1
    assert rep["top_bucket"] == "deck_matchup"
    assert rep["ranked"][0][0] == "deck_matchup"
    assert set(rep["buckets"]) == set(BUCKETS)


def test_report_over_directory(tmp_path):
    json.dump(_replay([(0, 5, 3, 5, 1, 600.0)], rewards=[-1, 1]), open(tmp_path / "a.json", "w"))
    json.dump(_replay([(0, 3, 3, 4, 6, 600.0)], rewards=[1, -1]), open(tmp_path / "b.json", "w"))
    open(tmp_path / "broken.json", "w").write("{ not json")
    rep = scout.report(tmp_path)
    assert rep["games"] == 2  # the broken file is skipped, not fatal
    assert rep["wins"] == 1 and rep["losses"] == 1
    assert rep["top_bucket"] == "deck_matchup"


def test_run_kaggle_missing_binary(monkeypatch):
    def _boom(*a, **k):
        raise FileNotFoundError()

    monkeypatch.setattr(scout.subprocess, "run", _boom)
    res = scout.run_kaggle(["competitions", "list"])
    assert res["ok"] is False
    assert "kaggle CLI not found" in res["error"]


def test_fetch_episode_handles_unauthorized(monkeypatch, tmp_path):
    class _Proc:
        returncode = 1
        stdout = ""
        stderr = "403 Forbidden"

    monkeypatch.setattr(scout.subprocess, "run", lambda *a, **k: _Proc())
    res = scout.fetch_episode("12345", dest_dir=tmp_path)
    assert res["ok"] is False
    assert "403" in res["error"]


def _replay_with_decks(rows, rewards, team_names=None):
    """Like _replay but each row also carries (my_deck, opp_deck) and an info block.

    rows: (player, turn, n_options, my_prize, opp_prize, my_deck, opp_deck, overage).
    """
    steps = [[_inactive(), _inactive()]]
    for player, turn, n_opt, myp, oppp, mydeck, oppdeck, ov in rows:
        rec = _decision(player, turn, n_opt, myp, oppp, ov)
        players = rec["observation"]["current"]["players"]
        players[0]["deckCount"] = mydeck if player == 0 else oppdeck
        players[1]["deckCount"] = oppdeck if player == 0 else mydeck
        step = [None, None]
        step[player] = rec
        step[1 - player] = _inactive()
        steps.append(step)
    replay = {"steps": steps, "rewards": rewards}
    if team_names is not None:
        replay["info"] = {"TeamNames": list(team_names)}
    return replay


def test_classify_deckout_when_deck_hits_zero():
    # We lost with our deck emptied, even while ahead on prizes (3 left vs 6):
    # the real ladder failure mode the prize heuristic used to hide.
    rep = _replay_with_decks(
        [(0, 20, 3, 4, 6, 5, 18, 600.0), (0, 27, 4, 3, 6, 0, 18, 599.0)],
        rewards=[-1, 1],
    )
    dg = parse_replay(rep, our_index=0)
    assert dg["my_deck_end"] == 0
    assert classify_loss(dg) == "deckout"


def test_classify_one_card_ahead_on_prizes_is_deckout():
    # ep 82885022 signature: a self-mill ending with one card left, a non-empty
    # bench, and the opponent yet to take a prize (six remaining) is the next
    # turn's forced-draw deckout caught one observation early, not a developed
    # board race. The final observed deck is one, not zero.
    rec = _decision(0, 11, 4, 3, 6, 599.0)   # we took three prizes, opp took none
    players = rec["observation"]["current"]["players"]
    players[0]["deckCount"] = 1
    players[1]["deckCount"] = 20
    players[0]["bench"] = [{}, {}, {}]
    players[1]["bench"] = [{}]
    rep = {"steps": [[_inactive(), _inactive()], [rec, _inactive()]], "rewards": [-1, 1]}
    dg = parse_replay(rep, our_index=0)
    assert dg["my_deck_end"] == 1 and dg["my_bench_end"] == 3
    assert classify_loss(dg) == "deckout"


def test_classify_one_card_but_prize_blowout_stays_deck_matchup():
    # One card left is not a deckout when the opponent has actually won the prize
    # race (took five, one remaining): the near-deckout relaxation must not steal
    # a genuine blowout that merely ended on an odd card count.
    rec = _decision(0, 9, 4, 5, 1, 599.0)    # we took one, opp took five
    players = rec["observation"]["current"]["players"]
    players[0]["deckCount"] = 1
    players[1]["deckCount"] = 15
    players[0]["bench"] = [{}, {}]
    rep = {"steps": [[_inactive(), _inactive()], [rec, _inactive()]], "rewards": [-1, 1]}
    dg = parse_replay(rep, our_index=0)
    assert classify_loss(dg) == "deck_matchup"


def test_classify_one_card_empty_bench_stays_early_collapse():
    # A near-empty deck with an EMPTY bench is the empty-bench collapse (lone
    # active knocked out, nothing to promote), not a deckout: bench depletion is
    # the proximate cause, so the near-deckout relaxation must not fire.
    rec = _decision(0, 6, 4, 4, 6, 599.0)
    players = rec["observation"]["current"]["players"]
    players[0]["deckCount"] = 1
    players[1]["deckCount"] = 30
    players[0]["bench"] = []
    players[1]["bench"] = [{}]
    rep = {"steps": [[_inactive(), _inactive()], [rec, _inactive()]], "rewards": [-1, 1]}
    dg = parse_replay(rep, our_index=0)
    assert dg["my_bench_end"] == 0
    assert classify_loss(dg) == "early_collapse"


def test_classify_early_collapse_short_game_no_race():
    # Turn 7 loss, neither side took a prize, decks still full: a setup or rule
    # loss, not a prize blowout and not a deckout.
    rep = _replay_with_decks(
        [(0, 3, 3, 6, 6, 45, 44, 600.0), (0, 7, 4, 6, 6, 42, 41, 600.0)],
        rewards=[-1, 1],
    )
    dg = parse_replay(rep, our_index=0)
    assert classify_loss(dg) == "early_collapse"


def test_parse_tracks_final_bench_count():
    # Bench size is recovered for the end of game board, like deck and prize, so
    # an empty-bench collapse (lone active knocked out, nothing to promote) is
    # distinguishable from a deckout. Our last record shows an empty bench; the
    # opponent's shows two benched Pokemon.
    rec = _decision(0, 3, 3, 6, 6, 600.0)
    players = rec["observation"]["current"]["players"]
    players[0]["bench"] = []          # our seat: empty bench
    players[1]["bench"] = [{}, {}]    # opponent: two benched
    rep = {"steps": [[_inactive(), _inactive()], [rec, _inactive()]], "rewards": [-1, 1]}
    dg = parse_replay(rep, our_index=0)
    assert dg["my_bench_end"] == 0
    assert dg["opp_bench_end"] == 2


def test_parse_bench_absent_is_none():
    # Records without a bench field (older synthetic replays) leave bench None
    # rather than guessing, so the classifier never reads a fabricated zero.
    rep = _replay([(0, 3, 3, 6, 6, 600.0)], rewards=[-1, 1])
    dg = parse_replay(rep, our_index=0)
    assert dg["my_bench_end"] is None


def test_six_six_loss_is_not_deck_matchup():
    # A 6-6 loss is not a prize race blowout; with no deckout signal, not early,
    # and no observed empty bench it must fall through to bad_determinization,
    # never deck_matchup.
    rep = _replay_with_decks(
        [(0, 12, 3, 6, 6, 30, 28, 600.0), (0, 20, 4, 6, 6, 20, 22, 599.0)],
        rewards=[-1, 1],
    )
    assert classify_loss(parse_replay(rep, our_index=0)) == "bad_determinization"


def test_empty_bench_late_loss_is_early_collapse():
    # A turn 12 loss after we had already taken three prizes, deck still full,
    # opponent not steamrolling: the early-turn gate and the took-at-most-one
    # gate both exclude it, so it used to land in bad_determinization. But our
    # bench ended empty (lone active knocked out, nothing to promote), which is
    # the same deck-thinness collapse as the early version, so it is now
    # early_collapse. This is the late/partial collapse real ladder replays
    # showed slipping past the gate.
    rec = _decision(0, 12, 4, 3, 2, 599.0)
    players = rec["observation"]["current"]["players"]
    players[0]["deckCount"] = 33
    players[1]["deckCount"] = 8
    players[0]["bench"] = []        # our seat: empty bench
    players[1]["bench"] = [{}]      # opponent still has a bench
    rep = {"steps": [[_inactive(), _inactive()], [rec, _inactive()]], "rewards": [-1, 1]}
    dg = parse_replay(rep, our_index=0)
    assert dg["my_bench_end"] == 0 and dg["my_deck_end"] == 33
    assert classify_loss(dg) == "early_collapse"


def test_empty_bench_near_win_loss_is_early_collapse():
    # We were one or two prizes from winning (my_prize 2) but our bench ended
    # empty: the lone active was knocked out with nothing to promote. This is the
    # same deck-thinness collapse as the early version, not search slipping a
    # winnable endgame, so it is early_collapse even though the prize count is
    # inside the endgame_misplay (close_remaining) band. Real ladder replays on
    # both leaders showed every "endgame_misplay" loss was actually this shape.
    rec = _decision(0, 13, 4, 2, 3, 599.0)
    players = rec["observation"]["current"]["players"]
    players[0]["deckCount"] = 17
    players[1]["deckCount"] = 20
    players[0]["bench"] = []          # our seat: empty bench
    players[1]["bench"] = [{}, {}]    # opponent still has a bench
    rep = {"steps": [[_inactive(), _inactive()], [rec, _inactive()]], "rewards": [-1, 1]}
    dg = parse_replay(rep, our_index=0)
    assert dg["my_bench_end"] == 0 and dg["my_prize_end"] == 2
    assert classify_loss(dg) == "early_collapse"


def test_near_win_with_bench_stays_endgame_misplay():
    # The empty-bench rule must not swallow a genuine near-win misplay: here we
    # needed two prizes and lost the race but kept a two Pokemon bench, so bench
    # depletion is not the cause and it stays endgame_misplay.
    rec = _decision(0, 14, 4, 2, 1, 599.0)
    players = rec["observation"]["current"]["players"]
    players[0]["deckCount"] = 15
    players[1]["deckCount"] = 12
    players[0]["bench"] = [{}, {}]    # our seat: bench still standing
    rep = {"steps": [[_inactive(), _inactive()], [rec, _inactive()]], "rewards": [-1, 1]}
    dg = parse_replay(rep, our_index=0)
    assert dg["my_bench_end"] == 2 and dg["my_prize_end"] == 2
    assert classify_loss(dg) == "endgame_misplay"


def test_developed_board_midgame_loss_stays_bad_determinization():
    # The empty-bench rule must not swallow genuine middlegame race losses: here
    # we kept a three Pokemon bench but still lost the prize race after turn 8,
    # so it stays bad_determinization (the real residual lever, not a collapse).
    rec = _decision(0, 10, 4, 4, 2, 599.0)
    players = rec["observation"]["current"]["players"]
    players[0]["deckCount"] = 21
    players[1]["deckCount"] = 20
    players[0]["bench"] = [{}, {}, {}]   # our seat: still has a bench
    rep = {"steps": [[_inactive(), _inactive()], [rec, _inactive()]], "rewards": [-1, 1]}
    dg = parse_replay(rep, our_index=0)
    assert dg["my_bench_end"] == 3
    assert classify_loss(dg) == "bad_determinization"


def test_deck_matchup_requires_opponent_prize_race():
    # Opponent took every prize (0 remaining) while we took one: a true blowout.
    rep = _replay_with_decks(
        [(0, 5, 3, 5, 0, 40, 30, 600.0)],
        rewards=[-1, 1],
    )
    assert classify_loss(parse_replay(rep, our_index=0)) == "deck_matchup"


def test_is_self_play_detects_validation_episode():
    same = {"info": {"TeamNames": ["Dan Arreola", "Dan Arreola"]}}
    diff = {"info": {"TeamNames": ["Dan Arreola", "rival"]}}
    assert scout.is_self_play(same) is True
    assert scout.is_self_play(diff) is False
    assert scout.is_self_play({}) is False


def test_our_index_from_replay_matches_team_name():
    rep = {"info": {"TeamNames": ["rival", "dan arreola"]}}
    assert scout.our_index_from_replay(rep, "Dan Arreola") == 1  # case insensitive
    assert scout.our_index_from_replay({"info": {"TeamNames": ["a", "b"]}}, "Dan Arreola") is None
    assert scout.our_index_from_replay({}, "Dan Arreola") is None


def test_report_skips_self_play(tmp_path):
    # A self-play validation loss must not be counted as a ladder loss.
    ladder = _replay_with_decks([(0, 5, 3, 5, 0, 40, 30, 600.0)], rewards=[-1, 1],
                                team_names=["Dan Arreola", "rival"])
    validation = _replay_with_decks([(0, 5, 3, 5, 0, 40, 30, 600.0)], rewards=[-1, 1],
                                    team_names=["Dan Arreola", "Dan Arreola"])
    json.dump(ladder, open(tmp_path / "ladder.json", "w"))
    json.dump(validation, open(tmp_path / "validation.json", "w"))
    rep = scout.report(tmp_path)
    assert rep["games"] == 1  # validation episode excluded
    assert rep["losses"] == 1 and rep["top_bucket"] == "deck_matchup"


def test_parse_cli_json_ignores_trailing_usage_tip():
    # The real Kaggle CLI prints valid JSON then appends a usage hint line, which
    # makes plain json.loads raise "Extra data". parse_cli_json must read just the
    # leading value and ignore the trailing text.
    out = (
        '[\n  {"id": 82874243, "state": "EpisodeState.COMPLETED"}\n]\n'
        'Use "kaggle competitions replay <episode_id>" to download a replay.\n'
    )
    parsed = scout.parse_cli_json(out)
    assert parsed == [{"id": 82874243, "state": "EpisodeState.COMPLETED"}]
    assert scout.parse_cli_json("") == []


def test_list_episodes_tolerates_trailing_tip(monkeypatch):
    # End to end through list_episodes: the appended tip must not break parsing.
    monkeypatch.setattr(
        scout, "run_kaggle",
        lambda *a, **k: {"ok": True, "error": None, "returncode": 0, "stderr": "",
                         "stdout": '[{"id": 7}]\nUse "kaggle competitions replay" to download.\n'},
    )
    res = scout.list_episodes(7)
    assert res["ok"] and res["episodes"] == [{"id": 7}]


def test_kaggle_base_prefers_path_then_module(monkeypatch):
    # When a real kaggle is on PATH, use it directly.
    monkeypatch.setattr(scout.shutil, "which", lambda name: "/usr/bin/kaggle")
    assert scout.kaggle_base() == ["/usr/bin/kaggle"]
    # When it is not, fall back to running it under this interpreter so a venv
    # without kaggle on PATH still works for the unattended autoloop.
    monkeypatch.setattr(scout.shutil, "which", lambda name: None)
    base = scout.kaggle_base()
    assert base == [scout.sys.executable, "-m", "kaggle"]


def test_list_episodes_parses_json(monkeypatch):
    monkeypatch.setattr(
        scout, "run_kaggle",
        lambda *a, **k: {"ok": True, "stdout": '[{"id": 1, "state": "COMPLETED"}]',
                         "stderr": "", "returncode": 0, "error": None},
    )
    res = scout.list_episodes(123)
    assert res["ok"] and res["episodes"][0]["id"] == 1


def test_list_episodes_handles_cli_failure(monkeypatch):
    monkeypatch.setattr(
        scout, "run_kaggle",
        lambda *a, **k: {"ok": False, "stdout": "", "stderr": "403", "returncode": 1, "error": "403"},
    )
    res = scout.list_episodes(123)
    assert res["ok"] is False and res["episodes"] == []


def test_pull_submission_skips_existing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        scout, "list_episodes",
        lambda sid: {"ok": True, "episodes": [{"id": 1}, {"id": 2}]},
    )
    (tmp_path / "episode-1-replay.json").write_text("{}")  # already downloaded
    fetched = []
    monkeypatch.setattr(
        scout, "fetch_episode",
        lambda eid, dest_dir=None: fetched.append(eid) or {"ok": True, "episode": eid},
    )
    res = scout.pull_submission(99, dest_dir=tmp_path)
    assert res["ok"] and res["fetched"] == [2] and res["skipped"] == [1]
    assert fetched == [2]


def test_parse_replay_tolerates_short_players_list():
    # A malformed replay whose current.players has a single entry must not raise:
    # parsing degrades, it never crashes a batch.
    rec = _decision(0, 3, 2, 6, 6, 600.0)
    rec["observation"]["current"]["players"] = [{"prize": [None] * 6, "deckCount": 30}]
    rep = {"steps": [[_inactive(), _inactive()], [rec, _inactive()]], "rewards": [-1, 1]}
    dg = parse_replay(rep, our_index=0)  # must not raise
    assert dg["outcome"] == "loss"
    assert dg["opp_prize_end"] is None  # the absent seat reads as unknown


def test_parse_real_match():
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from ptcg_agent.engine import make_env
    from agents.agent_baseline import agent

    env = make_env()
    env.run([agent, agent])
    dg = parse_replay(env.toJSON(), our_index=0)
    assert dg["outcome"] in ("win", "loss", "draw")
    assert dg["n_decisions"] > 0
    assert all(d["n_options"] >= 1 for d in dg["decisions"])
