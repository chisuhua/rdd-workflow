---
name: INSTALL
description: 安装 RDD Workflow 技能——支持全局安装（~/.agents/skills/，跨项目可用）和项目安装（.opencode/skills/rdd-workflow/）。全局安装后从 1 个顶层 INSTALL.md 加 22 个 per-skill 子目录复制全部 23 个子技能到目标位置；自动安装 Python 依赖和 rddf CLI。
alias: install
version: "3.0"
author: sisyphus
---

# RDD Workflow 安装程序

本技能将 RDD Workflow 的 20 个子技能安装到当前项目目录。

## 包含的子技能

安装后可用以下技能：

| 技能名称 | 用途 |
|---------|------|
| `guide` | 推荐器入口（扫描项目状态，建议下一步） |
| `guide-arch` | Arch 阶段状态机（setup → roadmap → arch-done） |
| `guide-plan` | Plan 阶段状态机（scan → propose → deps → plan-done） |
| `guide-ship` | Ship 阶段状态机（plan → execute → archive → cleanup） |
| `propose` | 变更提案生成（被 guide-plan 调用） |
| `execute` | 实施计划执行（被 guide-ship 调用） |
| `status` | 状态查看和归档（被 guide-ship 调用或独立使用） |
| `feature` | Feature 管理视图（summary/graph/status/order） |
| `rddf-session` | 跨 OpenCode session 恢复（ADR-0017） |
| `roadmap` | 路线图管理（被 guide-arch 调用） |
| `deps` | 依赖分析（被 guide-plan 调用） |
| `rdd-workflow-writing-plans` | 实施计划生成器（v2.0 自包含 TDD 5 步结构） |
| `rdd-env-check` | 环境健康检查（openspec/git/build + cache 快照，被 4 个 phase 调用） |
| `rdd-doctor` | 手动触发的只读诊断工具（5 类结构化文件 schema/格式校验，输出分级报告） |
| `rdd-hub-bootstrap` | Hub 仓库一键初始化（目录结构 + Projects V2 看板 + CI 工作流模板，ADR-0030 Step 1） |
| `add-improve` | 交互式创建 rdd-workflow 改进提案（注册到 proposal-suggestions.md） |
| `openspec-gate` | Stage 守卫（未关联 active change 时阻止 commit） |
| `rdd-workflow-brainstorm` | 提案头脑风暴（5 段格式输出至 .rddf/improvements/） |
| `INSTALL` | 当前技能（顶层安装入口，被全局/项目安装流程使用） |
| `guide-design` | Design 阶段状态机（v2.1 新增；提案审查 + 内容审查） |
| `contract-check` | Spoke 本地实现 vs Hub OpenAPI contract 一致性校验（Breaking-Change 阻断 CI） |
| `cross-repo-protocol` | Hub-Spoke 联邦 MCP 客户端（4 Hub 工具 + REST fallback + trace logging） |
| `spoke-system-prompt-injection` | Hub-Spoke 协议注入 AI 助手配置（Cursor/Cline/Continue/Copilot/Claude Code） |
| `ac-verifier` | AI 语义验证 OpenSpec change 验收标准（archive 前自动调用） |

## 两种安装模式

| 模式 | 命令 | 目标 | 适用场景 |
|------|------|------|---------|
| **全局** | `bash install.sh --global` | `~/.agents/skills/` | 多个项目共享，OpenCode 自动发现 |
| **项目** | `skill_use("INSTALL")` 或 `bash install.sh` | `.opencode/skills/rdd-workflow/` | 单个项目隔离安装 |

### 全局安装（推荐）

```bash
cd /path/to/rdd-workflow-repo
bash install.sh --global
```

执行后：
- 12 个子技能 symlink 到 `~/.agents/skills/` → **所有项目**的 OpenCode 自动发现
- Python 依赖自动安装 (`pip install --user -r requirements.txt`)
- `_lib/` 路径写入 Python `.pth` 文件 → 任何项目 `from skills._lib.xxx import yyy` 可用
- `rddf` CLI 命令创建到 `~/.local/bin/rddf` → 终端直接运行 `rddf status`

全局安装后，在任何项目目录下：
```
skill_use("guide")       # 推荐器入口
skill_use("guide-arch")  # Arch 阶段
rddf status              # 查看工作流状态
```

> **注意**：Symlink 指向源码仓库，技能变更即时生效。如需固定版本，使用 `cp -r` 手动复制。

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
SKILLS_DIR="$PROJECT_ROOT/.opencode/skills/rdd-workflow"

mkdir -p "$SKILLS_DIR"

# 创建子技能目录
mkdir -p "$SKILLS_DIR/skills"

echo "✅ 技能目录已创建: $SKILLS_DIR"
```

### 步骤 3：复制子技能

```bash
# 获取技能包位置（兼容 macOS/BSD）
PACKAGE_DIR=$(dirname "$(dirname "$(realpath "$0" 2>/dev/null || echo "$HOME/.agents/skills/rdd-workflow")")")

# 检查技能包是否存在
if [ ! -d "$PACKAGE_DIR/skills" ]; then
    echo "❌ 找不到技能包: $PACKAGE_DIR/skills"
    echo "   请确认已正确安装 rdd-workflow 技能包"
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

# 复制 _lib/ 运行时所需 Python 模块、schemas 和 bash helper
# 这样 feature.md (depends-on: [iteration, deps_output])、rddf-session.md (depends-on: [rddf_session])
# 以及 status.md (source _lib/status_helpers.sh)、guide-ship.md (source _lib/archive.sh) 等
# 在目标项目里也能正常 import / source
if [ -d "$PACKAGE_DIR/skills/_lib" ]; then
    mkdir -p "$SKILLS_DIR/_lib/schemas"
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
skills/ 已被复制到本项目 .opencode/skills/rdd-workflow/ 下。

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
  "name": "rdd-workflow",
  "version": "${PKG_VERSION}",
  "description": "RDD Workflow - OpenSpec \u5de5\u4f5c\u6d41\u6280\u80fd\u5305\uff08propose\u2192plan\u2192execute\u2192status\u2192archive\uff09",
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
cat > "$PROJECT_ROOT/install-rdd-workflow.sh" << 'SCRIPT'
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
SCRIPT

chmod +x "$PROJECT_ROOT/install-rdd-workflow.sh"
echo "✅ 安装脚本已创建: $PROJECT_ROOT/install-rdd-workflow.sh"
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
# 全局安装（跨项目可用，推荐）
# 安装后 ~/.agents/skills/ 下每个子技能自动被 OpenCode 发现
bash ~/.agents/skills/rdd-workflow/install.sh --global

# 项目安装（单项目隔离）
# 方式 1: 使用安装脚本
bash ~/.agents/skills/rdd-workflow/install.sh /your/project

# 方式 2: 直接复制
cp -r ~/.agents/skills/rdd-workflow/skills /your/project/.opencode/skills/rdd-workflow/

# 方式 3: 使用安装脚本（旧方式）
bash install-rdd-workflow.sh

# 方式 4: Git 克隆
git clone <repo-url> /path/to/rdd-workflow && bash /path/to/rdd-workflow/install.sh --global
```

## 卸载

```bash
rm -rf "$PROJECT_ROOT/.opencode/skills/rdd-workflow"
rm -f "$PROJECT_ROOT/install-rdd-workflow.sh"
```

## 元信息

| 字段 | 值 |
|------|-----|
| 包名称 | rdd-workflow |
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
## 5. 项目设置检查

安装完成后,执行项目设置检查以确认 `.gitignore` 已正确配置:

```bash
source _lib/check_project_setup.sh
issues=$(check_project_setup "$(pwd)")
echo "$issues" | jq -r '.[] | "  \(if .status == "pass" then "✅" else "❌" end) \(.name): \(.detail)"'
```

检查项:`rddf_state_ignored` / `rddf_wt_ignored` / `rddf_plans_not_ignored` /
`openspec_cli_available` / `git_head_exists` / `large_untracked_dirs`。

无论结果如何,安装流程均不中断。如有 ❌,运行对应 `fix_command` 后重新执行。
