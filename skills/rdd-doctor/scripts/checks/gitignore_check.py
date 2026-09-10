"""Cat gitignore — consistency between .rddf/project.yaml git.openspec_tracked
and .gitignore openspec/ hard protection (add-gitignore-hard-protection).
Read-only: never mutates files.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List

from doctor_render import Finding, Severity

_GITIGNORE_ENTRY = re.compile(r"^\s*openspec/\s*$")


def _load_openspec_tracked(project_root: Path) -> str | None:
    """Return 'false'/'true' string from project.yaml, or None when unset."""
    yaml_file = project_root / ".rddf" / "project.yaml"
    if not yaml_file.is_file():
        return None
    try:
        import yaml

        cfg = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    value = (cfg.get("git") or {}).get("openspec_tracked")
    if value is None:
        return None
    return "false" if value is False or str(value).lower() == "false" else "true"


def _gitignore_has_entry(project_root: Path) -> bool:
    gitignore = project_root / ".gitignore"
    if not gitignore.is_file():
        return False
    try:
        lines = gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    return any(_GITIGNORE_ENTRY.match(line) for line in lines)


def _openspec_files_tracked(project_root: Path) -> bool:
    try:
        import subprocess

        result = subprocess.run(
            ["git", "ls-files", "openspec/"],
            cwd=project_root, capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False


def run(project_root: Path) -> List[Finding]:
    findings: List[Finding] = []
    tracked = _load_openspec_tracked(project_root)
    has_entry = _gitignore_has_entry(project_root)

    if tracked == "false":
        if has_entry:
            return findings
        mixed = _openspec_files_tracked(project_root)
        fix_hint = (
            "echo 'openspec/' >> .gitignore"
            + (
                "; 混合状态: 先 git rm -r --cached openspec/ (一次性切换)"
                if mixed
                else ""
            )
        )
        findings.append(Finding(
            severity=Severity.WARNING,
            category="gitignore",
            file=".gitignore",
            line=None,
            snippet="git.openspec_tracked=false but .gitignore lacks openspec/ entry — any git add -A can re-commit openspec files",
            fix_hint=fix_hint,
        ))
        return findings

    if tracked in (None, "true") and has_entry:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="gitignore",
            file=".gitignore",
            line=None,
            snippet="reverse inconsistency: .gitignore ignores openspec/ but git.openspec_tracked is not false — rdd-workflow's commit_archive_moves will git add ignored paths (no-op/empty commits)",
            fix_hint="二选一: 设 .rddf/project.yaml git.openspec_tracked: false, 或从 .gitignore 移除 openspec/",
        ))

    return findings


if __name__ == "__main__":
    print(run(Path(os.environ.get("RDDF_PROJECT_ROOT", "."))))
