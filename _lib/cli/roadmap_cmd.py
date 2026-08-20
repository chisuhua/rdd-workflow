"""``rddf roadmap`` subcommand handler.

Thin subprocess wrapper that dispatches to the ``roadmap`` skill's
scripts based on the first positional argument (subcommand):

- ``migrate`` → ``skills/roadmap/scripts/roadmap_migrate.sh``
- ``validate-fragments`` → ``skills/roadmap/scripts/roadmap_validate_fragments.sh``
- ``--help`` (or no subcommand) → print help text

Args after the subcommand are forwarded verbatim; exit codes propagate
transparently.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _help_text() -> str:
    return """rddf roadmap — 路线图管理子命令

用法:
  rddf roadmap <subcommand> [args...]

子命令:
  migrate             迁移扁平 roadmap 到 hierarchical 结构
    --dry-run            演练模式
    --execute --yes      真实迁移
    --rollback <dir>     回滚到备份

  validate-fragments    校验 fragment 引用 (8 规则 R1-R8)
    STRICT_ROADMAP_REFS_GATE=yes  升级 WARNING→CRITICAL
    SKIP_ROADMAP_REFS_GATE=yes    跳过校验

使用 env var:
  SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR 覆盖默认 .rddf/roadmap
"""


def cmd_roadmap(args: list[str]) -> int:
    """Handle ``rddf roadmap``.

    Args:
        args: CLI args. First positional arg is the subcommand,
            remaining args are forwarded to the subcommand script.

    Returns:
        Exit code from the subcommand script, or 0 for ``--help``.
    """
    project_root = Path(
        os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    )

    if not args or args[0] in ("--help", "-h"):
        print(_help_text())
        return 0

    subcommand = args[0]
    sub_args = args[1:]

    _SUBCOMMAND_MAP = {
        "migrate": project_root / "skills" / "roadmap" / "scripts" / "roadmap_migrate.sh",
        "validate-fragments": project_root
        / "skills"
        / "roadmap"
        / "scripts"
        / "roadmap_validate_fragments.sh",
    }

    if subcommand not in _SUBCOMMAND_MAP:
        print(
            f"❌ 未知子命令: {subcommand}",
            file=sys.stderr,
        )
        print(_help_text())
        return 2

    script = _SUBCOMMAND_MAP[subcommand]

    if not script.is_file():
        print(
            f"❌ roadmap: script not found at {script}",
            file=sys.stderr,
        )
        return 3

    result = subprocess.run(
        ["bash", str(script), *sub_args],
        cwd=str(project_root),
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(cmd_roadmap(sys.argv[1:]))