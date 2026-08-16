#!/usr/bin/env python3
"""rddf contract-check: validate Spoke impl against Hub contract.

Usage:
  rddf contract-check --hub <contract.yaml> --local <impl.py> [--dry-run] [--format json|markdown]

Exit codes:
  0 = compliant (No-Diff) or only Low/Medium severity
  1 = Breaking-Change detected (CI should block)
"""
import argparse
import os
import sys
import types
from pathlib import Path

_script_dir = os.path.dirname(os.path.abspath(__file__))
# skills/contract-check/scripts/ -> skills/contract-check/ -> skills/ -> repo root
_repo_root = Path(_script_dir).parent.parent.parent

# Replicate conftest.py module setup for skills._lib
if "skills._lib" not in sys.modules:
    _lib_mod = types.ModuleType("skills._lib")
    _lib_mod.__path__ = [str(_repo_root / "skills" / "_lib")]
    _lib_mod.__file__ = str(_repo_root / "skills" / "_lib" / "__init__.py")
    sys.modules["skills._lib"] = _lib_mod

from skills._lib.contract_diff import DiffEngine, format_output, Severity


def main() -> int:
    parser = argparse.ArgumentParser(description="Contract drift detection")
    parser.add_argument("--hub", required=True, help="Path to Hub OpenAPI contract")
    parser.add_argument("--local", required=True, help="Path to Spoke local impl")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--cache-file", default=".rddf/state/.contract-cache.json")
    args = parser.parse_args()

    if args.dry_run:
        print(f"[DRY-RUN] Would check Hub={args.hub} against Local={args.local}")
        return 0

    engine = DiffEngine()
    result = engine.run(args.hub, args.local)

    print(format_output(result, format=args.format))

    # Exit code: 1 if Breaking-Change, 0 otherwise
    if result.severity == Severity.BREAKING.value:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
