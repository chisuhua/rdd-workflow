"""``rddf ac-verify`` subcommand handler.

Wraps the ac-verifier skill's bash entry point so users can invoke
AC verification from the unified ``rddf`` CLI tool::

    rddf ac-verify <change-name> [--dry-run] [--strict] [--skip]

Exit codes match ac_verifier.sh:
  0 = all ACs pass (or no AC section found)
  1 = at least one AC fail
  2 = skipped (no proposal.md, --skip, or SKIP_AC_VERIFICATION)
  3 = error

Env vars forwarded to subprocess (inherits from parent shell):
  STRICT_AC_GATE, SKIP_AC_VERIFICATION, AC_LLM_MOCK, AC_LLM_PROVIDER,
  AC_LLM_MODEL, AC_LLM_TIMEOUT, RDDF_PROJECT_ROOT
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def cmd_ac_verify(args: list[str]) -> int:
    """Handle ``rddf ac-verify``.

    Args:
        args: CLI args (change_name, [--dry-run] [--strict] [--skip])

    Returns:
        Exit code from ac_verifier.sh (0/1/2/3 per spec).
    """
    parser = argparse.ArgumentParser(
        prog="rddf ac-verify",
        description="Verify OpenSpec change acceptance criteria against committed code",
    )
    parser.add_argument("change_name", help="OpenSpec change name")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run without writing audit log")
    parser.add_argument("--strict", action="store_true",
                        help="Block on any AC fail")
    parser.add_argument("--skip", action="store_true",
                        help="Skip verification entirely")
    parser.add_argument("--project-root", type=Path, default=None,
                        help="Project root (default: $RDDF_PROJECT_ROOT or cwd)")
    parsed = parser.parse_args(args)

    # Resolve project root: explicit > env > cwd
    project_root = parsed.project_root or Path(
        os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    )

    # Locate ac_verifier.sh in the project root's skills directory
    script = project_root / "skills" / "ac-verifier" / "scripts" / "ac_verifier.sh"
    if not script.is_file():
        print(f"❌ ac-verifier skill not found at {script}", file=sys.stderr)
        return 3

    # Build flag list
    flags = []
    if parsed.dry_run:
        flags.append("--dry-run")
    if parsed.strict:
        flags.append("--strict")
    if parsed.skip:
        flags.append("--skip")

    # Invoke bash wrapper (inherits env vars including AC_LLM_*)
    result = subprocess.run(
        ["bash", str(script), parsed.change_name, *flags],
        cwd=str(project_root),
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(cmd_ac_verify(sys.argv[1:]))