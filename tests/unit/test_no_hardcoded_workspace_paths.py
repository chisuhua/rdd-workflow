"""Regression test: scan active code for hardcoded absolute project-root paths.

Per fix-x-rdd-doctor-hardcoded-paths-and-skills-md-drift:
    Pre-patch repo had 30+ active-code occurrences of the legacy
    project-root absolute path (the project's old location). After
    project relocation, every such hardcode becomes a 127 (file-not-found)
    in bats tests or a silent sys.path noop in pytest.

This test scans active code (*.py / *.sh / *.bats / *.md) outside the
historical whitelist and FAILS if any line still hardcodes the legacy
or current absolute project-root path.

Whitelist (respects user data — historical change records preserve their
old paths as audit trail):
    - openspec/changes/archive/      (archived change records)
    - docs/superpowers/plans/        (historical plan docs)
    - docs/audit/                    (historical audit reports)
    - .rddf/state/                   (runtime trace / jsonl logs)
    - .rddf/wt/                      (worktree copies — owned by git worktree)
    - .rddf/plans/                   (workflow-generated TDD plans, read-only
                                      by humans — not executed by CI)
    - .rddf/issues/                  (issue reports quoting old paths)
    - .rddf/improvements/            (improvement proposals may reference
                                      historical paths in design narrative)
    - .omo/                          (opencode session plans, not git-tracked)

Run:
    pytest tests/unit/test_no_hardcoded_workspace_paths.py -q
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_LEGACY_PROJECT_ROOT = "/workspace/project/rdd-workflow"
_CURRENT_PROJECT_ROOT = "/workspace/main/rdd-workflow"
FORBIDDEN_PATTERNS = [
    re.compile(re.escape(_LEGACY_PROJECT_ROOT)),
    re.compile(re.escape(_CURRENT_PROJECT_ROOT)),
]

WHITELIST_PREFIXES = (
    "openspec/changes/archive/",
    "docs/superpowers/plans/",
    "docs/audit/",
    ".rddf/state/",
    ".rddf/wt/",
    ".rddf/plans/",
    ".rddf/issues/",
    ".rddf/improvements/",
    ".omo/",
)

SCAN_EXTENSIONS = {".py", ".sh", ".bats", ".md"}

SELF_FILE = Path(__file__).resolve()


def _iter_active_files() -> list[Path]:
    """Yield all active-code files under the project root."""
    files = []
    for path in _PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.resolve() == SELF_FILE:
            continue
        if any(part in path.parts for part in ("__pycache__", "node_modules", ".git")):
            continue
        if path.suffix not in SCAN_EXTENSIONS:
            continue
        rel = path.relative_to(_PROJECT_ROOT).as_posix()
        if any(rel.startswith(prefix) for prefix in WHITELIST_PREFIXES):
            continue
        files.append(path)
    return files


def test_no_hardcoded_workspace_paths_in_active_code():
    """Lock invariant: zero hardcoded /workspace/{project,main}/rdd-workflow in active code.

    Each forbidden-pattern hit is reported as a test failure with file + line
    so the next person seeing a 127 from bats can trace it back to the
    offending line in one grep.
    """
    violations: list[tuple[Path, int, str, str]] = []
    for f in _iter_active_files():
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pat in FORBIDDEN_PATTERNS:
                m = pat.search(line)
                if m:
                    rel = f.relative_to(_PROJECT_ROOT)
                    violations.append((rel, lineno, pat.pattern, line.strip()[:120]))

    if violations:
        msg_lines = [f"Found {len(violations)} hardcoded path(s):"]
        for rel, lineno, pat, snippet in violations:
            msg_lines.append(f"  {rel}:{lineno}  [{pat}]  {snippet}")
        pytest.fail("\n".join(msg_lines))


def test_active_code_scan_covers_expected_extensions():
    """Sanity: the scanner sees at least the four target extensions."""
    seen = set()
    for f in _iter_active_files():
        seen.add(f.suffix)
    # All four target extensions must be observed.
    assert SCAN_EXTENSIONS.issubset(seen), (
        f"Scanner missing expected extensions: {SCAN_EXTENSIONS - seen}. "
        "If new file types are added, update SCAN_EXTENSIONS."
    )


def test_whitelist_excludes_known_historical_paths():
    """Sanity: the scanner skips openspec/changes/archive/ and .rddf/state/."""
    sample_archive = _PROJECT_ROOT / "openspec/changes/archive/2026-06-28-v2-multi-session/tasks.md"
    if sample_archive.exists():
        text = sample_archive.read_text(encoding="utf-8")
        assert "/workspace/project/rdd-workflow" in text, (
            "Whitelist test invalid: sample archive file no longer contains "
            "the legacy path. Update the sample."
        )

    # And the active scan must NOT include it.
    for f in _iter_active_files():
        rel = f.relative_to(_PROJECT_ROOT).as_posix()
        assert not rel.startswith("openspec/changes/archive/"), (
            f"Scanner leaked archived file: {rel}"
        )
        assert not rel.startswith(".rddf/state/"), (
            f"Scanner leaked state trace: {rel}"
        )