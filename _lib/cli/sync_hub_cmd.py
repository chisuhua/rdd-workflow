"""``rddf sync-hub`` subcommand handler.

Thin subprocess wrapper that delegates to the existing
``skills/sync-hub/scripts/sync_hub.py`` argparse entry point (ADR-0030
下行通道: pull Hub contracts into local ``openspec/specs/``). Args are
forwarded verbatim; exit codes propagate transparently.

Registration precedent: ``contract_check_cmd.py`` (change
``complete-add-contract-lint-ci-gate``).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def cmd_sync_hub(args: list[str]) -> int:
    """Handle ``rddf sync-hub``.

    Args:
        args: CLI args forwarded verbatim to ``sync_hub.py``
            (e.g. ``["--contract", "auth-v2.yaml"]`` or ``["--help"]``).

    Returns:
        Exit code from the ``sync_hub.py`` subprocess.
    """
    project_root = Path(
        os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    )
    script = project_root / "skills" / "sync-hub" / "scripts" / "sync_hub.py"

    result = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(project_root),
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(cmd_sync_hub(sys.argv[1:]))
