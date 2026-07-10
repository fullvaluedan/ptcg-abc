"""U107b: per-build loss targeting reads the live shipped builds, not the pool.

tools/daily_refresh.py's refresh_loss_distribution renders a per-build loss
distribution (filtered by state/current.md's live_refs array) as the PRIMARY
"top loss bucket" current.md shows, with the pool-wide distribution over every
build ever submitted demoted to a secondary line. When live_refs is absent, or
the episode-to-ref manifest has no coverage for any ref in it, the tool falls
back to the pool-wide distribution as the primary reading -- but that fallback
must be stated LOUDLY in the rendered output, because a silent fallback would
look identical to real per-build targeting and mask a lost-update regression
back to the audited-broken mixed-pool behavior.

This unit also makes tools/loop_state.py's state writer concurrency-safe: a
temp-file-plus-os.replace write so a crash mid-write cannot truncate current.md,
and a lock-file-serialized update_current() so two concurrent read-modify-write
callers (the autoloop's bash-driven refresh and this push's canonical writes)
cannot silently lose one another's update. These tests are fully hermetic: no
network, no real data/replays or data/episode_to_ref.json, only fixture replay
dirs and a fixture manifest built in tmp_path.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import pytest

from tools import daily_refresh as dr
from tools import harvest_replays as hr
from tools import loop_state as ls


# --------------------------------------------------------------------------- #
# fixtures: an isolated state dir, and a tiny fixture replay corpus + manifest
# --------------------------------------------------------------------------- #
@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    """Point the module's state paths at a throwaway dir for the test.

    dr.loop_state is the SAME module object as ls (tools.daily_refresh imports
    tools.loop_state directly), so patching ls's paths here also redirects
    dr.refresh_loss_distribution's read_current()/update_current() calls.
    """
    state_dir = tmp_path / "state"
    monkeypatch.setattr(ls, "STATE_DIR", state_dir)
    monkeypatch.setattr(ls, "CURRENT_PATH", state_dir / "current.md")
    monkeypatch.setattr(ls, "HYPOTHESES_PATH", state_dir / "hypotheses.md")
    return state_dir


def _replay(reward, my_bench, my_deck, my_prize, opp_prize):
    """A minimal replay shape scout.parse_replay accepts. Our seat is 0."""
    return {
        "rewards": reward,
        "info": {"TeamNames": ["Dan Arreola", "them"]},
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


REF_A = "ref-A-111"
REF_B = "ref-B-222"


@pytest.fixture
def fixture_corpus(tmp_path, monkeypatch):
    """Five fixture episodes across two refs, plus their episode-to-ref manifest.

    refA: 2 early_collapse losses (empty bench, deck non-empty) + 1 win -> 3 games.
    refB: 1 deckout loss (deck hits 0) + 1 win -> 2 games.
    Pool-wide (no filter) therefore totals 5 games; refA-filtered totals 3;
    refB-filtered totals 2. hr.DEFAULT_MANIFEST is monkeypatched so
    classify_dirs_per_build's manifest lookup (hr._load_episode_to_ref_manifest,
    called with no args) reads this fixture instead of the real data/ path.
    """
    replay_dir = tmp_path / "replays_fixture"
    replay_dir.mkdir()

    episodes = {
        "ep-a1": (REF_A, _replay([0, 1], my_bench=0, my_deck=20, my_prize=2, opp_prize=1)),
        "ep-a2": (REF_A, _replay([0, 1], my_bench=0, my_deck=18, my_prize=3, opp_prize=1)),
        "ep-a3": (REF_A, _replay([1, 0], my_bench=3, my_deck=15, my_prize=0, opp_prize=3)),
        "ep-b1": (REF_B, _replay([0, 1], my_bench=3, my_deck=0, my_prize=2, opp_prize=1)),
        "ep-b2": (REF_B, _replay([1, 0], my_bench=3, my_deck=12, my_prize=0, opp_prize=3)),
    }
    manifest = {}
    for ep_id, (ref, replay) in episodes.items():
        (replay_dir / f"{ep_id}.json").write_text(json.dumps(replay), encoding="utf-8")
        manifest[ep_id] = ref

    manifest_path = tmp_path / "episode_to_ref.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(hr, "DEFAULT_MANIFEST", manifest_path)

    return replay_dir


# --------------------------------------------------------------------------- #
# scenario 1: live_refs present routes targeting to filtered counts
# --------------------------------------------------------------------------- #
def test_live_refs_present_routes_to_filtered_counts(tmp_state, fixture_corpus):
    dist = dr.refresh_loss_distribution(ladder_dirs=[str(fixture_corpus)], live_refs=[REF_A])

    assert dist["targeting_mode"] == "per_build"
    assert dist["fallback_reason"] is None
    assert dist["games"] == 3       # only refA's 3 episodes
    assert dist["wins"] == 1
    assert dist["losses"] == 2
    assert dist["top_bucket"] == "early_collapse"

    # The pool-wide secondary line covers every episode regardless of ref.
    assert dist["pool_wide"]["games"] == 5

    stored = ls.read_current()["loss_distribution"]
    assert stored == dist


def test_live_refs_present_for_other_build_routes_differently(tmp_state, fixture_corpus):
    dist = dr.refresh_loss_distribution(ladder_dirs=[str(fixture_corpus)], live_refs=[REF_B])
    assert dist["targeting_mode"] == "per_build"
    assert dist["games"] == 2       # only refB's 2 episodes
    assert dist["top_bucket"] == "deckout"


# --------------------------------------------------------------------------- #
# scenario 2: absent live_refs falls back, loudly and visibly
# --------------------------------------------------------------------------- #
def test_live_refs_absent_seeds_default_and_falls_back_loudly(tmp_state, fixture_corpus):
    # No live_refs key has ever been recorded: refresh_loss_distribution must
    # seed the default two live refs (via the canonical locked writer) AND,
    # since the fixture manifest has zero coverage for those production refs,
    # fall back to pool-wide -- with the fallback explicitly marked.
    assert "live_refs" not in ls.read_current()

    dist = dr.refresh_loss_distribution(ladder_dirs=[str(fixture_corpus)])

    assert dist["targeting_mode"] == "pool_fallback"
    assert dist["fallback_reason"]  # non-empty, explains why
    assert dist["games"] == 5  # pool-wide, not filtered

    seeded = ls.read_current().get("live_refs")
    assert seeded == ls.DEFAULT_LIVE_REFS

    prose = ls.CURRENT_PATH.read_text(encoding="utf-8")
    assert "FALLBACK TO POOL-WIDE TARGETING" in prose


def test_live_refs_explicit_empty_falls_back_with_no_live_refs_reason(tmp_state, fixture_corpus):
    dist = dr.refresh_loss_distribution(ladder_dirs=[str(fixture_corpus)], live_refs=[])
    assert dist["targeting_mode"] == "pool_fallback"
    assert "no live_refs recorded" in dist["fallback_reason"]
    # An explicitly empty live_refs is an operator choice; it must not be
    # silently overwritten by the default seed.
    assert ls.read_current().get("live_refs") in (None, [])


def test_manifest_lacking_coverage_falls_back_with_coverage_reason(tmp_state, fixture_corpus):
    dist = dr.refresh_loss_distribution(
        ladder_dirs=[str(fixture_corpus)], live_refs=["totally-unknown-ref"])
    assert dist["targeting_mode"] == "pool_fallback"
    assert "matched zero episodes" in dist["fallback_reason"]
    assert dist["games"] == 5  # pool-wide


# --------------------------------------------------------------------------- #
# scenario 3: a ref missing from the manifest contributes zero, never crashes
# --------------------------------------------------------------------------- #
def test_ref_missing_from_manifest_contributes_zero_not_crash(tmp_state, fixture_corpus):
    dist = dr.refresh_loss_distribution(
        ladder_dirs=[str(fixture_corpus)], live_refs=["not-in-manifest", REF_A])
    # refA still contributes its 3 games; the unknown ref silently adds nothing.
    assert dist["targeting_mode"] == "per_build"
    assert dist["games"] == 3


# --------------------------------------------------------------------------- #
# scenario 4: rendered current.md keeps the JSON block as source of truth
# --------------------------------------------------------------------------- #
def test_round_trip_preserves_pre_registrations(tmp_state, fixture_corpus):
    row = {
        "build": "heuristic+trolley_thick",
        "hypothesis": "thin_bench_threshold",
        "direction": "up",
        "margin": 60,
        "n": 30,
        "settle_by": "2026-07-09",
        "filters": "collapse 80.8->65.4 (n=240, p<0.001)",
        "actions": {"win": "promote to king", "loss": "evict, revert to king",
                    "band": "one repeat then scoreboard"},
    }
    data = {"loss_distribution": {}}
    ls.upsert_prereg(data, row)
    ls.write_current(data)
    before = ls.read_current()["pre_registrations"]
    assert before == [row]

    dr.refresh_loss_distribution(ladder_dirs=[str(fixture_corpus)], live_refs=[REF_A])

    after = ls.read_current()["pre_registrations"]
    assert after == before


def test_rendered_primary_and_secondary_lines(tmp_state, fixture_corpus):
    dr.refresh_loss_distribution(ladder_dirs=[str(fixture_corpus)], live_refs=[REF_A])
    prose = ls.CURRENT_PATH.read_text(encoding="utf-8")
    assert "per-build targeting (U107b), live refs: ref-A-111" in prose
    assert "secondary, pool-wide (every build ever submitted):" in prose
    assert "FALLBACK TO POOL-WIDE TARGETING" not in prose


# --------------------------------------------------------------------------- #
# scenario 5: two concurrent writers cannot lose an update
# --------------------------------------------------------------------------- #
def test_concurrent_writers_serialize_no_lost_update(tmp_state):
    ls.write_current({"counter_log": []})

    slow_started = threading.Event()
    release_slow = threading.Event()
    results = {}

    def _slow_mutate(data):
        # The slow writer has already done its read; it now holds the lock
        # while "thinking" before it writes. A second writer starting during
        # this window must block on the lock, not read the same stale
        # snapshot and clobber this writer's eventual write.
        slow_started.set()
        release_slow.wait(timeout=5)
        log = list(data.get("counter_log") or [])
        log.append("slow")
        data["counter_log"] = log
        return data

    def _fast_mutate(data):
        log = list(data.get("counter_log") or [])
        log.append("fast")
        data["counter_log"] = log
        return data

    def _run_slow():
        results["slow"] = ls.update_current(_slow_mutate)

    def _run_fast():
        results["fast"] = ls.update_current(_fast_mutate)

    t_slow = threading.Thread(target=_run_slow)
    t_slow.start()
    assert slow_started.wait(timeout=5)
    # The slow writer is holding the lock (inside its mutator) right now.
    t_fast = threading.Thread(target=_run_fast)
    t_fast.start()
    time.sleep(0.2)  # the fast writer should be blocked acquiring the lock here
    release_slow.set()
    t_slow.join(timeout=5)
    t_fast.join(timeout=5)

    assert not t_slow.is_alive()
    assert not t_fast.is_alive()
    final = ls.read_current()["counter_log"]
    # Both updates landed: the fast writer necessarily re-read AFTER the slow
    # writer released the lock and wrote, so nothing was lost.
    assert final == ["slow", "fast"]


def test_lock_times_out_rather_than_writing_unlocked(tmp_state):
    ls.write_current({"counter_log": []})
    lock_path = Path(str(ls.CURRENT_PATH) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        with pytest.raises(ls.LockTimeout):
            ls._FileLock(ls.CURRENT_PATH, timeout=0.2, poll_s=0.02).acquire()
        # A timed-out lock attempt must not have written anything.
        assert ls.read_current()["counter_log"] == []
    finally:
        os.close(fd)
        lock_path.unlink()


# --------------------------------------------------------------------------- #
# scenario 6: a failed write never leaves a truncated current.md
# --------------------------------------------------------------------------- #
def test_failed_write_does_not_truncate_existing_file(tmp_state, monkeypatch):
    ls.write_current({"shadow_king": {"build": "safe", "ladder": 1.0}})
    original = ls.CURRENT_PATH.read_text(encoding="utf-8")
    assert original  # sanity: something was actually written

    def _boom(*_args, **_kwargs):
        raise OSError("simulated crash mid-write")

    monkeypatch.setattr(os, "replace", _boom)
    with pytest.raises(OSError):
        ls.write_current({"shadow_king": {"build": "corrupt-attempt", "ladder": 2.0}})

    # The destination file is untouched: still the ORIGINAL content, not
    # truncated and not partially overwritten.
    assert ls.CURRENT_PATH.read_text(encoding="utf-8") == original

    # No orphaned temp file left behind in state/.
    leftovers = [p for p in ls.STATE_DIR.iterdir() if p.name != ls.CURRENT_PATH.name
                 and p.suffix == ".tmp"]
    assert leftovers == []


def test_ensure_live_refs_seeds_once_and_never_overwrites():
    data = {}
    ls.ensure_live_refs(data)
    assert data["live_refs"] == ls.DEFAULT_LIVE_REFS

    # A deliberately-emptied live_refs (operator choice) is left alone.
    data2 = {"live_refs": []}
    ls.ensure_live_refs(data2)
    assert data2["live_refs"] == []

    # A live_refs already carrying real refs is left alone too.
    data3 = {"live_refs": ["some-other-ref"]}
    ls.ensure_live_refs(data3)
    assert data3["live_refs"] == ["some-other-ref"]
