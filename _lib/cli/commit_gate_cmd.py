"""``rddf commit-gate`` 子命令：生成门禁声明。

用法::

    rddf commit-gate init [--dry-run] [--force]
    rddf commit-gate --help

**为什么不复用既有入口**（design D-1）：`rddf init` 是**安装器**（拷 skills）、
`rddf setup ai-context` 是**AI 配置注入器**、`_lib/check_project_setup.sh` 是**只读校验器** ——
三者语义都不合身，故新增专用子命令。

**边界**（ADR-commit-verification-gate D3 不变）：
- **不猜**验证命令：只从仓内**已存在**的入口推导（`_lib/commit_gate_declaration.CANDIDATES`）；
- 找不到入口 ⇒ **不写文件** + 给手工模板；
- **不代** `git add` / `git commit`（生成物须由作者自行 tracked）；
- 已存在声明 ⇒ **不覆盖**（`--force` 才覆盖）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from skills._lib.cli import resolve_project_root  # noqa: E402  (per fix-33-handlers)
from _lib.commit_gate_declaration import (  # noqa: E402
    declaration_path,
    derive_verify_commands,
    manual_template,
    read_declaration,
    render_declaration,
    shell_commands_display,
)

_USAGE = "usage: rddf commit-gate init [--dry-run] [--force]"


def _print_help() -> None:
    print(_USAGE)
    print()
    print("Generate <project>/.rddf/commit-gate.json from an EXISTING verification entry")
    print("point (test.sh / npm test / make test / pytest / go test / cargo test).")
    print()
    print("options:")
    print("  --dry-run   print the declaration instead of writing it")
    print("  --force     overwrite an existing declaration")
    print()
    print(f"⚠ 空壳判据：verify_commands 仅 1 条且命令 ∈ {shell_commands_display()} ⇒ 视为空壳（doctor 会报警）")
    print("⚠ 声明必须 git-tracked（否则 worktree 内无门禁，ADR-commit-verification-gate D3）")


def cmd_commit_gate(args: list[str]) -> int:
    """Handle ``rddf commit-gate [init]``. Returns a process exit code."""
    if not args or args[0] in ("-h", "--help"):
        _print_help()
        return 0
    sub = args[0]
    if sub != "init":
        print(f"❌ commit-gate: unknown subcommand {sub!r}", file=sys.stderr)
        print(f"   {_USAGE}", file=sys.stderr)
        return 2

    dry_run = "--dry-run" in args
    force = "--force" in args
    for flag in args[1:]:
        if flag.startswith("-") and flag not in ("--dry-run", "--force"):
            print(f"❌ commit-gate: unknown flag {flag!r}", file=sys.stderr)
            print(f"   {_USAGE}", file=sys.stderr)
            return 2

    project_root = Path(os.environ.get("RDDF_PROJECT_ROOT") or resolve_project_root())
    target = declaration_path(project_root)

    if target.is_file() and not force:
        existing = read_declaration(project_root)
        print(f"ℹ️  声明已存在，未覆盖：{target}")
        if existing is not None:
            print("   如需重新生成：rddf commit-gate init --force")
        else:
            print("   ⚠ 但该文件**解析失败** ⇒ 建议 `--force` 重新生成，或手工修复")
        return 0

    verify_commands = derive_verify_commands(project_root)
    if verify_commands is None:
        print("❌ 找不到可推导的验证入口 ⇒ **不生成**声明（不猜命令）", file=sys.stderr)
        print("   已探测：" + " / ".join(c["requires"] for c in _candidate_names()), file=sys.stderr)
        print(manual_template(), file=sys.stderr)
        return 1

    rendered = render_declaration(verify_commands)
    if dry_run:
        print(f"[dry-run] 将写入 {target}：")
        print(rendered, end="")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    print(f"✅ 已生成 {target}")
    print(f"   verify_commands = {verify_commands}")
    print("   下一步：git add .rddf/commit-gate.json（声明必须 tracked 才生效 —— 本命令不代 add）")
    return 0


def _candidate_names():
    """候选的 `requires` 清单（只用于错误提示）。"""
    from _lib.commit_gate_declaration import CANDIDATES

    return CANDIDATES


__all__ = ["cmd_commit_gate"]
