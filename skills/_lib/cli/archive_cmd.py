"""``rddf archive <name>`` subcommand handler.

**Thin wrapper** that subprocess-spawns the existing ``skills/_lib/archive.sh``
script, which provides the ``archive_change <name>`` function. The bash
script handles worktree-mode merge, ``openspec archive``, worktree cleanup,
and the auto-commit helper. A future change may port ``archive.sh`` to
Python; this module is the bridge until then.

Usage::

    python3 -m skills._lib.cli archive <name>
    python3 -m skills._lib.cli archive --help
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Cached path to archive.sh (resolved lazily, monkeypatchable for tests).
_ARCHIVE_SH: str | None = None


def _resolve_archive_sh() -> str:
    """Return the absolute path to ``skills/_lib/archive.sh``, cached."""
    global _ARCHIVE_SH
    if _ARCHIVE_SH is None:
        project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
        _ARCHIVE_SH = str(Path(project_root) / "skills" / "_lib" / "archive.sh")
    return _ARCHIVE_SH


def cmd_archive(args: list[str]) -> int:
    """Handle ``rddf archive <name>``.

    Args:
        args: Change name (required) or ``--help`` / ``-h``.

    Returns:
        0 on success, 1 if ``archive.sh`` is missing or returns non-zero,
        2 on bad flag.
    """
    if not args:
        _print_help()
        return 2
    if args[0] in ("-h", "--help"):
        _print_help()
        return 0
    if args[0].startswith("-"):
        print(f"❌ archive: unknown flag {args[0]!r}", file=sys.stderr)
        print("   usage: rddf archive <change-name>", file=sys.stderr)
        return 2

    name = args[0]
    archive_sh = _resolve_archive_sh()
    if not os.path.isfile(archive_sh):
        print(
            f"❌ archive: 找不到 {archive_sh}\n"
            f"   预期位置: <project_root>/skills/_lib/archive.sh",
            file=sys.stderr,
        )
        return 1

    print(f"📦 归档 change: {name}")
    print("━" * 40)

    # Spawn bash with the archive.sh sourced and archive_change invoked.
    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    try:
        result = subprocess.run(
            [
                "bash",
                "-c",
                f'source "{archive_sh}" && archive_change "$0"',
                name,
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        print(f"❌ archive: failed to spawn bash: {e}", file=sys.stderr)
        return 1

    # Surface bash stdout to the user.
    if result.stdout:
        print(result.stdout, end="")
    if result.returncode != 0:
        print(
            f"❌ archive: archive_change exited with code {result.returncode}",
            file=sys.stderr,
        )
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return 1

    print(f"✅ change {name} 归档完成")
    return 0


def _print_help() -> None:
    print("usage: rddf archive <change-name>")
    print()
    print("Archive a change (merge → openspec archive → worktree cleanup).")
    print("Delegates to skills/_lib/archive.sh::archive_change.")


# Reset for test isolation.
def _reset() -> None:
    global _ARCHIVE_SH
    _ARCHIVE_SH = None


__all__ = ["cmd_archive", "_reset"]