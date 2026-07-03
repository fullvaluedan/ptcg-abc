"""Deck-search-pick gap miner (plan U82, LOOP_BRIEF L6 "deck-search picks").

`agents.heuristics._choose_card_select` already has ONE rule for a deck-search
that can bring a Pokemon into play or hand (GAIN_POKEMON_CONTEXTS: SETUP_BENCH_
POKEMON, TO_BENCH, TO_FIELD, TO_HAND): when our bench is thin, fetch a Basic.
That rule was built for the early_collapse loss bucket and only fires when the
bench is actually thin. Every other deck-search decision -- the common case,
since a healthy board is thin far less often than not -- falls straight to
`_first_legal`, which just answers deck-option index 0 (the search effect's own
reveal order) with zero regard for what the fetched card actually is. This is a
genuine, previously-unmeasured blind spot distinct from RETREAT/PROMOTE (already
mined): the pilot HAS a rule here, but it covers only a narrow slice of the real
decision population.

This module runs the shipped pilot on every real expert deck-search-to-play/hand
decision (TO_BENCH / TO_FIELD / TO_HAND, filtered to genuine deck reveals) and
profiles what top players actually fetch, split by whether the existing
bench-thin rule already applies, so a concrete replacement/extension rule for
the NOT-thin majority can be proposed and checked against real data before it is
built, mirroring analysis/retreat_gap_miner.py and analysis/promote_gap_miner.py.

Most real search effects are optional ("you may search your deck..."), so their
select reports minCount 0 even though the expert still picked one card; the
forced post-knockout promote is the only CARD context that reports minCount 1.
This module passes min_counts={0, 1} to iter_expert_card_decisions (extended
here from its {1}-only default) so the optional-search population is not
silently dropped.

Pure over the raw replay dicts and the injected pilot; card classification
(is_basic_pokemon, evolvesFrom) reads the same offline card catalog the shipped
pilot already depends on at runtime, so this is not cg-free like the replay
spine, exactly like retreat_gap_miner's use of `should_retreat`. Reads the
competition dataset but never redistributes it (replay files stay gitignored).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.move_ranking_validator import (  # noqa: E402
    DEFAULT_EXPERT_TEAMS,
    load_replays,
)
from analysis.replay_trace import (  # noqa: E402
    iter_expert_card_decisions,
    option_card_id,
    team_seat,
)

# SelectContext values (api.py SelectContext enum) where a deck-search effect can
# put a Pokemon into play or hand. Mirrors agents.heuristics.GAIN_POKEMON_CONTEXTS
# minus SETUP_BENCH_POKEMON (2): that context is the game-start mulligan
# placement, not a mid-game search, so it is out of scope for "what do they fetch
# with ball/search effects".
DECK_SEARCH_CONTEXTS = frozenset({5, 6, 7})  # TO_BENCH, TO_FIELD, TO_HAND


def _pilot_index(choice) -> int | None:
    """Normalize a pilot's return value to a single option index, or None."""
    if (
        isinstance(choice, (list, tuple))
        and len(choice) == 1
        and isinstance(choice[0], int)
        and not isinstance(choice[0], bool)
    ):
        return choice[0]
    return None


def _in_play_names(me) -> set:
    """Names of every Pokemon currently in play (active + bench) for `me`.

    Used to test whether a fetched card is an immediate evolution target for a
    Pokemon already on the board. Pure and defensive: any missing piece is
    skipped, never raises.
    """
    from agents.heuristics import card_index

    idx = card_index()
    names = set()
    if not isinstance(me, dict):
        return names
    mons = list(me.get("active") or []) + list(me.get("bench") or [])
    for mon in mons:
        if not isinstance(mon, dict):
            continue
        c = idx.get(mon.get("id"))
        name = getattr(c, "name", None) if c is not None else None
        if name:
            names.add(name)
    return names


def _is_evolution_for_board(card_id, in_play_names) -> bool:
    """True when `card_id` evolves from a Pokemon already in play for this seat."""
    from agents.heuristics import card_index

    c = card_index().get(card_id) if card_id else None
    evolves_from = getattr(c, "evolvesFrom", None) if c is not None else None
    return bool(evolves_from and evolves_from in in_play_names)


def search_gap_rows(replays, expert_teams, pilot_choose=None):
    """One row per real expert deck-search-to-play/hand decision.

    For every scorable expert CARD decision in a DECK_SEARCH_CONTEXTS context
    whose options are a genuine deck reveal (select.deck present and non-empty),
    runs the pilot (agents.heuristics.choose by default, or an injected
    `pilot_choose` for tests) on the same observation and records agreement plus
    whether the expert's fetch was a Basic Pokemon, an immediate evolution target
    for a Pokemon already in play, or plain index 0 (what `_first_legal` already
    produces for free), alongside whether the shipped bench-thin rule already
    covers this decision. Pure, never raises: a pilot exception counts as a
    disagreement rather than aborting the batch.
    """
    from agents.heuristics import THIN_BENCH, is_basic_pokemon, my_bench_count

    if pilot_choose is None:
        from agents.heuristics import choose as pilot_choose

    rows = []
    for replay, label in replays:
        seat = team_seat(replay, expert_teams)
        if seat is None:
            continue
        for obs, played in iter_expert_card_decisions(
            replay, seat, DECK_SEARCH_CONTEXTS, min_counts=frozenset({0, 1})
        ):
            sel = obs.get("select") or {}
            deck = sel.get("deck")
            if not isinstance(deck, list) or not deck:
                continue
            try:
                choice = pilot_choose(obs)
            except Exception:
                choice = None
            pilot_idx = _pilot_index(choice)

            options = sel.get("option") or []
            played_opt = options[played] if 0 <= played < len(options) else None
            played_card_id = option_card_id(played_opt, sel, obs) if played_opt else None

            state = obs.get("current") or {}
            players = state.get("players") or []
            me = players[seat] if 0 <= seat < len(players) else {}
            in_play_names = _in_play_names(me)

            bench = my_bench_count(obs)
            rows.append(
                {
                    "episode": label,
                    "agree": pilot_idx == played,
                    "bench_thin": bench is not None and bench < THIN_BENCH,
                    "played_is_basic": is_basic_pokemon(played_card_id),
                    "played_is_evolution_for_board": _is_evolution_for_board(
                        played_card_id, in_play_names
                    ),
                    "played_is_index_zero": played == 0,
                }
            )
    return rows


def _rate(rows, key) -> float:
    n = len(rows)
    return (sum(1 for r in rows if r[key]) / n) if n else 0.0


def summarize(rows) -> dict:
    """Agreement and fetch-profile rates, split by whether bench-thin already fires.

    The shipped rule already answers the bench_thin subset (fetch a Basic); the
    interesting, previously-unmeasured tail is the NOT-thin subset, where
    `_first_legal` currently governs every fetch. Reporting both subsets
    separately shows how much of the real decision population the existing rule
    already reaches versus how much is still unruled. Pure.
    """
    thin = [r for r in rows if r["bench_thin"]]
    not_thin = [r for r in rows if not r["bench_thin"]]

    def _profile(subset):
        return {
            "n": len(subset),
            "agree_rate": _rate(subset, "agree"),
            "basic_rate": _rate(subset, "played_is_basic"),
            "evolution_rate": _rate(subset, "played_is_evolution_for_board"),
            "index_zero_rate": _rate(subset, "played_is_index_zero"),
        }

    return {
        "n": len(rows),
        "overall": _profile(rows),
        "bench_thin": _profile(thin),
        "not_thin": _profile(not_thin),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "source", help="a .zip of episode JSONs or a directory of *.json replays"
    )
    ap.add_argument(
        "--teams",
        nargs="+",
        default=list(DEFAULT_EXPERT_TEAMS),
        help="expert team names whose seat's decisions are scored",
    )
    ap.add_argument(
        "--limit", type=int, default=1500, help="max replays to read"
    )
    args = ap.parse_args(argv)

    rows = search_gap_rows(load_replays(args.source, limit=args.limit), args.teams)
    summary = summarize(rows)
    print(f"expert teams: {', '.join(args.teams)}")
    print(f"real expert deck-search (TO_BENCH/TO_FIELD/TO_HAND) decisions scored: {summary['n']}")
    for name in ("overall", "bench_thin", "not_thin"):
        p = summary[name]
        print(f"\n  {name} (n={p['n']}):")
        print(f"    pilot agreement rate:                 {p['agree_rate'] * 100:.1f}%")
        print(f"    expert fetched a Basic Pokemon:        {p['basic_rate'] * 100:.1f}%")
        print(f"    expert fetched an evolution for board: {p['evolution_rate'] * 100:.1f}%")
        print(f"    expert picked deck-reveal index 0:     {p['index_zero_rate'] * 100:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
