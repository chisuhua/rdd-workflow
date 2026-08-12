"""Resolve paths to the real _lib/ directory.

CRITICAL: After commit c3a90fe, `skills/_lib/` is a 6-line shim that sources
`${HOME}/.agents/skills/_lib/`. Any code path that loads JSON schema via
the shim risks silently inheriting stale global state. This module returns
ONLY the real _lib/ location.
"""
from __future__ import annotations

import os
from pathlib import Path

_PROJECT_ROOT_ENV = "RDDF_PROJECT_ROOT"


class LibPathNotFoundError(FileNotFoundError):
    """Raised when a required file is missing from the real _lib/."""


def _project_root() -> Path:
    raw = os.environ.get(_PROJECT_ROOT_ENV)
    if not raw:
        raise LibPathNotFoundError(
            f"{_PROJECT_ROOT_ENV} env var not set. doctor must be invoked through doctor.sh."
        )
    p = Path(raw).resolve()
    if not p.is_dir():
        raise LibPathNotFoundError(f"{_PROJECT_ROOT_ENV}={p} is not a directory")
    return p


def resolve_real_lib_path(relative: str, project_root: Path | None = None) -> Path:
    """Return absolute path to `<project_root>/_lib/<relative>`.

    Raises LibPathNotFoundError if the file does not exist at the real location.
    Does NOT consult any shim path.

    If ``project_root`` is provided, use it directly (avoids env var lookup).
    Otherwise fall back to ``RDDF_PROJECT_ROOT`` env var.
    """
    if project_root is None:
        root = _project_root()
    else:
        root = Path(project_root).resolve()
    real = root / "_lib" / relative
    if not real.is_file():
        raise LibPathNotFoundError(
            f"Real _lib file not found: {real}. "
            f"doctor must resolve from real _lib/, not skills/_lib/ shim."
        )
    return real