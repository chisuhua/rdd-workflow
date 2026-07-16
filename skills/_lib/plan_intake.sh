#!/usr/bin/env bash
# skills/_lib/plan_intake.sh — extracted from guide-plan.md L95-L175
# Exports: run_plan_intake()
#
# Behavior preserved:
# - openspec CLI detection (returns 1 if missing)
# - git workspace state check
# - Current branch display
# - HARD-GATE on .arch-handoff.json existence (returns 1 if missing)
# - Reads ADR_DIR, ROADMAP_PATH, ADR_PATTERN, ARCHITECTURE_DIR via jq from handoff
# - Falls back to defaults if jq missing or handoff fields absent
# - Reads ADR_IDS + CURRENT_PHASE from handoff via python3 (with $ARCH_HANDOFF via env-var)
# - Counts active openspec changes
# - Prints summary

run_plan_intake() {
  local PROJECT_ROOT
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  export PROJECT_ROOT

  echo "🔍 Plan 阶段环境检查..."
  echo ""

  # 1. openspec CLI 检测
  local OPENSPEC_PATH=""
  for p in $(command -v openspec 2>/dev/null) /home/ubuntu/.npm-global/bin/openspec /usr/local/bin/openspec /opt/homebrew/bin/openspec; do
    [ -x "$p" ] && OPENSPEC_PATH="$p" && break
  done
  if [ -z "$OPENSPEC_PATH" ]; then
      echo "❌ openspec CLI 未找到"
      echo "   请安装: npm install -g openspec-cli"
      return 1
  fi
  local OPENSPEC_VER="$("$OPENSPEC_PATH" --version 2>/dev/null || echo "?")"
  echo "✅ openspec CLI: $OPENSPEC_VER"

  # 2. git 状态
  local GIT_CLEAN
  GIT_CLEAN=$(git status --porcelain | grep -c . || true)
  if [ "$GIT_CLEAN" -eq 0 ]; then
      echo "✅ git 工作区干净"
  else
      echo "⚠️  git 工作区有 $GIT_CLEAN 个未跟踪/修改文件"
  fi

  # 3. 当前分支
  local CURRENT_BRANCH
  CURRENT_BRANCH=$(git branch --show-current)
  echo "📌 当前分支: $CURRENT_BRANCH"

  # 4. arch 端交付物检查（plan 端的前置条件 — 硬阻断）
  local ARCH_HANDOFF="$PROJECT_ROOT/.rddf/state/.arch-handoff.json"

  if [ ! -f "$ARCH_HANDOFF" ]; then
      echo "❌ 未检测到 arch-done handoff (.rddf/state/.arch-handoff.json)"
      echo ""
      echo "   arch 阶段必须先完成才能进入 plan 阶段。"
      echo "   → 请先运行: skill_use(\"guide-arch\")"
      echo ""
      echo "   如确定跳过 arch 阶段（已知风险），设置环境变量:"
      echo "     export SKIP_ARCH_HANDOFF=yes"
      return 1
  fi

  # ADR-0016 Layer 3: read discovered paths from handoff with v2.0 fallback defaults.
  local ADR_DIR ROADMAP_PATH ADR_PATTERN ARCHITECTURE_DIR
  ADR_DIR=$(jq -r '.adr_dir // "docs/adr"' "$ARCH_HANDOFF" 2>/dev/null || echo "docs/adr")
  ROADMAP_PATH=$(jq -r '.roadmap_path // "roadmap.md"' "$ARCH_HANDOFF" 2>/dev/null || echo "roadmap.md")
  ADR_PATTERN=$(jq -r '.adr_pattern // "ADR-*.md"' "$ARCH_HANDOFF" 2>/dev/null || echo "ADR-*.md")
  ARCHITECTURE_DIR=$(jq -r '.architecture_dir // "docs/architecture"' "$ARCH_HANDOFF" 2>/dev/null || echo "docs/architecture")

  # Roadmap existence uses DISCOVERED_ROADMAP_PATH (not hardcoded)
  local ROADMAP_EXISTS
  ROADMAP_EXISTS=$([ -f "$PROJECT_ROOT/$ROADMAP_PATH" ] && echo "yes" || echo "no")

  # Read ADR_IDS + CURRENT_PHASE from handoff via env-var passing (Oracle C1 safe)
  # Instead of bash $ARCH_HANDOFF string interpolation, use env var
  local ADR_IDS CURRENT_PHASE ADR_COUNT
  export PYTHON_HANDOFF_PATH="$ARCH_HANDOFF"
  ADR_IDS=$(python3 -c "
import json, os
try:
    with open(os.environ['PYTHON_HANDOFF_PATH']) as f:
        d = json.load(f)
    print(','.join(d.get('completed_adr_ids', [])))
except Exception:
    print('')
" 2>/dev/null || echo "")
  CURRENT_PHASE=$(python3 -c "
import json, os
try:
    with open(os.environ['PYTHON_HANDOFF_PATH']) as f:
        d = json.load(f)
    print(d.get('current_phase', 'default'))
except Exception:
    print('default')
" 2>/dev/null || echo "default")
  ADR_COUNT=$(echo "$ADR_IDS" | tr ',' '\n' | grep -c . || echo 0)

  echo "📋 ADR 数量: $ADR_COUNT (from arch-handoff, dir=$ADR_DIR)"
  echo "📋 Roadmap 阶段: $CURRENT_PHASE (path=$ROADMAP_PATH)"
  echo "📋 ADR 编号: $ADR_IDS"

  # 5. plan 端当前状态
  local ACTIVE_CHANGES
  ACTIVE_CHANGES=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | grep -c . || true)
  echo "📋 当前活跃 changes: $ACTIVE_CHANGES"
  echo "✅ 检测到 arch-done handoff（arch → plan 硬交接信号）"
}