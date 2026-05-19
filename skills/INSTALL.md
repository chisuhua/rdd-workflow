---
name: INSTALL
description: 安装 Spec Workflow 技能到项目目录。执行后会将子技能（guide/propose/plan/execute/status）复制到项目的 .opencode/skills/ 目录。
alias: install
version: "1.0"
author: sisyphus
---

# Spec Workflow 安装程序

本技能将 Spec Workflow 的子技能安装到当前项目目录。

## 安装步骤

### 步骤 1：检测环境

```bash
# 自动检测项目根目录
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

# 检查是否为 git 仓库
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo "⚠️  当前目录不是 git 仓库"
    echo "   建议在项目根目录执行本技能"
    PROJECT_ROOT=$(pwd)
fi

echo "📁 项目根目录: $PROJECT_ROOT"
```

### 步骤 2：创建目标目录

```bash
# 创建项目技能目录（如果不存在）
SKILLS_DIR="$PROJECT_ROOT/.opencode/skills/spec-workflow"

mkdir -p "$SKILLS_DIR"

# 创建子技能目录
mkdir -p "$SKILLS_DIR/skills"

echo "✅ 技能目录已创建: $SKILLS_DIR"
```

### 步骤 3：复制子技能

```bash
# 获取技能包位置
PACKAGE_DIR=$(dirname "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$HOME/.agents/skills/spec-workflow")"))

# 检查技能包是否存在
if [ ! -d "$PACKAGE_DIR/skills" ]; then
    echo "❌ 找不到技能包: $PACKAGE_DIR/skills"
    echo "   请确认已正确安装 spec-workflow 技能包"
    exit 1
fi

# 复制所有子技能
cp -f "$PACKAGE_DIR/skills/"*.md "$SKILLS_DIR/skills/"

echo "✅ 子技能已复制:"
ls -1 "$SKILLS_DIR/skills/"
```

### 步骤 4：创建包元数据

```bash
# 创建 package.json（如果不存在）
if [ ! -f "$SKILLS_DIR/package.json" ]; then
    cat > "$SKILLS_DIR/package.json" << 'EOF'
{
  "name": "spec-workflow",
  "version": "1.0",
  "description": "Spec Workflow - OpenSpec 工作流技能包",
  "author": "sisyphus",
  "skills": ["guide", "propose", "plan", "execute", "status"]
}
EOF
    echo "✅ package.json 已创建"
fi
```

### 步骤 5：生成安装脚本（供其他 AI 助手使用）

```bash
# 创建 install.sh 脚本到项目根目录
cat > "$PROJECT_ROOT/install-spec-workflow.sh" << 'SCRIPT'
#!/bin/bash
# Spec Workflow 安装脚本（供其他 AI 助手使用）
# 用法: bash install-spec-workflow.sh

set -e

PACKAGE_DIR="${PACKAGE_DIR:-$HOME/.agents/skills/spec-workflow}"
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

echo "📦 安装 Spec Workflow 到: $PROJECT_ROOT"

# 创建目录
mkdir -p "$PROJECT_ROOT/.opencode/skills/spec-workflow/skills"

# 复制技能
if [ -d "$PACKAGE_DIR/skills" ]; then
    cp -f "$PACKAGE_DIR/skills/"*.md "$PROJECT_ROOT/.opencode/skills/spec-workflow/skills/"
    echo "✅ 技能已安装"
    ls -1 "$PROJECT_ROOT/.opencode/skills/spec-workflow/skills/"
else
    echo "❌ 找不到技能包: $PACKAGE_DIR/skills"
    exit 1
fi
SCRIPT

chmod +x "$PROJECT_ROOT/install-spec-workflow.sh"
echo "✅ 安装脚本已创建: $PROJECT_ROOT/install-spec-workflow.sh"
```

### 步骤 6：验证安装

```bash
echo ""
echo "========================================"
echo "✅ 安装完成！"
echo "========================================"
echo ""
echo "已安装的子技能:"
ls -1 "$SKILLS_DIR/skills/"
echo ""
echo "下一步: 重新加载 session 或执行 skill_use(\"spec-workflow-guide\")"
```

## 安装脚本用法（其他 AI 助手）

其他 AI 编程助手可以使用以下命令安装：

```bash
# 方式 1: 直接复制
cp -r ~/.agents/skills/spec-workflow/skills /your/project/.opencode/skills/spec-workflow/

# 方式 2: 使用安装脚本
curl -sL <raw-url>/install-spec-workflow.sh | bash

# 方式 3: Git 克隆
git clone <repo-url> /path/to/spec-workflow && cp -r spec-workflow/skills /your/project/.opencode/skills/
```

## 卸载

```bash
rm -rf "$PROJECT_ROOT/.opencode/skills/spec-workflow"
rm -f "$PROJECT_ROOT/install-spec-workflow.sh"
```

## 元信息

| 字段 | 值 |
|------|-----|
| 包名称 | spec-workflow |
| 别名 | workflow, install |
| 版本 | 1.0 |
| 作者 | sisyphus |