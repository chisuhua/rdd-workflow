"""``rddf watch-hub`` subcommand handler.

Thin subprocess wrapper that delegates to the existing
``skills/watch-hub/scripts/watch_hub.py`` argparse entry point (ADR-0030
监听通道: one-shot poll of Hub Issue statuses, scheduled by cron/CI — no
long-running daemon). Args are forwarded verbatim; exit codes propagate
transparently.

Registration precedent: ``contract_check_cmd.py`` (change
``complete-add-contract-lint-ci-gate``).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def cmd_watch_hub(args: list[str]) -> int:
    """Handle ``rddf watch-hub``.

    Args:
        args: CLI args forwarded verbatim to ``watch_hub.py``
            (e.g. ``["--once", "--owner", "org/rdd-hub"]`` or ``["--help"]``).

    Returns:
        Exit code from the ``watch_hub.py`` subprocess.
    """
    project_root = Path(
        os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    )
    script = project_root / "skills" / "watch-hub" / "scripts" / "watch_hub.py"

    result = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(project_root),
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(cmd_watch_hub(sys.argv[1:]))
