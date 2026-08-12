"""``rddf migrate-improvements`` subcommand handler.

Moves legacy ``improvements/*.md`` to ``.rddf/improvements/*.md`` for
third-party projects using globally-installed rdd-workflow.

Reference: ``openspec/changes/archive/2026-08-11-migrate-improvements-to-rddf-namespace``
(ADR-0026 dot-prefix metadata namespace convention).

Why this command exists:
    rdd-workflow's own source repo migrated ``improvements/`` to
    ``.rddf/improvements/`` (134 files) to prevent the opencode-skillfull
    plugin from indexing them as slash commands (~4,887 tokens saved per
    system-prompt build). Third-party projects that accumulated content in
    ``improvements/`` while using an older rdd-workflow version need a
    one-shot migration to match the new namespace.

Usage::

    python3 -m _lib.cli migrate-improvements [--dry-run] [--help]

The ``--dry-run`` flag prints what would happen without touching the
filesystem. Exit codes: 0 = success / no-op, 1 = refusal (already
migrated, source repo detected, or other pre-condition failure), 2 =
bad flag.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


_MARKDOWN_LINK_FILES = ("proposal-approved.md", "proposal-suggestions.md")
_DOC_LINK_FILES = (
    "AGENTS.md",
    "README.md",
    "USAGE.md",
    "docs/proposal-suggestions-format.md",
    "docs/proposal-approved-format.md",
)
_ITERATION_STATE_FILE = ".rddf/state/iteration.json"
_LINK_REGEX = re.compile(r"\]\(improvements/([^)\s]+)\)")
_DOUBLE_PREFIX_REGEX = re.compile(r"\]\(\.rddf/\.rddf/improvements/([^)\s]+)\)")


def _link_replacement(match: re.Match) -> str:
    """Rewrite a markdown link target from ``improvements/X`` to ``.rddf/improvements/X``."""
    return "](.rddf/improvements/" + match.group(1) + ")"


def _double_prefix_replacement(match: re.Match) -> str:
    """Collapse a double-prefixed link to its single-prefix form."""
    return "](.rddf/improvements/" + match.group(1) + ")"


_PATH_FIELDS = ("path", "proposal_path", "spec_path")


def _print_help() -> None:
    """Print usage to stdout."""
    print("usage: rddf migrate-improvements [--dry-run] [--include-docs] [--allow-source-repo] [--help]")
    print()
    print("Migrate legacy improvements/*.md → .rddf/improvements/*.md.")
    print("For third-party projects using globally-installed rdd-workflow.")
    print()
    print("Behavior:")
    print("  - Refuses if the project is the rdd-workflow source repo itself")
    print("    (detected: skills/INSTALL.md + .rddf/improvements/ both exist).")
    print("    Use --allow-source-repo to bypass for self-maintenance.")
    print("  - No-op (exit 0) if improvements/ does not exist (unless --include-docs)")
    print("  - Refuses (exit 1) if .rddf/improvements/ already exists")
    print("  - Uses git mv inside git repos (preserves rename history)")
    print("  - Falls back to plain mv outside git repos")
    print("  - Updates markdown links in proposal-approved.md / proposal-suggestions.md")
    print("  - Updates path fields in .rddf/state/iteration.json")
    print("  - With --include-docs: also rewrites AGENTS.md + format docs")
    print("    (single-prefix improvements/ → .rddf/improvements/, plus fixes")
    print("    .rddf/.rddf/improvements/ double-prefix bug)")
    print()
    print("Flags:")
    print("  --dry-run              Print what would happen without touching the filesystem")
    print("  --include-docs         Scan AGENTS.md + format docs and rewrite stale references")
    print("  --allow-source-repo    Bypass the source-repo refusal guard")
    print("  --help, -h             Show this help")


def _is_rddwf_source_repo(proj_root: Path) -> bool:
    """Heuristic detection: is this directory the rdd-workflow source repo?

    Returns True when both ``skills/INSTALL.md`` (the rdd-workflow entry
    doc) and ``.rddf/improvements/`` (the post-migration marker) exist.
    This combination is unique to the rdd-workflow repo itself - third-
    party projects will never have ``skills/INSTALL.md`` at the project
    root because rdd-workflow installs to ``.opencode/skills/`` or
    ``~/.agents/skills/``.
    """
    install_md = proj_root / "skills" / "INSTALL.md"
    rddf_improvements = proj_root / ".rddf" / "improvements"
    return install_md.is_file() and rddf_improvements.is_dir()


def _is_git_repo(path: Path) -> bool:
    """Return True if ``path`` is inside a git working tree."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            cwd=str(path),
            timeout=10,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _move_files(src_dir: Path, dest_dir: Path, use_git: bool, dry_run: bool) -> list[str]:
    """Move all ``*.md`` files from ``src_dir`` into ``dest_dir``.

    Returns the list of filenames (basename only) that were moved.

    When ``use_git`` is True, uses ``git mv`` to preserve rename history
    (``git log --follow`` will trace the new path back to the old one).
    When False, uses a plain ``mv`` (third-party projects not under git
    version control).

    ``dry_run`` short-circuits without actually moving anything.
    """
    moved: list[str] = []
    if not src_dir.is_dir():
        return moved

    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)

    for entry in sorted(src_dir.iterdir()):
        if not entry.is_file() or entry.suffix != ".md":
            continue
        if dry_run:
            moved.append(entry.name)
            continue
        if use_git:
            r = subprocess.run(
                ["git", "mv", str(entry), str(dest_dir / entry.name)],
                cwd=str(src_dir.parent),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if r.returncode != 0:
                # Fall back to plain mv if git mv fails (e.g. file not tracked)
                shutil.move(str(entry), str(dest_dir / entry.name))
        else:
            shutil.move(str(entry), str(dest_dir / entry.name))
        moved.append(entry.name)

    # Remove the now-empty source directory (only if it is actually empty)
    if not dry_run and src_dir.is_dir() and not any(src_dir.iterdir()):
        try:
            src_dir.rmdir()
        except OSError:
            pass  # non-empty or otherwise unremovable; leave it

    return moved


def _rewrite_markdown_links(proj_root: Path, dry_run: bool) -> dict[str, int]:
    """Rewrite ``(improvements/X)`` to ``(.rddf/improvements/X)`` in link files.

    Only the substring ``](improvements/`` is rewritten - link text and
    surrounding context are untouched. Non-matching lines (e.g. plain text
    mentioning "improvements" without the link syntax) are left alone.

    Returns a mapping of filename -> number of links rewritten.
    """
    counts: dict[str, int] = {}
    for name in _MARKDOWN_LINK_FILES:
        path = proj_root / name
        if not path.is_file():
            continue
        original = path.read_text()
        new, n = _LINK_REGEX.subn(_link_replacement, original)
        if n == 0:
            continue
        counts[name] = n
        if not dry_run:
            path.write_text(new)
    return counts


def _rewrite_doc_references(proj_root: Path, dry_run: bool) -> dict[str, int]:
    """Rewrite link references in AGENTS.md + project docs.

    Handles two patterns:
    - ``](improvements/X)`` → ``](.rddf/improvements/X)`` (legacy pre-migration)
    - ``](.rddf/.rddf/improvements/X)`` → ``](.rddf/improvements/X)``
      (double-prefix bug from an earlier migration that ran a naive s/pattern/replacement/)

    Only files listed in ``_DOC_LINK_FILES`` are touched. Link text and
    surrounding context are left intact. Returns a mapping of
    filename -> total rewrites (single + double).
    """
    counts: dict[str, int] = {}
    for name in _DOC_LINK_FILES:
        path = proj_root / name
        if not path.is_file():
            continue
        original = path.read_text()
        # Double-prefix fix MUST run first to avoid leaving a
        # ``.rddf/.rddf/improvements/`` artifact when a file contains both
        # patterns.
        new, n_double = _DOUBLE_PREFIX_REGEX.subn(_double_prefix_replacement, original)
        n_single = 0
        if _LINK_REGEX.search(new):
            new, n_single = _LINK_REGEX.subn(_link_replacement, new)
        total = n_double + n_single
        if total == 0:
            continue
        counts[name] = total
        if not dry_run:
            path.write_text(new)
    return counts


def _rewrite_iteration_paths(proj_root: Path, dry_run: bool) -> int:
    """Rewrite ``"path": "improvements/X"`` fields in iteration.json.

    Iterates over every change entry; any string field whose value starts
    with ``improvements/`` is rewritten to ``.rddf/improvements/``. The
    schema is tolerant: unknown fields are left alone, only string values
    matching the prefix are touched.

    Returns the number of fields rewritten (0 if the file is absent).
    """
    path = proj_root / _ITERATION_STATE_FILE
    if not path.is_file():
        return 0
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return 0

    n = 0
    changes = data.get("changes", [])
    if isinstance(changes, list):
        for entry in changes:
            if not isinstance(entry, dict):
                continue
            for field in _PATH_FIELDS:
                value = entry.get(field)
                if isinstance(value, str) and value.startswith("improvements/"):
                    if not dry_run:
                        entry[field] = ".rddf/" + value
                    n += 1

    if n > 0 and not dry_run:
        # Atomic-ish write: write to tmp, rename. iteration.json is small
        # enough that the window is negligible but the rename is cheap insurance.
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        os.replace(tmp_path, path)
    return n


def cmd_migrate_improvements(args: list[str]) -> int:
    """Handle ``rddf migrate-improvements [--dry-run] [--include-docs] [--allow-source-repo]``.

    Args:
        args: Optional ``--dry-run`` / ``--include-docs`` / ``--allow-source-repo`` /
            ``--help`` / ``-h``.

    Returns:
        0 on success or no-op, 1 on refusal (already migrated / source
        repo), 2 on bad flag.
    """
    dry_run = False
    include_docs = False
    allow_source_repo = False
    for flag in args:
        if flag in ("--help", "-h"):
            _print_help()
            return 0
        if flag == "--dry-run":
            dry_run = True
            continue
        if flag == "--include-docs":
            include_docs = True
            continue
        if flag == "--allow-source-repo":
            allow_source_repo = True
            continue
        if flag.startswith("-"):
            print(f"❌ migrate-improvements: unknown flag {flag!r}", file=sys.stderr)
            print("   usage: rddf migrate-improvements [--dry-run] [--include-docs] [--allow-source-repo] [--help]", file=sys.stderr)
            return 2

    proj_root = Path(os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd())

    # ── Pre-flight check 1: refuse to run in rdd-workflow source repo (unless --allow-source-repo) ──
    if not allow_source_repo and _is_rddwf_source_repo(proj_root):
        print(
            f"❌ 检测到这是 rdd-workflow 源码仓库本身 ({proj_root})\n"
            "   此命令面向第三方项目,请勿在 rdd-workflow 仓库内运行。\n"
            "   源码仓库的迁移在 archived change 'migrate-improvements-to-rddf-namespace' 中已完成。\n"
            "   如确需在源码仓库执行（例如修复 AGENTS.md / format docs 残留引用），\n"
            "   请显式传 --allow-source-repo 标志。",
            file=sys.stderr,
        )
        return 1

    improvements_dir = proj_root / "improvements"
    target_dir = proj_root / ".rddf" / "improvements"

    # ── Pre-flight check 2: no-op when there's nothing to migrate ──
    if not improvements_dir.is_dir():
        if include_docs:
            # Docs-only mode: proceed even when there's no improvements/ dir
            pass
        else:
            print(f"ℹ️  improvements/ 不存在 — 无需迁移 (project: {proj_root})")
            return 0

    # ── Pre-flight check 3: refuse to overwrite an existing target ──
    if (
        not include_docs
        and target_dir.is_dir()
        and any(target_dir.iterdir())
    ):
        print(
            f"❌ {target_dir}/ 已存在且非空 — 拒绝覆盖以防数据丢失。\n"
            "   如果这是历史迁移残留,请手工合并或清空后重试。",
            file=sys.stderr,
        )
        return 1

    use_git = _is_git_repo(proj_root)
    move_method = "git mv" if use_git else "mv"
    prefix = "[DRY-RUN] " if dry_run else ""

    if improvements_dir.is_dir():
        print(f"{prefix}📦 迁移 improvements/ → .rddf/improvements/")
    else:
        print(f"{prefix}📦 仅 docs 引用修复 (improvements/ 不存在)")
    print(f"{prefix}   项目根: {proj_root}")
    print(f"{prefix}   移动方式: {move_method}{' (git rename detection)' if use_git else ''}")
    if include_docs:
        print(f"{prefix}   · 启用 --include-docs: 扫描 AGENTS.md + format docs")

    moved: list[str] = []
    if improvements_dir.is_dir():
        # ── Step 1: move *.md files ──
        moved = _move_files(improvements_dir, target_dir, use_git=use_git, dry_run=dry_run)
        print(f"{prefix}   ✓ 移动文件: {len(moved)} 个 ({', '.join(moved) if moved else '无'})")

    # ── Step 2: rewrite markdown links ──
    link_counts = _rewrite_markdown_links(proj_root, dry_run=dry_run)
    if link_counts:
        for fname, n in link_counts.items():
            print(f"{prefix}   ✓ 更新 {fname}: {n} 个链接")
    else:
        print(f"{prefix}   · 无 proposal-*.md markdown 链接需要更新")

    # ── Step 3: rewrite iteration.json paths ──
    n_paths = _rewrite_iteration_paths(proj_root, dry_run=dry_run)
    if n_paths > 0:
        print(f"{prefix}   ✓ 更新 {_ITERATION_STATE_FILE}: {n_paths} 个 path 字段")
    else:
        print(f"{prefix}   · 无 iteration.json path 字段需要更新")

    # ── Step 4 (optional): rewrite AGENTS.md + format docs references ──
    doc_counts: dict[str, int] = {}
    if include_docs:
        doc_counts = _rewrite_doc_references(proj_root, dry_run=dry_run)
        if doc_counts:
            for fname, n in doc_counts.items():
                print(f"{prefix}   ✓ 更新 {fname}: {n} 个引用")
        else:
            print(f"{prefix}   · 无 docs 引用需要更新")

    # ── Summary ──
    if dry_run:
        print(f"{prefix}✅ Dry-run 完成 — 未修改任何文件")
    else:
        total_links = sum(link_counts.values()) + sum(doc_counts.values())
        print(f"{prefix}✅ 迁移完成 ({len(moved)} 文件 / "
              f"{total_links} 链接 / {n_paths} state paths)")
    return 0


__all__ = ["cmd_migrate_improvements"]