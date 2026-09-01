#!/usr/bin/env bash
# test.sh — unified test runner for rdd-workflow
#
# Modes (pick one):
#   ./test.sh --quick                快速: smoke + pytest unit (~45s)
#   ./test.sh --full                 全量: bats recursive + pytest unit + integration (~8min)
#   ./test.sh --bats                 只跑 bats recursive
#   ./test.sh --python               pytest unit + integration
#   ./test.sh --unit                 只跑 pytest unit
#   ./test.sh --integration          只跑 pytest integration
#   ./test.sh <file.bats|file.py>    跑单个测试文件
#
# Options (compose with any mode):
#   --regression                     跑 bats 时用 report_regression.sh (对比 KNOWN_FAILURES baseline)
#   --stop-on-failure, -x            失败立即停止 (默认继续跑以拿到完整图)
#   --no-color                       禁用颜色 (默认: TTY 时自动启用)
#   --color                          强制启用颜色 (覆盖 TTY 检测)
#
# Exit code:
#   0   = 全绿
#   1   = 有失败 (任何 step)
#   2   = 参数错 / 文件不存在
#   127 = 缺少依赖 (bats / python3)
#
# See AGENTS.md "快速命令" for usage examples.

set -uo pipefail

cd "$(dirname "$0")"

# ── Defaults ──────────────────────────────────────────────────────────
WITH_COLOR=auto         # auto | always | never
STOP_ON_FAILURE=0
WITH_REGRESSION=0
MAX_DURATION=0          # (add-regression-gate-timeout-protection): 0 = no timeout
FAILED=0
MODE=""
POSITIONAL=()

# ── Color setup ────────────────────────────────────────────────────────
setup_colors() {
  if [ "$WITH_COLOR" = "never" ]; then
    RED=''; GREEN=''; YELLOW=''; CYAN=''; NC=''
  elif [ "$WITH_COLOR" = "always" ] || { [ "$WITH_COLOR" = "auto" ] && [ -t 1 ]; }; then
    RED=$'\033[0;31m'
    GREEN=$'\033[0;32m'
    YELLOW=$'\033[0;33m'
    CYAN=$'\033[0;36m'
    NC=$'\033[0m'
  else
    RED=''; GREEN=''; YELLOW=''; CYAN=''; NC=''
  fi
}

# ── Preflight ──────────────────────────────────────────────────────────
preflight() {
  local missing=()
  for cmd in "$@"; do
    command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    echo "${RED}❌ 缺少依赖: ${missing[*]}${NC}" >&2
    echo "   安装: bats-core (≥1.5) + python3 (≥3.11)" >&2
    exit 127
  fi
}

# ── Step runner ────────────────────────────────────────────────────────
#   run_step "<label>" <cmd...>
# - Increments FAILED counter on non-zero exit
# - Honors STOP_ON_FAILURE (exit immediately on first failure)
run_step() {
  local label="$1"; shift
  echo ""
  echo "${CYAN}=== ${label} ===${NC}"
  local start=$SECONDS
  if "$@"; then
    echo "${GREEN}✅ ${label} OK ($(( SECONDS - start ))s)${NC}"
  else
    local rc=$?
    echo "${RED}❌ ${label} FAILED (exit=$rc, $(( SECONDS - start ))s)${NC}"
    FAILED=$((FAILED + 1))
    if [ "$STOP_ON_FAILURE" = "1" ]; then
      echo "${YELLOW}⛔ --stop-on-failure: 退出${NC}"
      exit 1
    fi
  fi
}

# ── Summary ────────────────────────────────────────────────────────────
summary() {
  echo ""
  echo "───────────────────────────────────"
  if [ "$FAILED" -eq 0 ]; then
    echo "${GREEN}✅ ALL PASSED${NC}"
    return 0
  else
    echo "${RED}❌ FAILURES DETECTED (${FAILED} step(s) failed)${NC}"
    return 1
  fi
}

# ── Step recipes ───────────────────────────────────────────────────────
run_bats_smoke() {
  run_step "bats smoke" bats tests/smoke.bats "$@"
}

run_bats_recursive() {
  local bats_cmd
  if [ "$WITH_REGRESSION" = "1" ]; then
    bats_cmd="bash tests/scripts/report_regression.sh"
    if [ "$MAX_DURATION" -gt 0 ]; then
      echo "  bats (with --max-duration=$MAX_DURATION s)"
      timeout --kill-after=10 "$MAX_DURATION" bash -c "$bats_cmd"
      local rc=$?
      if [ $rc -eq 124 ]; then
        echo "  ⏱️ bats timed out after ${MAX_DURATION}s" >&2
        FAILED=1
      fi
      return $rc
    fi
    run_step "bats regression (baseline-aware)" \
      bash tests/scripts/report_regression.sh
  else
    if [ "$MAX_DURATION" -gt 0 ]; then
      echo "  bats (with --max-duration=$MAX_DURATION s)"
      timeout --kill-after=10 "$MAX_DURATION" bats tests/ --recursive "$@"
      local rc=$?
      if [ $rc -eq 124 ]; then
        echo "  ⏱️ bats timed out after ${MAX_DURATION}s" >&2
        FAILED=1
      fi
      return $rc
    fi
    run_step "bats recursive" bats tests/ --recursive "$@"
  fi
}

run_pytest_unit() {
  run_step "pytest unit" python3 -m pytest tests/unit/ -q --tb=line "$@"
}

run_pytest_integration() {
  run_step "pytest integration" python3 -m pytest tests/integration/ -q --tb=line "$@"
}

# ── Single-file invocation ─────────────────────────────────────────────
run_single_file() {
  local file="$1"
  if [ ! -f "$file" ]; then
    echo "${RED}❌ 文件不存在: $file${NC}" >&2
    exit 2
  fi
  case "$file" in
    *.bats)
      preflight bats
      run_step "bats $file" bats "$file"
      ;;
    *.py)
      preflight python3
      run_step "pytest $file" python3 -m pytest "$file" -q --tb=line
      ;;
    *)
      echo "${RED}❌ 不支持的文件类型: $file (仅 .bats 或 .py)${NC}" >&2
      exit 2
      ;;
  esac
}

# ── Help ───────────────────────────────────────────────────────────────
print_help() {
  cat <<'EOF'
test.sh — unified test runner for rdd-workflow

Modes (pick one):
  --quick, -q            快速: smoke + pytest unit (~45s)
  --full, -f             全量: bats recursive + pytest unit + integration (~8min)
  --bats, -b             只跑 bats recursive
  --python, -p           pytest unit + integration
  --unit                 只跑 pytest unit
  --integration          只跑 pytest integration

Options (compose with any mode):
  --regression           bats 用 report_regression.sh 对比 KNOWN_FAILURES baseline
  --stop-on-failure, -x  失败立即停止 (默认继续跑拿完整图)
  --no-color             禁用颜色 (默认: TTY 时自动启用)
  --color                强制启用颜色 (覆盖 TTY 检测)
  --max-duration=N      (add-regression-gate-timeout-protection) 超时保护—— bats 超过 N 秒则优雅退出并保存部分结果 (0 = 无限)

Single file:
  ./test.sh <file.bats>     跑单个 bats 文件
  ./test.sh <file.py>       跑单个 pytest 文件

  --help, -h                此帮助

Exit codes: 0=全绿, 1=有失败, 2=参数错, 127=缺依赖
EOF
}

# ── Argument parsing ───────────────────────────────────────────────────
# IMPORTANT: must NOT be invoked via `$(parse_args ...)` — `exit` inside a
# command substitution only kills the subshell. Run directly so `exit 0` and
# `exit 2` actually terminate the runner. (Bug fixed 2026-08-06.)
parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --quick|-q)            MODE="quick" ;;
      --full|-f)             MODE="full" ;;
      --bats|-b)             MODE="bats" ;;
      --python|-p)           MODE="python" ;;
      --unit)                MODE="unit" ;;
      --integration)         MODE="integration" ;;
      --regression)          WITH_REGRESSION=1 ;;
      --stop-on-failure|-x)  STOP_ON_FAILURE=1 ;;
      --no-color)            WITH_COLOR=never ;;
      --color)               WITH_COLOR=always ;;
      --max-duration=*)  MAX_DURATION="${1#--max-duration=}" ;;
      --max-duration)
        if [[ "$2" =~ ^[0-9]+$ ]]; then MAX_DURATION="$2"; else echo "❌ --max-duration needs integer seconds" >&2; exit 2; fi
        shift ;;
      --help|-h)             print_help; exit 0 ;;
      --*)                   setup_colors
                              echo "${RED}❌ 未知参数: $1${NC}" >&2
                              echo "   运行 ./test.sh --help 查看用法" >&2
                              exit 2 ;;
      *)                     POSITIONAL+=("$1") ;;
    esac
    shift
  done
}

# ── Main dispatch ──────────────────────────────────────────────────────
main() {
  parse_args "$@"
  setup_colors

  # Single-file invocation (any positional arg)
  if [ "${#POSITIONAL[@]}" -gt 0 ]; then
    for f in "${POSITIONAL[@]}"; do
      run_single_file "$f"
    done
    summary
    exit $?
  fi

  # No mode → show help
  if [ -z "$MODE" ]; then
    print_help
    exit 0
  fi

  # Mode dispatch (--full no longer runs smoke twice — recursive includes it)
  case "$MODE" in
    quick)
      preflight bats python3
      run_bats_smoke
      run_pytest_unit
      ;;
    full)
      preflight bats python3
      run_bats_recursive   # includes tests/smoke.bats
      run_pytest_unit
      run_pytest_integration
      ;;
    bats)
      preflight bats
      run_bats_recursive
      ;;
    python)
      preflight python3
      run_pytest_unit
      run_pytest_integration
      ;;
    unit)
      preflight python3
      run_pytest_unit
      ;;
    integration)
      preflight python3
      run_pytest_integration
      ;;
  esac

  summary
}

main "$@"