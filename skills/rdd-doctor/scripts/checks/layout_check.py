"""Cat: `.rddf/` layout — RDFF_LAYOUT is the single source of truth.

Three judgement branches:
  ① required_when=always entry missing          -> WARNING
  ② unregistered (and non-transient) top-level  -> INFO
  ③ storage class disagrees with .gitignore     -> WARNING

Rules that must not be left to the implementer:

- **One level only.** `.rddf/wt/<name>/` is a full checkout of the repo;
  recursing into it produces a wall of false positives.
- **Ignore probing.** For a directory entry, probe `<path>/.probe` instead of
  the directory itself: when a directory holds a tracked file, git does not
  put it in the exclude list, so `git check-ignore <dir>/` answers
  "not ignored" (measured on `.rddf/state/`, which holds the tracked
  `.rddf/state/index.md`). For a file entry, probe the path itself.
- **Unanswerable is not a mismatch.** A non-git directory (git exits 128) or a
  missing `.gitignore` means "cannot tell" — skip the judgement, never report
  it as a mismatch.
- **Glob entries.** A glob path (e.g. `.roadmap-migrate-backup-*`) is judged
  through the concrete directories that actually exist.

Read-only. This category never emits CRITICAL: layout drift must not break
`rddf doctor` (exit code 1, never 2) for a third-party project.
"""
from __future__ import annotations

import fnmatch
import os
import subprocess
import sys
from pathlib import Path
from typing import List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from doctor_render import Finding, Severity  # noqa: E402

# The manifest is imported at module level, but a failure must NOT raise:
# doctor_main.py's aggregator turns any checker exception into a CRITICAL
# finding, which would break this category's "never CRITICAL" contract in
# exactly the environment where the manifest is missing (a copy of
# rdd-doctor/ without _lib/). Import failure is recorded and reported as a
# WARNING by run() instead.
try:
    from _lib.core.rddf_layout import RDFF_LAYOUT  # noqa: E402

    _MANIFEST_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - depends on deployment layout
    RDFF_LAYOUT = ()
    _MANIFEST_ERROR = exc

_GLOB_CHARS = "*?["


def _is_glob(path: str) -> bool:
    return any(c in path for c in _GLOB_CHARS)


def _match_entry(name: str):
    """Exact match first, then fnmatch glob — never the reverse.

    Exact-first matters: `roadmap.md` must not be swallowed by `roadmap`.
    """
    for e in RDFF_LAYOUT:
        if e.path == name:
            return e
    for e in RDFF_LAYOUT:
        if _is_glob(e.path) and fnmatch.fnmatchcase(name, e.path):
            return e
    return None


def _is_ignored(repo_root: Path, rel_path: str, kind: str) -> bool | None:
    """True = ignored, False = not ignored, None = cannot tell."""
    if not (repo_root / ".gitignore").is_file():
        return None
    probe = f".rddf/{rel_path}/.probe" if kind == "dir" else f".rddf/{rel_path}"
    res = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", probe],
        cwd=repo_root, capture_output=True,
    )
    if res.returncode == 0:
        return True
    if res.returncode == 1:
        return False
    return None  # 128: not a git repository


def run(project_root: Path | None = None) -> List[Finding]:
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    findings: List[Finding] = []

    if _MANIFEST_ERROR is not None:
        return [Finding(
            severity=Severity.WARNING,
            category="layout.unavailable",
            file=str(project_root),
            line=None,
            snippet=(
                "layout manifest unavailable: "
                f"{type(_MANIFEST_ERROR).__name__}: {_MANIFEST_ERROR}"
            ),
            fix_hint="run doctor from a checkout that contains _lib/core/rddf_layout.py",
        )]
    rddf = project_root / ".rddf"
    if not rddf.is_dir():
        # The project has not opted into rdd — nothing to diagnose.
        return findings

    present = {p.name for p in rddf.iterdir()}

    # ① required entries missing
    for e in RDFF_LAYOUT:
        if e.required_when != "always" or e.path in present:
            continue
        findings.append(Finding(
            severity=Severity[e.severity],
            category="layout.missing-required",
            file=str(rddf),
            line=None,
            snippet=f"required entry '{e.path}' is missing",
            fix_hint=f"create .rddf/{e.path}/ — see docs/architecture/rddf-layout.md",
        ))

    # ② unregistered top-level entries
    for name in sorted(present):
        if _match_entry(name) is not None:
            continue
        findings.append(Finding(
            severity=Severity.INFO,
            category="layout.unregistered",
            file=str(rddf / name),
            line=None,
            snippet=f"top-level entry '{name}' is not in RDFF_LAYOUT",
            fix_hint=(
                "add it to _lib/core/rddf_layout.py, or move it out of .rddf/ "
                "(a user-owned directory is allowed — this is advisory)"
            ),
        ))

    # ③ storage class vs .gitignore reality
    for e in RDFF_LAYOUT:
        expect_ignored = e.layout_class == "runtime-only"
        if _is_glob(e.path):
            targets = [
                name for name in sorted(present)
                if fnmatch.fnmatchcase(name, e.path)
            ]
        else:
            targets = [e.path]
        for target in targets:
            ignored = _is_ignored(project_root, target, e.kind)
            if ignored is None or ignored == expect_ignored:
                continue
            findings.append(Finding(
                severity=Severity.WARNING,
                category="layout.class-mismatch",
                file=str(project_root / ".gitignore"),
                line=None,
                snippet=(
                    f"'{target}' is class={e.layout_class} but is "
                    f"{'ignored' if ignored else 'not ignored'} by git"
                ),
                fix_hint="align .gitignore with the ADR-0026 class of this entry",
            ))
    return findings
