"""``rddf version`` subcommand handler.

Reads the ``version`` field from ``<project_root>/package.json`` and prints
the canonical banner ``rddf v<X.Y.Z> — spec-workflow CLI``. Project root
is injected by ``cli.__main__`` via the ``RDDF_PROJECT_ROOT`` env var;
falls back to ``os.getcwd()`` when unset (so direct test invocation
works).

Usage::

    python3 -m skills._lib.cli version
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def cmd_version(args: list[str]) -> int:
    """Handle ``rddf version``.

    Args:
        args: Unused (the version subcommand takes no arguments).

    Returns:
        0 on success, 1 if ``package.json`` is missing or unreadable.
    """
    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    pkg_path = Path(project_root) / "package.json"

    if not pkg_path.is_file():
        print(
            f"❌ version: package.json not found at {pkg_path}",
            file=sys.stderr,
        )
        return 1

    try:
        data = json.loads(pkg_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"❌ version: failed to read {pkg_path}: {e}", file=sys.stderr)
        return 1

    version = data.get("version") or "0.0.0"
    print(f"rddf v{version} — spec-workflow CLI")
    return 0


__all__ = ["cmd_version"]