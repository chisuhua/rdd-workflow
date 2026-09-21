"""``rddf setup ai-context`` subcommand handler.

Injects the Layer 0 protocol block (from the SSOT template at
``_lib/templates/layer0_rdd_workflow_usage.md``) into the target project's
AI configuration files.

Usage::

    rddf setup ai-context [--dry-run] [--yes] [--uninstall]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


# Sentinel markers — must match the SSOT template exactly.
_SENTINEL_START = "<!-- RDD-WORKFLOW-CORE-USAGE-START -->"
_SENTINEL_END = "<!-- RDD-WORKFLOW-CORE-USAGE-END -->"

# AI config file detection order (per ADR-0052).
_AI_CONFIG_FILES = [
    "AGENTS.md",
    ".cursorrules",
    "CLAUDE.md",
    ".clinerules",
    ".continue/rules/*.md",
    ".github/copilot-instructions.md",
]

_TEMPLATE_REL = "_lib/templates/layer0_rdd_workflow_usage.md"


def _read_template(project_root: Path) -> str | None:
    """Read the SSOT template, return its text or None if missing."""
    tpl = project_root / _TEMPLATE_REL
    if not tpl.is_file():
        return None
    return tpl.read_text(encoding="utf-8")


def _detect_config_files(project_root: Path) -> list[Path]:
    """Return ordered list of existing AI config files in the target project.

    Glob patterns (like ``.continue/rules/*.md``) are expanded; only
    existing regular files are returned. Order follows the detection
    priority in ADR-0052.
    """
    found: list[Path] = []
    for pattern in _AI_CONFIG_FILES:
        full_pattern = project_root / pattern
        if "*" in str(full_pattern):
            matches = sorted(project_root.glob(pattern))
            found.extend(m for m in matches if m.is_file())
        else:
            if full_pattern.is_file():
                found.append(full_pattern)
    return found


def _has_sentinel(content: str) -> bool:
    """Return True if content already contains the Layer 0 sentinel."""
    return _SENTINEL_START in content


def _block_from_template(template: str) -> str:
    """Wrap template content in sentinel markers (already present in SSOT)."""
    return template


def _strip_sentinel_block(content: str) -> str:
    """Remove the Layer 0 sentinel block (inclusive) from content.

    Returns the content with the block removed. If the sentinel is not
    found, returns the content unchanged.
    """
    start = content.find(_SENTINEL_START)
    end = content.find(_SENTINEL_END)
    if start == -1 or end == -1:
        return content
    # Include the sentinel END marker line's newline.
    end_line = content.find("\n", end)
    if end_line == -1:
        end_line = len(content)
    else:
        end_line += 1  # include the newline
    return content[:start] + content[end_line:]


def cmd_setup(args: list[str]) -> int:
    """Handle ``rddf setup [ai-context|--help]``.

    Args:
        args: CLI args (e.g. ``["ai-context", "--dry-run"]`` or
            ``["--help"]``).

    Returns:
        0 on success, 1 on error, 2 on bad usage.
    """
    parser = argparse.ArgumentParser(
        prog="rddf setup",
        description="Setup rdd-workflow project configuration.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Sub-commands")

    # --- ai-context subcommand ---
    ac_parser = subparsers.add_parser(
        "ai-context",
        help="Deploy Layer 0 protocol block to AI config files.",
        description=(
            "Inject the rdd-workflow Layer 0 protocol block into the project's "
            "AI configuration files (AGENTS.md, .cursorrules, CLAUDE.md, etc.). "
            "Idempotent: repeated runs skip already-injected files."
        ),
    )
    ac_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing any files.",
    )
    ac_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt.",
    )
    ac_parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove previously injected Layer 0 blocks from all AI config files.",
    )
    ac_parser.add_argument(
        "--target",
        default=None,
        help="Target project root (default: RDDF_PROJECT_ROOT or cwd).",
    )

    parsed = parser.parse_args(args)

    if parsed.subcommand != "ai-context":
        parser.print_help()
        return 2

    return _handle_ai_context(parsed)


def _handle_ai_context(args: argparse.Namespace) -> int:
    """Core logic for ``rddf setup ai-context``."""
    project_root = Path(
        args.target
        or os.environ.get("RDDF_PROJECT_ROOT")
        or os.getcwd()
    )

    # Read SSOT template.
    template = _read_template(project_root)
    if template is None:
        print(
            f"❌ setup ai-context: SSOT template not found at "
            f"{project_root / _TEMPLATE_REL}",
            file=sys.stderr,
        )
        return 1

    # Detect AI config files.
    existing = _detect_config_files(project_root)

    if not existing:
        # No config files exist → create AGENTS.md.
        target_path = project_root / "AGENTS.md"
        already_has = target_path.is_file() and _has_sentinel(
            target_path.read_text(encoding="utf-8")
        )

        if args.dry_run:
            if already_has:
                print(f"🔍 [dry-run] 已存在 → 跳过: {target_path}")
            else:
                print(f"🔍 [dry-run] 将创建: {target_path} (AGENTS.md)")
            return 0

        if already_has:
            print(f"⏩ 已存在 Layer 0 块 → 跳过: {target_path}")
            return 0

        if not args.yes:
            print(f"将创建 {target_path}")
            reply = input("  确认? [Y/n] ").strip().lower()
            if reply not in ("", "y", "yes"):
                print("❌ 已取消")
                return 1

        target_path.write_text(template + "\n", encoding="utf-8")
        print(f"✅ 已创建 {target_path} (Layer 0 块)")
        return 0

    # Config files exist → append or remove.
    modified = 0
    skipped = 0
    for cfg in existing:
        content = cfg.read_text(encoding="utf-8")

        if args.uninstall:
            # Remove sentinel block.
            if _has_sentinel(content):
                new_content = _strip_sentinel_block(content)
                if args.dry_run:
                    print(f"🔍 [dry-run] 将移除 Layer 0 块: {cfg}")
                else:
                    cfg.write_text(new_content, encoding="utf-8")
                    modified += 1
                print(f"   {'[dry-run] ' if args.dry_run else ''}移除: {cfg}")
            else:
                print(f"   ⏩ 无 Layer 0 块: {cfg}")
            continue

        # Append mode.
        if _has_sentinel(content):
            skipped += 1
            continue

        # Check for trailing newline before appending.
        sep = "\n\n" if content.endswith("\n") else "\n\n"
        new_content = content + sep + template

        if args.dry_run:
            print(f"🔍 [dry-run] 将追加 Layer 0 块: {cfg}")
        else:
            cfg.write_text(new_content, encoding="utf-8")
            modified += 1
        print(f"   {'[dry-run] ' if args.dry_run else ''}追加: {cfg}")

    if not args.dry_run:
        total = modified + skipped
        if args.uninstall:
            print(f"✅ Layer 0 块已从 {modified} 个文件移除" + (
                f" ({skipped} 个文件无块)" if skipped else ""
            ))
        else:
            print(f"✅ Layer 0 块已部署到 {modified} 个文件" + (
                f" ({skipped} 个文件已存在, 跳过)" if skipped else ""
            ))

    return 0


__all__ = ["cmd_setup"]