#!/usr/bin/env bash
# Explicitly regenerate tests/KNOWN_PYTHON_FAILURES.txt from current pytest output.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BASELINE="$REPO_ROOT/tests/KNOWN_PYTHON_FAILURES.txt"
TMP_DIR="$(mktemp -d -t rdd-refresh-python-known-failures-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

set +e
(cd "$REPO_ROOT" && python3 -m pytest tests/unit/ tests/integration/ -q --tb=line) >"$TMP_DIR/pytest-output" 2>&1
pytest_status=$?
set -e

export pytest_status
BASELINE_PATH="$BASELINE" ACTUAL_PATH="$TMP_DIR/pytest-output" python3 - <<'PY'
import os
from pathlib import Path
from tests.unit.python_regression import _load_baseline, parse_failed_tests

baseline = Path(os.environ["BASELINE_PATH"])
actual = parse_failed_tests(Path(os.environ["ACTUAL_PATH"]).read_text(encoding="utf-8"))
comments = {}
for name in _load_baseline(baseline):
    comments[name] = "reason required"

lines = [f"# Known stable Python test failures. Reviewed baseline; new failures block CI."]
for name in actual:
    comment = comments.get(name, "reason required")
    lines.append(f"{name} # {comment}")

baseline.parent.mkdir(parents=True, exist_ok=True)
tmp = baseline.with_suffix(baseline.suffix + ".tmp")
tmp.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
tmp.replace(baseline)
print(f"✅ refreshed {len(actual)} known failures: {baseline}")
PY
