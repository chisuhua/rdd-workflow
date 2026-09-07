"""``rddf ac-verify`` subcommand handler — REMOVED stub (ADR-0045 + remove-ac-verifier-completely).

The ac-verifier skill has been removed (ADR-0045: inline-ac-verifier-into-rdd-verifier).
This CLI is retained ONLY as a friendly-error stub so users see a clear migration
hint instead of `command not found` or a silent failure.

Behavior (effective from remove-ac-verifier-completely, 2026-09-07):
    rddf ac-verify [...any args] → exit 4 + stderr migration hint

Exit code 4 is reserved for "command has been removed; use the replacement".
This is distinct from exit 2 (skipped) and exit 1 (verification failed).

Replacement: `rddf rdd-verify` (rdd-verifier v2.0; ADR-0045).
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


_REMOVAL_NOTICE = (
    "❌ `rddf ac-verify` was removed per ADR-0045 (inline-ac-verifier-into-rdd-verifier) "
    "and `remove-ac-verifier-completely` (2026-09-07).\n"
    "   Replacement: `rddf rdd-verify` — rdd-verifier v2.0 self-contains LLM verification.\n"
    "   The executing AI agent IS the LLM (no `AC_LLM_*` env vars needed).\n"
    "   See: docs/adr/ADR-0045-inline-ac-verifier-into-rdd-verifier.md"
)


def cmd_ac_verify(args: list[str]) -> int:
    """Handle ``rddf ac-verify`` — friendly-error stub (exit 4)."""
    print(_REMOVAL_NOTICE, file=sys.stderr)
    return 4


if __name__ == "__main__":
    sys.exit(cmd_ac_verify(sys.argv[1:]))