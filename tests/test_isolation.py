"""The shared out-path isolation helper (plan U30).

tools/isolation.py is the single chokepoint every extraction tool (census,
scoreboard, screening, miner) writes through so competition-derived data stays
inside the gitignored data/derived/ tree and never leaks into a tracked path.
These tests pin the three properties the loop relies on:

  1. derived_path() returns an absolute path under data/derived/ and creates the
     parent directories so a caller can write immediately,
  2. a target that would climb out of the isolated root (via "..", an absolute
     component, or an empty request) is refused with ValueError,
  3. the isolated root lives under the repo's data/ dir, which .gitignore already
     excludes wholesale, so nothing written through the helper is ever committed.
"""
from pathlib import Path

import pytest

from tools import isolation


def test_derived_path_is_under_the_isolated_root():
    p = isolation.derived_path("census", "expert_census.json")
    root = isolation.derived_root(create=False).resolve()
    assert p.is_absolute()
    assert p.is_relative_to(root)
    assert p.name == "expert_census.json"


def test_derived_path_creates_parent_dirs():
    p = isolation.derived_path("scoreboard", "nested", "board.json")
    assert p.parent.is_dir()


def test_derived_root_is_data_derived_under_repo_root():
    root = isolation.derived_root(create=False)
    repo_root = Path(__file__).resolve().parents[1]
    assert root == repo_root / "data" / "derived"


def test_traversal_escape_is_refused():
    with pytest.raises(ValueError):
        isolation.derived_path("..", "..", "agents", "leak.py")


def test_absolute_component_escape_is_refused(tmp_path):
    with pytest.raises(ValueError):
        isolation.derived_path(str(tmp_path / "leak.json"))


def test_empty_request_is_refused():
    with pytest.raises(ValueError):
        isolation.derived_path()


def test_gitignore_excludes_the_data_tree():
    # The isolation guarantee rests on data/ being gitignored; assert the rule
    # is present so a future .gitignore edit cannot silently unshield derived
    # competition data.
    repo_root = Path(__file__).resolve().parents[1]
    ignore = (repo_root / ".gitignore").read_text(encoding="utf-8")
    lines = {line.strip() for line in ignore.splitlines()}
    assert "data/" in lines
