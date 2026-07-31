#!/usr/bin/env python3
"""Entry-point script for skills/_lib/plan_deps_candidates.sh::generate_deps_candidates.

Reads env var PROJECT_ROOT and delegates to plan_deps_candidates.generate_deps_candidates().
No bash string interpolation - all values flow through os.environ (Oracle C1 safe).
"""
import importlib.util
import os
import sys


def _load_plan_deps_candidates(project_root):
    """Load plan_deps_candidates module via spec, raising ImportError on failure."""
    target = os.path.join(project_root, "skills", "guide-plan", "scripts", "plan_deps_candidates.py")
    spec = importlib.util.spec_from_file_location("plan_deps_candidates", target)
    if spec is None:
        raise ImportError(
            "Cannot load plan_deps_candidates from {}: spec_from_file_location returned None (file missing or unsupported)".format(target)
        )
    pdc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pdc)
    return pdc


def main():
    project_root = os.environ.get("PROJECT_ROOT")
    if not project_root:
        print("ERROR: PROJECT_ROOT env var not set", file=sys.stderr)
        sys.exit(1)

    sys.path.insert(0, project_root)
    pdc = _load_plan_deps_candidates(project_root)
    pdc.generate_deps_candidates(project_root)


if __name__ == "__main__":
    main()
