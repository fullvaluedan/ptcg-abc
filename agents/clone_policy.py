"""Pure-Python per-family clone-policy scorer (plan U71).

Loads the weights tools/train_clone.py exports to
agents/clone_weights/<family>.json (one file per family that passed U71's
qualification gate) and scores a list of per-option feature rows in pure
Python, no sklearn, no numpy at scoring time. Two payload shapes are
supported, dispatched on the JSON's "model_type" key:
  - absent or "linear": a standardized logistic-regression combination,
    same shape and same scoring code as search/move_prior.py.
  - "gbdt": a shallow gradient-boosted tree ensemble (tools/train_clone.py's
    "tree" model kind, added when the 2026-07-03 gate retry found the linear
    model exactly ties the first-legal baseline). Score = init_score +
    learning_rate * sum(tree walk outputs); walking a tree means following
    children_left/children_right by comparing the row's feature value to
    each node's threshold until a leaf (children_left == -1) is reached.
Mirrors search/move_prior.py's structure so the family of scorers stays
recognizably the same shape; this one is keyed by archetype family and only
ever consumed by dev-side clone opponents (U72), never by a shipped agent, so
it carries none of move_prior's flat-submission-layout concerns.

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


def _load_linear_model(payload):
    feature_names = tuple(payload["feature_names"])
    mean = [float(v) for v in payload["mean"]]
    std = [float(v) for v in payload["std"]]
    coef = [float(v) for v in payload["coef"]]
    intercept = float(payload["intercept"])
    if len(feature_names) == len(mean) == len(std) == len(coef):
        return ("linear", feature_names, mean, std, coef, intercept)
    return None


def _load_tree_model(payload):
    feature_names = tuple(payload["feature_names"])
    learning_rate = float(payload["learning_rate"])
    init_score = float(payload["init_score"])
    trees = []
    for tree in payload["trees"]:
        feature = [int(v) for v in tree["feature"]]
        threshold = [float(v) for v in tree["threshold"]]
        left = [int(v) for v in tree["left"]]
        right = [int(v) for v in tree["right"]]
        value = [float(v) for v in tree["value"]]
        if not (len(feature) == len(threshold) == len(left) == len(right) == len(value)):
            return None
        trees.append((feature, threshold, left, right, value))
    return ("gbdt", feature_names, learning_rate, init_score, trees)


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
            model_type = payload.get("model_type", "linear")
            if model_type == "gbdt":
                model = _load_tree_model(payload)
            elif model_type == "linear":
                model = _load_linear_model(payload)
    except Exception:
        model = None
    _models[family] = model
    return model


def _score_row_linear(row, mean, std, coef, intercept) -> float:
    z = intercept
    for x, m, s, w in zip(row, mean, std, coef):
        denom = s if s else 1.0
        z += w * ((x - m) / denom)
    return z


def _walk_tree(row, feature, threshold, left, right, value) -> float:
    node = 0
    while left[node] != -1:
        node = left[node] if row[feature[node]] <= threshold[node] else right[node]
    return value[node]


def _score_row_tree(row, learning_rate, init_score, trees) -> float:
    z = init_score
    for feature, threshold, left, right, value in trees:
        z += learning_rate * _walk_tree(row, feature, threshold, left, right, value)
    return z


def score_options(rows, family):
    """Raw scores, one per row, in the same order as `rows`, or None.

    None on an unknown/unqualified family, a stale feature_version, or a row
    whose length does not match the model's feature count. Never raises.
    """
    model = _load_model(family)
    if model is None:
        return None
    kind = model[0]
    feature_names = model[1]
    try:
        scores = []
        for row in rows:
            if len(row) != len(feature_names):
                return None
            if kind == "linear":
                _, _, mean, std, coef, intercept = model
                scores.append(_score_row_linear(row, mean, std, coef, intercept))
            else:
                _, _, learning_rate, init_score, trees = model
                scores.append(_score_row_tree(row, learning_rate, init_score, trees))
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
