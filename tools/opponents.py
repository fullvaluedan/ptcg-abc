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


def deck_names() -> list:
    """Sorted stems of the deck csvs available as `deck:<name>` opponents.

    Empty when the decks directory is absent, so a missing pool degrades to the
    built-in opponents rather than raising.
    """
    if not _DECKS_DIR.is_dir():
        return []
    return sorted(p.stem for p in _DECKS_DIR.glob("*.csv"))


def names() -> list:
    """Every resolvable opponent name: the built-ins plus one `deck:<name>` per deck."""
    return list(BUILTINS) + [f"deck:{stem}" for stem in deck_names()]


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


def get(name):
    """Return the agent callable for a registered opponent name.

    Beyond the built-ins, `deck:<stem>` resolves to the heuristic piloting
    decks/<stem>.csv, so the gauntlet can score against real-field deck diversity.
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
    raise KeyError(f"Unknown agent '{name}'. Known: {names()}")
