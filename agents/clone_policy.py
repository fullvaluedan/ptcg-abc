"""Pure-Python per-family clone-policy scorer (plan U71).

Loads the standardized logistic-regression weights tools/train_clone.py
exports to agents/clone_weights/<family>.json (one file per family that
passed U71's qualification gate) and scores a list of per-option feature rows
the same way search/move_prior.py scores the move-ordering model: no
sklearn, no numpy, a plain standardized linear combination in pure Python.
Mirrors that module's structure so the two scorers stay recognizably the
same shape; this one is keyed by archetype family and only ever consumed by
dev-side clone opponents (U72), never by a shipped agent, so it carries none
of move_prior's flat-submission-layout concerns.

score_options(rows, family) takes the rows produced by
agents.imitation_features.decision_features(obs) and returns one raw score
per row, or None on any load or scoring failure (unknown/unqualified family,
a stale feature_version, a malformed row, ...). choose_index(rows, family) is
the guaranteed-legal wrapper U72's clone opponents actually call: it never
raises and falls back to 0 (the first legal option) whenever scoring is
unavailable, so a clone opponent can always make a legal move even for a
family with no qualified weights.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from agents.imitation_features import feature_version

_WEIGHTS_DIRNAME = "clone_weights"
_models: dict = {}  # family -> loaded model tuple, or None (load already failed)


def _weights_dir() -> Path:
    return Path(__file__).resolve().parent / _WEIGHTS_DIRNAME


def _safe_filename(family: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", family) + ".json"


def available_families() -> list:
    """Sorted family names with a weight file on disk right now."""
    d = _weights_dir()
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def _load_model(family):
    if family in _models:
        return _models[family]
    model = None
    try:
        path = _weights_dir() / _safe_filename(family)
        with open(path) as fh:
            payload = json.load(fh)
        # Same feature-version guard as search/move_prior.py: reject a model
        # trained against a different featurizer layout outright, rather than
        # risk scoring silently against the wrong feature meanings.
        if tuple(payload.get("feature_version") or ()) == tuple(feature_version()):
            feature_names = tuple(payload["feature_names"])
            mean = [float(v) for v in payload["mean"]]
            std = [float(v) for v in payload["std"]]
            coef = [float(v) for v in payload["coef"]]
            intercept = float(payload["intercept"])
            if len(feature_names) == len(mean) == len(std) == len(coef):
                model = (feature_names, mean, std, coef, intercept)
    except Exception:
        model = None
    _models[family] = model
    return model


def _score_row(row, mean, std, coef, intercept) -> float:
    z = intercept
    for x, m, s, w in zip(row, mean, std, coef):
        denom = s if s else 1.0
        z += w * ((x - m) / denom)
    return z


def score_options(rows, family):
    """Raw scores, one per row, in the same order as `rows`, or None.

    None on an unknown/unqualified family, a stale feature_version, or a row
    whose length does not match the model's feature count. Never raises.
    """
    model = _load_model(family)
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


def choose_index(rows, family) -> int:
    """Index of the option `family`'s clone rates best, or 0 on any failure.

    The guaranteed-legal fallback U72's clone opponents rely on: option 0 is
    always a legal choice by construction (imitation_features.decision_features
    only returns rows for a real multi-option MAIN decision), so a scoring
    failure for an unknown, unqualified, or version-mismatched family degrades
    to "always play the first legal option" rather than raising or picking an
    out-of-range index.
    """
    if not rows:
        return 0
    try:
        scores = score_options(rows, family)
        if scores is None or len(scores) != len(rows):
            return 0
        return max(range(len(rows)), key=lambda i: scores[i])
    except Exception:
        return 0
