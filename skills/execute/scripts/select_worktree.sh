#!/usr/bin/env bash
# _lib/select_worktree.sh — extracted from execute.md L54-L168
# Exports: auto_detect_worktree_context()
#
# Detects if currently inside an openspec/* worktree branch.
# If yes: sets CHANGE_NAME + HAS_WORKTREE=true.
# If no: lists available worktrees, prompts via EXECUTE_CHOICE (default 1), cd's into selected.
# If NO worktrees exist: prints error + lists available changes + exits 1.

# ADR-0027 script-plane trigger (see add-post-flow-analysis change)
export RDDF_PHASE="${RDDF_PHASE:-execute}"
source "${RDDF_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}/skills/_lib/post_flow_wrap.sh" 2>/dev/null || true
trap 'post_flow_on_err' ERR
#
# Honors env vars:
#   EXECUTE_CHOICE=N — selects Nth worktree (default 1, avoid read -p in non-interactive envs)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

if [ -f "$SCRIPT_DIR/change_name.sh" ]; then
  source "$SCRIPT_DIR/change_name.sh"
fi

auto_detect_worktree_context() {
  # Source helper (worktree-aware functions) — needed by both the RDDF_EXECUTION_ROOT
  # containment check and the legacy worktree detection below.
  if [ -f "$SCRIPT_DIR/worktree.sh" ]; then
    source "$SCRIPT_DIR/worktree.sh"
  fi

  # Honor RDDF_EXECUTION_ROOT if guide-ship set it (single source of truth for workspace).
  # When set, do NOT re-detect; just export PROJECT_ROOT from it and skip worktree probing.
  # Containment check: RDDF_EXECUTION_ROOT must be a git repo whose --git-common-dir
  # matches the detected main repo root, otherwise a poisoned env var would redirect
  # execute into an arbitrary directory.
  if [ -n "${RDDF_EXECUTION_ROOT:-}" ] && [ -d "${RDDF_EXECUTION_ROOT}" ]; then
    local _expected_main
    _expected_main=$(main_repo_root 2>/dev/null || pwd)
    local _rddf_common
    _rddf_common=$(git -C "${RDDF_EXECUTION_ROOT}" rev-parse --git-common-dir 2>/dev/null || true)
    local _expected_common
    _expected_common=$(git -C "$_expected_main" rev-parse --git-common-dir 2>/dev/null || true)
    # Resolve to absolute paths so a relative ".git" matches itself.
    [ -n "$_rddf_common" ] && _rddf_common=$(cd "${RDDF_EXECUTION_ROOT}" 2>/dev/null && cd "$_rddf_common" 2>/dev/null && pwd -P)
    [ -n "$_expected_common" ] && _expected_common=$(cd "$_expected_main" 2>/dev/null && cd "$_expected_common" 2>/dev/null && pwd -P)
    if [ -n "$_rddf_common" ] && [ -n "$_expected_common" ] && [ "$_rddf_common" = "$_expected_common" ]; then
      PROJECT_ROOT="${RDDF_EXECUTION_ROOT}"
      export PROJECT_ROOT
      cd "$PROJECT_ROOT" || return 1
      return 0
    fi
    echo "⚠️  RDDF_EXECUTION_ROOT (${RDDF_EXECUTION_ROOT}) 不在项目仓库内,忽略并继续探测" >&2
    unset RDDF_EXECUTION_ROOT
  fi

  # 自动检测项目根目录（用于全局安装的技能）
  # P0-8: use main_repo_root (works in both main repo and worktrees)
  if type main_repo_root &>/dev/null; then
    PROJECT_ROOT=$(main_repo_root)
  else
    PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  fi
  [ -d "$PROJECT_ROOT" ] || PROJECT_ROOT=$(pwd)
  export PROJECT_ROOT
  # 检测当前 git 上下文
  local CURRENT_BRANCH
  CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
  local GIT_ROOT
  GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "unknown")

  # 列出所有 worktree 以确定关系
  local WORKTREE_LIST
  WORKTREE_LIST=$(git worktree list 2>/dev/null || echo "")

  # 判断是否在 worktree 内
  if echo "$CURRENT_BRANCH" | grep -q '^openspec/'; then
      WORKTREE_PATH=$(pwd)
      HAS_WORKTREE=true
      export HAS_WORKTREE WORKTREE_PATH
      ensure_change_name
      export CHANGE_NAME

      # 验证当前目录确实是对应的 worktree 目录
      local MAIN_WT_PATH
      MAIN_WT_PATH=$(echo "$WORKTREE_LIST" | grep "openspec/$CHANGE_NAME" | awk '{print $1}')
      if [ "$MAIN_WT_PATH" != "$(pwd)" ]; then
          echo "⚠️ 分支名与 worktree 路径不匹配"
          echo "   branch: openspec/$CHANGE_NAME"
          echo "   worktree from list: $MAIN_WT_PATH"
          echo "   current dir: $(pwd)"
      fi
  else
      # ============================================================
      # P0 修复：不在 worktree 内时，提供自动引导而非直接退出
      # ============================================================
      echo "⚠️  当前不在 worktree 内"
      echo ""

      # 检查是否有已创建的 worktree
      local WT_INFO
      WT_INFO=$(git worktree list --porcelain | awk '
        /^worktree / { path = substr($0, length("worktree ") + 1); next }
        /^branch /   {
          branch = substr($0, length("branch ") + 1)
          sub(/^refs\/heads\//, "", branch)
          if (branch ~ /^openspec\//) print path " " branch
          next
        }
      ')

      if [ -z "$WT_INFO" ]; then
          echo "❌ 无已创建的 worktree"
          echo ""
          echo "请先执行 guide-ship 技能创建 worktree："
          echo "  skill_use(\"guide-ship\")   # 内部选择 change"
          echo ""
          echo "可用 change 列表："
          local change_dir
          for change_dir in $(ls -d "$PROJECT_ROOT"/openspec/changes/*/ 2>/dev/null | grep -v archive/); do
              echo "  - $(basename "$change_dir")"
          done
          return 1
      fi

      # 有 worktree 存在，显示选择菜单
      local WT_TOTAL WORKTREE_COUNT plan_file status choice selected_line target_path target_branch
      WT_TOTAL=$(echo "$WT_INFO" | grep -c .)
      echo "📋 发现 $WT_TOTAL 个已创建的 worktree："
      echo ""
      WORKTREE_COUNT=0
      while read -r wt_path wt_branch; do
          WORKTREE_COUNT=$((WORKTREE_COUNT + 1))
          name=$(echo "$wt_branch" | sed 's|^openspec/||')
          plan_file="$wt_path/.rddf/plans/$name.md"
          if [ -f "$plan_file" ]; then
              status="✅ 有计划文件"
          else
              status="⏳ 无计划文件"
          fi
          echo "  $WORKTREE_COUNT. $name"
          echo "     路径: $wt_path"
          echo "     分支: $wt_branch"
          echo "     状态: $status"
          echo ""
      done <<< "$WT_INFO"

      # P0-9 修复：用 EXECUTE_CHOICE 环境变量取代 read -p
      # 原因：read -p 在 AI/CI 等非交互环境会从 stdin 读取，永远阻塞直到输入
      # 新行为：
      #   - 默认选择 1（最常见：进入主 worktree）
      #   - 可通过 EXECUTE_CHOICE=N 覆盖选择 N
      #   - 多 worktree 场景下提示用户可通过环境变量覆盖
      choice="${EXECUTE_CHOICE:-1}"
      if [ -z "${EXECUTE_CHOICE:-}" ] && [ "$WT_TOTAL" -gt 1 ]; then
          echo "ℹ️  多个 worktree 检测到，默认选择 1（可通过 EXECUTE_CHOICE=N 覆盖）"
      fi
      selected_line=$(echo "$WT_INFO" | sed -n "${choice}p")

      if [ -z "$selected_line" ]; then
          echo "❌ 无效选择，请设置 EXECUTE_CHOICE=1..$WT_TOTAL"
          return 1
      fi

      target_path=$(echo "$selected_line" | awk '{print $1}')
      target_branch=$(echo "$selected_line" | awk '{print $2}')

      echo ""
      echo "正在切换到 worktree：$target_path"
      cd "$target_path"
      HAS_WORKTREE=true
      export HAS_WORKTREE
      if [ -z "${CHANGE_NAME:-}" ]; then
        CHANGE_NAME="${target_branch#openspec/}"
      fi
      export CHANGE_NAME
      echo "✅ 已切换到: $(pwd)"
      echo "   Branch: $(git branch --show-current)"
      echo "   Change: $CHANGE_NAME"
      echo ""
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "💡 提示：下次可直接使用以下命令进入此 worktree"
      echo "   cd $target_path"
      echo "   skill_use(\"execute\")"
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo ""
  fi
}