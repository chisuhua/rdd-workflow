"""``rddf roadmap`` subcommand handler.

Thin subprocess wrapper that dispatches to the ``roadmap`` skill's
scripts based on the first positional argument (subcommand):

- ``migrate`` → ``skills/roadmap/scripts/roadmap_migrate.sh``
- ``validate-fragments`` → ``skills/roadmap/scripts/roadmap_validate_fragments.sh``
- ``list-features`` → ``skills/roadmap/scripts/roadmap_list_features.sh``
- ``update-agent-md`` → ``skills/roadmap/scripts/roadmap_update_agent_md.sh``
- ``--update-agent-md`` (top-level flag) → ``skills/roadmap/scripts/roadmap_update_agent_md.sh``
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
  rddf roadmap --update-agent-md  (顶层 flag, 等价于 update-agent-md 子命令)

子命令:
  migrate             迁移扁平 roadmap 到 hierarchical 结构
    --dry-run            演练模式
    --execute --yes      真实迁移
    --rollback <dir>     回滚到备份

  validate-fragments    校验 fragment 引用 (8 规则 R1-R8)
    STRICT_ROADMAP_REFS_GATE=yes  升级 WARNING→CRITICAL
    SKIP_ROADMAP_REFS_GATE=yes    跳过校验

  add-feature           创建 feature fragment (rddf roadmap add-feature <name> ...)
    --phase-refs p1,p2,...   Required. Comma-separated phase IDs
    --theme "<text>"         Required. Single-line 主题
    --status a|d|x           Optional. Default: active
    --force                  Optional. Overwrite existing feat-<name>.md

  list-features         列出所有 feature fragments (rddf roadmap list-features)
    --format table|json|yaml  Optional. Default: table
    --no-archived             Optional. Exclude archived features
    --fragments-dir <path>    Optional. Override default .rddf/roadmap

  update-agent-md       重写 AGENTS.md AUTO 哨兵段 (rddf roadmap update-agent-md)
    --agents-md <path>        Optional. Override default AGENTS.md
    --fragments-dir <path>    Optional. Override default .rddf/roadmap

  --update-agent-md    顶层 flag, 等价于 update-agent-md 子命令

使用 env var:
  SPEC_WORKFLOW_ROADMAP_FRAGMENTS_DIR 覆盖默认 .rddf/roadmap
"""


def cmd_roadmap(args: list[str]) -> int:
    """Handle ``rddf roadmap``.

    Args:
        args: CLI args. First positional arg is the subcommand,
            remaining args are forwarded to the subcommand script.
            Special case: ``--update-agent-md`` as first arg maps to
            ``update-agent-md`` subcommand (per proposal AC top-level flag).

    Returns:
        Exit code from the subcommand script, or 0 for ``--help``.
    """
    project_root = Path(
        os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    )

    if not args or args[0] in ("--help", "-h"):
        print(_help_text())
        return 0

    # Top-level flag form: `rddf roadmap --update-agent-md ...`
    # Maps to update-agent-md subcommand (per proposal AC).
    if args[0] == "--update-agent-md":
        subcommand = "update-agent-md"
        sub_args = args[1:]
    else:
        subcommand = args[0]
        sub_args = args[1:]

    _SUBCOMMAND_MAP = {
        "migrate": project_root / "skills" / "roadmap" / "scripts" / "roadmap_migrate.sh",
        "validate-fragments": project_root
        / "skills"
        / "roadmap"
        / "scripts"
        / "roadmap_validate_fragments.sh",
        "add-feature": project_root / "skills" / "roadmap" / "scripts" / "roadmap_add_feature.sh",
        "list-features": project_root
        / "skills"
        / "roadmap"
        / "scripts"
        / "roadmap_list_features.sh",
        "update-agent-md": project_root
        / "skills"
        / "roadmap"
        / "scripts"
        / "roadmap_update_agent_md.sh",
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