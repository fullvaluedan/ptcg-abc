"""U11 two deck portfolio: legality validation and the head to head matrix."""
from pathlib import Path

from tools import deck_match, deck_validate

_ROOT = Path(__file__).resolve().parents[1]
_DECKS = _ROOT / "decks"

# A small legal partner used by the engine layer: the baseline deck is known good.
_BASELINE = deck_validate.read_deck(_DECKS / "baseline.csv")


def test_portfolio_decks_are_legal():
    for name in ("baseline", "aggro", "control"):
        verdict = deck_validate.validate(deck_validate.read_deck(_DECKS / f"{name}.csv"))
        assert verdict["ok"], (name, verdict)


def test_rule_errors_catches_size():
    assert deck_validate.rule_errors([3] * 59)  # 59 cards
    assert deck_validate.rule_errors([3] * 61)  # 61 cards
    assert not deck_validate.rule_errors([3] * 60)  # exactly 60 basic energy is fine


def test_rule_errors_copy_limit_exempts_basic_energy():
    # Five copies of a non basic energy card (722 Snover) is illegal.
    bad = [722] * 5 + [3] * 55
    assert any("722" in e for e in deck_validate.rule_errors(bad))
    # Thirty five copies of a basic energy (3) is legal.
    ok = [722] * 4 + [723] * 4 + [3] * 52
    assert not deck_validate.rule_errors(ok)


def test_rule_errors_ace_spec_limit():
    # Two copies of an ACE SPEC (1158 Maximum Belt) is illegal.
    bad = [1158] * 2 + [722] * 4 + [723] * 4 + [3] * 50
    assert any("ACE SPEC" in e for e in deck_validate.rule_errors(bad))


def test_engine_check_agrees_with_engine():
    legal = deck_validate.engine_check(_BASELINE)
    assert legal["ok"] and legal["errorPlayer"] == -1
    # A deck of pure energy has no basic Pokemon: the engine faults seat 0.
    illegal = deck_validate.engine_check([3] * 60)
    assert not illegal["ok"] and illegal["errorPlayer"] == 0


def test_validate_short_circuits_engine_on_rule_failure():
    # A rule-illegal deck skips the native engine check (engine is None) and the
    # report still renders without touching the absent engine result.
    verdict = deck_validate.validate([3] * 59)
    assert verdict["ok"] is False
    assert verdict["engine"] is None
    assert "59 cards" in deck_validate._format("toosmall", verdict)


def test_deck_bound_returns_deck_then_defers():
    sentinel = object()
    policy = lambda obs: sentinel  # noqa: E731
    agent = deck_match.deck_bound(policy, [1, 2, 3])
    assert agent({"select": None}) == [1, 2, 3]
    assert agent({"select": {"option": [0]}}) is sentinel


def test_head_to_head_runs_end_to_end():
    # Both new decks must actually play a full match under a live policy.
    aggro = deck_validate.read_deck(_DECKS / "aggro.csv")
    control = deck_validate.read_deck(_DECKS / "control.csv")
    res = deck_match.head_to_head(aggro, control, policy="heuristic", n_matches=2)
    assert res["matches"] == 2
    assert res["wins"] + res["draws"] + res["losses"] == 2
    assert 0.0 <= res["win_rate"] <= 1.0


def test_matrix_selects_a_best():
    result = deck_match.matrix(
        [str(_DECKS / "aggro.csv"), str(_DECKS / "control.csv")],
        policy="heuristic",
        n_matches=2,
    )
    assert result["best"] in ("aggro", "control")
    assert set(result["overall"]) == {"aggro", "control"}
