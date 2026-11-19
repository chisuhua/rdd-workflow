#!/usr/bin/env bash
# test.sh — unified test runner for rdd-workflow
#
# Modes (pick one):
#   ./test.sh --gates                只跑「本地门」(4 道静态门, ~10-20s) — 见下
#   ./test.sh --quick                快速: 门(隔离+ruff) + smoke + pytest unit (~2min 实测 2026-11-19)
#   ./test.sh --full                 全量: 门(4 道) + bats recursive + pytest unit + integration (~15min 实测 2026-11-19)
#   ./test.sh --bats                 只跑 bats recursive
#   ./test.sh --python               pytest unit + integration
#   ./test.sh --unit                 只跑 pytest unit
#   ./test.sh --integration          只跑 pytest integration
#   ./test.sh --e2e-smoke            只跑 A 层 e2e (tests/e2e/script/) — CI 必跑
#   ./test.sh --e2e-agent            只跑 C 层 e2e (tests/e2e/agent/) — nightly 必跑
#   ./test.sh --e2e-all              A + C 全跑 (本地选)
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
# 本地门覆盖 CI 的哪几道（口径必须与 .github/workflows/test.yml 一致）:
#   ✅ 测试隔离门（含 check #4 断言质量检查）→ tests/scripts/check_test_isolation.sh
#   ✅ Ruff lint check           → python3 -m ruff check skills/_lib/
#   ✅ Mypy strict type check    → python3 -m mypy --strict skills/_lib/core/
#   ✅ rdd-doctor structural gate→ doctor.sh --gate structural (10 categories)
#   ❌ 未镜像的门见下方 NOT_MIRRORED —— 那份清单是「本地还差哪些门」的诚实台账,
#      由 tests/unit/test_ci_local_mirror.py 守住（镜像它, 或把它写进 NOT_MIRRORED）。
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

# ── NOT_MIRRORED：本地门故意不镜像的 CI step ───────────────────────────
# 「本地门镜像 CI」不等于「本地门 = CI」：下面这些 step 需要 CI 特有的环境
# （Hub token / 浅克隆基线 / e2e 运行时），本地镜像它们只会制造假红。
# 每加一项的理由见 tests/unit/test_ci_local_mirror.py 的注释。
NOT_MIRRORED=(
  "Install Python deps"
  "Install bats"
  # 测试套件的环境依赖（CI runner 是白板机器），本地开发机本来就有
  "Install openspec CLI (unit-test prerequisite)"
  "Configure git identity (temp-repo fixtures commit)"
  "Make repo importable for subprocesses (parity with install.sh .pth)"
  # CI 把 bats 分成两半：integration/ 走 baseline 门（KNOWN_FAILURES 里有已接受的失败），
  # 其余裸跑。本地 --bats 是一次性裸跑全部 ⇒ 两者不是同一条命令。
  "Bats smoke (non-integration scope; integration runs under the baseline gate)"
  "Put repo CLI on PATH (bats suites call rddf)"
  "Arch quality gate (strict mode)"
  "Change alignment gate (strict mode)"
  "Spec validation gate (baseline + delta targets)"
  "rdd-doctor advisory gate (4 categories, non-blocking)"
  # 逻辑由 tests/integration/test_regression_baseline_shrink_only.bats 镜像；
  # 基线取法依赖 git 历史（HEAD~1 / origin/master），本地工作树没有 CI 的
  # 「这次 push 之前」语义 ⇒ 镜像它只会制造假红/假绿。
  "KNOWN_UNEVALUATED.txt shrink-only enforcement"
  "KNOWN_FAILURES.txt shrink-only enforcement"
  "Regression-gate bypass must not be set in CI"
)

# ── 工具版本检查（警告，不硬失败）────────────────────────────────────────
# 口径写在 requirements.txt（钉版）与 pyproject.toml（规则集）里；这里读同一份
# requirements.txt，避免「门说该装哪个版本」和「CI 装哪个版本」两处各写一遍。
# 不符时只警告：门的作用是给信号，不是当门卫（硬失败会把「跑一下门」变成
# 「先升级环境」，使用率会掉）。
_check_tool_version() {
  local tool="$1" module="$2"
  local pinned actual
  pinned=$(grep -E "^${tool}==" requirements.txt 2>/dev/null | head -1 | cut -d= -f3-)
  [ -n "$pinned" ] && pinned="${pinned%%;*}"
  actual=$(python3 -m "$module" --version 2>/dev/null | head -1 | awk '{print $NF}')
  if [ -z "$actual" ]; then
    echo "${YELLOW}⚠️  ${tool} 版本未知（装在 python3 -m ${module} 下）${NC}" >&2
    return 0
  fi
  if [ -n "$pinned" ]; then
    # pinned 形如 ">=0.15,<0.16" —— 只做「实际版本是否落在区间内」的粗判：
    # 主版本必须相同，且次版本 >= 下界。
    local want_major want_min
    want_major=$(echo "$pinned" | sed -nE 's/.*>=([0-9]+)\..*/\1/p')
    want_min=$(echo "$pinned" | sed -nE 's/.*>=[0-9]+\.([0-9]+).*/\1/p')
    local got_major got_min
    got_major=$(echo "$actual" | sed -nE 's/^([0-9]+).*/\1/p')
    got_min=$(echo "$actual" | sed -nE 's/^[0-9]+\.([0-9]+).*/\1/p')
    if [ -n "$want_major" ] && [ "$got_major" != "$want_major" ]; then
      echo "${YELLOW}⚠️  ${tool} 版本与 requirements.txt 不符: pinned ${pinned}, actual ${actual}${NC}" >&2
      echo "   安装: pip install -r requirements.txt   （门仍会用当前版本跑）" >&2
    elif [ -n "$want_min" ] && [ -n "$got_min" ] && [ "$got_min" -lt "$want_min" ]; then
      echo "${YELLOW}⚠️  ${tool} 版本与 requirements.txt 不符: pinned ${pinned}, actual ${actual}${NC}" >&2
      echo "   安装: pip install -r requirements.txt   （门仍会用当前版本跑）" >&2
    fi
  fi
}

# 逃生阀：与仓库既有旁路治理一致（_lib/bypass_audit.sh::audit_bypass_log），
# 不是静默 env skip —— 每次使用都留审计记录。
_local_gates_bypass() {
  if [ "${SKIP_LOCAL_GATES:-0}" = "1" ]; then
    if [ -f "_lib/bypass_audit.sh" ]; then
      # shellcheck source=/dev/null
      source "_lib/bypass_audit.sh"
      audit_bypass_log "SKIP_LOCAL_GATES" "${SKIP_LOCAL_GATES_REASON:-no reason given}" "" "local-gates" || true
    fi
    echo "${YELLOW}⚠️  SKIP_LOCAL_GATES=1 ⇒ 跳过本地门（已记 bypass 审计）${NC}" >&2
    return 0
  fi
  return 1
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

# Test isolation gate (anti-pollution) — the SAME script CI runs
# (.github/workflows/test.yml, step "Test isolation gate (anti-pollution)").
# It used to run ONLY in CI: ./test.sh never called it ⇒ a violation could
# turn the CI gate red while the local full gate stayed green (that is
# exactly how 9 pre-existing violations survived: see
# .rddf/plans/quick-fix-test-isolation-gate-red.md).
run_test_isolation_gate() {
  run_step "test isolation gate (anti-pollution)" \
    bash tests/scripts/check_test_isolation.sh
}

# ruff / mypy 的命令与 CI 逐字一致（CI 用 `python3 -m ...`，这里也用，
# 绑定到跑 pytest 的同一个解释器，免疫 PATH 上 pipx/uv/系统版的影子）。
run_ruff_gate() {
  _check_tool_version ruff ruff
  run_step "ruff lint (skills/_lib/)" \
    python3 -m ruff check skills/_lib/
}

run_mypy_gate() {
  _check_tool_version mypy mypy
  run_step "mypy strict (skills/_lib/core/)" \
    python3 -m mypy --strict skills/_lib/core/
}

# doctor 的门落在「被归档的那个仓」而不是调用方的 cwd —— 显式钉住项目根。
# ⚠ 这道门镜像 CI，但 findings 依赖**本地工作状态**（.rddf/ 下的本地状态），
#   所以「本地红、CI 绿」在这道门上不一定是 flake。
run_doctor_structural_gate() {
  run_step "rdd-doctor structural gate (10 categories)" \
    env RDDF_PROJECT_ROOT="$(pwd)" bash skills/rdd-doctor/scripts/doctor.sh --gate structural
}

# 本地门：4 道静态门，一次跑完（~10-20s）。这是「本地绿 ⇒ 可以推」的最小集。
run_local_gates() {
  if _local_gates_bypass; then
    return 0
  fi
  run_test_isolation_gate
  run_ruff_gate
  run_mypy_gate
  run_doctor_structural_gate
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
        FAILED=$((FAILED + 1))
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
        FAILED=$((FAILED + 1))
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

run_bats_dir() {
  local dir="$1"
  if [ -d "$dir" ]; then
    run_step "bats $dir" bats "$dir"
  else
    echo "${YELLOW}SKIP: $dir not found (will be created in later phase)${NC}"
    return 0
  fi
}

run_e2e_smoke() {
  preflight bats
  run_bats_dir "tests/e2e/script/"
}

run_e2e_agent() {
  if [ "${RDDF_AGENT_E2E:-0}" != "1" ]; then
    echo "${YELLOW}SKIP: C-layer e2e agent (set RDDF_AGENT_E2E=1 to enable)${NC}"
    echo "${YELLOW}Hint: nightly cron sets this automatically${NC}"
    return 0
  fi
  preflight bats
  run_bats_dir "tests/e2e/agent/"
}

run_e2e_external() {
  preflight git bats
  local repo_root
  repo_root="$(cd "$(dirname "$0")" && pwd)"
  run_step "external testbed (chisuhua/rdd-workflow-e2e)" \
    bash "$repo_root/tests/e2e/run_external_testbed.sh" "$@"
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
  --gates, -g            只跑「本地门」: 隔离门 + ruff + mypy strict + doctor structural (~10-20s)
  --quick, -q            快速: 门(隔离+ruff) + smoke + pytest unit (~2min 实测 2026-11-19)
  --full, -f             全量: 门(4 道) + bats recursive + pytest unit + integration (~15min 实测 2026-11-19)
  --bats, -b             只跑 bats recursive
  --python, -p           pytest unit + integration
  --unit                 只跑 pytest unit
  --integration          只跑 pytest integration
  --e2e-smoke            只跑 A 层 e2e (tests/e2e/script/) — CI 必跑
  --e2e-agent            只跑 C 层 e2e (tests/e2e/agent/) — nightly 必跑 (需 RDDF_AGENT_E2E=1)
  --e2e-all              A + C 全跑 (本地选)
  --external-e2e         跑外部 testbed (chisuhua/rdd-workflow-e2e)；auto-clone 到 $RDD_E2E_DIR

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

本地门覆盖 CI 的哪几道（口径与 .github/workflows/test.yml 一致）:
  ✅ 测试隔离门（含 check #4 断言质量检查）→ tests/scripts/check_test_isolation.sh
  ✅ Ruff lint check          → python3 -m ruff check skills/_lib/
  ✅ Mypy strict type check   → python3 -m mypy --strict skills/_lib/core/
  ✅ rdd-doctor structural    → doctor.sh --gate structural
  ❌ 故意不镜像的 CI step 见 test.sh 里的 NOT_MIRRORED（tests/unit/test_ci_local_mirror.py 守住）

Escape hatch: SKIP_LOCAL_GATES=1 跳过本地门（会写 bypass 审计，不是静默跳过）

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
      --gates|-g)            MODE="gates" ;;
      --quick|-q)            MODE="quick" ;;
      --full|-f)             MODE="full" ;;
      --bats|-b)             MODE="bats" ;;
      --python|-p)           MODE="python" ;;
      --unit)                MODE="unit" ;;
      --integration)         MODE="integration" ;;
      --e2e-smoke)           MODE="e2e-smoke" ;;
      --e2e-agent)           MODE="e2e-agent" ;;
      --e2e-all)             MODE="e2e-all" ;;
      --external-e2e)        MODE="external-e2e" ;;
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
    gates)
      preflight python3
      run_local_gates
      ;;
    quick)
      preflight bats python3
      # quick 只跑「不依赖 .rddf/ 本地状态」的门：隔离门 + ruff。
      # mypy / doctor 留在 --full 与 --gates（mypy 冷缓存 8-15s 且这道门目前
      # 只覆盖 0-def shim；doctor 的 findings 依赖本地工作状态）。
      run_test_isolation_gate
      run_ruff_gate
      run_bats_smoke
      run_pytest_unit
      ;;
    full)
      preflight bats python3
      run_local_gates
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
    e2e-smoke)
      run_e2e_smoke
      ;;
    e2e-agent)
      run_e2e_agent
      ;;
    e2e-all)
      run_e2e_smoke
      run_e2e_agent
      ;;
    external-e2e)
      run_e2e_external
      ;;
  esac

  summary
}

main "$@"