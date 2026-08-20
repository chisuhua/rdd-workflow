"""``rddf rdd-hub-bootstrap`` subcommand handler.

Thin subprocess wrapper that delegates to the existing
``skills/rdd-hub-bootstrap/scripts/init_hub.sh`` entry point. Args are
forwarded verbatim; exit codes propagate transparently.

Subcommands map to scripts under ``skills/rdd-hub-bootstrap/scripts/``:
- ``init`` -> ``init_hub.sh`` (--org required, --dry-run / --yes)
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _help_text() -> str:
    return (
        "rddf rdd-hub-bootstrap - Hub repository init\n"
        "\n"
        "Usage:\n"
        "  rddf rdd-hub-bootstrap init [--org <org>] [--repo <repo>] [--dry-run] [--yes]\n"
        "\n"
        "Subcommands:\n"
        "  init    Initialize rdd-hub repository (GitHub Org required)\n"
        "    --org <org>      GitHub Org name (required)\n"
        "    --repo <repo>    Hub repo name (default: rdd-hub)\n"
        "    --dry-run        Simulate without calling GitHub API\n"
        "    --yes            Skip confirmation prompt\n"
    )


def cmd_rdd_hub_bootstrap(args: list[str]) -> int:
    """Handle ``rddf rdd-hub-bootstrap``.

    Args:
        args: CLI args. First positional arg is the subcommand,
            remaining args are forwarded to the subcommand script.

    Returns:
        Exit code from the subcommand script, or 0 for ``--help``.
    """
    project_root = Path(
        os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    )

    if not args or args[0] in ("--help", "-h"):
        print(_help_text())
        return 0

    subcommand = args[0]
    sub_args = args[1:]

    _SUBCOMMAND_MAP = {
        "init": project_root / "skills" / "rdd-hub-bootstrap" / "scripts" / "init_hub.sh",
    }

    if subcommand not in _SUBCOMMAND_MAP:
        print(f"ERROR: unknown subcommand: {subcommand}", file=sys.stderr)
        print(_help_text())
        return 2

    script = _SUBCOMMAND_MAP[subcommand]

    if not script.is_file():
        print(f"ERROR: rdd-hub-bootstrap: script not found at {script}", file=sys.stderr)
        return 3

    result = subprocess.run(
        ["bash", str(script), *sub_args],
        cwd=str(project_root),
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(cmd_rdd_hub_bootstrap(sys.argv[1:]))