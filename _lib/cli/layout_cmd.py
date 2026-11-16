"""``rddf layout`` subcommand handler.

Prints the `.rddf/` layout manifest (RDFF_LAYOUT) as JSON. Read-only.

The payload is the *declared* layout — the product's definition of what
`.rddf/` contains — not a scan of the current tree. What a given project
actually has on disk is the doctor's job
(`rddf doctor --category layout`).

The payload carries no timestamp, so two runs over the same installation
produce byte-identical output and consumers may diff them.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from skills._lib.cli import resolve_project_root  # noqa: E402

SCHEMA_VERSION = 1


def cmd_layout(args: list[str]) -> int:
    """Handle ``rddf layout [--json]``."""
    project_root = Path(os.environ.get("RDDF_PROJECT_ROOT") or resolve_project_root())
    sys.path.insert(0, str(project_root))

    from _lib.core.rddf_layout import as_dicts

    payload = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": _tool_version(project_root),
        "entries": as_dicts(),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _tool_version(project_root: Path) -> str:
    """Version of the rdd-workflow package that owns this handler."""
    pkg = Path(__file__).resolve().parents[2] / "package.json"
    try:
        return json.loads(pkg.read_text(encoding="utf-8")).get("version", "0.0.0")
    except (OSError, ValueError):
        return "0.0.0"
