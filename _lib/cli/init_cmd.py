"""``rddf init [target]`` subcommand handler.

Installs the rdd-workflow distribution to ``<target>/.opencode/skills/rdd-workflow/``.
Default target is the current project (``RDDF_PROJECT_ROOT``).

Layout copied (relative to source project root):
  - ``skills/`` (entire directory, including INSTALL.md, all SKILL.md files, scripts/)
  - ``_lib/`` (entire directory)
  - ``package.json``
  - ``skills/cli/rddf.sh`` (the thin shim, NOT the legacy root ``rddf``)

Usage::

    python3 -m _lib.cli init [target]
    python3 -m _lib.cli init --help
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


# Subset of files checked from the source project root before install.
_INSTALL_SOURCES = ["skills", "_lib", "package.json", "skills/cli/rddf.sh"]


def cmd_init(args: list[str]) -> int:
    """Handle ``rddf init [target|--help]``.

    Args:
        args: Optional target directory. If omitted, defaults to
            ``RDDF_PROJECT_ROOT`` (the current project). ``--help`` /
            ``-h`` prints usage and returns 0.

    Returns:
        0 on success, 1 if required source files are missing or copy
        fails, 2 on bad flag.
    """
    if args and args[0] in ("-h", "--help"):
        _print_help()
        return 0
    for flag in args:
        if flag.startswith("-"):
            print(f"❌ init: unknown flag {flag!r}", file=sys.stderr)
            print("   usage: rddf init [target]", file=sys.stderr)
            return 2

    project_root = Path(os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd())
    target_str = args[0] if args else str(project_root)
    target = Path(target_str) / ".opencode" / "skills" / "rdd-workflow"

    # Verify source layout exists.
    missing = [s for s in _INSTALL_SOURCES if not (project_root / s).exists()]
    if missing:
        print(
            f"❌ init: 找不到源文件: {', '.join(missing)}\n"
            f"   当前 RDDF_PROJECT_ROOT={project_root}",
            file=sys.stderr,
        )
        return 1

    # Build the destination tree.
    target.mkdir(parents=True, exist_ok=True)

    # Copy skills/ as a whole (preserves subdirs like guide/scripts/, rddf-session/).
    if (project_root / "skills").is_dir():
        shutil.copytree(
            project_root / "skills",
            target / "skills",
            dirs_exist_ok=True,
        )

    # Copy _lib/ as a whole.
    if (project_root / "_lib").is_dir():
        shutil.copytree(
            project_root / "_lib",
            target / "_lib",
            dirs_exist_ok=True,
        )

    # Copy package.json (single file).
    if (project_root / "package.json").is_file():
        shutil.copy2(project_root / "package.json", target / "package.json")

    # The shim is already inside skills/ from the copytree above, but we
    # also surface it at the dest root for convenience (matches legacy
    # ``rddf`` behavior in the dest dir).
    shim_src = project_root / "skills" / "cli" / "rddf.sh"
    if shim_src.is_file():
        shutil.copy2(shim_src, target / "rddf.sh")
        os.chmod(target / "rddf.sh", 0o755)

    skills_md_count = (
        sum(1 for _ in (target / "skills").glob("*.md"))
        if (target / "skills").is_dir()
        else 0
    )
    lib_count = (
        sum(1 for _ in (target / "_lib").rglob("*") if _.is_file())
        if (target / "_lib").is_dir()
        else 0
    )
    print("📦 安装 rdd-workflow 到项目")
    print(f"   目标: {target}")
    print(f"   技能文件: {skills_md_count} 个")
    print(f"   工具库:   _lib ({lib_count} 文件)")
    print(f"   CLI:      {target}/rddf.sh")
    print("✅ 安装完成!")
    return 0


def _print_help() -> None:
    print("usage: rddf init [target]")
    print()
    print("Install rdd-workflow to <target>/.opencode/skills/rdd-workflow/.")
    print("Default target is RDDF_PROJECT_ROOT (the current project).")


__all__ = ["cmd_init"]