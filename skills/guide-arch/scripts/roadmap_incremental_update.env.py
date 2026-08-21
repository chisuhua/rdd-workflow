#!/usr/bin/env python3
"""Env-var validator for roadmap_incremental_update (Oracle C1).

Reads all configuration from os.environ — never from bash string
interpolation — and validates it before the main module runs.

Exit codes:
  0  all env vars valid
  2  one or more env vars invalid (errors printed to stderr with ❌ prefix)

Validated vars:
  RDDF_PROJECT_ROOT      required; must be an existing directory
  RDDF_CODEBASE_COMMIT   optional; if set must match ^[0-9a-f]{7,40}$
  RDDF_ROADMAP_UPDATE    optional; one of {on, off, force} (default on)
  RDDF_INCREMENTAL       optional; one of {on, off} (default on)
"""
from __future__ import annotations

import os
import re
import sys

_COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
_VALID_ROADMAP_UPDATE = {"on", "off", "force"}
_VALID_INCREMENTAL = {"on", "off"}


def _err(msg: str) -> None:
    print(f"❌ {msg}", file=sys.stderr)


def validate() -> int:
    ok = True

    project_root = os.environ.get("RDDF_PROJECT_ROOT", "")
    if not project_root:
        _err("RDDF_PROJECT_ROOT is required but not set")
        ok = False
    elif not os.path.isdir(project_root):
        _err(f"RDDF_PROJECT_ROOT is not a directory: {project_root!r}")
        ok = False

    codebase_commit = os.environ.get("RDDF_CODEBASE_COMMIT", "")
    if codebase_commit and not _COMMIT_RE.match(codebase_commit):
        _err(
            "RDDF_CODEBASE_COMMIT malformed (expected ^[0-9a-f]{7,40}$): "
            f"{codebase_commit!r}"
        )
        ok = False

    roadmap_update = os.environ.get("RDDF_ROADMAP_UPDATE", "on")
    if roadmap_update not in _VALID_ROADMAP_UPDATE:
        _err(
            f"RDDF_ROADMAP_UPDATE must be one of {sorted(_VALID_ROADMAP_UPDATE)}, "
            f"got {roadmap_update!r}"
        )
        ok = False

    incremental = os.environ.get("RDDF_INCREMENTAL", "on")
    if incremental not in _VALID_INCREMENTAL:
        _err(
            f"RDDF_INCREMENTAL must be one of {sorted(_VALID_INCREMENTAL)}, "
            f"got {incremental!r}"
        )
        ok = False

    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(validate())
