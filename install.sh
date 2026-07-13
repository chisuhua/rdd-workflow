#!/bin/bash
# Spec Workflow 安装脚本
# 用法: bash install.sh [项目目录]
# 不带参数时安装到当前目录

set -euo pipefail

# 配置
# PACKAGE_DIR 推断顺序（与 skills/INSTALL.md 保持一致）：
#   1) 显式环境变量 PACKAGE_DIR
#   2) 标准全局安装路径 ~/.agents/skills/spec-workflow
#   3) 脚本自身位置（realpath 向上两级）— 兼容本地/便携式部署
PACKAGE_DIR="${PACKAGE_DIR:-$HOME/.agents/skills/spec-workflow}"
PACKAGE_DIR="${PACKAGE_DIR:-$(dirname "$(dirname "$(realpath "$0" 2>/dev/null)")")}"
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
mkdir -p "$TARGET_DIR/.opencode/skills/spec-workflow/skills/_lib/schemas"

# 复制所有子技能（.md）
cp -f "$PACKAGE_DIR/skills/"*.md "$TARGET_DIR/.opencode/skills/spec-workflow/skills/"

# 复制 skills/_lib/ 运行时所需 Python 模块与 schemas（排除 __pycache__ / plugins / schedulers）
# 这样 feature.md 和 rddf-session.md 的 depends-on 模块才能在目标项目里 import
if [ -d "$PACKAGE_DIR/skills/_lib" ]; then
    find "$PACKAGE_DIR/skills/_lib" \
        -type d \( -name __pycache__ -o -name plugins -o -name schedulers \) -prune \
        -o -type f \( -name '*.py' -o -name '*.json' \) -print 2>/dev/null | while read -r src; do
        rel="${src#$PACKAGE_DIR/}"
        mkdir -p "$TARGET_DIR/.opencode/skills/spec-workflow/$(dirname "$rel")"
        cp -f "$src" "$TARGET_DIR/.opencode/skills/spec-workflow/$rel"
    done
fi

# 复制 package.json（如果存在）
if [ -f "$PACKAGE_DIR/package.json" ]; then
    cp -f "$PACKAGE_DIR/package.json" "$TARGET_DIR/.opencode/skills/spec-workflow/"
fi

echo "✅ 安装完成!"
echo ""
echo "已安装的子技能:"
ls -1 "$TARGET_DIR/.opencode/skills/spec-workflow/skills/"
echo ""
echo "使用方式: skill_use(\"guide\")"