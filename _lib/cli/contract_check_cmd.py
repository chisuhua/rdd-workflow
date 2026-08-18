"""``rddf contract-check`` subcommand handler.

Thin subprocess wrapper that delegates to the existing
``skills/contract-check/scripts/contract_check.py`` argparse entry
point. Exit codes propagate transparently (0 = no breaking,
1 = breaking change, 2+ = tool error).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def cmd_contract_check(args: list[str]) -> int:
    """Handle ``rddf contract-check``.

    Args:
        args: CLI args forwarded to contract_check.py.

    Returns:
        Exit code from contract_check.py subprocess.
    """
    parser = argparse.ArgumentParser(
        prog="rddf contract-check",
        description="Diff Hub OpenAPI contract vs Spoke local implementation",
        add_help=False,
    )
    parser.add_argument("--hub", required=True,
                        help="Path to Hub OpenAPI YAML")
    parser.add_argument("--local", required=True,
                        help="Path to Spoke local implementation")
    parser.add_argument("--cache-file", default=None,
                        help="Path to contract-cache.jsonl")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute diff without writing cache")
    parser.add_argument("--help", action="store_true",
                        help="Show help")
    parsed, forwarded = parser.parse_known_args(args)

    project_root = Path(
        os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    )
    script = project_root / "skills" / "contract-check" / "scripts" / "contract_check.py"

    if parsed.help or "--help" in forwarded:
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            cwd=str(project_root),
        )
        return result.returncode

    cmd = [
        sys.executable, str(script),
        "--hub", parsed.hub,
        "--local", parsed.local,
    ]
    if parsed.cache_file:
        cmd += ["--cache-file", parsed.cache_file]
    if parsed.format:
        cmd += ["--format", parsed.format]
    if parsed.dry_run:
        cmd += ["--dry-run"]

    result = subprocess.run(cmd, cwd=str(project_root))
    return result.returncode


if __name__ == "__main__":
    sys.exit(cmd_contract_check(sys.argv[1:]))