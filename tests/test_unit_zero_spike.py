"""Tests for the unit-zero linear-ranker spike (plan U26).

Cg-free: the pairwise ranker is exercised on synthetic numeric groups and the
featurizer on synthetic option dicts, so the card engine never loads. The
card-data features (play card type, attack damage) default to 0 without cg, which
these tests rely on rather than fight.
"""
import numpy as np
import pytest

from analysis import unit_zero_spike as U


def _opt(**kw):
    return kw


def test_feature_vector_length_matches_names():
    assert U.N_FEATURES == len(U.FEATURE_NAMES) == 20


def test_category_one_hot_is_set_per_option_type():
    sel = {"option": [
        _opt(type=U.H.OPT_PLAY, index=0),
        _opt(type=U.H.OPT_ATTACK, attackId=1),
        _opt(type=U.H.OPT_END),
    ]}
    obs = {"select": sel, "current": {}}
    f_play = U.option_features(obs, sel, 0)
    f_attack = U.option_features(obs, sel, 1)
    f_end = U.option_features(obs, sel, 2)
    assert f_play[U.FEATURE_NAMES.index("is_play")] == 1.0
    assert f_attack[U.FEATURE_NAMES.index("is_attack")] == 1.0
    assert f_end[U.FEATURE_NAMES.index("is_end")] == 1.0
    # Distinct categories do not collide on one indicator.
    assert f_play[U.FEATURE_NAMES.index("is_attack")] == 0.0


def test_end_action_count_cross_scales_with_turn_progress():
    sel = {"option": [_opt(type=U.H.OPT_ATTACK, attackId=1), _opt(type=U.H.OPT_END)]}
    early = {"select": sel, "current": {"turnActionCount": 0}}
    late = {"select": sel, "current": {"turnActionCount": 6}}
    fe = U.option_features(early, sel, 1)[U.FEATURE_NAMES.index("end_x_action_count")]
    fl = U.option_features(late, sel, 1)[U.FEATURE_NAMES.index("end_x_action_count")]
    assert fe == 0.0
    assert fl == 1.0


def test_option_features_defensive_on_bad_index_and_shape():
    sel = {"option": [_opt(type=U.H.OPT_END)]}
    obs = {"select": sel, "current": {}}
    # Out of range index yields all zeros, never raises.
    assert U.option_features(obs, sel, 5) == [0.0] * U.N_FEATURES
    # Non-dict option yields all zeros.
    sel2 = {"option": ["not a dict"]}
    assert U.option_features({"select": sel2, "current": {}}, sel2, 0) == [0.0] * U.N_FEATURES


def test_decision_matrix_skips_single_option():
    assert U.decision_matrix({"select": {"option": [{"type": U.H.OPT_END}]}}) is None
    X = U.decision_matrix(
        {"select": {"option": [{"type": U.H.OPT_END}, {"type": U.H.OPT_ATTACK}]},
         "current": {}}
    )
    assert X.shape == (2, U.N_FEATURES)


def test_ranker_learns_a_separable_pairwise_signal():
    # Feature 0 perfectly predicts the chosen option; the ranker must learn a
    # positive weight on it and pick the right option on unseen groups.
    rng = np.random.default_rng(0)
    groups = []
    for _ in range(200):
        X = rng.normal(size=(4, U.N_FEATURES))
        chosen = int(rng.integers(0, 4))
        X[chosen, 0] += 5.0  # the separable signal
        groups.append((X, chosen))
    ranker = U.PairwiseLinearRanker(iters=300).fit(groups)
    assert ranker.w[0] > 0
    # Held-out: highest feature-0 option is picked.
    hits = 0
    for _ in range(100):
        X = rng.normal(size=(4, U.N_FEATURES))
        target = int(rng.integers(0, 4))
        X[target, 0] += 5.0
        hits += ranker.top1(X) == target
    assert hits >= 95


def test_ranker_is_deterministic():
    rng = np.random.default_rng(1)
    groups = [(rng.normal(size=(3, U.N_FEATURES)), int(rng.integers(0, 3))) for _ in range(50)]
    w1 = U.PairwiseLinearRanker().fit(groups).w
    w2 = U.PairwiseLinearRanker().fit([(X.copy(), c) for X, c in groups]).w
    assert np.allclose(w1, w2)


def test_evaluate_pass_requires_delta_and_gap_reorder():
    # Build a tiny synthetic test set where the ranker beats the baseline AND
    # top-1s an ABILITY option the baseline never prefers.
    ability_i = U.FEATURE_NAMES.index("is_ability")
    attack_i = U.FEATURE_NAMES.index("is_attack")

    def ability_group():
        # Index 0 is an attack (baseline loves it); index 1 is the ability the
        # expert actually chose. Baseline picks 0, so it never gets ability right.
        X = np.zeros((2, U.N_FEATURES))
        X[0, attack_i] = 1.0
        X[1, ability_i] = 1.0
        return X, 1

    def attack_group(chosen):
        X = np.zeros((3, U.N_FEATURES))
        X[chosen, attack_i] = 1.0
        return X, chosen

    # Train the ranker to prefer the ability option in an attack-vs-ability choice.
    # Decision tuples are (X, chosen, category, episode, pilot_idx); pilot_idx None
    # here means no deployed-heuristic baseline, so the proxy weight is the baseline.
    train = [(ability_group()[0], 1, "ABILITY", "e", None) for _ in range(60)]
    train += [(attack_group(1)[0], 1, "ATTACK", "e", None) for _ in range(20)]
    test = [(ability_group()[0], 1, "ABILITY", "e", None) for _ in range(10)]
    test += [(attack_group(2)[0], 2, "ATTACK", "e", None) for _ in range(10)]
    res = U.evaluate(train, test)
    assert res["baseline_kind"] == "proxy"
    assert "ABILITY" in res["reordered_gap_categories"]
    assert res["ability_reordered"] is True
    assert res["ranker_agreement"] >= res["baseline_agreement"]


def test_baseline_weight_never_prefers_ability():
    # The specced gap: the unlearned baseline must assign no positive pull to the
    # ability indicator, so it can never top-1 an ability-only option.
    assert U._BASELINE_WEIGHT[U.FEATURE_NAMES.index("is_ability")] == 0.0
    assert len(U._BASELINE_WEIGHT) == U.N_FEATURES


def test_extract_decisions_uses_winner_seat_and_skips_draws():
    # A draw replay (equal rewards) contributes nothing; a decided one with a
    # scorable 2-option MAIN contributes one decision for the winning seat.
    def main_step(seat, played):
        return [
            {
                "status": "ACTIVE",
                "action": [played],
                "observation": {
                    "select": {
                        "type": 0, "minCount": 1, "maxCount": 1,
                        "option": [{"type": U.H.OPT_ATTACK, "attackId": 1},
                                   {"type": U.H.OPT_END}],
                    },
                    "current": {"yourIndex": seat, "players": [{}, {}]},
                },
            },
            {"status": "INACTIVE"},
        ]

    decided = {"rewards": [1, -1], "steps": [main_step(0, 1)]}
    draw = {"rewards": [0, 0], "steps": [main_step(0, 1)]}
    got = U.extract_decisions([(decided, "a"), (draw, "b")])
    assert len(got) == 1
    X, chosen, cat, label, pilot_idx = got[0]
    assert chosen == 1 and cat == "END" and label == "a"
    assert pilot_idx is None  # no pilot passed
    assert X.shape == (2, U.N_FEATURES)


def test_extract_decisions_records_pilot_pick():
    obs_step = [
        {
            "status": "ACTIVE",
            "action": [0],
            "observation": {
                "select": {
                    "type": 0, "minCount": 1, "maxCount": 1,
                    "option": [{"type": U.H.OPT_ATTACK, "attackId": 1},
                               {"type": U.H.OPT_END}],
                },
                "current": {"yourIndex": 0, "players": [{}, {}]},
            },
        },
    ]
    decided = {"rewards": [1, -1], "steps": [obs_step]}
    got = U.extract_decisions([(decided, "a")], pilot=lambda obs: [1])
    assert len(got) == 1
    assert got[0][4] == 1  # recorded the pilot's top-1 index


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
