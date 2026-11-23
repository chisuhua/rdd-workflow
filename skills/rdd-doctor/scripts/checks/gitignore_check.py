"""Cat gitignore — consistency between .rddf/project.yaml git.openspec_tracked
and .gitignore openspec/ hard protection (add-gitignore-hard-protection).
Read-only: never mutates files.

⚠ 语义（ADR-0036 修订 2026-11-17）：``git.openspec_tracked`` 只管**归档路径**维度
（``openspec/changes/``），不表示「整个 ``openspec/`` 都不跟踪」。因此 ``false`` 下有
两种合法形态：

  (a) ``openspec/``         —— 整树不跟踪（更严格：specs 也不入库）
  (b) ``openspec/changes/`` —— 只挡归档路径，``openspec/specs/`` 可跟踪（方案 B）
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List

from doctor_render import Finding, Severity

#: 形态 (a)：整树排除。
_GITIGNORE_ENTRY_WHOLE = re.compile(r"^\s*openspec/\s*$")
#: 形态 (b)：只排除归档路径（允许尾斜杠）。
_GITIGNORE_ENTRY_CHANGES = re.compile(r"^\s*openspec/changes/?\s*$")


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


def _gitignore_entries(project_root: Path) -> tuple[bool, bool]:
    """Return ``(has_whole, has_changes)`` — the two legal exclusion forms."""
    gitignore = project_root / ".gitignore"
    if not gitignore.is_file():
        return False, False
    try:
        lines = gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False, False
    has_whole = any(_GITIGNORE_ENTRY_WHOLE.match(line) for line in lines)
    has_changes = any(_GITIGNORE_ENTRY_CHANGES.match(line) for line in lines)
    return has_whole, has_changes


def _archive_files_tracked(project_root: Path) -> bool:
    """True when ``openspec/changes/`` has tracked files (i.e. the archive leaks)."""
    return _git_ls_files_nonempty(project_root, "openspec/changes/")


def _specs_files_tracked(project_root: Path) -> bool:
    """True when ``openspec/specs/`` has tracked files (the form-B contract surface)."""
    return _git_ls_files_nonempty(project_root, "openspec/specs/")


def _git_ls_files_nonempty(project_root: Path, pathspec: str) -> bool:
    try:
        import subprocess

        result = subprocess.run(
            ["git", "ls-files", pathspec],
            cwd=project_root, capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False


def run(project_root: Path) -> List[Finding]:
    findings: List[Finding] = []
    tracked = _load_openspec_tracked(project_root)
    has_whole, has_changes = _gitignore_entries(project_root)
    has_entry = has_whole or has_changes

    if tracked == "false":
        if has_entry:
            # 方案 B 的失效模式：只挡了归档路径，但 specs 从未 git add ⇒ 保护落空
            # （fresh checkout 里没有 openspec/specs/ ⇒ CI 的 validate 门静默 skip）。
            # INFO 级：不改变「受保护」的结论，只提示补齐（WARNING 会拖红 advisory gate）。
            if (
                not has_whole
                and (project_root / "openspec" / "specs").is_dir()
                and not _specs_files_tracked(project_root)
            ):
                findings.append(Finding(
                    severity=Severity.INFO,
                    category="gitignore",
                    file=".gitignore",
                    line=None,
                    snippet=(
                        "openspec/specs/ exists but is not tracked — the archive-only "
                        "exclusion (openspec/changes/) only protects when specs/ is committed"
                    ),
                    fix_hint="git add openspec/specs/ openspec/config.yaml",
                ))
            return findings
        mixed = _archive_files_tracked(project_root)
        fix_hint = (
            "echo 'openspec/changes/' >> .gitignore   # 只挡归档路径; 或用 'openspec/' 整树排除"
            + (
                "; 混合状态: 先 untrack openspec/changes/ from index (一次性切换)"
                if mixed
                else ""
            )
        )
        findings.append(Finding(
            severity=Severity.WARNING,
            category="gitignore",
            file=".gitignore",
            line=None,
            snippet=(
                "git.openspec_tracked=false but .gitignore lacks both 'openspec/' and "
                "'openspec/changes/' — any git add -A can re-commit the archive"
            ),
            fix_hint=fix_hint,
        ))
        return findings

    if tracked in (None, "true") and has_entry:
        findings.append(Finding(
            severity=Severity.WARNING,
            category="gitignore",
            file=".gitignore",
            line=None,
            snippet=(
                "reverse inconsistency: .gitignore ignores openspec/ (or openspec/changes/) "
                "but git.openspec_tracked is not false — rdd-workflow's commit_archive_moves "
                "will git add ignored paths (no-op/empty commits)"
            ),
            fix_hint=(
                "二选一: 设 .rddf/project.yaml git.openspec_tracked: false, "
                "或从 .gitignore 移除该条目"
            ),
        ))

    return findings


if __name__ == "__main__":
    print(run(Path(os.environ.get("RDDF_PROJECT_ROOT", "."))))

