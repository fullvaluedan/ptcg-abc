"""Pure-Python move-ordering scorer (plan U8c).

Loads the logistic-regression weights exported by tools/train_move_prior.py from
move_prior.json (feature_names, feature_version, mean, std, coef, intercept) and
scores a list of per-option feature rows the same way training does, via
agents.imitation_features so training and match-time inference read the same
feature layout by construction. No sklearn, no numpy: the score is a plain
standardized linear combination in pure Python so this module ships unchanged
next to main.py.

score_options takes the rows produced by imitation_features.decision_features(obs)
(one N_FEATURES-long row per legal option, in option order) and returns a list of
raw scores in that same order, higher meaning more likely to be the move the
eventual winner chose. search/rollout.py uses these to reorder candidates before
its rollout loop. Any load or scoring failure returns None so callers can fall
back to the unordered candidate list; this module never raises.
"""
from __future__ import annotations

import json
from pathlib import Path

try:
    from agents.imitation_features import feature_version
except ImportError:  # inside a submission, support modules sit at the top level
    from imitation_features import feature_version

_MODEL_FILENAME = "move_prior.json"
_model = None  # lazily loaded and cached; None also marks "load already failed"
_load_attempted = False


def _model_path() -> Path:
    # move_prior.json ships alongside this file both in the repo (search/) and
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
        # Reject a model trained against a different feature layout outright
        # (mirrors search/learned_eval.py's U64 guard): a stale-version model
        # that happens to match the current feature COUNT would otherwise pass
        # the length check below and score silently against the wrong feature
        # meanings.
        if tuple(payload.get("feature_version") or ()) != tuple(feature_version()):
            _model = None
            return _model
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


def _score_row(row, mean, std, coef, intercept) -> float:
    z = intercept
    for x, m, s, w in zip(row, mean, std, coef):
        denom = s if s else 1.0
        z += w * ((x - m) / denom)
    return z


def score_options(rows):
    """Raw linear scores, one per row, in the same order as `rows`, or None.

    `rows` is the output of agents.imitation_features.decision_features(obs).
    Returns None on any load or scoring failure (missing/stale model, a row
    whose length does not match the model's feature count, ...) so callers can
    fall back to the unordered candidate list rather than raising. A higher
    score means the model rates that option more likely to be the move the
    eventual winner chose; this is a ranking score, not a calibrated
    probability, so no sigmoid is applied.
    """
    model = _load_model()
    if model is None:
        return None
    feature_names, mean, std, coef, intercept = model
    try:
        scores = []
        for row in rows:
            if len(row) != len(feature_names):
                return None
            scores.append(_score_row(row, mean, std, coef, intercept))
        return scores
    except Exception:
        return None
