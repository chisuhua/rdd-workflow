"""``rddf doctor`` subcommand handler.

Thin subprocess wrapper that delegates to the existing
``skills/rdd-doctor/scripts/doctor.sh`` entry point. Args are
forwarded verbatim; exit codes propagate transparently (0=pass,
1=fail, 2=bad input / skip, 3=error).

The ``doctor.sh`` script is a read-only diagnostic; this wrapper does
not modify any skill internals — only the routing layer.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def cmd_doctor(args: list[str]) -> int:
    """Handle ``rddf doctor``.

    Args:
        args: CLI args forwarded verbatim to ``doctor.sh``
            (e.g. ``["--category", "roadmap-refs"]`` or
            ``["--json"]`` or ``["--version"]``).

    Returns:
        Exit code from the ``doctor.sh`` subprocess.
    """
    project_root = Path(
        os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    )
    script = project_root / "skills" / "rdd-doctor" / "scripts" / "doctor.sh"

    if not script.is_file():
        print(
            f"❌ doctor: script not found at {script}",
            file=sys.stderr,
        )
        print(
            "   Hint: ensure you are in a rdd-workflow project root",
            file=sys.stderr,
        )
        return 3

    result = subprocess.run(
        ["bash", str(script), *args],
        cwd=str(project_root),
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(cmd_doctor(sys.argv[1:]))