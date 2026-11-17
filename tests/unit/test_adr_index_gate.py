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
    return [
        p for p in ADR_DIR.glob("ADR-*.md")
        if "template" not in p.name.lower()
    ]


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
    assert m, "ADR_INDEX_START/END markers missing in README"
    body = m.group(1)
    bad: list[str] = []
    checked = 0
    for line in body.splitlines()[2:]:
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        checked += 1
        # A short row is a FAILURE, not something to skip. The previous
        # version skipped every row with fewer than 4 cells, which silently
        # passed an entire 3-column table — exactly the shape produced by the
        # now-deleted second generator. Skipping is how a guard becomes a no-op.
        if len(cells) != 4:
            bad.append(f"expected 4 columns, got {len(cells)}: {line}")
            continue
        status, date = cells[2], cells[3]
        if not status or status == "—":
            bad.append(f"empty status: {line}")
        if not date or date == "—":
            bad.append(f"empty date: {line}")
    assert not bad, "\n".join(bad)
    # Paired count assertion: without it, any `continue` reintroduced above
    # shrinks the checked set silently instead of failing.
    adr_count = len(_collect_adr_files())
    assert checked == adr_count, (
        f"checked {checked} index rows but docs/adr has {adr_count} non-template ADRs"
    )


def test_readme_index_markers_appear_exactly_once():
    """A generator that rewrites the whole file drops the markers silently."""
    readme = README_PATH.read_text(encoding="utf-8")
    assert readme.count("<!-- ADR_INDEX_START -->") == 1, (
        "ADR_INDEX_START must appear exactly once"
    )
    assert readme.count("<!-- ADR_INDEX_END -->") == 1, (
        "ADR_INDEX_END must appear exactly once"
    )


def test_readme_index_header_is_four_columns():
    """3 columns (ADR | 标题 | 状态) is the shape of the deleted generator."""
    readme = README_PATH.read_text(encoding="utf-8")
    m = re.search(r"<!-- ADR_INDEX_START -->\n(.*?)<!-- ADR_INDEX_END -->", readme, re.DOTALL)
    assert m, "ADR_INDEX_START/END markers missing in README"
    header = m.group(1).splitlines()[0].strip()
    assert header == "| ADR | 标题 | 状态 | 日期 |", f"unexpected index header: {header!r}"


def test_index_generator_module_resolves_inside_this_repo():
    """The test must validate this repo's implementation, not a global copy.

    tests/unit/test_sync_adr_index.py passed for months while importing
    `skills._lib.sync_adr_index` — a module that does not exist in this repo.
    It resolved to ~/.agents/skills/_lib/ instead, so it verified nothing here.
    """
    import _lib.adr_index_generator as gen

    module_path = Path(gen.__file__).resolve()
    repo = REPO_ROOT.resolve()
    assert module_path.is_relative_to(repo), (
        f"adr_index_generator resolved to {module_path}, outside {repo} — "
        "this test is validating a globally-installed copy, not this repo"
    )


def test_no_duplicate_adr_index_generator():
    """Only one ADR index generator may exist (per fix-adr-index-generator-dup).

    The second one lived at _lib/sync_adr_index.py: 3 columns, status always
    "待定" (it looked for a `## Status` heading; this repo uses `> **状态**:`),
    and it DELETED the ADR_INDEX_START/END markers. Misusing it corrupted
    docs/adr/README.md with no error — 3-column tables render perfectly.
    """
    second = REPO_ROOT / "_lib" / "sync_adr_index.py"
    assert not second.exists(), (
        "a second ADR index generator reappeared: it produces 3-column tables "
        "(no date) and deletes the ADR_INDEX_START/END markers"
    )

    # Scope: code + live docs must not reference it. Historical records may —
    # they describe what existed at the time (archived changes, review reports,
    # improvement files). `.rddf/` is a records area, not code.
    allowed_prefixes = (
        ".rddf/",                       # improvement pool + review reports
        "openspec/changes/archive/",    # historical change records
    )
    allowed = {
        "improvement-suggestions.md",   # the proposal index quotes the finding
        "tests/unit/test_adr_index_gate.py",  # this guard names what it forbids
        # Negative references — the two places that warn readers NOT to
        # recreate it. Both are worth keeping: the docstring is what a future
        # implementer reads first, and README.md is what a maintainer reads.
        "docs/adr/README.md",
        "_lib/adr_index_generator.py",
    }
    offenders: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".sh", ".bats", ".md"}:
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if (rel in allowed or rel.startswith(allowed_prefixes)
                or rel.startswith((".git/", "node_modules/")) or "__pycache__" in rel):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "sync_adr_index" in text:
            offenders.append(rel)
    assert not offenders, f"stale references to the deleted generator: {offenders}"


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