"""Universal proxy retrodiction gate (plan U24).

No offline proxy may gate a ladder slot until it has retrodicted the ordering of
the builds we already have ladder truth for. The ladder is the only arbiter; a
proxy (move-ranking validator, collapse harness, cloned/deck-diverse gauntlet,
any future measure) earns the right to BLOCK a slot, never to promote one, only
by first reproducing the rank order of the five known builds:

    heuristic+trolley    569.6   (the king / floor)
    heuristic+benchguard 554.5
    search+trolley       514.7
    meta_grimmsnarl      510.1
    meta_archaludon      382.5

A proxy assigns each build a scalar (higher = better). We rank-correlate its
scores against the ladder scores over the builds it covers with Kendall's tau
(concordant minus discordant pairs, over untied pairs). A proxy PASSES
calibration when it covers enough of the known builds AND its tau clears the
threshold; only then may loop_state let it block a slot. A passing proxy still
only BLOCKS, never promotes: the ladder A/B stays the sole arbiter, and the
weak-bot gauntlet is banned from every gate regardless of any tau it posts.

Pure and dependency-free: the math takes plain {build: score} dicts, so it is
unit-tested with no engine, card data, or dataset.
"""
from __future__ import annotations

# The five builds whose ladder public scores we know: the ground-truth ordering a
# proxy must retrodict before it may gate a slot (loop brief hard constraint).
KNOWN_LADDER = {
    "heuristic+trolley": 569.6,
    "heuristic+benchguard": 554.5,
    "search+trolley": 514.7,
    "meta_grimmsnarl": 510.1,
    "meta_archaludon": 382.5,
}

# A proxy must score at least this many of the known builds for the rank test to
# mean anything: two points can only ever be perfectly concordant or discordant,
# so a two-build "calibration" is no evidence at all.
MIN_COVERAGE = 4

# Kendall tau the proxy's ranking must reach against the ladder ranking. 0.8 lets
# at most one of the ten pairs invert (9 concordant, 1 discordant -> tau 0.8) over
# the full five-build set; a proxy that flips more than one pair is not predictive
# enough to be trusted to kill a candidate.
TAU_THRESHOLD = 0.8


def _concordance(a, b):
    """(concordant, discordant) pair counts between two aligned score sequences.

    A pair tied in EITHER sequence is dropped from both counts, so a proxy is
    neither rewarded nor punished for two builds it cannot tell apart.
    """
    if len(a) != len(b):
        raise ValueError("_concordance needs equal-length sequences")
    concordant = discordant = 0
    n = len(a)
    for i in range(n):
        for j in range(i + 1, n):
            da = a[i] - a[j]
            db = b[i] - b[j]
            if da == 0 or db == 0:
                continue
            if (da > 0) == (db > 0):
                concordant += 1
            else:
                discordant += 1
    return concordant, discordant


def kendall_tau(a, b):
    """Kendall's tau between two equal-length score sequences.

    (concordant - discordant) / (untied pairs). Returns None when every pair is
    tied (no rank information) or there are fewer than two points.
    """
    concordant, discordant = _concordance(list(a), list(b))
    total = concordant + discordant
    if total == 0:
        return None
    return (concordant - discordant) / total


def calibrate(proxy_scores, ladder=None, min_coverage=MIN_COVERAGE,
              threshold=TAU_THRESHOLD):
    """Retrodiction report for a proxy over the known builds.

    proxy_scores maps a build name to the proxy's scalar for it (higher = better).
    Only builds present in BOTH proxy_scores and the known ladder are scored; the
    rest are ignored (a proxy that measures three of the five just gets a low
    coverage). Returns a report dict: the covered builds, Kendall tau against the
    ladder, the coverage and tau thresholds, concordant/discordant counts, and
    `passes` (coverage met AND tau at or above the threshold).
    """
    ladder = ladder or KNOWN_LADDER
    covered = sorted(b for b in ladder if b in proxy_scores)
    proxy_vals = [proxy_scores[b] for b in covered]
    ladder_vals = [ladder[b] for b in covered]
    concordant, discordant = _concordance(proxy_vals, ladder_vals)
    total = concordant + discordant
    tau = (concordant - discordant) / total if total else None

    passes = (
        len(covered) >= min_coverage
        and tau is not None
        and tau >= threshold
    )
    return {
        "covered": covered,
        "n_covered": len(covered),
        "n_known": len(ladder),
        "tau": tau,
        "concordant": concordant,
        "discordant": discordant,
        "min_coverage": min_coverage,
        "threshold": threshold,
        "passes": bool(passes),
    }


def is_calibrated(proxy_scores, **kwargs):
    """True when the proxy retrodicts the known ordering well enough to gate."""
    return calibrate(proxy_scores, **kwargs)["passes"]


def _main(argv=None):
    """CLI: python -m analysis.proxy_calibration --scores '{"build": val, ...}'.

    Prints the calibration report as JSON and exits 0 on PASS, 2 on FAIL, so a
    driver can gate on the exit code. The proxy's scores are supplied as a JSON
    object mapping known build names to the proxy's scalar for each.
    """
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Proxy retrodiction gate (U24)")
    ap.add_argument("--scores", required=True,
                    help='JSON object {build: score} of the proxy per known build')
    ap.add_argument("--proxy", default="proxy", help="proxy name (for the report)")
    args = ap.parse_args(argv)
    try:
        scores = json.loads(args.scores)
    except ValueError as exc:
        print(f"invalid --scores JSON: {exc}")
        return 2
    if not isinstance(scores, dict):
        print("--scores must be a JSON object mapping build -> score")
        return 2
    report = calibrate(scores)
    report["proxy"] = args.proxy
    print(json.dumps(report, indent=2, default=str))
    return 0 if report["passes"] else 2


if __name__ == "__main__":
    raise SystemExit(_main())
