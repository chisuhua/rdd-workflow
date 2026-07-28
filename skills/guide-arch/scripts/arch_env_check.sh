#!/usr/bin/env bash
# skills/_lib/arch_env_check.sh — extracted from guide-arch.md Phase 1 Steps 1-5 (L92-L189)
# Exports: run_arch_env_check()
#
# Behavior preserved from inline block:
# - openspec CLI detection (returns 1 if missing)
# - git workspace state check
# - Current branch display
# - Build directory detection by project type (Rust/Node/Python/C++/Unknown)
# - ADR/roadmap/gap-analysis/active-change counts
# - Delegates to discover-arch-artifacts.sh (ADR-0016 Layer 1)

run_arch_env_check() {
  local PROJECT_ROOT
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  export PROJECT_ROOT

  echo "🔍 环境检查..."
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

  # 4. 构建目录（按项目类型检测）
  local BUILD_DIR PROJECT_TYPE
  if [ -f "Cargo.toml" ]; then
    BUILD_DIR="target"; PROJECT_TYPE="Rust"
  elif [ -f "package.json" ]; then
    BUILD_DIR="node_modules"; PROJECT_TYPE="Node.js"
  elif [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
    BUILD_DIR="venv"; PROJECT_TYPE="Python"
  elif [ -f "CMakeLists.txt" ] || [ -f "Makefile" ]; then
    BUILD_DIR="build"; PROJECT_TYPE="C++/Make"
  else
    BUILD_DIR="build"; PROJECT_TYPE="Unknown"
  fi

  if [ -d "$BUILD_DIR" ]; then
      echo "✅ 构建目录存在 ($BUILD_DIR/, $PROJECT_TYPE)"
  else
      echo "⚠️  构建目录不存在 ($BUILD_DIR/, $PROJECT_TYPE)"
  fi

  # 5. arch 阶段专用检查 — 先发现路径，再用于计数 (ADR-0016)
  local DISCOVERED_ADR_DIR DISCOVERED_ADR_PATTERN DISCOVERED_ROADMAP_PATH DISCOVERED_ARCHITECTURE_DIR
  local DISCOVERED_ADR_DIR_FOUND DISCOVERED_ROADMAP_FOUND DISCOVERED_ARCH_FOUND

  # === Phase 1 Step 5: 工件发现 (ADR-0016 Layer 1) ===
  source "${PROJECT_ROOT:-/nonexistent}/.opencode/skills/_lib/skill_root.sh" 2>/dev/null || source "$HOME/.agents/skills/_lib/skill_root.sh"
  if [ -f "$(resolve_rdd_lib_dir)/discover-arch-artifacts.sh" ]; then
      source "$(resolve_rdd_lib_dir)/discover-arch-artifacts.sh"
      discover_adr_dir          >/dev/null
      discover_roadmap          >/dev/null
      discover_architecture_dir >/dev/null
      discover_adr_pattern      >/dev/null
  else
      DISCOVERED_ADR_DIR="docs/adr"
      DISCOVERED_ROADMAP_PATH="roadmap.md"
      DISCOVERED_ARCHITECTURE_DIR="docs/architecture"
      DISCOVERED_ADR_PATTERN="ADR-*.md"
      DISCOVERED_ADR_DIR_FOUND="false"
      DISCOVERED_ROADMAP_FOUND="false"
      DISCOVERED_ARCH_FOUND="false"
  fi

  local ADR_COUNT ROADMAP_EXISTS GAP_COUNT ACTIVE_CHANGES
  ADR_COUNT=$(ls -d "$PROJECT_ROOT/$DISCOVERED_ADR_DIR/"$DISCOVERED_ADR_PATTERN 2>/dev/null | wc -l)
  ROADMAP_EXISTS=$([ -f "$PROJECT_ROOT/$DISCOVERED_ROADMAP_PATH" ] && echo "yes" || echo "no")
  GAP_COUNT=$(ls "$PROJECT_ROOT/$DISCOVERED_ARCHITECTURE_DIR/"*-gap-analysis.md 2>/dev/null | wc -l)
  ACTIVE_CHANGES=$(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/ | wc -l)

  echo "📋 现有 ADR: $ADR_COUNT"
  echo "📋 Roadmap: $ROADMAP_EXISTS"
  echo "📋 架构差距分析: $GAP_COUNT"
  echo "📋 活动 changes: $ACTIVE_CHANGES"

  echo ""
  echo "🔍 工件发现 (ADR-0016):"
  echo "   ADR 目录:      $DISCOVERED_ADR_DIR ($DISCOVERED_ADR_DIR_FOUND)"
  echo "   ADR 模式:      $DISCOVERED_ADR_PATTERN"
  echo "   Roadmap:       $DISCOVERED_ROADMAP_PATH ($DISCOVERED_ROADMAP_FOUND)"
  echo "   Architecture:  $DISCOVERED_ARCHITECTURE_DIR ($DISCOVERED_ARCH_FOUND)"
}
