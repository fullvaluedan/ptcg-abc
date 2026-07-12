"""Pure-Python outcome-labeled option scorer (analysis/ranker_outcome_model.md).

Loads the model tools/train_ranker.py exports to search/ranker_model.json and
scores a single MAIN option's agents/imitation_features.FEATURE_NAMES vector
with P(win | this option is taken), no sklearn/numpy dependency so this ships
unchanged next to main.py. Mirrors search/learned_eval.py's load/cache/
never-raise contract, but the payload can be either model_type "logreg"
(coef/intercept, sigmoid, identical shape to eval_model.json) or "mlp" (one
ReLU hidden layer plus a single sigmoid output unit, matching sklearn's
MLPClassifier binary-classification layout), whichever tools/train_ranker.py's
held-out AUC picked.

Unlike learned_eval.predict_win_probability (0.5 neutral fallback for a
state-level value used everywhere unconditionally), score_option returns None
on any load or scoring failure. A per-option score is meant to participate in
an argmax comparison against sibling options at the same decision
(agents/heuristics.py's PTCG_RANKER resolver); a fabricated neutral 0.5 would
silently tie every option and pick an arbitrary one (whichever sorts first)
rather than signaling "no valid model, defer to the heuristic ladder" to the
caller.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

try:
    from agents.imitation_features import feature_version as _imitation_feature_version
except ImportError:  # inside a submission, main.py and these sit together
    from imitation_features import feature_version as _imitation_feature_version

_MODEL_FILENAME = "ranker_model.json"
_model = None  # lazily loaded and cached; None also marks "load already failed"
_load_attempted = False


def _model_path() -> Path:
    # ranker_model.json ships alongside this file both in the repo (search/)
    # and in a built submission (flat, via tools/build_submission.py extras),
    # mirroring search/learned_eval.py's _model_path.
    return Path(__file__).resolve().parent / _MODEL_FILENAME


def _load_model():
    global _model, _load_attempted
    if _load_attempted:
        return _model
    _load_attempted = True
    try:
        with open(_model_path()) as fh:
            payload = json.load(fh)
        # Reject a model trained against a different featurizer layout outright
        # (mirrors learned_eval.py's U64 fix): a stale-version model that
        # happens to match the current feature COUNT would otherwise pass the
        # length check below and score silently against the wrong meanings.
        if tuple(payload.get("feature_version") or ()) != tuple(_imitation_feature_version()):
            _model = None
            return _model
        feature_names = tuple(payload["feature_names"])
        mean = [float(v) for v in payload["mean"]]
        std = [float(v) for v in payload["std"]]
        if not (len(feature_names) == len(mean) == len(std)):
            _model = None
            return _model
        model_type = payload.get("model_type")
        if model_type == "logreg":
            coef = [float(v) for v in payload["coef"]]
            intercept = float(payload["intercept"])
            if len(coef) != len(feature_names):
                _model = None
                return _model
            _model = ("logreg", feature_names, mean, std, coef, intercept)
        elif model_type == "mlp":
            w0 = [[float(v) for v in row] for row in payload["w0"]]
            b0 = [float(v) for v in payload["b0"]]
            w1 = [float(v) for v in payload["w1"]]
            b1 = float(payload["b1"])
            if len(w0) != len(feature_names) or len(b0) != len(w1):
                _model = None
                return _model
            for row in w0:
                if len(row) != len(b0):
                    _model = None
                    return _model
            _model = ("mlp", feature_names, mean, std, w0, b0, w1, b1)
        else:
            _model = None
    except Exception:
        _model = None
    return _model


def _sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def _standardize(features, mean, std):
    return [((v - m) / (s if s else 1.0)) for v, m, s in zip(features, mean, std)]


def score_option(features):
    """P(win | this option's feature vector is taken), or None on any failure.

    `features` must be in agents/imitation_features.FEATURE_NAMES order (the
    exact vector decision_features/option_features produce). Returns None,
    never a fabricated neutral value, when the model failed to load, the
    feature layout does not match, or scoring raises.
    """
    model = _load_model()
    if model is None:
        return None
    try:
        if len(features) != len(model[1]):
            return None
        kind = model[0]
        _, _names, mean, std, *rest = model
        xs = _standardize(features, mean, std)
        if kind == "logreg":
            coef, intercept = rest
            z = intercept
            for x, w in zip(xs, coef):
                z += w * x
            return _sigmoid(z)
        if kind == "mlp":
            w0, b0, w1, b1 = rest
            hidden = []
            for j in range(len(b0)):
                s = b0[j]
                for i, xv in enumerate(xs):
                    s += xv * w0[i][j]
                hidden.append(s if s > 0.0 else 0.0)  # ReLU
            z = b1
            for hv, w in zip(hidden, w1):
                z += hv * w
            return _sigmoid(z)
    except Exception:
        return None
    return None
