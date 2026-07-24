#!/usr/bin/env bash
# test.sh — unified test runner for rdd-workflow
#
# Usage:
#   ./test.sh --quick     # 快速: bats smoke + pytest unit (~30s)
#   ./test.sh --full      # 全量: bats recursive + pytest unit+integration (~3min)
#   ./test.sh --bats      # 只跑 bats 全量
#   ./test.sh --python    # 只跑 pytest (unit + integration)
#   ./test.sh --help      # 此帮助
#
# Exit code: 0 = 全绿, 非 0 = 有失败 (最后失败的命令的 exit code)

set -uo pipefail

cd "$(dirname "$0")"

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[0;33m'
NC=$'\033[0m'

FAILED=0

run_step() {
  local label="$1"; shift
  echo ""
  echo "=== ${label} ==="
  local start=$SECONDS
  if "$@"; then
    echo "${GREEN}✅ ${label} OK ($(( SECONDS - start ))s)${NC}"
  else
    local rc=$?
    echo "${RED}❌ ${label} FAILED (exit=$rc, $(( SECONDS - start ))s)${NC}"
    FAILED=$rc
  fi
}

summary() {
  echo ""
  echo "───────────────────────────────────"
  if [ "$FAILED" -eq 0 ]; then
    echo "${GREEN}✅ ALL PASSED${NC}"
  else
    echo "${RED}❌ FAILURES DETECTED (last exit=$FAILED)${NC}"
  fi
  return "$FAILED"
}

case "${1:-}" in
  --quick|-q)
    echo "${YELLOW}🚀 QUICK mode: smoke + unit${NC}"
    run_step "bats smoke"        bats tests/smoke.bats
    run_step "pytest unit"       python3 -m pytest tests/unit/ -q --tb=line
    summary
    ;;
  --full|-f)
    echo "${YELLOW}🚀 FULL mode: bats recursive + pytest all${NC}"
    run_step "bats smoke"        bats tests/smoke.bats
    run_step "bats recursive"    bats tests/ --recursive
    run_step "pytest unit"       python3 -m pytest tests/unit/ -q --tb=line
    run_step "pytest integration" python3 -m pytest tests/integration/ -q --tb=line
    summary
    ;;
  --bats|-b)
    run_step "bats recursive"    bats tests/ --recursive
    summary
    ;;
  --python|-p)
    run_step "pytest unit"       python3 -m pytest tests/unit/ -q --tb=line
    run_step "pytest integration" python3 -m pytest tests/integration/ -q --tb=line
    summary
    ;;
  --help|-h|"")
    cat <<'EOF'
test.sh — unified test runner

  ./test.sh --quick    快速: smoke + unit (~30s)
  ./test.sh --full     全量: 所有 bats + 所有 pytest (~3min)
  ./test.sh --bats     只跑 bats 全量
  ./test.sh --python   只跑 pytest
  ./test.sh --help     此帮助
EOF
    exit 0
    ;;
  *)
    echo "${RED}未知参数: $1${NC}" >&2
    echo "运行 ./test.sh --help 查看用法" >&2
    exit 2
    ;;
esac