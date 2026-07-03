"""Machine audit for docs/writeup/comprehension.md's claims ledger (U94).

The ledger's whole point is that every claimed number cites a committed
source file. This test parses that table mechanically and fails if a cited
path does not exist, so a future rename/removal of a source file cannot
silently leave a dangling claim in the writeup.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "writeup" / "comprehension.md"

PATH_RE = re.compile(r"`([\w./\\-]+\.(?:md|py|json))`")


def _ledger_rows():
    text = DOC_PATH.read_text(encoding="utf-8")
    section = text.split("## The claims ledger", 1)[1]
    section = section.split("## Bottom line", 1)[0]
    rows = [
        line for line in section.splitlines()
        if line.strip().startswith("|") and "---" not in line
    ]
    # Drop the header row ("| claim | number | source |").
    return rows[1:]


def test_doc_exists():
    assert DOC_PATH.exists()


def test_ledger_has_rows():
    rows = _ledger_rows()
    assert len(rows) >= 15, "claims ledger should not be gutted to a handful of rows"


def test_every_row_cites_a_source_path():
    for row in _ledger_rows():
        assert PATH_RE.search(row), f"claims ledger row has no cited source path: {row}"


def test_every_cited_source_exists():
    missing = []
    for row in _ledger_rows():
        for path in PATH_RE.findall(row):
            if not (ROOT / path).exists():
                missing.append(path)
    assert not missing, f"claims ledger cites source paths that do not exist: {missing}"
