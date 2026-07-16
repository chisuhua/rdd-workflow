#!/usr/bin/env python3
"""Entry-point script for skills/_lib/plan_deps_candidates.sh::generate_deps_candidates.

Reads env var PROJECT_ROOT and delegates to plan_deps_candidates.generate_deps_candidates().
No bash string interpolation — all values flow through os.environ (Oracle C1 safe).
"""
import os
import sys


def main():
    project_root = os.environ.get("PROJECT_ROOT")
    if not project_root:
        print("ERROR: PROJECT_ROOT env var not set", file=sys.stderr)
        sys.exit(1)

    sys.path.insert(0, project_root)
    from skills._lib import plan_deps_candidates as pdc
    pdc.generate_deps_candidates(project_root)


if __name__ == "__main__":
    main()