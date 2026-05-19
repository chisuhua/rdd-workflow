#!/bin/bash
# Spec Workflow 安装脚本
# 用法: bash install.sh [项目目录]
# 不带参数时安装到当前目录

set -e

# 配置
PACKAGE_DIR="${PACKAGE_DIR:-$HOME/.agents/skills/spec-workflow}"
TARGET_DIR="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

echo "📦 安装 Spec Workflow 技能"
echo "   包位置: $PACKAGE_DIR"
echo "   目标目录: $TARGET_DIR"

# 检查包是否存在
if [ ! -d "$PACKAGE_DIR/skills" ]; then
    echo "❌ 错误: 找不到技能包 at $PACKAGE_DIR/skills"
    echo "   请先安装 spec-workflow 技能包"
    exit 1
fi

# 创建目标目录
mkdir -p "$TARGET_DIR/.opencode/skills/spec-workflow/skills"

# 复制所有子技能
cp -f "$PACKAGE_DIR/skills/"*.md "$TARGET_DIR/.opencode/skills/spec-workflow/skills/"

# 复制 package.json（如果存在）
if [ -f "$PACKAGE_DIR/package.json" ]; then
    cp -f "$PACKAGE_DIR/package.json" "$TARGET_DIR/.opencode/skills/spec-workflow/"
fi

echo "✅ 安装完成!"
echo ""
echo "已安装的子技能:"
ls -1 "$TARGET_DIR/.opencode/skills/spec-workflow/skills/"
echo ""
echo "使用方式: skill_use(\"spec-workflow-guide\")"