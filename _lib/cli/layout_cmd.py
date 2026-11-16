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
from pathlib import Path

# Import through the package's own path (the `skills._lib.cli` shim already
# binds `_lib.cli` to this package). Deliberately NOT `sys.path.insert(0,
# project_root)`: the consumer's project root may contain a `_lib/` package
# of its own, and putting it first would shadow the tool's own modules —
# `from _lib.core.rddf_layout import ...` would then resolve to the
# consumer's code, and the payload would no longer be the product's
# declared layout.
from _lib.core.rddf_layout import as_dicts  # noqa: E402

SCHEMA_VERSION = 1


def cmd_layout(args: list[str]) -> int:
    """Handle ``rddf layout [--json]``."""
    payload = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": _tool_version(),
        "entries": as_dicts(),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _tool_version() -> str:
    """Version of the rdd-workflow package that owns this handler."""
    pkg = Path(__file__).resolve().parents[2] / "package.json"
    try:
        return json.loads(pkg.read_text(encoding="utf-8")).get("version", "0.0.0")
    except (OSError, ValueError):
        return "0.0.0"
