#!/bin/bash
# RDD Workflow 安装脚本（供其他 AI 助手使用）
# 用法: bash install-rdd-workflow.sh

set -e

PACKAGE_DIR="${PACKAGE_DIR:-$HOME/.agents/skills/rdd-workflow}"
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

echo "📦 安装 RDD Workflow 到: $PROJECT_ROOT"

# 创建目录
mkdir -p "$PROJECT_ROOT/.opencode/skills/rdd-workflow/skills"

# 复制技能（递归 per-skill 子目录 + INSTALL.md 在顶层）
if [ -d "$PACKAGE_DIR/skills" ]; then
    for skill_dir in "$PACKAGE_DIR/skills/"*/; do
        skill_name=$(basename "$skill_dir")
        [ "$skill_name" = "_lib" ] && continue
        [ "$skill_name" = "__pycache__" ] && continue
        if [ -d "$skill_dir" ]; then
            mkdir -p "$PROJECT_ROOT/.opencode/skills/rdd-workflow/skills/$skill_name/scripts" \
                     "$PROJECT_ROOT/.opencode/skills/rdd-workflow/skills/$skill_name/references"
            [ -f "$skill_dir/SKILL.md" ] && cp -f "$skill_dir/SKILL.md" "$PROJECT_ROOT/.opencode/skills/rdd-workflow/skills/$skill_name/"
        fi
    done
    cp -f "$PACKAGE_DIR/skills/INSTALL.md" "$PROJECT_ROOT/.opencode/skills/rdd-workflow/skills/"
    echo "✅ 技能已安装"
    ls -1 "$PROJECT_ROOT/.opencode/skills/rdd-workflow/skills/"
else
    echo "❌ 找不到技能包: $PACKAGE_DIR/skills"
    exit 1
fi
