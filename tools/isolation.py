"""Shared out-path isolation for competition-derived data (plan U30).

Every extraction tool that turns raw competition episodes into a derived
artifact (the expert census U25, the episode scoreboard U23, deck screening
U39, the seed miner U36) writes its output THROUGH this helper. The
competition data license forbids redistributing episodes or anything mined
from them, so a derived file must never land in a tracked location and must
never escape the gitignored data/ tree. This module is the single chokepoint
that enforces both: it hands back a path under data/derived/ (which sits
inside the already gitignored data/ root) and refuses any target that would
climb out of that isolated root.

Usage:
    from tools.isolation import derived_path
    out = derived_path("census", "expert_census.json")
    out.write_text(payload, encoding="utf-8")

derived_path() creates the parent directories and returns an absolute Path;
it raises ValueError if the requested target would resolve outside
data/derived/ (for example via a "../.." traversal), so a caller cannot
accidentally write competition-derived data into the repository.
"""

from __future__ import annotations

from pathlib import Path

# tools/ sits one level under the repo root; data/ is gitignored wholesale.
_ROOT = Path(__file__).resolve().parents[1]
_DERIVED = _ROOT / "data" / "derived"


def derived_root(create: bool = True) -> Path:
    """Return the isolated root for competition-derived output (data/derived/).

    Everything under this directory is covered by the data/ .gitignore rule, so
    nothing written here is ever committed. Creates the directory by default.
    """
    if create:
        _DERIVED.mkdir(parents=True, exist_ok=True)
    return _DERIVED


def derived_path(*parts: str, mkparents: bool = True) -> Path:
    """Resolve an output path under data/derived/, refusing any escape.

    parts are joined onto the derived root (a tool passes its own subdir and
    filename, e.g. derived_path("census", "expert_census.json")). The joined
    path is resolved and checked to still live inside data/derived/; a target
    that climbs out (via "..", an absolute part, or a symlink) raises
    ValueError so competition-derived data cannot leak into a tracked path.
    With mkparents (the default) the parent directories are created so the
    caller can write immediately.
    """
    if not parts:
        raise ValueError("derived_path requires at least one path component")
    root = derived_root(create=False).resolve()
    target = root.joinpath(*parts).resolve()
    if target != root and not target.is_relative_to(root):
        raise ValueError(
            f"refusing to write outside the isolated derived root: {target}"
        )
    if mkparents:
        target.parent.mkdir(parents=True, exist_ok=True)
    return target
