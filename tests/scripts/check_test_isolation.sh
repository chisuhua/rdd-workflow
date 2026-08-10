#!/usr/bin/env bash
# tests/scripts/check_test_isolation.sh
#
# CI gate: ban test pollution anti-patterns in tests/unit/ and tests/integration/.
#
# Background: commit 88a839e (this repo, 2026-08-08) fixed 28 cascading test
# failures caused by tests/unit/test_dashboard_pending_filter.py::os.chdir(tmpdir)
# — when the temp dir was cleaned up, cwd pointed to a deleted path, and every
# subsequent test's monkeypatch.chdir() failed with FileNotFoundError.
#
# This script greps for known-polluting patterns and fails CI on detection.
# It mirrors the "Assertion quality gate" pattern (line 30 of test.yml).
#
# Usage:
#   bash tests/scripts/check_test_isolation.sh
# Exit code:
#   0 = no violations
#   1 = violations found (printed to stderr)
#
# Override (use sparingly):
#   ALLOW_TEST_POLLUTION=1 — skip the gate for emergency hotfixes
#
# Adding a new check: append a `check_<name>` function below, register it
# in main(), and document the rationale + commit example in this header.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
SELF_SCRIPT="tests/scripts/check_test_isolation.sh"

if [ "${ALLOW_TEST_POLLUTION:-0}" = "1" ]; then
  echo "⚠️  ALLOW_TEST_POLLUTION=1: skipping gate"
  exit 0
fi

EXIT_CODE=0

# Check 1: os.chdir() in tests
# Reason: temp dirs auto-clean after test → cwd points to deleted path →
# subsequent monkeypatch.chdir() fails with FileNotFoundError.
# Fix: use monkeypatch.chdir() or tmp_path fixture.
check_no_os_chdir() {
  local result
  result=$(grep -rn 'os\.chdir\b' tests/unit/ tests/integration/ 2>/dev/null \
    | grep -v "^${SELF_SCRIPT}:" || true)
  if [ -n "$result" ]; then
    echo "❌ os.chdir() in tests (pollutes cwd across test boundary):" >&2
    echo "$result" >&2
    echo "   Fix: use monkeypatch.chdir() or pytest tmp_path fixture." >&2
    return 1
  fi
  return 0
}

# Check 2: raw os.environ[KEY] = writes in tests
# Reason: if assert fails between write and del, env var leaks permanently
# and pollutes downstream tests that read os.environ.
# Fix: use monkeypatch.setenv() (auto-restore on teardown).
# Note: exclude lines that are asserting/reading (`assert os.environ[...]`),
# already wrapped (`monkeypatch`), or cleaned up (`del os.environ`).
check_no_raw_env_writes() {
  local result
  result=$(grep -rn 'os\.environ\[[^]]*\]\s*=' tests/unit/ tests/integration/ 2>/dev/null \
    | grep -v 'monkeypatch\|del os\.environ\|assert os\.environ' \
    | grep -v "^${SELF_SCRIPT}:" || true)
  if [ -n "$result" ]; then
    echo "❌ raw os.environ[KEY] = writes in tests (env var may leak on assert fail):" >&2
    echo "$result" >&2
    echo "   Fix: use monkeypatch.setenv('KEY', 'VALUE')." >&2
    return 1
  fi
  return 0
}

# Check 3: tempfile.mkdtemp() without cleanup in test setup
# Reason: leaks /tmp/tmpXXXX/ dirs across test runs; can also cause path
# resolution differences between tmp_path (resolves /tmp -> /private/tmp on
# macOS) and direct mkdtemp().
# Fix: use pytest tmp_path fixture in setup_method(self, tmp_path).
check_no_mkdtemp_without_cleanup() {
  local result
  result=$(grep -rn 'tempfile\.mkdtemp\b' tests/unit/ tests/integration/ 2>/dev/null \
    | grep -v "^${SELF_SCRIPT}:" || true)
  if [ -n "$result" ]; then
    echo "❌ tempfile.mkdtemp() in tests (no auto-cleanup):" >&2
    echo "$result" >&2
    echo "   Fix: use tmp_path fixture; assign self.tmpdir = str(tmp_path)." >&2
    return 1
  fi
  return 0
}

# Check 4: assert.*or True / assert True tautologies
# Reason: existing "Assertion quality gate" in CI test.yml. We mirror it
# here so devs can run this script locally before pushing.
check_no_assert_tautologies() {
  local result
  result=$(grep -rn 'assert.*or True\|assert True' tests/ 2>/dev/null \
    | grep -v "^${SELF_SCRIPT}:" || true)
  if [ -n "$result" ]; then
    echo "❌ tautological assertions in tests:" >&2
    echo "$result" >&2
    return 1
  fi
  return 0
}

main() {
  echo "🧪 Checking test isolation (anti-pollution)..."
  local checks=(check_no_os_chdir check_no_raw_env_writes
               check_no_mkdtemp_without_cleanup check_no_assert_tautologies)
  for check in "${checks[@]}"; do
    if ! "$check"; then
      EXIT_CODE=1
    fi
  done
  if [ "$EXIT_CODE" -eq 0 ]; then
    echo "✅ No test isolation violations"
  else
    echo "" >&2
    echo "❌ Test isolation gate FAILED" >&2
    echo "" >&2
    echo "Rationale: these patterns cause cross-test pollution that is hard to" >&2
    echo "debug. See commit 88a839e for the canonical fix example." >&2
    echo "Override (emergency): ALLOW_TEST_POLLUTION=1" >&2
  fi
  exit "$EXIT_CODE"
}

main "$@"