"""Tests for analysis/gameplan_seeds.py, the seeds emitter (plan U36, piece 3).

The emitter reads the miner's win-vs-loss stat blocks and turns only the blocks
whose winning signal is both observable (not barred) and concentrated enough into
a small seeds JSON for the U37 consumer. These tests pin the emission gate over
synthetic block dicts (the exact shape gameplan_mine.mine produces), so no cg
engine or competition data is touched:

  1. each block's emission bar (0.70 share for the three target blocks, 0.95
     unanimity for the opening, 0.80 consistency for the two timing blocks),
  2. the three skip reasons -- barred (miner resolution bar), no_mode (nothing
     resolved), below_bar -- are recorded, never silently dropped,
  3. emit_seeds keeps only cleared blocks and carries the decision log + counts,
  4. render_gameplan_doc emits aggregates only (no raw episodes) and shows the
     win-vs-loss contrast,
  5. run_emit / main read the miner's JSON and write the isolated seeds JSON plus
     the committed game-plan doc.
"""
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis import gameplan_seeds as gs  # noqa: E402


# --- block builders (the shape gameplan_mine.mine emits) -------------------

def _cat(win_mode, win_share, *, barred=False, loss_mode=None):
    """A categorical block with the winning mode_share / mode we want to test."""
    return {
        "kind": "categorical",
        "win": {"mode": win_mode, "mode_share": win_share, "resolution_rate": 1.0},
        "loss": {"mode": loss_mode, "mode_share": 0.0, "resolution_rate": 1.0},
        "barred": barred,
    }


def _tim(win_ord, win_consistency, *, barred=False, loss_ord=None):
    """A timing block with the winning consistency / mode_ordinal we want to test."""
    return {
        "kind": "timing",
        "win": {"mode_ordinal": win_ord, "consistency": win_consistency,
                "resolution_rate": 1.0},
        "loss": {"mode_ordinal": loss_ord, "consistency": 0.0, "resolution_rate": 1.0},
        "barred": barred,
    }


# --- emission bars ---------------------------------------------------------

def test_bars_are_the_plan_values():
    assert gs.SHARE_BAR == 0.70
    assert gs.TIMING_BAR == 0.80
    assert gs.UNANIMITY_BAR == 0.95


def test_target_block_uses_share_bar():
    # 0.70 is exactly the bar -> emits; 0.69 is under -> skipped.
    assert gs.evaluate_block("attach_target", _cat("w", 0.70))["emitted"] is True
    under = gs.evaluate_block("attach_target", _cat("w", 0.69))
    assert under["emitted"] is False and under["reason"] == "below_bar"


def test_opening_uses_unanimity_bar():
    # A 0.90 opening share clears the 0.70 share bar but NOT the 0.95 opening bar.
    d = gs.evaluate_block("opening_category", _cat("PLAY", 0.90))
    assert d["emitted"] is False and d["reason"] == "below_bar" and d["bar"] == 0.95
    assert gs.evaluate_block("opening_category", _cat("PLAY", 0.95))["emitted"] is True


def test_timing_uses_consistency_bar():
    assert gs.evaluate_block("first_attack_ordinal", _tim(3, 0.80))["emitted"] is True
    under = gs.evaluate_block("first_evolve_ordinal", _tim(2, 0.79))
    assert under["emitted"] is False and under["reason"] == "below_bar"


# --- skip reasons ----------------------------------------------------------

def test_barred_block_never_emits_even_when_concentrated():
    # Share well over the bar, but barred by the miner's resolution gate.
    d = gs.evaluate_block("attach_target", _cat("w", 1.0, barred=True))
    assert d["emitted"] is False and d["reason"] == "barred"


def test_no_mode_is_recorded_not_dropped():
    d = gs.evaluate_block("play_target", _cat(None, 0.0))
    assert d["emitted"] is False and d["reason"] == "no_mode"


def test_decision_carries_loss_contrast_value():
    d = gs.evaluate_block("attach_target", _cat("win-card", 0.8, loss_mode="loss-card"))
    assert d["value"] == "win-card" and d["loss_value"] == "loss-card"
    t = gs.evaluate_block("first_attack_ordinal", _tim(3, 0.9, loss_ord=5))
    assert t["value"] == 3 and t["loss_value"] == 5


# --- emit_seeds ------------------------------------------------------------

def _full_blocks():
    return {
        "opening_category": _cat("PLAY", 0.96),          # clears unanimity
        "attach_target": _cat("basic-water", 0.80),       # clears share
        "play_target": _cat("ball", 0.50),                # under share
        "evolve_target": _cat("stage2", 1.0, barred=True),  # barred
        "first_attack_ordinal": _tim(3, 0.85),            # clears timing
        "first_evolve_ordinal": _tim(2, 0.60),            # under timing
    }


def test_emit_seeds_keeps_only_cleared_blocks():
    result = gs.emit_seeds({"blocks": _full_blocks(), "episodes_win": 10,
                            "episodes_loss": 4})
    assert set(result["seeds"]) == {
        "opening_category", "attach_target", "first_attack_ordinal"
    }
    assert result["seeds"]["attach_target"]["value"] == "basic-water"
    assert result["seeds"]["first_attack_ordinal"]["value"] == 3
    # Every block still has a recorded decision (nothing silently dropped).
    assert set(result["decisions"]) == set(gs.EMISSION_BAR)
    assert result["decisions"]["evolve_target"]["reason"] == "barred"
    assert result["episodes_win"] == 10 and result["episodes_loss"] == 4


def test_emit_seeds_tolerates_missing_blocks():
    result = gs.emit_seeds({"blocks": {"attach_target": _cat("w", 0.9)}})
    assert set(result["seeds"]) == {"attach_target"}
    assert set(result["decisions"]) == {"attach_target"}


# --- doc rendering (aggregates only) ---------------------------------------

def test_render_doc_shows_contrast_and_no_raw_episodes():
    blocks = {"attach_target": _cat("win-card", 0.80, loss_mode="loss-card")}
    result = gs.emit_seeds({"blocks": blocks, "episodes_win": 7, "episodes_loss": 3})
    result["target_family"] = "meta_grimmsnarl"
    result["source_blocks"] = "data/derived/gameplans/gameplan_blocks.json"
    result["bar_resolution"] = 0.90
    doc = gs.render_gameplan_doc(result)
    assert "meta_grimmsnarl" in doc
    assert "win-card" in doc and "loss-card" in doc  # win-vs-loss contrast
    assert "7 winning, 3 losing" in doc
    assert "SEEDED" in doc
    assert "steps" not in doc and "rewards" not in doc  # no raw-episode leakage


# --- CLI round trip --------------------------------------------------------

def test_run_emit_and_main_write_isolated_json_and_committed_doc(tmp_path):
    blocks_payload = {
        "target_family": "alpha",
        "bar_resolution": 0.90,
        "episodes_win": 5,
        "episodes_loss": 2,
        "blocks": _full_blocks(),
    }
    blocks_file = tmp_path / "gameplan_blocks.json"
    blocks_file.write_text(json.dumps(blocks_payload), encoding="utf-8")

    result = gs.run_emit(str(blocks_file))
    assert result["target_family"] == "alpha"
    assert result["thresholds"]["share"] == 0.70
    assert set(result["seeds"]) == {
        "opening_category", "attach_target", "first_attack_ordinal"
    }

    doc_out = tmp_path / "alpha_gameplan.md"
    rc = gs.main(["--blocks", str(blocks_file), "--out", "test_gameplan_seeds.json",
                  "--doc", str(doc_out)])
    assert rc == 0
    from tools.isolation import derived_path
    seeds_json = derived_path("gameplans", "test_gameplan_seeds.json")
    assert seeds_json.exists()
    written = json.loads(seeds_json.read_text(encoding="utf-8"))
    assert written["target_family"] == "alpha"
    assert set(written["seeds"]) == {
        "opening_category", "attach_target", "first_attack_ordinal"
    }
    assert doc_out.exists() and "alpha" in doc_out.read_text(encoding="utf-8")
    seeds_json.unlink()  # keep the isolated tree clean between runs
