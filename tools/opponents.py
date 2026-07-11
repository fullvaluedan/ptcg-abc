"""Opponent registry for the gauntlet.

Resolves opponent names to agent callables. Sets up sys.path so the local agents
import without installation.

A diverse, real-field opponent pool (plan U4): beyond the built-in bots and our
own agents, an opponent can be any validated deck piloted by the heuristic
(`deck:<name>`), so a candidate is scored against the field's DECK diversity
instead of only against itself. Optimizing against ourselves on a single deck
yields a self-beater, the textbook overfit that explains our ~570 live rating; a
spread of harvested-meta and archetype decks is the anti-overfit foil pool the CEM
engine (plan U6) tunes against. The deck is agent-supplied at the selection step
(engine.run_match passes no decks), so a deck-parameterized opponent is just the
heuristic pilot returning a fixed 60-card list when asked to pick a deck.

Frozen agent-version snapshots are the planned second axis of diversity (past
selves as opponents); they are added here once a snapshot-save step exists, so
this module stays useful now without a half-built loader.

`clone:<family>` (plan U72) is a second, DIFFERENT kind of opponent: instead of
piloting a foil deck with OUR OWN heuristic strategy (a mirror in disguise, the
audited cause of the offline-to-ladder non-transfer), it pilots a top-team
archetype's harvested deck and picks the FIRST LEGAL option at every decision,
the practical ceiling U71's three independent attempts (richer features, a
tree model, an ablation) found no trained per-option scorer could beat on real
top-player decisions (analysis/clone_quality.md). Only the guard-rail safety
checks already proven in agents/heuristics.py sit on top of first-legal: take
a guaranteed lethal, never activate a repeatable (stateless-loop-risk)
ability, and never voluntarily over-draw into a deck-out. This makes clone:
opponents a real, non-mirror foil for the calibration ring (U73), not another
copy of our own strategic logic wearing a different deck.

`clone:top50_<slug>` (plan S1, analysis/path_above_1000.md) is the same
first-legal-plus-safety pilot, sourced from decks/top50/ (tools/top50_harvest.py's
harvest of the live top-50 leaderboard's own decklists) instead of decks/ itself.
It is a separate, high-band ring for measuring win rate against elite play; unlike
CLONE_FAMILIES and BRACKET_DECK_PREFIX families it is never folded into
clone_family_names()/names()/pool(), so the existing calibrated bracket ring is
untouched. See top50_clone_names().
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_DECKS_DIR = _ROOT / "decks"

# Built-in and own-agent opponents, resolved by exact name.
BUILTINS = ("random", "first", "baseline", "heuristic", "search")

# The curated diverse foil set: harvested top-meta decks plus our own archetype
# decks, each piloted by the heuristic. Passed to the gauntlet or CEM so a
# candidate faces the real field's deck diversity, never only a mirror of itself.
# Only the entries that actually exist on disk are used (see pool()).
POOL_DECKS = (
    "meta_archaludon",
    "meta_grimmsnarl",
    "meta_grimmsnarl_tonakaiiii",
    "aggro",
    "control",
    "ultraball",
    "trolley",
    "trolley_thick",
)

# Archetype families the U70/U71 pipeline can actually attribute to a real,
# single harvested decklist (analysis/expert_cohort.classify_family's non-
# "other" outcomes; the exact three decklists embedded as
# analysis/archetype._BUILTIN_DECKLISTS). "other" is a mixed catch-all bucket
# with no one deck to pilot, so it is never offered as a clone: opponent.
CLONE_FAMILIES = (
    "meta_archaludon",
    "meta_grimmsnarl",
    "meta_grimmsnarl_tonakaiiii",
)

# Bracket-band clone opponents (plan U81) are auto-discovered by filename
# prefix rather than a fixed tuple like CLONE_FAMILIES: they are harvested
# directly from real games played by the ~450-750 rating band we actually
# face (tools/bracket_decks.py), not attributed via classify_family's
# archetype-signature matching, so there is no fixed family name to enumerate
# ahead of time.
BRACKET_DECK_PREFIX = "bracket_"

# High-band (top50) clone opponents (plan S1, analysis/path_above_1000.md) are a
# THIRD, separate auto-discovery path, deliberately not folded into
# clone_family_names()/names()/pool(): those feed the existing calibrated
# bracket ring (tools/ring_calibrate.py), which analysis/path_above_1000.md
# says must stay untouched as a cheap saturated regression guard. The top50
# decklists (tools/top50_harvest.py) live in their own decks/top50/
# subdirectory rather than decks/ itself, so this scan can never collide with
# deck_names()'s flat decks/*.csv glob or bracket_clone_names()'s prefix
# filter over it. Callers that want the high-band ring (e.g. tools/top50_ring.py)
# call top50_clone_names() directly instead of going through clone_family_names().
TOP50_DECK_PREFIX = "top50_"
_TOP50_DECKS_DIR = _DECKS_DIR / "top50"


def top50_clone_names() -> list:
    """Sorted deck-csv stems under decks/top50/ (plan S1's high-band ring).

    Empty when the directory is absent, the same fault-tolerant shape as
    deck_names() and bracket_clone_names(). Not included in clone_family_names()
    or names(): see the module-level note above TOP50_DECK_PREFIX.
    """
    if not _TOP50_DECKS_DIR.is_dir():
        return []
    return sorted(p.stem for p in _TOP50_DECKS_DIR.glob(f"{TOP50_DECK_PREFIX}*.csv"))


def deck_names() -> list:
    """Sorted stems of the deck csvs available as `deck:<name>` opponents.

    Empty when the decks directory is absent, so a missing pool degrades to the
    built-in opponents rather than raising.
    """
    if not _DECKS_DIR.is_dir():
        return []
    return sorted(p.stem for p in _DECKS_DIR.glob("*.csv"))


def bracket_clone_names() -> list:
    """Sorted deck-csv stems starting with BRACKET_DECK_PREFIX (plan U81).

    Auto-discovered like deck_names(), not a fixed tuple: any decks/bracket_*.csv
    tools/bracket_decks.py writes becomes a clone: opponent with no code change.
    """
    return sorted(n for n in deck_names() if n.startswith(BRACKET_DECK_PREFIX))


def clone_family_names() -> list:
    """Sorted CLONE_FAMILIES entries plus bracket_clone_names(), each with a
    matching decklist present on disk.

    Empty when the decks directory is absent, mirroring deck_names() so a
    missing pool degrades to the built-ins plus deck: opponents rather than
    raising.
    """
    have = set(deck_names())
    return sorted([f for f in CLONE_FAMILIES if f in have] + bracket_clone_names())


def names() -> list:
    """Every resolvable name: built-ins, one `deck:<name>` per deck, one `clone:<family>` per clone family."""
    return (
        list(BUILTINS)
        + [f"deck:{stem}" for stem in deck_names()]
        + [f"clone:{fam}" for fam in clone_family_names()]
    )


def pool() -> list:
    """Deck-parameterized opponent names for the diverse foils present on disk.

    Preserves POOL_DECKS order (harvested meta first), skipping any deck whose csv
    is not present. This is the anti-self-beater field a gauntlet or CEM run scores
    against; the gauntlet already round-robins across the names it is handed.
    """
    have = set(deck_names())
    return [f"deck:{d}" for d in POOL_DECKS if d in have]


def _read_deck_csv(path) -> list:
    """The first 60 card ids from a deck csv (one integer id per line).

    Mirrors the deck read in agents.agent_heuristic so an opponent brings the same
    60-card list a submission would. Raises on a deck too short to be legal.
    """
    ids = [int(line) for line in Path(path).read_text().split("\n") if line.strip()]
    if len(ids) < 60:
        raise ValueError(f"deck {path} has {len(ids)} cards, need at least 60")
    return ids[:60]


def _deck_opponent(deck):
    """A heuristic pilot that brings a fixed deck at the selection step.

    Mirrors agents.agent_heuristic.agent: return the deck when the select is None
    (deck selection), otherwise the heuristic move with a guaranteed-legal fallback
    so the opponent never forfeits the match by raising.
    """
    from agents import heuristics

    def agent(obs):
        sel = obs.get("select")
        if sel is None:
            return deck
        try:
            move = heuristics.choose(obs)
            if move is not None:
                return move
        except Exception:
            pass
        try:
            return heuristics._first_legal(sel)
        except Exception:
            return [0]

    return agent


def _safe_first_legal_index(sel, obs):
    """The lowest-index legal MAIN option, minus any repeatable-ability risk.

    Reuses agents.heuristics' own L2 ability-loop VETO primitives
    (options_by_type, option_card_id, _is_once_per_turn_ability): an
    ABILITY-type option whose card is not limited to "once during your turn"
    is excluded before picking, since a stateless first-legal picker offered
    the same repeatable option every decision could loop instead of ending
    its turn. Falls back to plain _first_legal(sel) if every option is
    excluded (so this never returns an empty pick). Never raises.
    """
    from agents import heuristics

    options = sel.get("option", [])
    unsafe = set()
    for oi, opt in heuristics.options_by_type(options).get(heuristics.OPT_ABILITY, []):
        try:
            cid = heuristics.option_card_id(opt, sel, obs)
        except Exception:
            cid = None
        if cid is None or not heuristics._is_once_per_turn_ability(cid):
            unsafe.add(oi)
    mn = sel.get("minCount", 1)
    mx = sel.get("maxCount", 1)
    k = mn if mn > 0 else (1 if mx >= 1 else 0)
    safe = [i for i in range(len(options)) if i not in unsafe]
    if len(safe) >= k:
        return safe[:k]
    return heuristics._first_legal(sel)


def _clone_opponent(deck):
    """A first-legal-plus-safety pilot that brings a fixed deck at selection.

    The clone design U71 settled on (analysis/clone_quality.md): no trained
    per-option scorer, since first-legal alone already beat every model family
    tried on real top-team decisions. Only the guard-rail safety checks stack
    on top, in the same priority order agents.heuristics.choose uses for its
    own scorer-independent safety guards: a guaranteed lethal is taken first,
    then a repeatable-ability veto, then a deck-out-safe first-legal pick.
    Never raises; degrades to option 0 on any unexpected obs shape.
    """
    from agents import heuristics

    def agent(obs):
        sel = obs.get("select")
        if sel is None:
            return deck
        try:
            if sel.get("type") == heuristics.SEL_MAIN:
                lethal = heuristics.lethal_move(obs, sel)
                if lethal is not None:
                    return lethal
            move = _safe_first_legal_index(sel, obs)
            return heuristics.cap_count_for_deckout(move, sel, obs)
        except Exception:
            pass
        try:
            return heuristics._first_legal(sel)
        except Exception:
            return [0]

    return agent


def get(name):
    """Return the agent callable for a registered opponent name.

    Beyond the built-ins, `deck:<stem>` resolves to the heuristic piloting
    decks/<stem>.csv, so the gauntlet can score against real-field deck diversity.
    `clone:<family>` resolves to the first-legal-plus-safety pilot (see
    _clone_opponent) piloting that family's harvested decklist, for any family
    in CLONE_FAMILIES with a decklist on disk.
    """
    if name in ("random", "first"):
        from kaggle_environments.envs.cabt.cabt import random_agent, first_agent

        return {"random": random_agent, "first": first_agent}[name]
    if name == "baseline":
        from agents.agent_baseline import agent

        return agent
    if name == "heuristic":
        from agents.agent_heuristic import agent

        return agent
    if name == "search":
        from agents.agent_search import agent

        return agent
    if isinstance(name, str) and name.startswith("deck:"):
        stem = name[len("deck:"):]
        path = _DECKS_DIR / f"{stem}.csv"
        if not path.exists():
            raise KeyError(
                f"Unknown deck opponent '{name}'. Known decks: {deck_names()}"
            )
        return _deck_opponent(_read_deck_csv(path))
    if isinstance(name, str) and name.startswith("clone:"):
        family = name[len("clone:"):]
        if family.startswith(TOP50_DECK_PREFIX):
            # New code path (plan S1): resolved from decks/top50/, not decks/
            # itself, so it never touches the CLONE_FAMILIES/BRACKET_DECK_PREFIX
            # branch below or the family-name validation it does.
            path = _TOP50_DECKS_DIR / f"{family}.csv"
            if not path.exists():
                raise KeyError(
                    f"Unknown top50 clone '{name}'. Known: {top50_clone_names()}"
                )
            return _clone_opponent(_read_deck_csv(path))
        if family not in CLONE_FAMILIES and not family.startswith(BRACKET_DECK_PREFIX):
            raise KeyError(
                f"Unknown clone family '{name}'. Known: {clone_family_names()}"
            )
        path = _DECKS_DIR / f"{family}.csv"
        if not path.exists():
            raise KeyError(
                f"Unknown clone family '{name}'. Known: {clone_family_names()}"
            )
        return _clone_opponent(_read_deck_csv(path))
    raise KeyError(f"Unknown agent '{name}'. Known: {names()}")
