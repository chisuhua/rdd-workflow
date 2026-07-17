---
name: INSTALL
description: 安装 Spec Workflow 技能到项目目录。执行后会将 skills/ 目录下全部 13 个子技能（1 个 INSTALL.md 在顶层 + 12 个 per-skill SKILL.md，含 feature / rddf-session / spec-workflow-writing-plans 等运行时 Python 模块）复制到项目的 .opencode/skills/spec-workflow/ 目录。
alias: install
version: "2.0"
author: sisyphus
---

# Spec Workflow 安装程序

本技能将 Spec Workflow 的子技能安装到当前项目目录。

## 前置条件检查

```bash
# 检查 openspec CLI 是否已安装（非交互式，AI 环境友好）
# 设置 SKIP_OPENSPEC_PROMPT=yes 可跳过此检查（已知风险）
if [ "${SKIP_OPENSPEC_PROMPT:-no}" = "yes" ]; then
  echo "⚠️  跳过 openspec 检查（SKIP_OPENSPEC_PROMPT=yes）"
elif command -v openspec >/dev/null 2>&1; then
  OPENSPEC_VERSION=$(openspec --version 2>/dev/null || echo "unknown")
  echo "✅ openspec CLI 已安装: v$OPENSPEC_VERSION"
elif command -v npx >/dev/null 2>&1 && npx openspec --version >/dev/null 2>&1; then
  OPENSPEC_VERSION=$(npx openspec --version 2>/dev/null || echo "unknown")
  echo "✅ openspec CLI 已安装 (via npx): v$OPENSPEC_VERSION"
else
  echo ""
  echo "❌ openspec CLI 未安装"
  echo ""
  echo "请选择安装方式："
  echo ""
  echo "  方式 1 - npm 全局安装（推荐）："
  echo "    npm install -g openspec-cli"
  echo ""
  echo "  方式 2 - npx 临时运行："
  echo "    npx openspec <command>"
  echo ""
  echo "  方式 3 - 跳过此检查（已知风险）："
  echo "    export SKIP_OPENSPEC_PROMPT=yes 后重试"
  echo ""
  exit 1
fi

# 检查其他常用依赖（仅警告，不阻塞安装）
for cmd in python3 jq git cmake; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "✅ $cmd: $(command -v $cmd)"
  else
    echo "⚠️  缺失依赖: $cmd （某些功能将不可用）"
  fi
done
```

## 安装步骤

### 步骤 1：检测环境

```bash
# 自动检测项目根目录
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

# 检查是否为 git 仓库
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo "⚠️  当前目录不是 git 仓库"
    echo "   建议在项目根目录执行本技能"
    PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
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
# 获取技能包位置（兼容 macOS/BSD）
PACKAGE_DIR=$(dirname "$(dirname "$(realpath "$0" 2>/dev/null || echo "$HOME/.agents/skills/spec-workflow")")")

# 检查技能包是否存在
if [ ! -d "$PACKAGE_DIR/skills" ]; then
    echo "❌ 找不到技能包: $PACKAGE_DIR/skills"
    echo "   请确认已正确安装 spec-workflow 技能包"
    exit 1
fi

# 复制所有子技能（递归 per-skill 子目录 + INSTALL.md 在顶层）
for skill_dir in "$PACKAGE_DIR/skills/"*/; do
    skill_name=$(basename "$skill_dir")
    [ "$skill_name" = "_lib" ] && continue
    [ "$skill_name" = "__pycache__" ] && continue
    if [ -d "$skill_dir" ]; then
        mkdir -p "$SKILLS_DIR/skills/$skill_name/scripts" "$SKILLS_DIR/skills/$skill_name/references"
        [ -f "$skill_dir/SKILL.md" ] && cp -f "$skill_dir/SKILL.md" "$SKILLS_DIR/skills/$skill_name/"
        if [ -d "$skill_dir/scripts" ]; then
            cp -rf "$skill_dir/scripts/." "$SKILLS_DIR/skills/$skill_name/scripts/"
        fi
        if [ -d "$skill_dir/references" ]; then
            cp -rf "$skill_dir/references/." "$SKILLS_DIR/skills/$skill_name/references/"
        fi
    fi
done
# 顶层 INSTALL.md 单独复制（保持在 skills/ 顶层，不放入子目录）
cp -f "$PACKAGE_DIR/skills/INSTALL.md" "$SKILLS_DIR/skills/"

# 复制 skills/_lib/ 运行时所需 Python 模块、schemas 和 bash helper
# 这样 feature.md (depends-on: [iteration, deps_output])、rddf-session.md (depends-on: [rddf_session])
# 以及 status.md (source _lib/status_helpers.sh)、guide-ship.md (source _lib/archive.sh) 等
# 在目标项目里也能正常 import / source
if [ -d "$PACKAGE_DIR/skills/_lib" ]; then
    mkdir -p "$SKILLS_DIR/skills/_lib/schemas"
    find "$PACKAGE_DIR/skills/_lib" \
        -type d \( -name __pycache__ -o -name plugins -o -name schedulers \) -prune \
        -o -type f \( -name '*.py' -o -name '*.json' -o -name '*.sh' \) -print 2>/dev/null | while read -r src; do
        rel="${src#$PACKAGE_DIR/}"
        mkdir -p "$SKILLS_DIR/$(dirname "$rel")"
        cp -f "$src" "$SKILLS_DIR/$rel"
    done
fi

# Python sys.path 提示：target 项目的 root 需要在 sys.path 才能 `from skills._lib.X import Y`
# 在 AI 助手环境中通常已经满足（conftest.py 自动加）; 在 npx 直接调用场景需用户配置
cat >> "$SKILLS_DIR/INSTALL_NOTES.txt" << 'NOTES'
skills/ 已被复制到本项目 .opencode/skills/spec-workflow/ 下。

要让 skills/<name>/SKILL.md 中的 Python depends-on 模块能 import，需要：
1. 确保本项目根目录在 Python sys.path 中（多数 AI 编程助手自动处理）
2. skills/ 目录下存在 __init__.py 文件（已包含在本次安装中）

如果运行 skill 报 ImportError，请检查上述两点。
NOTES

echo "✅ 子技能已复制:"
ls -1 "$SKILLS_DIR/skills/"
echo "✅ _lib 模块已复制（49 .py + 7 schema + 6 bash helper）:"
find "$SKILLS_DIR/skills/_lib" -type f \( -name '*.py' -o -name '*.json' -o -name '*.sh' \) | wc -l
```

### 步骤 4：创建包元数据

```bash
# 创建 package.json（如果不存在）
# 版本与技能列表从源 PACKAGE_DIR/package.json 动态派生,保证与上游一致
if [ ! -f "$SKILLS_DIR/package.json" ]; then
    if command -v python3 >/dev/null 2>&1 && [ -f "$PACKAGE_DIR/package.json" ]; then
        # 使用 python3 安全地提取 version 与 skills 数组(避免 jq 依赖)
        PKG_VERSION=$(python3 -c "import json,sys;print(json.load(open('$PACKAGE_DIR/package.json'))['version'])" 2>/dev/null || echo "2.0.0-beta")
        # 动态推导 skills 列表（避免硬编码漂移）
        PKG_SKILLS=$(python3 -c "import json;print(','.join(['\"'+s+'\"' for s in json.load(open('$PACKAGE_DIR/package.json'))['skills']]))" 2>/dev/null)
    else
        PKG_VERSION="2.0.0-beta"
        # 磁盘推导 fallback：从 skills/*/SKILL.md + skills/INSTALL.md 动态生成 skill 列表（避免与 package.json 漂移）
        # Phase 1+：技能以 per-skill 子目录形式存在；INSTALL.md 仍在顶层
        PKG_SKILLS=$(find "$PACKAGE_DIR/skills/" -maxdepth 2 -name 'SKILL.md' 2>/dev/null \
            | while read -r f; do basename "$(dirname "$f")"; done \
            | sort -u \
            | awk 'BEGIN{ORS=""; printf "\""}{printf "\"" $0 "\","}' \
            | sed 's/,$//')
    fi
    # 当 PKG_SKILLS 仍为空（python3 与 source 都不可用）的兜底
    if [ -z "$PKG_SKILLS" ]; then
        PKG_SKILLS='"INSTALL"'
    fi
    cat > "$SKILLS_DIR/package.json" << EOF
{
  "name": "spec-workflow",
  "version": "${PKG_VERSION}",
  "description": "Spec Workflow - OpenSpec \u5de5\u4f5c\u6d41\u6280\u80fd\u5305\uff08propose\u2192plan\u2192execute\u2192status\u2192archive\uff09",
  "author": "sisyphus",
  "skills": [${PKG_SKILLS}]
}
EOF
    echo "✅ package.json 已创建 (version: ${PKG_VERSION})"
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

# 复制技能（递归 per-skill 子目录 + INSTALL.md 在顶层）
if [ -d "$PACKAGE_DIR/skills" ]; then
    for skill_dir in "$PACKAGE_DIR/skills/"*/; do
        skill_name=$(basename "$skill_dir")
        [ "$skill_name" = "_lib" ] && continue
        [ "$skill_name" = "__pycache__" ] && continue
        if [ -d "$skill_dir" ]; then
            mkdir -p "$PROJECT_ROOT/.opencode/skills/spec-workflow/skills/$skill_name/scripts" \
                     "$PROJECT_ROOT/.opencode/skills/spec-workflow/skills/$skill_name/references"
            [ -f "$skill_dir/SKILL.md" ] && cp -f "$skill_dir/SKILL.md" "$PROJECT_ROOT/.opencode/skills/spec-workflow/skills/$skill_name/"
        fi
    done
    cp -f "$PACKAGE_DIR/skills/INSTALL.md" "$PROJECT_ROOT/.opencode/skills/spec-workflow/skills/"
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
echo "下一步: 重新加载 session 或执行 skill_use(\"guide\")"
```

## 安装脚本用法（其他 AI 助手）

其他 AI 编程助手可以使用以下命令安装：

```bash
# 方式 1: 直接复制
cp -r ~/.agents/skills/spec-workflow/skills /your/project/.opencode/skills/spec-workflow/

# 方式 2: 使用安装脚本
curl -sL -o /tmp/install-spec-workflow.sh <raw-url>/install-spec-workflow.sh
# Optional: verify SHA256 checksum here (security)
bash /tmp/install-spec-workflow.sh
rm -f /tmp/install-spec-workflow.sh

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
| 版本 | 2.0.0-beta |
| 作者 | sisyphus |

## npm test vs pytest

> ⚠️ **重要 trap（反漂移提示）**：npm test 只跑 bats tests/，**不会**捕获 Python 测试失败。
>
> 本项目 Python 测试数量（pytest tests/ -q）远多于 bats，**改完任何 Python 代码后必须显式**：
>
> ```bash
> python3 -m pytest tests/unit/ -q --tb=short          # ~46 个 unit 文件
> python3 -m pytest tests/integration/ -q --tb=short   # ~9 个 Python integration
> ```
>
> 完整 CI 顺序（见 .github/workflows/test.yml）：安装 deps → **断言质量门控**（grep -rn "assert.*or True|assert True" tests/ 命中即 FAIL）→ Python unit → Python integration → bats smoke → bats static 子集 → bats git-worktree 子集。
>
> 任何 assert ... or True / assert True 写法会立即触发 CI 失败（恒真断言拦截）。