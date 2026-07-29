#!/usr/bin/env bash
# skills/guide-arch/scripts/arch_proposal_review.sh
# Phase 5.5 提案审批逻辑（从 SKILL.md 内联代码提取 + 增强）
#
# 职责：
#   1. 同时扫描 improvements/ 和 proposal-suggestions.md 发现待审提案
#   2. 交叉引用 proposal-approved.md 排除已批准的
#   3. 处理已归档提案的自动批准
#   4. 展示审查菜单，支持：
#      - 编号选择 → 查看单提案详情 + y(批准)/n(拒绝)/d(延迟)/s(跳过)
#      - 批量批准所有
#      - 跳过
#   5. 在 proposal-suggestions.md 中记录拒绝/延迟状态
#
# 用法：
#   source "$(dirname "${BASH_SOURCE[0]}")/scripts/arch_proposal_review.sh"
#   arch_proposal_review "$PROJECT_ROOT" "$PHASE_5_5_ENTRY"
#   rc=$?  # 0=正常完成, 1=返回上级
#
# 参数：
#   $1: PROJECT_ROOT — 项目根目录
#   $2: PHASE_5_5_ENTRY — "phase1" 或 "gate"

set -euo pipefail

arch_proposal_review() {
  local PROJECT_ROOT="$1"
  local PHASE_5_5_ENTRY="${2:-phase1}"
  local SCRIPT_DIR
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
  local LIB_DIR="$SCRIPT_DIR/../../_lib"

  # 加载共享函数
  if [ -f "$LIB_DIR/state.sh" ]; then
    source "$LIB_DIR/state.sh"
  fi

  local IMPROVEMENTS_DIR="$PROJECT_ROOT/improvements"
  local APPROVED_FILE="$PROJECT_ROOT/proposal-approved.md"
  local SUGGESTIONS_FILE="$PROJECT_ROOT/proposal-suggestions.md"

  echo ""
  echo "========================================"
  echo "    提案审批阶段"
  echo "========================================"
  echo ""

  # ============ Step 1: 收集提案 ============

  # 从 proposal-suggestions.md 解析所有提案条目
  # 支持两种格式：
  #   | [name](path) | priority | source | status [| added_time] |
  declare -A SUGGESTION_PATHS    # name -> path (from suggestions)
  declare -A SUGGESTION_PRIORITY # name -> priority
  declare -A SUGGESTION_STATUS   # name -> status (from suggestions)

  if [ -f "$SUGGESTIONS_FILE" ]; then
    while IFS='|' read -r _ name_link rest; do
      [ -z "$name_link" ] && continue
      # Extract [name](path)
      name=$(echo "$name_link" | sed -n 's/.*\[\([^]]*\)\](\([^)]*\)).*/\1/p')
      path=$(echo "$name_link" | sed -n 's/.*\[\([^]]*\)\](\([^)]*\)).*/\2/p')
      [ -z "$name" ] && continue
      SUGGESTION_PATHS["$name"]="$path"
      # Extract priority (first column after name, non-empty)
      local priority=$(echo "$rest" | awk -F'|' '{gsub(/^[[:space:]]+|[[:space:]]+$/, "", $1); if ($1 != "") print $1}')
      SUGGESTION_PRIORITY["$name"]="${priority:-?}"
      # Extract status
      local status=$(echo "$rest" | awk -F'|' '{gsub(/^[[:space:]]+|[[:space:]]+$/, "", $3); if ($3 != "") print $3}')
      SUGGESTION_STATUS["$name"]="${status:-待讨论}"
    done < <(grep -E '^\s*\|\s*\[' "$SUGGESTIONS_FILE" 2>/dev/null || true)
  fi

  # 从 proposal-approved.md 读取已批准的提案名
  local APPROVED_NAMES=""
  if [ -f "$APPROVED_FILE" ]; then
    APPROVED_NAMES=$(python3 -c "
import re, sys
with open('$APPROVED_FILE') as f:
    content = f.read()
# Find all [name](improvements/...) or [name](...) in the approved section (before ## 已实施)
section = re.split(r'## 已实施', content)[0]
for m in re.finditer(r'\|\s*\[([^\]]+)\]\([^)]+\)', section):
    print(m.group(1))
" 2>/dev/null || true)
  fi

  # ============ Step 2: 构建待审查提案列表 ============

  # 收集所有候选提案名（来自 improvements/ + proposal-suggestions.md）
  local ALL_CANDIDATES=()
  local -A CANDIDATE_SET=()

  # Pass A: 从 improvements/ 目录
  if [ -d "$IMPROVEMENTS_DIR" ]; then
    for f in "$IMPROVEMENTS_DIR"/*.md; do
      [ -f "$f" ] || continue
      local name=$(basename "$f" .md)
      if [ -z "${CANDIDATE_SET[$name]:-}" ]; then
        ALL_CANDIDATES+=("$name")
        CANDIDATE_SET["$name"]=1
      fi
    done
  fi

  # Pass B: 从 proposal-suggestions.md（补全 improvements/ 遗漏的）
  for name in "${!SUGGESTION_PATHS[@]}"; do
    if [ -z "${CANDIDATE_SET[$name]:-}" ]; then
      ALL_CANDIDATES+=("$name")
      CANDIDATE_SET["$name"]=1
    fi
  done

  # ============ Step 3: 分类 ============

  local -a PENDING_PROPS=()       # name|priority|source
  local ARCHIVED_COUNT=0
  local DEFERRED_COUNT=0
  local SHOW_ALL="${SHOW_ALL:-false}"

  for name in "${ALL_CANDIDATES[@]}"; do
    # 跳过已批准的
    local is_approved=false
    while IFS= read -r approved_name; do
      [ "$approved_name" = "$name" ] && is_approved=true && break
    done <<< "$APPROVED_NAMES"
    $is_approved && continue

    local imp_file="$IMPROVEMENTS_DIR/$name.md"
    local status="${SUGGESTION_STATUS[$name]:-}"

    # 跳过已标记 rejected / deferred 的
    if echo "$status" | grep -qiE 'rejected|已拒绝|deferred|已延迟'; then
      continue
    fi

    # 读取 improvement 文件中的 **状态** 字段（ADR: proposal defer support）
    local file_status=$(grep -m1 '^\*\*状态\*\*:' "$imp_file" 2>/dev/null | sed 's/.*\*\*状态\*\*: *//' | cut -d'|' -f1 | xargs)
    file_status="${file_status:-待讨论}"

    # 已推迟 -> 默认跳过（除非 SHOW_ALL 模式）
    if [ "$file_status" = "已推迟" ] && [ "$SHOW_ALL" != "true" ]; then
      DEFERRED_COUNT=$((DEFERRED_COUNT + 1))
      continue
    fi

    # 检测是否已归档（通过 openspec/changes/archive/ 匹配）
    local is_archived=false
    if ls -d "$PROJECT_ROOT/openspec/changes/archive/"*"-$name" 2>/dev/null | grep -q .; then
      is_archived=true
    fi

    if $is_archived; then
      # 已归档 → 自动批准到已实施
      if [ -f "$imp_file" ]; then
        local priority="${SUGGESTION_PRIORITY[$name]:-$(grep -m1 '^\*\*优先级\*\*:' "$imp_file" 2>/dev/null | sed 's/.*\*\*优先级\*\*: *//' | cut -d'|' -f1 | xargs)}"
        if type mark_approved_completed &>/dev/null; then
          mark_approved_completed "$PROJECT_ROOT" "$name" 2>/dev/null || true
        fi
      fi
      ARCHIVED_COUNT=$((ARCHIVED_COUNT + 1))
      continue
    fi

    # 确定优先级和来源
    local priority="${SUGGESTION_PRIORITY[$name]:-?}"
    local source="${SUGGESTION_STATUS[$name]:-}"

    if [ -f "$imp_file" ]; then
      local file_priority=$(grep -m1 '^\*\*优先级\*\*:' "$imp_file" 2>/dev/null | sed 's/.*\*\*优先级\*\*: *//' | cut -d'|' -f1 | xargs)
      [ -n "$file_priority" ] && priority="$file_priority"
      local file_source=$(grep -m1 '^\*\*来源\*\*:' "$imp_file" 2>/dev/null | sed 's/.*\*\*来源\*\*: *//' | xargs)
      [ -n "$file_source" ] && source="$file_source"
    fi

    PENDING_PROPS+=("$name|$priority|$source")
  done

  # ============ Step 4: 展示 ============

  echo "📂 提案列表:"
  echo ""

  if [ "$ARCHIVED_COUNT" -gt 0 ]; then
    echo "📦 已归档自动批准: $ARCHIVED_COUNT 个（跳过审查）"
    echo ""
  fi

  local pending_count=${#PENDING_PROPS[@]}
  echo "📋 待审查: $pending_count 个"
  if [ "$DEFERRED_COUNT" -gt 0 ]; then
    echo "⏸️ 已推迟: $DEFERRED_COUNT 个（按 v 查看全部）"
  fi
  echo ""

  if [ "$pending_count" -eq 0 ]; then
    echo "  (无待讨论提案)"
    echo ""
    if [ "$PHASE_5_5_ENTRY" = "phase1" ]; then
      echo "-> 无待审批提案，返回上级菜单"
    else
      echo "-> 跳过审批，直接进入 arch-done"
    fi
    return 0
  fi

  # 列表展示
  local idx=0
  for entry in "${PENDING_PROPS[@]}"; do
    idx=$((idx + 1))
    local name=$(echo "$entry" | cut -d'|' -f1)
    local priority=$(echo "$entry" | cut -d'|' -f2)
    local source=$(echo "$entry" | cut -d'|' -f3-)
    local path_hint="${SUGGESTION_PATHS[$name]:-}"
    local imp_file="$IMPROVEMENTS_DIR/$name.md"
    local disp_status=$(grep -m1 '^\*\*状态\*\*:' "$imp_file" 2>/dev/null | sed 's/.*\*\*状态\*\*: *//' | cut -d'|' -f1 | xargs)
    local prefix=""
    if [ "$SHOW_ALL" = "true" ] && [ "$disp_status" = "已推迟" ]; then
      prefix="⏸️ "
    fi
    echo "  ${idx}. [${priority}] ${prefix}${name}"
    if [ -n "$source" ]; then
    echo "     来源: $source"
    fi
  done

  echo ""
  echo "选择操作:"
  echo "  <编号>        - 查看并审批该提案（批准/拒绝/延迟）"
  echo "  a             - 全部批准"
  if [ "$DEFERRED_COUNT" -gt 0 ]; then
  echo "  v             - 查看全部（含已推迟提案）"
  fi
  if [ "$PHASE_5_5_ENTRY" = "phase1" ]; then
    echo "  s             - 跳过审批，返回上级菜单"
  else
    echo "  s             - 跳过审批，直接 arch-done"
  fi
  echo "  q             - 返回上级菜单"

  # ============ Step 5: 处理用户选择 ============

  echo ""
  read -r CHOICE

  case "$CHOICE" in
    q|quit|exit)
      return 1
      ;;
    s|skip)
      echo "-> 跳过提案审批"
      return 0
      ;;
    a|all)
      echo "批量批准所有提案..."
      for entry in "${PENDING_PROPS[@]}"; do
        local name=$(echo "$entry" | cut -d'|' -f1)
        local priority=$(echo "$entry" | cut -d'|' -f2)
        local imp_file="$IMPROVEMENTS_DIR/$name.md"
        if [ ! -f "$imp_file" ]; then
          echo "  ⚠️  $name: improvements/$name.md 不存在，跳过"
          continue
        fi
        bash "$SCRIPT_DIR/approve_proposal.sh" "$name" "${priority:-P1}" "$PROJECT_ROOT" && \
          echo "  ✅ $name 已批准"
      done
      ;;
    v|V|view-all)
      SHOW_ALL=true
      export SHOW_ALL
      arch_proposal_review "$PROJECT_ROOT" "$PHASE_5_5_ENTRY"
      return $?
      ;;
    *)
      # 数字选择：查看单个提案并审批
      # 验证输入
      local sel=$CHOICE
      if ! [[ "$sel" =~ ^[0-9]+$ ]]; then
        echo "❌ 无效输入 '$CHOICE', 请输入编号、a(全部批准)、s(跳过) 或 q(返回)"
        return 0
      fi
      if [ "$sel" -lt 1 ] || [ "$sel" -gt "$pending_count" ]; then
        echo "❌ 编号超出范围 (1-$pending_count)"
        return 0
      fi

      local entry="${PENDING_PROPS[$((sel - 1))]}"
      local name=$(echo "$entry" | cut -d'|' -f1)
      local priority=$(echo "$entry" | cut -d'|' -f2)
      local imp_file="$IMPROVEMENTS_DIR/$name.md"

      echo ""
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "  提案: $name ($priority)"
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

      if [ -f "$imp_file" ]; then
        # 展示提案前 40 行
        head -40 "$imp_file"
        local total_lines=$(wc -l < "$imp_file")
        if [ "$total_lines" -gt 40 ]; then
          echo ""
          echo "... (共 $total_lines 行，省略 $((total_lines - 40)) 行)"
        fi
      else
        local path_hint="${SUGGESTION_PATHS[$name]:-}"
        echo "⚠️  改进文件不存在: improvements/$name.md"
        if [ -n "$path_hint" ] && [ "$path_hint" != "improvements/$name.md" ]; then
          echo "   建议路径: $path_hint"
          if [ -f "$PROJECT_ROOT/$path_hint" ]; then
            echo ""
            echo "从建议路径读取:"
            head -30 "$PROJECT_ROOT/$path_hint"
          fi
        fi
      fi

      echo ""
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo "选择:"
      echo "  y   - 批准（添加到 proposal-approved.md）"
      echo "  n   - 拒绝（在 proposal-suggestions.md 标记 rejected）"
      echo "  d   - 延迟（在 proposal-suggestions.md 标记 deferred，保留待讨论）"
      echo "  s   - 跳过，返回列表"
      echo ""
      read -r DECISION

      case "$DECISION" in
        y|Y|yes)
          if [ -f "$imp_file" ]; then
            bash "$SCRIPT_DIR/approve_proposal.sh" "$name" "${priority:-P1}" "$PROJECT_ROOT"
            echo "✅ $name 已批准"
          else
            echo "❌ 无法批准: improvements/$name.md 不存在"
            echo "   请先通过 add-improve 创建该提案文件"
          fi
          ;;
        n|N|no)
          # 拒绝：在 proposal-suggestions.md 中标记
          if [ -f "$SUGGESTIONS_FILE" ]; then
            local timestamp=$(date -u +%Y-%m-%d)
            if grep -q "\[$name\]" "$SUGGESTIONS_FILE" 2>/dev/null; then
              sed -i "s/\(\[$name\].[^|]*|[^|]*|[^|]*|\)[^|]*/\1 ❌ 已拒绝 ($timestamp)/" "$SUGGESTIONS_FILE"
            fi
            echo "❌ $name 已标记为拒绝"
          fi
          ;;
        d|D|defer)
          if [ -f "$SUGGESTIONS_FILE" ]; then
            local timestamp=$(date -u +%Y-%m-%d)
            if grep -q "\[$name\]" "$SUGGESTIONS_FILE" 2>/dev/null; then
              sed -i "s/\(\[$name\].[^|]*|[^|]*|[^|]*|\)[^|]*/\1 ⏳ 已延迟 ($timestamp)/" "$SUGGESTIONS_FILE"
            fi
            echo "⏳ $name 已标记为延迟"
          fi
          ;;
        s|S|skip)
          echo "-> 跳过 $name"
          ;;
        *)
          echo "❌ 无效选择: $DECISION"
          ;;
      esac
      ;;
  esac

  return 0
}

# 如果直接执行，使用默认参数
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  arch_proposal_review "${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}" "${2:-phase1}"
fi
