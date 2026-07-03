"""Unit-zero linear-ranker spike (plan U26).

The central bet of the U40/U41 imitation pipeline is that a LINEAR ranker over a
handful of hand-decoded features can outrank the hand-coded heuristic on the top
players' real MAIN decisions. Roughly two dozen units are specced on top of that
bet, so this spike tests it BEFORE they are built: a small feature extractor
(~20 features per option), a pairwise-logistic ranker trained by gradient descent
on the winning-seat cohort (plan U25), and a per-category held-out top-1 agreement
comparison against the deployed heuristic pilot as the baseline.

Substitution note: the plan named an sklearn pairwise ranker; sklearn is not in
the venv and the shipped agent must stay dependency-light, so the ranker here is a
numpy pairwise-logistic model (RankNet with a linear score = logistic regression
on within-decision difference vectors). That is exactly the linear ranking pilot
U40/U41 would build, so the spike proves the same bet with the production math and
no extra dependency.

PASS (gates the U40/U41 learned-pilot pipeline, plan U26): held-out top-1
agreement at least +0.03 over the heuristic baseline AND the ranker reorders at
least one known-gap category (ABILITY: the heuristic plays it 0 of 554 times, so
any correct ABILITY top-1 pick is a reorder the hand-coded layer cannot make).

The featurizer reuses the pilot's own option decoders (agents.heuristics) so the
spike and the pilot read options the same way; every card-data lookup is wrapped
so the module imports and unit-tests without the card engine (the cg-dependent
features simply read 0). Pure and defensive over the raw replay dict; reads the
competition dataset but never redistributes it (replays stay gitignored, and any
extracted matrices are written under data/derived/ via tools.isolation).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agents import heuristics as H  # noqa: E402  (pure at import; cg loads lazily)
from analysis.expert_cohort import cohort_seat  # noqa: E402
from analysis.move_ranking_validator import (  # noqa: E402
    OPT_CATEGORY,
    iter_expert_decisions,
    load_replays,
)

# One feature per name, in a fixed order so a learned weight vector is auditable.
# Seven category indicators, seven option-content signals, six state crosses.
FEATURE_NAMES = (
    "is_play",
    "is_attach",
    "is_evolve",
    "is_ability",
    "is_retreat",
    "is_attack",
    "is_end",
    "play_basic_pokemon",
    "play_pokemon",
    "play_trainer",
    "play_energy",
    "attack_lethal",
    "attack_dmg_ratio",
    "attach_to_active",
    "attack_x_turn",
    "play_basic_x_thin_bench",
    "attack_x_active_healthy",
    "end_x_action_count",
    "attach_x_no_energy_yet",
    "attach_active_underpowered",
)
N_FEATURES = len(FEATURE_NAMES)


def _safe(fn, default):
    """Call fn() returning default on any failure (card-engine lookups are lazy)."""
    try:
        return fn()
    except Exception:
        return default


def _card_type_of(opt, me):
    """(CardType int, is_basic_pokemon) for the card a PLAY option plays.

    A MAIN PLAY option carries a hand index, decoded by play_card_id (the generic
    option_card_id keys off an area a PLAY option does not have). Returns
    (None, False) when the card or the card engine is unavailable; never raises.
    """
    cid = _safe(lambda: H.play_card_id(opt, me), None)
    if cid is None:
        return None, False
    ctype = _safe(lambda: H._card_type(cid), None)
    is_basic = bool(_safe(lambda: H.is_basic_pokemon(cid), False))
    return ctype, is_basic


def _state(obs):
    """(current, me, opp, my_active, opp_active) with defensive defaults."""
    st = obs.get("current") or {}
    players = st.get("players") or []
    yi = st.get("yourIndex", 0)
    me = players[yi] if 0 <= yi < len(players) else {}
    opp = players[1 - yi] if len(players) == 2 and 0 <= yi < 2 else {}
    my_active = H._active(me) if me else None
    opp_active = H._active(opp) if opp else None
    return st, me, opp, my_active, opp_active


def _hp_ratio(slot):
    if not slot:
        return 0.0
    hp = slot.get("hp", 0) or 0
    mx = slot.get("maxHp") or hp
    return (hp / mx) if mx else 0.0


def option_features(obs, sel, opt_index) -> list:
    """~20 features for one MAIN option, in FEATURE_NAMES order.

    Pure and defensive: an out-of-range index, a missing field, or an unavailable
    card engine yields zeros for the affected features rather than raising, so a
    batch over thousands of real decisions never aborts on one odd record.
    """
    feats = [0.0] * N_FEATURES

    def put(name, value):
        feats[FEATURE_NAMES.index(name)] = float(value)

    options = sel.get("option") or []
    if not (0 <= opt_index < len(options)):
        return feats
    opt = options[opt_index]
    if not isinstance(opt, dict):
        return feats
    otype = opt.get("type")

    is_play = otype == H.OPT_PLAY
    is_attach = otype == H.OPT_ATTACH
    is_attack = otype == H.OPT_ATTACK
    is_end = otype == H.OPT_END
    put("is_play", is_play)
    put("is_attach", is_attach)
    put("is_evolve", otype == H.OPT_EVOLVE)
    put("is_ability", otype == H.OPT_ABILITY)
    put("is_retreat", otype == H.OPT_RETREAT)
    put("is_attack", is_attack)
    put("is_end", is_end)

    st, me, opp, my_active, opp_active = _state(obs)
    turn = min(int(st.get("turn", 0) or 0), 10) / 10.0
    action_count = min(int(st.get("turnActionCount", 0) or 0), 6) / 6.0
    energy_attached = bool(st.get("energyAttached"))
    bench_count = _safe(lambda: H.my_bench_count(obs), None) or 0
    thin_bench = bench_count < H.THIN_BENCH
    active_healthy = _hp_ratio(my_active) > 0.5

    if is_play:
        ctype, is_basic = _card_type_of(opt, me)
        put("play_basic_pokemon", is_basic)
        put("play_pokemon", ctype == H.CARD_POKEMON)
        put("play_trainer", ctype in (H.CARD_ITEM, H.CARD_TOOL, H.CARD_SUPPORTER, H.CARD_STADIUM))
        put("play_energy", ctype in (H.CARD_BASIC_ENERGY, H.CARD_SPECIAL_ENERGY))
        put("play_basic_x_thin_bench", is_basic and thin_bench)

    if is_attack:
        attack = _safe(lambda: H.attack_index().get(opt.get("attackId")), None)
        my_id = my_active.get("id") if my_active else None
        opp_id = opp_active.get("id") if opp_active else None
        dmg = _safe(lambda: H.effective_damage(my_id, attack, opp_id), 0) if attack else 0
        opp_hp = opp_active.get("hp") if opp_active else None
        opp_mx = (opp_active.get("maxHp") or opp_hp) if opp_active else None
        put("attack_lethal", opp_hp is not None and dmg >= opp_hp)
        put("attack_dmg_ratio", min(dmg / opp_mx, 1.0) if opp_mx else 0.0)
        put("attack_x_turn", turn)
        put("attack_x_active_healthy", active_healthy)

    if is_attach:
        to_active = opt.get("inPlayArea") == H.AREA_ACTIVE
        put("attach_to_active", to_active)
        put("attach_x_no_energy_yet", not energy_attached)
        if to_active and my_active is not None:
            costs = _safe(lambda: H._attack_costs(my_active.get("id")), [])
            attached = _safe(lambda: H._attached_count(my_active), 0)
            underpowered = bool(costs) and attached < costs[0]
            put("attach_active_underpowered", underpowered)

    if is_end:
        put("end_x_action_count", action_count)

    return feats


def decision_matrix(obs):
    """Feature matrix (n_options x N_FEATURES) for a MAIN observation, or None."""
    sel = obs.get("select") or {}
    options = sel.get("option") or []
    if len(options) <= 1:
        return None
    return np.array([option_features(obs, sel, i) for i in range(len(options))], dtype=float)


class PairwiseLinearRanker:
    """A linear option scorer fit by pairwise-logistic gradient descent (RankNet).

    Trains a weight vector w so that within each decision the chosen option scores
    above every other option: minimizes sum log(1 + exp(-w . (x_chosen - x_other)))
    with L2 regularization, over standardized features. predict scores are w . x;
    the argmax is the pilot's top-1 pick. Pure numpy, deterministic (no RNG).
    """

    def __init__(self, l2: float = 1e-3, lr: float = 0.5, iters: int = 300):
        self.l2 = l2
        self.lr = lr
        self.iters = iters
        self.w = None
        self.mean = None
        self.std = None

    def _standardize(self, X):
        return (X - self.mean) / self.std

    def fit(self, groups):
        """groups: list of (X [n_opt, d], chosen_idx). Returns self.

        `d` (the feature width) is read from the data, not hard-coded to this
        module's own N_FEATURES, so the class works unchanged over any other
        caller's feature vectors (e.g. agents.imitation_features's rows).
        """
        rows = np.vstack([X for X, _ in groups]) if groups else np.zeros((1, N_FEATURES))
        n_features = rows.shape[1]
        self.mean = rows.mean(axis=0)
        std = rows.std(axis=0)
        std[std == 0] = 1.0
        self.std = std
        # Precompute difference vectors chosen - other for every pair.
        diffs = []
        for X, chosen in groups:
            if not (0 <= chosen < len(X)):
                continue
            Xs = self._standardize(X)
            xc = Xs[chosen]
            for j in range(len(Xs)):
                if j == chosen:
                    continue
                diffs.append(xc - Xs[j])
        d = np.array(diffs, dtype=float) if diffs else np.zeros((1, n_features))
        w = np.zeros(n_features)
        n = len(d)
        for _ in range(self.iters):
            # loss = sum log(1+exp(-w.d)); grad = sum -sigmoid(-w.d) * d + l2*w
            m = d @ w
            sig = 1.0 / (1.0 + np.exp(m))  # sigmoid(-m)
            grad = -(d * sig[:, None]).sum(axis=0) / n + self.l2 * w
            w -= self.lr * grad
        self.w = w
        return self

    def score(self, X):
        return self._standardize(X) @ self.w

    def top1(self, X):
        return int(np.argmax(self.score(X)))


def _pick_index(choice):
    """The single index a choose()-style answer returned, or None."""
    if (
        isinstance(choice, (list, tuple))
        and len(choice) == 1
        and isinstance(choice[0], int)
        and not isinstance(choice[0], bool)
    ):
        return choice[0]
    return None


def extract_decisions(replays, pilot=None, limit_groups=None):
    """Collect (X, chosen_idx, expert_category, episode, pilot_idx) over winner MAINs.

    Uses the U25 cohort seat (the winner) and the validator's scorable-decision
    gating, so the spike learns from and is scored on the same decisions the census
    counted. When `pilot` (a choose(obs)-like callable) is given, its top-1 pick on
    the same observation is recorded as the deployed-heuristic baseline; a pilot
    that raises or returns a non-single answer records None (a non-match). Skips any
    decision whose matrix cannot be built. Pure over inputs.
    """
    out = []
    for replay, label in replays:
        seat = cohort_seat(replay)
        if seat is None:
            continue
        for obs, played in iter_expert_decisions(replay, seat):
            X = decision_matrix(obs)
            if X is None or not (0 <= played < len(X)):
                continue
            sel = obs.get("select") or {}
            opt = (sel.get("option") or [])[played]
            cat = OPT_CATEGORY.get(opt.get("type"), "OTHER") if isinstance(opt, dict) else "OTHER"
            pilot_idx = None
            if pilot is not None:
                try:
                    pilot_idx = _pick_index(pilot(obs))
                except Exception:
                    pilot_idx = None
            out.append((X, played, cat, label, pilot_idx))
            if limit_groups is not None and len(out) >= limit_groups:
                return out
    return out


def _per_category(decisions, pick_fn):
    """{category: {n, agree}} for a top-1 pick function pick_fn(decision) -> index."""
    by = {}
    for dec in decisions:
        chosen, cat = dec[1], dec[2]
        row = by.setdefault(cat, {"n": 0, "agree": 0})
        row["n"] += 1
        if pick_fn(dec) == chosen:
            row["agree"] += 1
    return by


def _totals(by):
    n = sum(r["n"] for r in by.values())
    agree = sum(r["agree"] for r in by.values())
    return n, agree, (agree / n if n else None)


def evaluate(train, test):
    """Fit on train, compare the ranker against the baselines on the held-out test.

    Two baselines are scored on the identical decisions: (1) the DEPLOYED heuristic
    pilot's recorded top-1 pick (dec[4], the real "recomputed baseline" the plan
    means, present when extract_decisions was given the pilot), and (2) an unlearned
    fixed-weight proxy over the same features (present even without the card engine,
    so a cg-free run still has a reference). The verdict delta is against the
    heuristic when it is available, else the proxy. Returns a verdict dict.
    """
    ranker = PairwiseLinearRanker().fit([(dec[0], dec[1]) for dec in train])

    def ranker_pick(dec):
        return ranker.top1(dec[0])

    def proxy_pick(dec):
        # Unlearned reference: lethal > attack > develop-basic > evolve > attach >
        # play > retreat > end, read off the feature indicators. The "no training"
        # pilot the ranker must beat when the card engine is absent.
        return int(np.argmax(dec[0] @ _BASELINE_WEIGHT))

    def heuristic_pick(dec):
        return dec[4]  # recorded deployed-pilot top-1, or None (a non-match)

    rank_by = _per_category(test, ranker_pick)
    proxy_by = _per_category(test, proxy_pick)
    have_heuristic = any(dec[4] is not None for dec in test)
    heur_by = _per_category(test, heuristic_pick) if have_heuristic else {}

    _, _, ragr = _totals(rank_by)
    _, _, pagr = _totals(proxy_by)
    _, _, hagr = _totals(heur_by) if have_heuristic else (0, 0, None)

    base_by = heur_by if have_heuristic else proxy_by
    bagr = hagr if have_heuristic else pagr
    delta = (ragr - bagr) if (ragr is not None and bagr is not None) else None

    # Reorder of the specced known gap: ABILITY, where the deployed heuristic scores
    # 0 (it never plays an ability, 0 of 554). Any correct ability top-1 by the
    # ranker is a reorder the hand-coded layer cannot make. Also report every
    # category the ranker rescues from a zero baseline.
    reordered = []
    for cat in sorted(set(rank_by) | set(base_by)):
        r = rank_by.get(cat, {"n": 0, "agree": 0})
        b = base_by.get(cat, {"n": 0, "agree": 0})
        if r["agree"] > 0 and b["agree"] == 0 and r["n"] > 0:
            reordered.append(cat)
    ability_reordered = "ABILITY" in reordered

    passed = (delta is not None and delta >= 0.03) and ability_reordered
    return {
        "train_groups": len(train),
        "test_groups": len(test),
        "ranker_agreement": ragr,
        "baseline_agreement": bagr,
        "baseline_kind": "heuristic" if have_heuristic else "proxy",
        "heuristic_agreement": hagr,
        "proxy_agreement": pagr,
        "delta": delta,
        "ranker_by_category": rank_by,
        "baseline_by_category": base_by,
        "heuristic_by_category": heur_by,
        "proxy_by_category": proxy_by,
        "reordered_gap_categories": reordered,
        "ability_reordered": ability_reordered,
        "weights": dict(zip(FEATURE_NAMES, ranker.w.tolist())) if ranker.w is not None else {},
        "pass": bool(passed),
    }


# Baseline (unlearned) category preference, in FEATURE_NAMES order. A fixed
# hand-coded ordering the ranker must beat: lethal top, then attack strength,
# development of a thin bench, evolve, attach-to-active, generic play, retreat,
# end last. ABILITY carries no positive weight (the 0-of-554 gap the ranker can
# learn to fill), so the baseline never top-1s an ability option.
_BASELINE_WEIGHT = np.array([
    0.3,   # is_play
    0.5,   # is_attach
    0.7,   # is_evolve
    0.0,   # is_ability  (the known gap: baseline never prefers it)
    0.2,   # is_retreat
    0.8,   # is_attack
    -0.5,  # is_end
    1.0,   # play_basic_pokemon
    0.4,   # play_pokemon
    0.1,   # play_trainer
    0.2,   # play_energy
    5.0,   # attack_lethal  (take the knockout)
    1.5,   # attack_dmg_ratio
    0.6,   # attach_to_active
    0.3,   # attack_x_turn
    1.2,   # play_basic_x_thin_bench
    0.3,   # attack_x_active_healthy
    -0.3,  # end_x_action_count
    0.3,   # attach_x_no_energy_yet
    0.4,   # attach_active_underpowered
], dtype=float)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", help="a .zip of episode JSONs or a directory of *.json")
    ap.add_argument("--limit", type=int, default=1200, help="max replays to read")
    ap.add_argument("--test-frac", type=float, default=0.25, help="held-out fraction")
    ap.add_argument("--max-groups", type=int, default=None, help="cap decisions")
    ap.add_argument(
        "--no-heuristic",
        action="store_true",
        help="skip the deployed-pilot baseline (proxy weight only, no card engine)",
    )
    args = ap.parse_args(argv)

    pilot = None
    if not args.no_heuristic:
        from agents.heuristics import choose as pilot  # noqa: N813

    decisions = extract_decisions(
        load_replays(args.source, limit=args.limit),
        pilot=pilot,
        limit_groups=args.max_groups,
    )
    # Held-out split by extraction order, snapped to an episode boundary so no game
    # straddles train and test (the tail is a disjoint set of games from the head):
    # deterministic, no RNG.
    cut = int(len(decisions) * (1.0 - args.test_frac))
    while 0 < cut < len(decisions) and decisions[cut][3] == decisions[cut - 1][3]:
        cut += 1
    train, test = decisions[:cut], decisions[cut:]
    result = evaluate(train, test)
    print(f"decisions: {len(decisions)} (train {len(train)}, test {len(test)})")
    print(f"baseline kind: {result['baseline_kind']}")
    ra = result["ranker_agreement"]
    ba = result["baseline_agreement"]
    ha = result["heuristic_agreement"]
    pa = result["proxy_agreement"]
    print(f"heuristic top-1: {ha:.4f}" if ha is not None else "heuristic top-1: n/a")
    print(f"proxy top-1:     {pa:.4f}" if pa is not None else "proxy top-1: n/a")
    print(f"ranker top-1:    {ra:.4f}" if ra is not None else "ranker top-1: n/a")
    if result["delta"] is not None:
        print(f"delta vs {result['baseline_kind']}: {result['delta']:+.4f}")
    print(f"reordered zero-baseline categories: {result['reordered_gap_categories'] or 'none'}")
    print(f"ability reordered (specced gap): {result['ability_reordered']}")
    print("\nper-category (n, baseline agree, ranker agree):")
    both = sorted(set(result["ranker_by_category"]) | set(result["baseline_by_category"]))
    for cat in both:
        r = result["ranker_by_category"].get(cat, {"n": 0, "agree": 0})
        b = result["baseline_by_category"].get(cat, {"n": 0, "agree": 0})
        print(f"  {cat:<8} n={r['n']:<5} base={b['agree']:<5} ranker={r['agree']:<5}")
    print(f"\nVERDICT: {'PASS' if result['pass'] else 'FAIL'}")

    # Persist the result under the isolated derived root (gitignored, plan U30):
    # never leak competition-derived numbers into a tracked path.
    try:
        import json

        from tools.isolation import derived_path

        out = derived_path("spike", "unit_zero_result.json")
        out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        print(f"(result written to {out})")
    except Exception as exc:  # never let dumping fail the run
        print(f"(result dump skipped: {exc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
