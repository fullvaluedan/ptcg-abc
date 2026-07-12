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
SYNTH_PATH = ROOT / "docs" / "writeup" / "final_synthesis.md"

PATH_RE = re.compile(r"`([\w./\\-]+\.(?:md|py|json))`")

# The Strategy writeup is one Kaggle Writeup with a hard 2000-word ceiling; the
# repo holds it in a 1900-1990 band so 2000 is never a target (findings.md,
# second blindspot audit). Word count = whitespace tokens over the whole file.
SYNTH_WORD_MIN = 1900
SYNTH_WORD_MAX = 1990


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


# ---------------------------------------------------------------------------
# final_synthesis.md: the model-approach story. Its whole claim is that every
# cited source file is real, so this audits EVERY backticked path in the file
# (not just a table), keeps the word count in the hard-ceiling band, and
# enforces the repo-wide no-dash rule on the submission text itself.
# ---------------------------------------------------------------------------


def test_synthesis_exists():
    assert SYNTH_PATH.exists()


def test_synthesis_word_count_in_band():
    words = len(SYNTH_PATH.read_text(encoding="utf-8").split())
    assert SYNTH_WORD_MIN <= words <= SYNTH_WORD_MAX, (
        f"final_synthesis.md is {words} words, outside "
        f"[{SYNTH_WORD_MIN}, {SYNTH_WORD_MAX}]"
    )


def test_synthesis_every_cited_source_exists():
    text = SYNTH_PATH.read_text(encoding="utf-8")
    missing = sorted(
        {p for p in PATH_RE.findall(text) if not (ROOT / p).exists()}
    )
    assert not missing, f"final_synthesis.md cites paths that do not exist: {missing}"


def test_synthesis_has_no_em_or_en_dashes():
    text = SYNTH_PATH.read_text(encoding="utf-8")
    assert "—" not in text, "final_synthesis.md contains an em dash"
    assert "–" not in text, "final_synthesis.md contains an en dash"
