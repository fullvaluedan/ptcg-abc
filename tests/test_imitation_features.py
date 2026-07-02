"""Tests for the per-option imitation featurizer (plan U8a, agents/imitation_features.py).

The module predates this test file (preserved WIP from the parked U40/U41 plan,
commit 733add5) and U8a is the first unit to give it coverage. Pins FEATURE_NAMES /
N_FEATURES so a later edit cannot silently shift the feature layout, checks
decision_features' <=1-option gate and per-option row shape, and checks
option_features never raises on a malformed obs/opt (mirrors tests/test_learned_eval.py's
never-raises posture for the sibling learned-eval module).
"""
from agents import card_effects
from agents import heuristics as H
from agents import imitation_features as IF


def _opt(otype, **kw):
    opt = {"type": otype}
    opt.update(kw)
    return opt


def _obs(options, turn=1, your_index=0):
    return {
        "select": {"option": options, "minCount": 1, "maxCount": 1, "type": H.SEL_MAIN},
        "current": {
            "turn": turn,
            "yourIndex": your_index,
            "turnActionCount": 0,
            "energyAttached": False,
            "players": [
                {"active": [], "bench": [], "hand": [], "discard": []},
                {"active": [], "bench": [], "hand": [], "discard": []},
            ],
        },
    }


def test_feature_names_pinned():
    assert IF.N_FEATURES == len(IF.FEATURE_NAMES)
    assert IF.N_FEATURES == 31
    assert IF.FEATURE_NAMES[:7] == (
        "is_play", "is_attach", "is_evolve", "is_ability", "is_retreat", "is_attack", "is_end",
    )
    assert len(set(IF.FEATURE_NAMES)) == IF.N_FEATURES  # no accidental duplicate name


def test_tag_order_matches_tag_vocab():
    # TAG_ORDER fixes an iteration order over the frozenset TAG_VOCAB; a vocabulary
    # change that forgets to update TAG_ORDER would desync the tag multi-hot layout.
    assert set(IF.TAG_ORDER) == card_effects.TAG_VOCAB


def test_feature_version_is_version_pair():
    assert IF.feature_version() == (IF.FEATURE_VERSION, card_effects.TAGS_VERSION)


def test_decision_features_none_for_zero_or_one_option():
    assert IF.decision_features(_obs([])) is None
    assert IF.decision_features(_obs([_opt(H.OPT_END)])) is None


def test_decision_features_returns_one_row_per_option():
    options = [_opt(H.OPT_END), _opt(H.OPT_RETREAT), _opt(H.OPT_ATTACK, attackId=1)]
    rows = IF.decision_features(_obs(options))

    assert rows is not None
    assert len(rows) == 3
    assert all(len(row) == IF.N_FEATURES for row in rows)
    assert all(isinstance(v, float) for row in rows for v in row)


def test_option_features_never_raises_on_missing_select_or_state():
    assert IF.option_features({}, {}, 0) == [0.0] * IF.N_FEATURES


def test_option_features_never_raises_on_out_of_range_index():
    obs = _obs([_opt(H.OPT_END)])
    assert IF.option_features(obs, obs["select"], 5) == [0.0] * IF.N_FEATURES
    assert IF.option_features(obs, obs["select"], -1) == [0.0] * IF.N_FEATURES


def test_option_features_never_raises_on_non_dict_option():
    obs = _obs([None, _opt(H.OPT_END)])
    assert IF.option_features(obs, obs["select"], 0) == [0.0] * IF.N_FEATURES


def test_option_features_never_raises_on_malformed_current():
    obs = {"select": {"option": [_opt(H.OPT_PLAY)]}, "current": {"players": "not-a-list"}}
    result = IF.option_features(obs, obs["select"], 0)
    assert len(result) == IF.N_FEATURES


def test_option_features_marks_the_matching_option_type():
    obs = _obs([_opt(H.OPT_END)])
    feats = IF.option_features(obs, obs["select"], 0)
    assert feats[IF._INDEX["is_end"]] == 1.0
    assert feats[IF._INDEX["is_play"]] == 0.0
