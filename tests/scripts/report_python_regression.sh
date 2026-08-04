#!/usr/bin/env bash
# Compare the current pytest failure set with tests/KNOWN_PYTHON_FAILURES.txt.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BASELINE="$REPO_ROOT/tests/KNOWN_PYTHON_FAILURES.txt"
TMP_DIR="$(mktemp -d -t rdd-python-known-failures-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

if [ ! -f "$BASELINE" ]; then
  printf '❌ baseline file is missing: %s\n' "$BASELINE" >&2
  exit 1
fi

set +e
(cd "$REPO_ROOT" && python3 -m pytest tests/unit/ tests/integration/ -q --tb=line) >"$TMP_DIR/pytest-output" 2>&1
pytest_status=$?
set -e

export pytest_status
python3 - "$BASELINE" "$TMP_DIR/pytest-output" <<'PY'
import os
import sys
from pathlib import Path
from tests.unit.python_regression import compare_failures, parse_failed_tests

baseline_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
output = output_path.read_text(encoding="utf-8")
actual = parse_failed_tests(output)
result = compare_failures(actual, baseline_path)

print(f"Pytest exit status: {os.environ.get('pytest_status', 'unknown')}")
print(f"已知失败: {result['known_count']}")
print(f"新增失败: {result['new_count']}")
print(f"基线中已修复: {result['stale_count']}")

if result["new_count"] > 0:
    print("新增失败明细:")
    for name in result["new"]:
        print(name)
    sys.exit(1)

if result["stale_count"] > 0:
    print("基线中已修复 (请运行 tests/scripts/refresh_python_known_failures.sh 刷新):")
    for name in result["stale"]:
        print(name)

print("✅ 0 新增失败")
PY
