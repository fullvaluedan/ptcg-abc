"""Pure-Python learned win-probability predictor (plan U4).

Loads the logistic-regression weights exported by tools/train_eval.py from
eval_model.json (feature_names, mean, std, coef, intercept) and scores a raw
state dict the same way search/eval.py does, via
ptcg_agent.features.extract_features, so training and match-time inference
read the same feature layout by construction. No sklearn, no numpy: the
sigmoid is computed in pure Python so this module ships unchanged next to
main.py.

predict_win_probability returns p in [0, 1]; predict_value maps it to the
existing rollout value scale (2*p - 1) so it is a drop-in replacement for
search/eval.py's board_value under PTCG_LEARNED_EVAL=1. Terminal results are
handled by search/eval.py's terminal_value before this module is ever
consulted; this module only scores non-terminal rollout cutoffs. Any load or
scoring failure returns 0.0 (a neutral estimate) rather than raising,
mirroring ptcg_agent.features' never-raise contract.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

try:
    from ptcg_agent.features import extract_features
except ImportError:  # inside a submission, support modules sit at the top level
    from features import extract_features

_MODEL_FILENAME = "eval_model.json"
_model = None  # lazily loaded and cached; None also marks "load already failed"
_load_attempted = False


def _model_path() -> Path:
    # eval_model.json ships alongside this file both in the repo (search/) and
    # in a built submission (flat, via tools/build_submission.py extras), so
    # looking next to __file__ resolves in either layout.
    return Path(__file__).resolve().parent / _MODEL_FILENAME


def _load_model():
    global _model, _load_attempted
    if _load_attempted:
        return _model
    _load_attempted = True
    try:
        with open(_model_path()) as fh:
            payload = json.load(fh)
        feature_names = tuple(payload["feature_names"])
        mean = [float(v) for v in payload["mean"]]
        std = [float(v) for v in payload["std"]]
        coef = [float(v) for v in payload["coef"]]
        intercept = float(payload["intercept"])
        if len(feature_names) == len(mean) == len(std) == len(coef):
            _model = (feature_names, mean, std, coef, intercept)
    except Exception:
        _model = None
    return _model


def _sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def predict_win_probability(state, your_index) -> float:
    """Learned win probability in [0, 1] for `state` from our seat, or 0.5.

    0.5 (maximally uncertain, not 0.0) is the neutral fallback here because this
    function's output is a probability, not a value on the [-1, 1] scale;
    predict_value below is what maps a genuine failure to the neutral 0.0 the
    rollout value scale expects.
    """
    model = _load_model()
    if model is None:
        return 0.5
    feature_names, mean, std, coef, intercept = model
    try:
        features = extract_features(state, your_index)
        if len(features) != len(feature_names):
            return 0.5
        z = intercept
        for x, m, s, w in zip(features, mean, std, coef):
            denom = s if s else 1.0
            z += w * ((x - m) / denom)
        return _sigmoid(z)
    except Exception:
        return 0.5


def predict_value(state, your_index) -> float:
    """Learned state value in [-1, 1], drop-in for search/eval.py's board_value.

    2*p - 1 puts a confident win near WIN (1.0), a confident loss near LOSS
    (-1.0), and total uncertainty at 0.0, the same scale search/eval.py already
    uses for terminal results and hand-tuned shaping.
    """
    try:
        return 2.0 * predict_win_probability(state, your_index) - 1.0
    except Exception:
        return 0.0
