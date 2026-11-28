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
    detect_script_entries,
    is_shell_declaration,
    manual_template,
    read_declaration,
    render_declaration,
    shell_commands_display,
)
from _lib.core.atomic_write import atomic_write_text  # noqa: E402

_USAGE = "usage: rddf commit-gate init [--dry-run] [--force]"

#: 拒绝退出码：**与**「找不到可推导入口」的 1 区分**（调用方 / CI 需要分辨两种失败）。
_REFUSAL_RC = 3
#: 拒绝时 stderr 的固定关键字（脚本据此匹配，别再解析散文）。
_REFUSAL_KEY = "需要显式 argv"


def _print_help() -> None:
    print(_USAGE)
    print()
    print("Generate <project>/.rddf/commit-gate.json from an EXISTING verification entry")
    print("point (pytest / go test / cargo test).")
    print()
    print("⚠ 脚本类入口（test.sh / npm test / make test）**不自动推导**：裸调用是否真的执行验证")
    print("  无法静态判定 ⇒ 需在声明里写明显式 argv（本命令会 rc=3 拒绝并打印模板）。")
    print("  `--force` 时若既有声明合法，则**沿用**它的 verify_commands（不重新推导、不改文件）。")
    print()
    print("options:")
    print("  --dry-run   print the declaration instead of writing it")
    print("  --force     re-derive (or reuse an existing valid declaration)")
    print()
    print("exit codes: 0=写好/沿用, 1=找不到可推导入口, 2=参数错, 3=脚本类入口需要显式 argv")
    print()
    print(f"⚠ 空壳判据：verify_commands 仅 1 条且命令 ∈ {shell_commands_display()} ⇒ 视为空壳（doctor 会报警）")
    print("⚠ 声明必须 git-tracked（否则 worktree 内无门禁，ADR-commit-verification-gate D3）")


def _explicit_source(project_root: Path) -> list[list[str]] | None:
    """既有**合法且非 shell** 声明即显式来源；否则 None（shell 声明不算）。"""
    decl = read_declaration(project_root)
    cmds = decl.get("verify_commands") if isinstance(decl, dict) else None
    if not cmds or is_shell_declaration(cmds):
        return None
    return cmds


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

    reused: list[list[str]] | None = None
    if target.is_file() and force:
        reused = _explicit_source(project_root)
    if reused is not None:
        # 既有合法声明就是**显式来源** ⇒ 沿用（不改文件、不丢 timeout_ms / known_failures）
        print(f"ℹ️  沿用既有声明的 verify_commands（未重新推导）：{target}")
        print(f"   verify_commands = {reused}")
        return 0

    verify_commands = derive_verify_commands(project_root)
    if verify_commands is None:
        script_entries = detect_script_entries(project_root)
        if script_entries:
            print(f"❌ 脚本类入口{_REFUSAL_KEY} ⇒ 拒绝生成", file=sys.stderr)
            print("   探测到：" + " / ".join(script_entries), file=sys.stderr)
            print(
                "   裸调用这些入口是否真的执行验证**无法静态判定**"
                "（实测：裸 `./test.sh` 只打印 help 并 exit 0 ⇒ 恒绿声明）",
                file=sys.stderr,
            )
            print(manual_template(), file=sys.stderr)
            return _REFUSAL_RC
        print("❌ 找不到可推导的验证入口 ⇒ **不生成**声明（不猜命令）", file=sys.stderr)
        print("   已探测：" + " / ".join(c["requires"] for c in _candidate_names()), file=sys.stderr)
        print(manual_template(), file=sys.stderr)
        return 1

    rendered = render_declaration(verify_commands)
    if dry_run:
        print(f"[dry-run] 将写入 {target}：")
        print(rendered, end="")
        return 0

    atomic_write_text(target, rendered)
    print(f"✅ 已生成 {target}")
    print(f"   verify_commands = {verify_commands}")
    print("   下一步：git add .rddf/commit-gate.json（声明必须 tracked 才生效 —— 本命令不代 add）")
    return 0


def _candidate_names():
    """候选的 `requires` 清单（只用于错误提示）。"""
    from _lib.commit_gate_declaration import CANDIDATES

    return CANDIDATES


__all__ = ["cmd_commit_gate"]
