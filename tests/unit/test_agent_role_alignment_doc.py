"""Contract tests for `docs/architecture/agent-role-alignment.md`.

The new architecture doc describes the **two-layer role model**:

  - the opencode build-agent **role layer** (governance identity, artifacts
    under `.rddf/reviews/**` and `.rddf/config/arch-docs.json`)
  - the rdd-workflow **skill layer** (stage skills, artifacts declared in each
    `SKILL.md` frontmatter `role.boundaries.owns`)

Two invariants are worth mechanising (everything else in that doc is prose and
is deliberately NOT machine-checked — see the doc's own "不复述清单"):

  1. The doc's `.rddf/` quick-reference table must agree with
     `_lib/core/rddf_layout.py::RDFF_LAYOUT` (the single source of truth).
     Otherwise the doc becomes a second, drifting source of truth.
  2. Every `agent-role-alignment` reference in the repo must point at a
     section anchor that actually exists in the doc.

CHANGED 2026-11-17: added with the new architecture doc (audit P1-1).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from _lib.core.rddf_layout import as_dicts  # noqa: E402

DOC = PROJECT_ROOT / "docs" / "architecture" / "agent-role-alignment.md"
README = PROJECT_ROOT / "docs" / "architecture" / "README.md"


def _doc_text() -> str:
    assert DOC.is_file(), f"missing architecture doc: {DOC}"
    return DOC.read_text(encoding="utf-8")


def test_doc_exists_and_is_registered_in_the_doc_map():
    """A doc nobody can find is a doc nobody reads."""
    assert DOC.is_file()
    readme = README.read_text(encoding="utf-8")
    assert "agent-role-alignment.md" in readme, \
        "docs/architecture/README.md Doc Map does not list agent-role-alignment.md"


def test_doc_declares_that_it_is_not_the_source_of_truth():
    """The doc is an explanation layer — it must say so, or it becomes a second
    source of truth for the role matrix."""
    text = _doc_text()
    assert "真源" in text
    assert re.search(r"(不是真源|以\s*\S+\s*为准|真源\s*=|真源是)", text), \
        "the doc does not declare which layer is the source of truth"


def test_layout_quick_reference_table_matches_the_manifest():
    """The doc's `.rddf/` quick-reference must match RDFF_LAYOUT **exactly**.

    Parses the ``read_by = …`` / ``write_by = …`` cells and compares them as
    lists — so *deleting* a role (not just adding one) also fails. A weaker
    "does the role name appear anywhere in the row" check would let a deletion
    slip through, which is exactly the false-guarantee shape this repo is
    trying to eliminate.
    """
    text = _doc_text()
    entries = {d["path"]: d for d in as_dicts()}
    for path in ("reviews", "config", "state"):
        entry = entries[path]
        rows = [
            line for line in text.splitlines()
            if line.strip().startswith("|") and f"`{path}`" in line
        ]
        assert rows, f"quick-reference table has no row for `{path}`"
        row = rows[0]
        m_read = re.search(r"`read_by\s*=\s*([^`]+)`", row)
        m_write = re.search(r"`write_by\s*=\s*([^`]+)`", row)
        assert m_read and m_write, (
            f"row for `{path}` lacks a machine-readable `read_by = …` / "
            f"`write_by = …` cell: {row}"
        )
        doc_read = [x.strip() for x in m_read.group(1).split(",") if x.strip()]
        doc_write = [x.strip() for x in m_write.group(1).split(",") if x.strip()]
        assert doc_read == list(entry["read_by"]), (
            f"read_by mismatch for `{path}`: doc={doc_read} manifest={entry['read_by']}"
        )
        assert doc_write == list(entry["write_by"]), (
            f"write_by mismatch for `{path}`: doc={doc_write} manifest={entry['write_by']}"
        )


def test_all_repo_references_to_the_doc_point_at_existing_anchors():
    """No dangling references — the anchors are the doc's contract with SKILL.md."""
    text = _doc_text()
    anchors = {
        m.group(1).lower()
        for m in re.finditer(r"^#{2,4}\s+(.+)$", text, re.MULTILINE)
    }
    slugged = {
        re.sub(r"[^\w\u4e00-\u9fff-]+", "-", a.strip().lower()).strip("-")
        for a in anchors
    }
    targets = list(PROJECT_ROOT.glob("skills/*/SKILL.md")) + list(
        (PROJECT_ROOT / "docs").rglob("*.md")
    )
    dangling: list[str] = []
    for t in targets:
        if t == DOC:
            continue
        body = t.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"agent-role-alignment\.md#([^\s)`]+)", body):
            if m.group(1).lower() not in slugged:
                dangling.append(f"{t.relative_to(PROJECT_ROOT)} -> #{m.group(1)}")
    assert not dangling, f"dangling anchors: {dangling}"
