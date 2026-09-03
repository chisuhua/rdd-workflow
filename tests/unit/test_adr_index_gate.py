"""Structural gates for docs/adr/ and the AUTO-SPRINT single-writer rule.

Per Wave 2 Task 3.4b:
- Unique ADR numbering (no collisions in docs/adr/).
- README ADR_INDEX_START..END segment matches the generator output.
- Every ADR row has non-empty status and date (excluding templates).
- Single-writer enforcement for AUTO-SPRINT block: the literal
  `AUTO-SPRINT-START` must not appear outside `_lib/roadmap_sprint.py`
  (except for tests under `tests/`).
"""
from __future__ import annotations

import re
from pathlib import Path

ADR_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "adr"
README_PATH = ADR_DIR / "README.md"
REPO_ROOT = ADR_DIR.parent.parent


def _collect_adr_files() -> list[Path]:
    return [p for p in ADR_DIR.glob("ADR-*.md") if "template" not in p.name.lower()]


def test_adr_numbering_is_unique():
    nums = []
    for p in _collect_adr_files():
        m = re.match(r"ADR-(\d{4})-", p.name)
        if m:
            nums.append(m.group(1))
    duplicates = sorted({n for n in nums if nums.count(n) > 1})
    assert not duplicates, f"duplicate ADR numbers: {duplicates}"


def test_readme_index_matches_generator_output():
    from _lib.adr_index_generator import render_table, scan_adrs
    adrs = scan_adrs(ADR_DIR)
    seen: dict[str, object] = {}
    for a in adrs:
        seen.setdefault(a["number"], a)
    deduped = sorted(seen.values(), key=lambda a: a["number"])
    expected = render_table(deduped).rstrip()
    readme = README_PATH.read_text(encoding="utf-8")
    m = re.search(r"<!-- ADR_INDEX_START -->\n(.*?)<!-- ADR_INDEX_END -->", readme, re.DOTALL)
    assert m, "ADR_INDEX_START/END markers missing in README"
    actual = m.group(1).rstrip()
    assert actual == expected, (
        f"README index out of sync with generator\n---\nactual:\n{actual}\n---\nexpected:\n{expected}"
    )


def test_readme_index_rows_have_status_and_date():
    readme = README_PATH.read_text(encoding="utf-8")
    m = re.search(r"<!-- ADR_INDEX_START -->\n(.*?)<!-- ADR_INDEX_END -->", readme, re.DOTALL)
    body = m.group(1)
    bad: list[str] = []
    for line in body.splitlines()[2:]:
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        status, date = cells[2], cells[3]
        if not status or status == "—":
            bad.append(f"empty status: {line}")
        if not date or date == "—":
            bad.append(f"empty date: {line}")
    assert not bad, "\n".join(bad)


def test_auto_sprint_start_only_in_roadmap_sprint():
    """`AUTO-SPRINT-START` literal must only appear in roadmap_sprint.py (or tests/)."""
    offenders: list[str] = []
    for path in REPO_ROOT.rglob("*.py"):
        rel = path.relative_to(REPO_ROOT)
        rel_str = str(rel)
        if rel_str.startswith("."):
            continue
        if rel_str.startswith("tests/"):
            continue
        if "roadmap_sprint" in rel_str:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "AUTO-SPRINT-START" in text:
            offenders.append(rel_str)
    assert not offenders, f"AUTO-SPRINT-START leaked into: {offenders}"