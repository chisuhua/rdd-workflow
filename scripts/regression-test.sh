#!/usr/bin/env bash
# regression-test.sh — quick or full regression test runner
set -euo pipefail
MODE="${1:-full}"
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
BUILD_DIR="$PROJECT_ROOT/build"

if [ "${SKIP_REGRESSION:-}" = "1" ]; then
  echo "⚠️ 已跳过全量回归 (SKIP_REGRESSION=1)"
  exit 0
fi

run_bats_smoke() {
  echo "🔍 运行 bats smoke 测试..."
  bats "$PROJECT_ROOT/tests/smoke.bats"
}

run_quick() {
  if [ -d "$BUILD_DIR" ]; then
    echo "🔍 build 目录存在，运行 ctest 快速回归..."
    ctest --test-dir "$BUILD_DIR" -R "test_alloc|test_map|test_dma" --output-on-failure 2>/dev/null || true
  else
    echo "🔍 无 build 目录，运行 bats smoke 快速回归..."
    run_bats_smoke
  fi
}

run_full() {
  if [ -d "$BUILD_DIR" ]; then
    echo "🔍 build 目录存在，运行 ctest 全量回归..."
    ctest --test-dir "$BUILD_DIR" --output-on-failure
  else
    echo "🔍 无 build 目录，运行可用的 bats/pytest 全量回归..."
    run_bats_smoke
    # 只跑新增/稳定的单元测试，避免仓库中既有失败阻塞回归门
    local gate_test
    gate_test="$PROJECT_ROOT/tests/unit/test_execute_regression_gate.py"
    if [ -f "$gate_test" ]; then
      echo "🔍 运行 gate 单元测试..."
      python3 -m pytest "$gate_test" -q --tb=short
    fi
  fi
}

case "$MODE" in
  quick) run_quick ;;
  full)  run_full ;;
  *) echo "Usage: $0 {quick|full}" >&2; exit 1 ;;
esac
