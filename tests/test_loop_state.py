"""The stateful loop memory (plan U12): round trip, re-test gating, bucket ranking.

tools/loop_state.py is the loop's memory: current.md carries the live loss
distribution plus kings/candidates/ledger, and hypotheses.md is the falsified-
lever registry with sample sizes and re-test conditions. These tests pin the four
properties the loop relies on:

  1. both state files round-trip (the json STATE block written == read back),
  2. a missing state/ is created on first write rather than erroring, and a
     missing file reads as an empty state rather than raising,
  3. a hypothesis refuted at sample n is flagged for re-test once a larger-sample
     or different-deck condition is met, and not before,
  4. the bucket ranking over fixed replays is stable (deterministic top bucket).

The round-trip and re-test tests write into a tmp state dir by monkeypatching the
module paths, so a run never clobbers the committed state/ files.
"""
import json

import pytest

from tools import loop_state as ls


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    """Point the module's state paths at a throwaway dir for the test."""
    state_dir = tmp_path / "state"
    monkeypatch.setattr(ls, "STATE_DIR", state_dir)
    monkeypatch.setattr(ls, "CURRENT_PATH", state_dir / "current.md")
    monkeypatch.setattr(ls, "HYPOTHESES_PATH", state_dir / "hypotheses.md")
    return state_dir


def test_current_round_trips(tmp_state):
    data = {
        "loss_distribution": {"top_bucket": "early_collapse", "losses": 21,
                              "buckets": {"early_collapse": 21}, "sample_size": 47},
        "shadow_king": {"build": "heuristic+trolley", "ref": "54215558", "ladder": 569.6},
        "reclaim_king": {"build": "heuristic+trolley", "ref": "54215558", "ladder": 569.6},
        "active_candidates": [{"build": "cand-A", "note": "awaiting slot"}],
        "ledger": [{"build": "heuristic+trolley", "ladder": 569.6, "sample_size": 47}],
    }
    ls.write_current(data)
    assert ls.CURRENT_PATH.exists()
    assert ls.read_current() == data


def test_hypotheses_round_trips(tmp_state):
    data = {"hypotheses": [
        {"name": "bench_dig", "verdict": "refuted", "sample_size": 200,
         "deck": "trolley", "retest_sample": 400, "retest_condition": "sample >= 400"},
    ]}
    ls.write_hypotheses(data)
    assert ls.HYPOTHESES_PATH.exists()
    assert ls.read_hypotheses() == data


def test_missing_state_dir_created_on_write(tmp_state):
    assert not tmp_state.exists()
    ls.write_current({"loss_distribution": {}})
    assert tmp_state.exists()
    assert ls.CURRENT_PATH.exists()


def test_missing_file_reads_empty_not_error(tmp_state):
    # Nothing written yet: reads must degrade to {} rather than raise.
    assert ls.read_current() == {}
    assert ls.read_hypotheses() == {}


def test_malformed_block_reads_empty(tmp_state):
    tmp_state.mkdir(parents=True)
    ls.CURRENT_PATH.write_text("# prose only, no json block\n", encoding="utf-8")
    assert ls.read_current() == {}
    ls.HYPOTHESES_PATH.write_text("```json STATE\n{ not valid json\n```\n", encoding="utf-8")
    assert ls.read_hypotheses() == {}


def test_prose_edit_does_not_corrupt_state(tmp_state):
    data = {"shadow_king": {"build": "x", "ladder": 569.6}}
    ls.write_current(data)
    # A human edits the prose above the block; the json block is untouched.
    text = ls.CURRENT_PATH.read_text(encoding="utf-8")
    edited = "# my own notes\n\nsome hand-written prose\n\n" + text[text.find(ls._BLOCK_OPEN):]
    ls.CURRENT_PATH.write_text(edited, encoding="utf-8")
    assert ls.read_current() == data


def test_parse_block_extracts_only_the_fenced_json():
    text = "prose\n```json STATE\n" + json.dumps({"a": 1}) + "\n```\ntrailing prose\n"
    assert ls.parse_state_block(text) == {"a": 1}


def test_round_trip_survives_fence_string_in_a_value(tmp_state):
    # The prose view is rendered from these values WITHOUT json-escaping, so a
    # value that quotes the open-fence string plants a decoy fence above the real
    # block. The parser must anchor to the LAST fence (the appended real block),
    # not the first, or the state is silently lost. Regression for that bug.
    data = {
        "active_candidates": [{"build": "x", "note": "see the ```json STATE block above"}],
        "shadow_king": {"build": "```json STATE", "ladder": 569.6},
    }
    ls.write_current(data)
    assert ls.read_current() == data

    hyp = {"hypotheses": [{"name": "h", "verdict": "refuted",
                           "claim": "quotes a ```json STATE fence and a ``` close"}]}
    ls.write_hypotheses(hyp)
    assert ls.read_hypotheses() == hyp


def test_loss_distribution_from_dirs_happy_path(tmp_path):
    # Two synthetic replays classified through the module's own dir plumbing (not
    # classify_batch directly): one empty-bench collapse loss, one win. Pins that
    # loss_distribution_from_dirs re-keys buckets to BUCKETS, renames games ->
    # sample_size, and records the source dir.
    from analysis.loss_classifier import BUCKETS

    d = tmp_path / "replays_synth"
    d.mkdir()
    # A minimal replay shape scout.parse_replay accepts: one MAIN decision that
    # records the board, then rewards decide the outcome. Our seat is 0.
    def _replay(reward, my_bench, my_deck, my_prize, opp_prize):
        return {
            "rewards": reward,
            "info": {"TeamNames": ["us", "them"]},
            "steps": [[
                {"status": "ACTIVE", "action": 0, "observation": {
                    "select": {"type": 0, "option": [1, 2], "minCount": 1, "maxCount": 1},
                    "remainingOverageTime": 599.0,
                    "current": {"yourIndex": 0, "turn": 10, "players": [
                        {"bench": [0] * my_bench, "deckCount": my_deck, "prize": [0] * my_prize},
                        {"bench": [0, 0], "deckCount": 20, "prize": [0] * opp_prize},
                    ]},
                }},
                {"status": "INACTIVE", "observation": {}},
            ]],
        }
    (d / "episode-1-replay.json").write_text(
        json.dumps(_replay([0, 1], my_bench=0, my_deck=20, my_prize=2, opp_prize=1)),
        encoding="utf-8")
    (d / "episode-2-replay.json").write_text(
        json.dumps(_replay([1, 0], my_bench=3, my_deck=15, my_prize=0, opp_prize=3)),
        encoding="utf-8")

    dist = ls.loss_distribution_from_dirs([d])
    assert dist["games"] == 2
    assert dist["wins"] == 1
    assert dist["losses"] == 1
    assert dist["sample_size"] == dist["games"]
    assert set(dist["buckets"].keys()) == set(BUCKETS)
    assert dist["top_bucket"] == "early_collapse"
    assert dist["sources"] == [str(d)]


def test_retest_flags_on_sample_growth():
    hyp = {"name": "bench_dig", "verdict": "refuted", "sample_size": 200,
           "deck": "trolley", "retest_sample": 400}
    assert ls.needs_retest(hyp, current_sample=200, current_deck="trolley") is False
    assert ls.needs_retest(hyp, current_sample=399, current_deck="trolley") is False
    assert ls.needs_retest(hyp, current_sample=400, current_deck="trolley") is True
    assert ls.needs_retest(hyp, current_sample=800, current_deck="trolley") is True


def test_retest_flags_on_deck_change_only_when_opted_in():
    opted = {"name": "thin_bench", "verdict": "refuted", "deck": "trolley",
             "retest_on_deck_change": True}
    assert ls.needs_retest(opted, current_sample=None, current_deck="trolley") is False
    assert ls.needs_retest(opted, current_sample=None, current_deck="trolley_thick") is True
    # A lever refuted on the meta decks is NOT re-licensed just by being on trolley.
    not_opted = {"name": "meta_copy", "verdict": "refuted", "deck": "meta_archaludon"}
    assert ls.needs_retest(not_opted, current_sample=None, current_deck="trolley") is False


def test_retest_never_flags_non_refuted():
    for verdict in ("active", "confirmed", "resolved"):
        hyp = {"name": "x", "verdict": verdict, "deck": "trolley", "retest_sample": 1}
        assert ls.needs_retest(hyp, current_sample=999, current_deck="other") is False


def test_retest_candidates_lists_only_met():
    data = {"hypotheses": [
        {"name": "grown", "verdict": "refuted", "deck": "trolley", "retest_sample": 100},
        {"name": "standing", "verdict": "refuted", "deck": "trolley", "retest_sample": 10_000},
        {"name": "done", "verdict": "resolved", "deck": "trolley", "retest_sample": 1},
    ]}
    names = ls.retest_candidates(data, current_sample=200, current_deck="trolley")
    assert names == ["grown"]


def _digest(outcome, bucket_shape):
    """A minimal digest classify_batch will bucket the way we want.

    bucket_shape sets the board-end fields loss_classifier reads. For an
    early_collapse we leave an empty bench with cards still in deck; for a deckout
    we zero the deck.
    """
    d = {"outcome": outcome, "our_decisions": [], "rewards": [0, 1] if outcome == "loss" else [1, 0],
         "our_index": 0, "n_turns": 12}
    d.update(bucket_shape)
    return d


def test_bucket_ranking_is_stable():
    # Three empty-bench collapses and one deckout: early_collapse must rank top,
    # and re-running on the same digests must return the same top bucket.
    collapse = {"my_deck_end": 20, "my_bench_end": 0, "my_prize_end": 2, "opp_prize_end": 0}
    deckout = {"my_deck_end": 0, "my_bench_end": 3, "my_prize_end": 3, "opp_prize_end": 1}
    digests = [_digest("loss", collapse) for _ in range(3)] + [_digest("loss", deckout)]
    digests.append(_digest("win", {"my_deck_end": 10, "my_bench_end": 3}))
    from analysis.loss_classifier import classify_batch
    first = classify_batch(digests)
    second = classify_batch(list(digests))
    assert first["top_bucket"] == "early_collapse"
    assert first["ranked"] == second["ranked"]
    assert first["buckets"]["early_collapse"] == 3
    assert first["buckets"]["deckout"] == 1


def test_classify_dirs_missing_dir_contributes_nothing(tmp_path):
    rep = ls.classify_dirs([tmp_path / "does_not_exist"])
    assert rep["games"] == 0
    assert rep["sample_size"] == 0
    assert rep["sources"] == []
    assert rep["top_bucket"] is None


# --------------------------------------------------------------------------- #
# pre-registration: the machine-checked A/B gate (plan U22)
# --------------------------------------------------------------------------- #
def _complete_row(**overrides):
    row = {
        "build": "heuristic+trolley_thick",
        "hypothesis": "thin_bench_threshold",
        "direction": "up",
        "margin": 60,
        "n": 30,
        "settle_by": "2026-07-09",
        "filters": "collapse 80.8->65.4 (n=240, p<0.001), no win-rate regression",
        "actions": {"win": "promote to king", "loss": "evict, revert to king",
                    "band": "one repeat then scoreboard"},
    }
    row.update(overrides)
    return row


def test_complete_prereg_passes():
    assert ls.validate_prereg(_complete_row()) == []
    assert ls.is_prereg_complete(_complete_row()) is True


@pytest.mark.parametrize("field", ["build", "hypothesis", "settle_by", "filters"])
def test_missing_required_string_field_blocks(field):
    row = _complete_row()
    del row[field]
    assert ls.validate_prereg(row)  # non-empty -> incomplete
    assert ls.is_prereg_complete(row) is False


def test_bad_direction_blocks():
    assert ls.validate_prereg(_complete_row(direction="sideways"))
    assert ls.validate_prereg(_complete_row(direction=""))


def test_margin_must_be_positive_int():
    assert ls.validate_prereg(_complete_row(margin=0))
    assert ls.validate_prereg(_complete_row(margin=-5))
    assert ls.validate_prereg(_complete_row(margin="sixty"))


def test_n_must_meet_episode_floor():
    assert ls.validate_prereg(_complete_row(n=29))
    assert ls.validate_prereg(_complete_row(n=ls.MIN_EPISODES)) == []
    assert ls.validate_prereg(_complete_row(n=None))


def test_settle_by_must_be_iso_date():
    assert ls.validate_prereg(_complete_row(settle_by="soon"))
    assert ls.validate_prereg(_complete_row(settle_by="2026-13-40"))
    assert ls.validate_prereg(_complete_row(settle_by="2026-07-09")) == []


def test_actions_need_all_three_branches():
    assert ls.validate_prereg(_complete_row(actions={"win": "x", "loss": "y"}))
    assert ls.validate_prereg(_complete_row(actions={"win": "x", "loss": "y", "band": ""}))
    assert ls.validate_prereg(_complete_row(actions="promote"))


def test_non_mapping_row_is_incomplete():
    assert ls.validate_prereg(None)
    assert ls.validate_prereg("not a row")


def test_upsert_refuses_incomplete_and_stores_complete():
    data = {}
    with pytest.raises(ValueError):
        ls.upsert_prereg(data, _complete_row(margin=0))
    assert "pre_registrations" not in data  # nothing stored on refusal
    ls.upsert_prereg(data, _complete_row())
    assert len(data["pre_registrations"]) == 1


def test_upsert_replaces_by_build():
    data = {}
    ls.upsert_prereg(data, _complete_row(n=30))
    ls.upsert_prereg(data, _complete_row(n=40))
    assert len(data["pre_registrations"]) == 1  # same build -> replaced, not appended
    assert data["pre_registrations"][0]["n"] == 40


def test_submission_gate_blocks_without_row_and_allows_with_one():
    data = {}
    ok, reason = ls.submission_allowed(data, "heuristic+trolley_thick")
    assert ok is False and "no pre-registration" in reason
    ls.upsert_prereg(data, _complete_row())
    ok, reason = ls.submission_allowed(data, "heuristic+trolley_thick")
    assert ok is True
    # A different build still has no row of its own.
    assert ls.submission_allowed(data, "some-other-build")[0] is False


def test_submission_gate_blocks_on_incomplete_stored_row():
    # A hand-planted incomplete row (bypassing upsert) must still be refused.
    data = {"pre_registrations": [{"build": "x", "hypothesis": "h"}]}
    ok, reason = ls.submission_allowed(data, "x")
    assert ok is False and "incomplete" in reason


def test_prereg_round_trips_through_current_md(tmp_state):
    data = {"loss_distribution": {}}
    ls.upsert_prereg(data, _complete_row())
    ls.write_current(data)
    assert ls.read_current()["pre_registrations"] == data["pre_registrations"]


def test_draft_prereg_validates_and_stamps_status():
    data = {}
    with pytest.raises(ValueError):
        ls.upsert_draft_prereg(data, _complete_row(margin=0))
    assert "draft_pre_registrations" not in data  # nothing stored on refusal
    ls.upsert_draft_prereg(data, _complete_row())
    assert len(data["draft_pre_registrations"]) == 1
    assert data["draft_pre_registrations"][0]["status"] == "DRAFT"


def test_draft_prereg_does_not_open_the_submission_gate():
    # A draft is validate-clean but must NEVER allow a submission on its own.
    data = {}
    ls.upsert_draft_prereg(data, _complete_row())
    assert "pre_registrations" not in data  # draft stays out of the live gate list
    ok, reason = ls.submission_allowed(data, "heuristic+trolley_thick")
    assert ok is False and "no pre-registration" in reason


def test_draft_prereg_replaces_by_build_and_round_trips(tmp_state):
    data = {"loss_distribution": {}}
    ls.upsert_draft_prereg(data, _complete_row(n=30))
    ls.upsert_draft_prereg(data, _complete_row(n=40))
    assert len(data["draft_pre_registrations"]) == 1  # same build -> replaced
    assert data["draft_pre_registrations"][0]["n"] == 40
    ls.write_current(data)
    assert ls.read_current()["draft_pre_registrations"] == data["draft_pre_registrations"]


def test_settle_verdict_margin_arithmetic():
    assert ls.settle_verdict(660, 600, margin=60) == "WIN"    # exactly +M
    assert ls.settle_verdict(661, 600, margin=60) == "WIN"
    assert ls.settle_verdict(540, 600, margin=60) == "LOSS"   # exactly -M
    assert ls.settle_verdict(539, 600, margin=60) == "LOSS"
    assert ls.settle_verdict(600, 600, margin=60) == "BAND"   # tie is noise
    assert ls.settle_verdict(659, 600, margin=60) == "BAND"   # sub-margin gain
    assert ls.settle_verdict(541, 600, margin=60) == "BAND"


def test_auto_settle_returns_the_rows_own_committed_action():
    data = {}
    ls.upsert_prereg(data, _complete_row())
    result = ls.auto_settle(data, "heuristic+trolley_thick", 660, 600)
    assert result["verdict"] == "WIN"
    assert result["margin"] == 60
    assert result["action"] == "promote to king"

    result = ls.auto_settle(data, "heuristic+trolley_thick", 540, 600)
    assert result["verdict"] == "LOSS"
    assert result["action"] == "evict, revert to king"

    result = ls.auto_settle(data, "heuristic+trolley_thick", 600, 600)
    assert result["verdict"] == "BAND"
    assert result["action"] == "one repeat then scoreboard"


def test_auto_settle_margin_override_beats_row_margin():
    data = {}
    ls.upsert_prereg(data, _complete_row(margin=60))
    # 30 points is BAND at the row's own M=60 but a WIN once overridden to M=20.
    assert ls.auto_settle(data, "heuristic+trolley_thick", 630, 600)["verdict"] == "BAND"
    result = ls.auto_settle(data, "heuristic+trolley_thick", 630, 600, margin=20)
    assert result["verdict"] == "WIN"
    assert result["margin"] == 20


def test_auto_settle_raises_without_a_registration_row():
    with pytest.raises(ValueError, match="no pre-registration row"):
        ls.auto_settle({}, "unregistered-build", 660, 600)


def test_auto_settle_raises_on_incomplete_row():
    # A hand-planted incomplete row (bypassing upsert) must still be refused.
    data = {"pre_registrations": [{"build": "x", "hypothesis": "h"}]}
    with pytest.raises(ValueError, match="pre-registration incomplete"):
        ls.auto_settle(data, "x", 660, 600)


# --------------------------------------------------------------------------- #
# proxy retrodiction gate: no uncalibrated proxy may block a slot (plan U24)
# --------------------------------------------------------------------------- #
def test_proxy_gate_blocks_uncalibrated():
    # Default-deny: a proxy with no calibration report may never gate.
    ok, reason = ls.proxy_may_gate({}, "cloned_gauntlet")
    assert ok is False and "no calibration report" in reason


def test_proxy_gate_allows_passing_proxy():
    from analysis.proxy_calibration import KNOWN_LADDER

    data = {}
    ls.record_proxy_calibration(data, "ladder_echo", dict(KNOWN_LADDER))
    ok, reason = ls.proxy_may_gate(data, "ladder_echo")
    assert ok is True and "may BLOCK a slot" in reason


def test_proxy_gate_refuses_failing_proxy():
    from analysis.proxy_calibration import KNOWN_LADDER

    data = {}
    # A proxy that reverses the ordering fails retrodiction.
    ls.record_proxy_calibration(data, "weak_bot_gauntlet",
                                {b: -v for b, v in KNOWN_LADDER.items()})
    ok, reason = ls.proxy_may_gate(data, "weak_bot_gauntlet")
    assert ok is False and "failed retrodiction" in reason


def test_record_proxy_calibration_replaces_by_name():
    from analysis.proxy_calibration import KNOWN_LADDER

    data = {}
    ls.record_proxy_calibration(data, "p", {b: -v for b, v in KNOWN_LADDER.items()})
    ls.record_proxy_calibration(data, "p", dict(KNOWN_LADDER))
    assert len(data["calibrated_proxies"]) == 1  # same name -> replaced
    assert ls.proxy_may_gate(data, "p")[0] is True


def test_proxy_calibration_round_trips_through_current_md(tmp_state):
    from analysis.proxy_calibration import KNOWN_LADDER

    data = {"loss_distribution": {}}
    ls.record_proxy_calibration(data, "ladder_echo", dict(KNOWN_LADDER),
                                note="illustrative perfect proxy")
    ls.write_current(data)
    assert ls.read_current()["calibrated_proxies"] == data["calibrated_proxies"]


def test_census_round_trips_and_renders(tmp_state):
    """The U25 census tier survives the round trip and shows in the prose view."""
    data = {
        "loss_distribution": {},
        "census": {
            "cohort": "winning seat",
            "dataset": "2026-06-30 (5734 episodes)",
            "episodes_scored": 5732,
            "ranking_groups": 167531,
            "target_family": "meta_grimmsnarl",
            "target_tier": "full",
            "source": "analysis/expert_census.md",
        },
    }
    ls.write_current(data)
    assert ls.read_current()["census"] == data["census"]
    prose = ls.CURRENT_PATH.read_text(encoding="utf-8")
    assert "Expert census tier (U25)" in prose
    assert "meta_grimmsnarl" in prose
    assert "tier **full**" in prose


def test_reconciliation_round_trips_and_renders(tmp_state):
    """The U28 contract reconciliation record survives the round trip and renders."""
    data = {
        "loss_distribution": {},
        "reconciliation": {
            "rulings": 11,
            "source": "docs/design/deck-aware-execution-design.md",
            "recorded": "2026-07-02",
            "w_generic": "DROPPED (fallback = pure ladder; no pooled block)",
            "census_tier": "FULL (167531 groups >> 2500)",
        },
    }
    ls.write_current(data)
    assert ls.read_current()["reconciliation"] == data["reconciliation"]
    prose = ls.CURRENT_PATH.read_text(encoding="utf-8")
    assert "Contract reconciliation record (U28)" in prose
    assert "11 forked contracts" in prose
    assert "W_generic ruling: DROPPED" in prose


def test_reconciliation_absent_renders_nothing(tmp_state):
    """No reconciliation key means no U28 section in the prose view."""
    ls.write_current({"loss_distribution": {}})
    prose = ls.CURRENT_PATH.read_text(encoding="utf-8")
    assert "Contract reconciliation record (U28)" not in prose


def test_final_scoring_round_trips_and_renders(tmp_state):
    """The U29 final scoring semantics survive the round trip and render."""
    data = {
        "loss_distribution": {},
        "final_scoring": {
            "model": "latest-2 tracked and used for final scoring; leaderboard shows best of the 2",
            "source": "analysis/final_scoring_semantics.md",
            "recorded": "2026-07-02",
            "deadline": "2026-08-16 23:59 UTC",
            "final_window": "~2 weeks continued games, then leaderboard final",
            "daily_limit": "5 submissions/day",
        },
    }
    ls.write_current(data)
    assert ls.read_current()["final_scoring"] == data["final_scoring"]
    prose = ls.CURRENT_PATH.read_text(encoding="utf-8")
    assert "Final scoring semantics (U29)" in prose
    assert "latest-2" in prose
    assert "gates U48" in prose


def test_final_scoring_absent_renders_nothing(tmp_state):
    """No final_scoring key means no U29 section in the prose view."""
    ls.write_current({"loss_distribution": {}})
    prose = ls.CURRENT_PATH.read_text(encoding="utf-8")
    assert "Final scoring semantics (U29)" not in prose
