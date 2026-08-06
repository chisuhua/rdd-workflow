#!/usr/bin/env bash
# _lib/arch_gap_analysis.sh — extracted from guide-arch.md L343-L431
# Exports:
#   - generate_gap_analysis <slug> — creates docs/architecture/<slug>-gap-analysis.md
#   - list_gap_analyses           — prints numbered list of existing gap analyses
#
# Honors env vars:
#   DISCOVERED_ARCHITECTURE_DIR — architecture directory path (from arch_env_check.sh)
#   PROJECT_ROOT               — project root (auto-detected if not set)

generate_gap_analysis() {
  local SLUG="${1:-}"
  local PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local ARCH_DIR="$PROJECT_ROOT/${DISCOVERED_ARCHITECTURE_DIR:-docs/architecture}"

  if [ -z "$SLUG" ]; then
    echo "❌ 主题不能为空"
    return 1
  fi

  mkdir -p "$ARCH_DIR" || { echo "❌ 无法创建目录: $ARCH_DIR"; return 1; }
  local NEW_GAP="$ARCH_DIR/${SLUG}-gap-analysis.md"
  if [ -f "$NEW_GAP" ]; then
    echo "❌ 差距分析已存在: $NEW_GAP"
    return 1
  fi

  cat > "$NEW_GAP" << EOF
# 架构差距分析: ${SLUG}

> **生成日期**: $(date -Iseconds)
> **状态**: 草案
> **关联 ADR**: (待补充)

## 1. 目标架构

(描述 ADR 中定义的目标架构)

## 2. 当前架构

(描述项目当前实际架构)

## 3. 差距清单

| # | 差距项 | 严重程度 | 优先级 | 关联 change |
|---|--------|---------|--------|------------|
| 1 | ... | 高/中/低 | P0/P1/P2 | ... |

## 4. 补齐路径

(描述从当前架构迁移到目标架构的步骤、顺序、依赖)

## 5. 参考资料

- 相关 ADR
- 相关 change artifacts
EOF

  echo "✅ 已创建: $NEW_GAP"
  echo "   请编辑该文件补全差距分析内容"
}

list_gap_analyses() {
  local PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local ARCH_DIR="$PROJECT_ROOT/${DISCOVERED_ARCHITECTURE_DIR:-docs/architecture}"

  local GAP_DOCS GAP_COUNT
  GAP_DOCS=$(ls "$ARCH_DIR/"*-gap-analysis.md 2>/dev/null || true)

  if [ -z "$GAP_DOCS" ]; then
    GAP_COUNT=0
  else
    GAP_COUNT=$(echo "$GAP_DOCS" | wc -l | tr -d '[:space:]')
  fi

  if [ "$GAP_COUNT" -eq 0 ]; then
    echo "⚠️  暂无差距分析"
    return 1
  fi

  echo "现有差距分析列表:"
  echo "$GAP_DOCS" | nl -w2 -s". " | while read -r line; do
      echo "  $line"
  done
  return 0
}