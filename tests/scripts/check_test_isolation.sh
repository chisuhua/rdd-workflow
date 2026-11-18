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
#
# Env (added by fix-script-project-root-anchoring):
#   RDDF_ISOLATION_SCAN_ROOTS — scan roots for check_no_unanchored_repo_paths
#     (colon-separated directories; default skills/rdd-builder/scripts).
#   RDDF_ISOLATION_ONLY — run exactly one check; its exit code then reflects
#     only that check. Needed because this repo has pre-existing violations in
#     the other checks, so a test cannot assert "the whole gate is green".
#   ALLOW_TEST_POLLUTION=1 — the bypass is no longer silent for the new
#     check: it still runs in report mode, prints "skipped:
#     check_no_unanchored_repo_paths" and writes .rddf/state/.bypass-audit.jsonl.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
SELF_SCRIPT="tests/scripts/check_test_isolation.sh"

# Write a bypass-audit entry (best effort — never fails the gate).
_audit_bypass() {
  local env_var="$1" reason="$2"
  if [ -f "$REPO_ROOT/_lib/bypass_audit.sh" ]; then
    # shellcheck source=../../_lib/bypass_audit.sh
    source "$REPO_ROOT/_lib/bypass_audit.sh" 2>/dev/null || true
    if declare -f audit_bypass_log >/dev/null 2>&1; then
      audit_bypass_log "$env_var" "$reason" "" "test-isolation-gate" || true
    fi
  fi
}

if [ "${ALLOW_TEST_POLLUTION:-0}" = "1" ]; then
  # The bypass is NOT silent for the new check: it still runs (in report mode),
  # prints what was skipped, and leaves an audit entry. Otherwise a permanent
  # bypass would be indistinguishable from "the repo is clean".
  if [ "${RDDF_ISOLATION_ONLY:-}" = "check_no_unanchored_repo_paths" ]; then
    :
  else
    echo "⚠️  ALLOW_TEST_POLLUTION=1: skipping gate"
    check_no_unanchored_repo_paths && {
      echo "skipped: check_no_unanchored_repo_paths (bypass)"
      exit 0
    }
    echo "skipped: check_no_unanchored_repo_paths (bypass, violations below)"
  fi
  _audit_bypass "ALLOW_TEST_POLLUTION" "${RDDF_ISOLATION_BYPASS_REASON:-no reason given}"
  echo "skipped: check_no_unanchored_repo_paths (bypass)"
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

# Check 5: 未锚定项目根的仓库相对路径
# Reason: phase 脚本的 IO 落点必须由 $PROJECT_ROOT 决定。cwd 相对写法在生产里
# 碰巧正确（cwd == 项目根），只在「cwd ≠ PROJECT_ROOT」时暴露 —— 而那时它会写进
# **调用方所在的仓库**（实测：真仓被塞进 openspec/<name> 分支 + 整树检出，
# 两次被当成负载 flake 放过）。判定必须按 token 而非按行：行级会让
# `cp "openspec/x" "$PROJECT_ROOT/openspec/x"` 整行放行 ⇒ 门空转。
#
# Env:
#   RDDF_ISOLATION_SCAN_ROOTS  扫描根（目录，冒号分隔）。默认 skills/rdd-builder/scripts
#   RDDF_ISOLATION_ONLY        只跑这一个 check（退出码只反映它）—— 本仓的其它 check
#                              已有历史违规，不隔离就断言不了本 check 自己的退出码
check_no_unanchored_repo_paths() {
  local result
  result="$(RDDF_ISOLATION_SCAN_ROOTS="${RDDF_ISOLATION_SCAN_ROOTS:-skills/rdd-builder/scripts}" \
            python3 - <<'PYEOF'
import os
import re
import sys

ROOTS = [r for r in os.environ.get("RDDF_ISOLATION_SCAN_ROOTS", "").split(":") if r]

# 锚定前缀（枚举，不写「等」）：出现其中任一 ⇒ 该 token 已锚定到项目根。
ANCHORS = (
    "$PROJECT_ROOT", "$project_root", "$RDDF_PROJECT_ROOT", "$REPO_ROOT",
    "$main_root", "$TASKS_ROOT", "$WT_PATH", "$EXEC_DIR", "$root",
    "$BOOTSTRAP_REPO_ROOT", "$(git rev-parse --show-toplevel)",
)

# 只匹配「这个字面量**就是**仓库相对路径」的形态：引号紧跟着 openspec/changes/
# 或 .rddf/。含路径的**消息文本**（"plan file missing at .rddf/plans/x"）不匹配
# —— 它不是路径用法。裸 `openspec/` 是 git ref（openspec/<name>）的形态，同样不匹配。
TOKEN_RE = re.compile(r"""["']((?:openspec/changes/|\.rddf/)[^"']*)["']""")
EXEMPT_RE = re.compile(r"#\s*isolation-ok:\s*(\S.*)")

violations = []
for root in ROOTS:
    if not os.path.isdir(root):
        continue
    for dirpath, _dirs, files in os.walk(root):
        for name in sorted(files):
            if not name.endswith((".sh", ".py")):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    lines = fh.readlines()
            except OSError:
                continue
            for lineno, line in enumerate(lines, 1):
                if line.lstrip().startswith("#"):
                    continue                       # 注释行不算
                exempt = EXEMPT_RE.search(line)
                if exempt and len(exempt.group(1).strip()) >= 10:
                    continue                       # 显式豁免（理由 ≥10 字）
                for tok in TOKEN_RE.findall(line):
                    if any(a in tok for a in ANCHORS):
                        continue                   # 已锚定
                    violations.append("%s:%d: %s" % (path, lineno, tok))
                    break                         # 一行只报一次
for v in violations:
    print(v)
sys.exit(1 if violations else 0)
PYEOF
)"
  if [ -n "$result" ]; then
    echo "❌ 未锚定项目根的仓库相对路径（cwd 相对 ⇒ 会写进调用方所在的仓库）:" >&2
    echo "$result" >&2
    return 1
  fi
  return 0
}

main() {
  echo "🧪 Checking test isolation (anti-pollution)..."
  local checks=(check_no_os_chdir check_no_raw_env_writes
               check_no_mkdtemp_without_cleanup check_no_assert_tautologies
               check_no_unanchored_repo_paths)
  # Single-check mode: run exactly one check so its own exit code can be
  # asserted (the other checks have pre-existing violations in this repo).
  if [ -n "${RDDF_ISOLATION_ONLY:-}" ]; then
    local only="$RDDF_ISOLATION_ONLY"
    local found=0
    for check in "${checks[@]}"; do
      [ "$check" = "$only" ] || continue
      found=1
      break
    done
    if [ "$found" -ne 1 ]; then
      echo "❌ unknown check for RDDF_ISOLATION_ONLY: $only" >&2
      echo "   available: ${checks[*]}" >&2
      exit 2
    fi
    "$only"
    exit "$?"
  fi
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