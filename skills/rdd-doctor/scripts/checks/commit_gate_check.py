"""rdd-doctor category: `commit-gate` —— 声明的**可用性**三面检测。

`ADR-commit-verification-gate` D3 明文决策：仓库未声明 `.rddf/commit-gate.json` ⇒ 三判据**不设门禁**。
⇒ 使用方仓「门禁根本没跑」这件事对 agent **不可见**（commit 照样过）。本 category 让三种不可用状态**可见**：

| 面 | 判据 | 结论 |
|---|---|---|
| ① 未声明 | 声明文件**不存在** | 门禁三判据不设门禁（D3）⇒ 给 `rddf commit-gate init` |
| ② 空壳 | 声明存在且 `is_shell_declaration(...)`（恰好 1 条且命令 ∈ `SHELL_COMMANDS`） | 形同虚设 ⇒ 给非平凡示例 |
| ③ 未 tracked | 声明存在、非空壳，但 `git ls-files --error-unmatch` 失败 | worktree 内无门禁（D3 要求声明须 git-tracked）⇒ 给 `git add` |

⚠ **检测 ≠ 拦截**：本 category 只报 WARNING，**不改** D3 决策、不改声明、不代提交。
⚠ **三面互斥**（按 ① → ② → ③ 的顺序判，最多一条 finding）。
⚠ 判据单一真源 = `_lib/commit_gate_declaration.py`（非平凡枚举与声明读法都不在此复制）。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import List

from doctor_render import Finding, Severity

_PKG_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from _lib.commit_gate_declaration import (  # noqa: E402
    DECLARATION_REL,
    is_shell_declaration,
    read_declaration,
    shell_commands_display,
)

_CATEGORY = "commit-gate"


def _is_tracked(project_root: Path, rel: str) -> bool:
    """声明是否 git-tracked（非 git 目录 / 命令失败 ⇒ 视为未 tracked）。"""
    try:
        res = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", rel],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return res.returncode == 0 and bool(res.stdout.strip())


def run(project_root: Path | str | None = None) -> List[Finding]:
    """Return findings for the `commit-gate` category. Never raises."""
    if project_root is None:
        project_root = os.environ.get("RDDF_PROJECT_ROOT", ".")
    root = Path(project_root)
    decl_path = root / DECLARATION_REL

    # ① 未声明
    if not decl_path.is_file():
        return [
            Finding(
                severity=Severity.WARNING,
                category=_CATEGORY,
                file=DECLARATION_REL,
                line=None,
                snippet="declaration missing",
                fix_hint=(
                    "未声明 ⇒ 门禁三判据不设门禁（ADR D3 明文决策）⇒ 该仓的 commit 没有跑过任何验证命令。"
                    " 启用两条路：工具链类仓（pytest / go / cargo）直接 `rddf commit-gate init`；"
                    "脚本类入口（test.sh / npm test / make test）须**手写** `.rddf/commit-gate.json` 给出显式 argv"
                    "（init 会以 rc=3 拒绝并打印模板）；生成/手写后都须 `git add`"
                ),
            )
        ]

    decl = read_declaration(root)
    # ② 空壳（声明存在但解析失败也按「不可用」报）
    if decl is None:
        return [
            Finding(
                severity=Severity.WARNING,
                category=_CATEGORY,
                file=DECLARATION_REL,
                line=None,
                snippet="unparsable",
                fix_hint=(
                    "声明解析失败 ⇒ 门禁视作未声明（ADR D6 fail-closed）⇒ 修复 JSON，"
                    "或 rddf commit-gate init --force 重新生成"
                ),
            )
        ]

    verify_commands = decl.get("verify_commands")
    if is_shell_declaration(verify_commands):
        return [
            Finding(
                severity=Severity.WARNING,
                category=_CATEGORY,
                file=DECLARATION_REL,
                line=None,
                snippet=str(verify_commands),
                fix_hint=(
                    f"空壳声明（verify_commands 仅 1 条且命令 ∈ {shell_commands_display()}）"
                    "⇒ 门禁形同虚设 ⇒ 换成真实的验证命令"
                ),
            )
        ]

    # ③ 未 tracked
    if not _is_tracked(root, DECLARATION_REL):
        return [
            Finding(
                severity=Severity.WARNING,
                category=_CATEGORY,
                file=DECLARATION_REL,
                line=None,
                snippet="untracked",
                fix_hint=(
                    "声明未 git-tracked ⇒ worktree 内无门禁（ADR D3 要求声明须 tracked，否则静默无门禁）"
                    f" ⇒ git add {DECLARATION_REL}"
                ),
            )
        ]

    return []


__all__ = ["run"]
